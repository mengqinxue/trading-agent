# -*- coding: utf-8 -*-
"""回测策略反思Agent

使用AI评估策略表现，提出改进建议。
"""

import json
import logging
from typing import Any, Dict, List, Optional

from src.core.llm import get_llm

logger = logging.getLogger(__name__)


# Reflection提示词
REFLECTION_PROMPT = """你是一个量化交易策略评估专家。请根据以下回测数据评估策略表现。

## 策略信息
- 策略描述：{description}
- 参数：{params_json}

## 回测结果
- 总收益率：{total_return}%
- 年化收益：{annual_return}%
- 最大回撤：{max_drawdown}%
- 夏普比率：{sharpe_ratio}
- 总交易次数：{total_trades}
- 胜率：{win_rate}%
- 盈亏比：{profit_ratio}
- 回测天数：{total_days}天

## 交易记录摘要
{trades_summary}

请从以下角度评估：

1. **策略优势**：列举2-4个策略的优点（如趋势捕捉能力、风险控制等）

2. **策略劣势**：列举2-4个策略的缺点（如止损过于敏感、未考虑XX等）

3. **改进建议**：提出3-5个具体可执行的改进建议

4. **风险提示**：列举2-3个使用该策略需要注意的风险

请以JSON格式返回：
{
    "strengths": ["优势1", "优势2"],
    "weaknesses": ["劣势1", "劣势2"],
    "improvements": ["建议1", "建议2", "建议3"],
    "risk_warnings": ["风险1", "风险2"]
}
"""


def reflect_on_strategy(
    description: str,
    params: Dict[str, Any],
    summary: Dict[str, Any],
    trades: List[Dict],
) -> Dict[str, List[str]]:
    """反思策略表现

    Args:
        description: 策略描述
        params: 策略参数
        summary: 回测结果摘要
        trades: 交易记录

    Returns:
        {
            'strengths': ['优势1', '优势2'],
            'weaknesses': ['劣势1', '劣势2'],
            'improvements': ['建议1', '建议2'],
            'risk_warnings': ['风险1', '风险2']
        }
    """
    # 提取关键数据
    total_return = summary.get("total_return", 0)
    annual_return = summary.get("annual_return", 0)
    max_drawdown = summary.get("max_drawdown", 0)
    sharpe_ratio = summary.get("sharpe_ratio", 0)
    total_trades = summary.get("total_trades", 0)
    win_rate = summary.get("win_rate", 0)
    profit_ratio = summary.get("profit_ratio", 0)
    total_days = summary.get("total_days", 0)

    # 生成交易摘要（只取前20笔）
    trades_summary = _generate_trades_summary(trades[:20])

    # 构建提示词
    prompt = REFLECTION_PROMPT.format(
        description=description,
        params_json=json.dumps(params, ensure_ascii=False),
        total_return=total_return,
        annual_return=annual_return,
        max_drawdown=max_drawdown,
        sharpe_ratio=sharpe_ratio,
        total_trades=total_trades,
        win_rate=win_rate,
        profit_ratio=profit_ratio,
        total_days=total_days,
        trades_summary=trades_summary,
    )

    # 调用LLM
    llm = get_llm(temperature=0.7)

    try:
        response = llm.invoke(prompt)
        content = response.content
        logger.info(f"[Reflection] LLM响应: {content[:200]}...")

        # 提取JSON - 多种策略
        import re

        # 策略1: 从代码块提取
        code_block_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", content)
        if code_block_match:
            json_str = code_block_match.group(1).strip()
            try:
                result = json.loads(json_str)
                logger.info("[Reflection] 从代码块解析成功")
                return result
            except json.JSONDecodeError:
                pass

        # 策略2: 找到包含 strengths 键的JSON对象
        # 使用更精确的模式匹配
        patterns = [
            r'\{\s*"strengths"\s*:\s*\[[^\]]*\]\s*,?\s*"weaknesses"\s*:\s*\[[^\]]*\]\s*,?\s*"improvements"\s*:\s*\[[^\]]*\]\s*,?\s*"risk_warnings"\s*:\s*\[[^\]]*\]\s*\}',
            r'\{\s*"strengths"\s*:\s*\[[\s\S]*?\]\s*,\s*"weaknesses"\s*:\s*\[[\s\S]*?\]\s*,\s*"improvements"\s*:\s*\[[\s\S]*?\]\s*,\s*"risk_warnings"\s*:\s*\[[\s\S]*?\]\s*\}',
        ]

        for pattern in patterns:
            match = re.search(pattern, content)
            if match:
                try:
                    result = json.loads(match.group(0))
                    logger.info("[Reflection] JSON模式匹配成功")
                    return result
                except json.JSONDecodeError:
                    continue

        # 策略3: 手动构建JSON（从文本中提取列表）
        strengths = re.findall(r'"strengths"\s*:\s*\[([^\]]*)\]', content)
        weaknesses = re.findall(r'"weaknesses"\s*:\s*\[([^\]]*)\]', content)
        improvements = re.findall(r'"improvements"\s*:\s*\[([^\]]*)\]', content)
        risk_warnings = re.findall(r'"risk_warnings"\s*:\s*\[([^\]]*)\]', content)

        if strengths and weaknesses and improvements and risk_warnings:
            # 尝试解析每个列表
            def parse_list(lst_str):
                items = re.findall(r'"([^"]*)"', lst_str)
                return items

            result = {
                "strengths": parse_list(strengths[0]),
                "weaknesses": parse_list(weaknesses[0]),
                "improvements": parse_list(improvements[0]),
                "risk_warnings": parse_list(risk_warnings[0]),
            }
            logger.info("[Reflection] 手动提取列表成功")
            return result

        # 解析失败，返回默认
        logger.warning("[Reflection] 无法提取有效JSON，使用默认反思")
        logger.warning(f"[Reflection] 响应内容: {content}")
        return _default_reflection(summary)

    except Exception as e:
        logger.error(f"[Reflection] AI调用失败: {e}")
        return _default_reflection(summary)


def _generate_trades_summary(trades: List[Dict]) -> str:
    """生成交易记录摘要"""
    if not trades:
        return "无交易记录"

    lines = []
    buy_count = 0
    sell_count = 0
    win_count = 0
    loss_count = 0

    for t in trades:
        if t.get("trade_type") == "buy":
            buy_count += 1
        else:
            sell_count += 1
            if t.get("profit_pct", 0) > 0:
                win_count += 1
            else:
                loss_count += 1

    lines.append(f"- 买入次数：{buy_count}")
    lines.append(f"- 卖出次数：{sell_count}")
    lines.append(f"- 盈利次数：{win_count}")
    lines.append(f"- 亏损次数：{loss_count}")

    # 典型交易示例
    if trades:
        lines.append("\n典型交易示例：")
        for t in trades[:5]:
            if t.get("trade_type") == "buy":
                lines.append(f"- 买入 {t.get('code')} {t.get('name')} @ {t.get('price', 0):.2f}元")
            else:
                profit_pct = t.get("profit_pct", 0)
                lines.append(f"- 卖出 {t.get('code')} {t.get('name')} 盈亏{profit_pct:+.2f}%")

    return "\n".join(lines)


def _default_reflection(summary: Dict) -> Dict[str, List[str]]:
    """生成默认反思（当AI调用失败时）"""
    total_return = summary.get("total_return", 0)
    win_rate = summary.get("win_rate", 0)

    strengths = []
    weaknesses = []
    improvements = []
    risk_warnings = []

    # 根据表现推断
    if total_return > 0:
        strengths.append("策略整体盈利，具备一定的获利能力")
    else:
        weaknesses.append("策略整体亏损，需要优化参数或逻辑")

    if win_rate > 40:
        strengths.append(f"胜率{win_rate:.1f}%处于合理范围")
    else:
        weaknesses.append(f"胜率{win_rate:.1f}%偏低，选股逻辑需改进")

    if summary.get("max_drawdown", 0) > 30:
        weaknesses.append("最大回撤较高，风险控制不足")
        improvements.append("建议降低单笔仓位，分散风险")

    # 默认建议
    improvements.append("建议测试不同止盈止损参数组合")
    improvements.append("建议增加市场趋势确认条件")
    improvements.append("建议过滤高风险股票（ST、次新股等）")

    # 默认风险
    risk_warnings.append("历史回测不代表未来表现")
    risk_warnings.append("实盘交易需考虑流动性风险")
    risk_warnings.append("需密切关注市场状态变化")

    return {
        "strengths": strengths,
        "weaknesses": weaknesses,
        "improvements": improvements,
        "risk_warnings": risk_warnings,
    }