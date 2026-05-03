"""数据汇总 Agent - 合并技术面和基本面分析结果"""

import json
from typing import Optional
from pathlib import Path

from ..base import BaseAgent


class DataAggregator(BaseAgent):
    """数据汇总 Agent - 合并技术面 + 基本面分析结果"""

    name = "aggregator"
    role = "数据分析汇总师"

    def get_system_prompt(self) -> str:
        return """你是数据分析汇总师，负责合并技术面和基本面分析结果。

你需要：
1. 综合技术面和基本面的评分
2. 计算综合评分
3. 提取买入论据（支持买入的理由）
4. 提取卖出论据（支持卖出/观望的理由）
5. 生成分析摘要

请用 JSON 格式返回：
{
    "combined_score": 0-100,
    "tech_weight": 0.4,
    "fund_weight": 0.6,
    "buy_arguments": ["买入理由1", "买入理由2", ...],
    "sell_arguments": ["卖出理由1", "卖出理由2", ...],
    "summary": "分析摘要",
    "recommendation": "buy/sell/hold",
    "confidence": 0.0-1.0
}"""

    def get_user_prompt(self, context: dict) -> str:
        fundamentals = context.get("fundamentals", {})
        technical = context.get("technical", {})

        return f"""请汇总以下分析结果：

基本面分析：
- 评分：{fundamentals.get('score', 'N/A')}
- 优势：{json.dumps(fundamentals.get('strengths', []), ensure_ascii=False)}
- 劣势：{json.dumps(fundamentals.get('weaknesses', []), ensure_ascii=False)}

技术面分析：
- 评分：{technical.get('score', 'N/A')}
- 趋势：{technical.get('trend', 'N/A')}
- 买入信号：{technical.get('buy_signal', False)}
- 卖出信号：{technical.get('sell_signal', False)}
- 信号列表：{json.dumps(technical.get('signals', []), ensure_ascii=False)}

请生成综合分析摘要。"""

    def run(self, context: dict) -> dict:
        """执行汇总分析"""
        # 如果有 LLM，使用 LLM 分析
        if self.llm:
            response = super().run(context)
            try:
                result = json.loads(response)
                return result
            except json.JSONDecodeError:
                pass

        # 否则使用规则计算
        fundamentals = context.get("fundamentals", {})
        technical = context.get("technical", {})

        # 计算综合评分
        fund_score = fundamentals.get("score", 50)
        tech_score = technical.get("score", 50)

        # 基本面权重更高
        combined_score = fund_score * 0.6 + tech_score * 0.4

        # 提取论据
        buy_arguments = []
        sell_arguments = []

        # 基本面论据
        for strength in fundamentals.get("strengths", []):
            buy_arguments.append(f"[基本面] {strength}")
        for weakness in fundamentals.get("weaknesses", []):
            sell_arguments.append(f"[基本面] {weakness}")

        # 技术面论据
        if technical.get("buy_signal"):
            buy_arguments.append("[技术面] 出现买入信号")
        if technical.get("sell_signal"):
            sell_arguments.append("[技术面] 出现卖出信号")
        for signal in technical.get("signals", []):
            if "上涨" in signal or "突破" in signal or "金叉" in signal:
                buy_arguments.append(f"[技术面] {signal}")
            elif "下跌" in signal or "破位" in signal or "死叉" in signal:
                sell_arguments.append(f"[技术面] {signal}")

        # 生成推荐
        if combined_score >= 70:
            recommendation = "buy"
            confidence = 0.7
        elif combined_score >= 50:
            recommendation = "hold"
            confidence = 0.5
        else:
            recommendation = "sell"
            confidence = 0.6

        return {
            "combined_score": combined_score,
            "tech_weight": 0.4,
            "fund_weight": 0.6,
            "buy_arguments": buy_arguments,
            "sell_arguments": sell_arguments,
            "summary": f"综合评分 {combined_score:.1f}，建议 {recommendation}",
            "recommendation": recommendation,
            "confidence": confidence
        }


def aggregator_node(state: dict, log_folder: Optional[Path] = None) -> dict:
    """汇总节点函数"""
    from trading_agent.core.llm import get_llm
    from trading_agent.core.logger import logger
    from trading_agent.scheduler.workspace_manager import write_log

    if log_folder:
        write_log(log_folder, "=== Node: 数据汇总 [开始] ===")

    logger.info("汇总分析结果...")

    llm = get_llm()
    aggregator = DataAggregator(llm)
    result = aggregator.run(state)

    if log_folder:
        write_log(log_folder, f"综合评分: {result['combined_score']}")
        write_log(log_folder, f"买入论据: {len(result['buy_arguments'])} 条")
        write_log(log_folder, f"卖出论据: {len(result['sell_arguments'])} 条")
        write_log(log_folder, f"建议: {result['recommendation']}")
        write_log(log_folder, "=== Node: 数据汇总 [结束] ===")

    return {
        "analysis_summary": result,
        "logs": state.get("logs", []) + ["数据汇总完成"]
    }