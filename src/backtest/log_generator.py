# -*- coding: utf-8 -*-
"""回测策略日志生成器

生成完整的策略回测日志，包含：
- 策略描述
- 执行日志（交易记录）
- 月度结算
- 最终汇总
- Reflection反思
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .monthly_settlement import calculate_monthly_settlements, format_settlement_for_log

logger = logging.getLogger(__name__)


def generate_strategy_log(
    task_id: str,
    description: str,
    params: Dict[str, Any],
    trades: List[Dict],
    equity_curve: List[Dict],
    summary: Dict[str, Any],
    reflection: Optional[Dict[str, Any]] = None,
) -> str:
    """生成完整的策略日志

    Args:
        task_id: 任务ID
        description: 用户输入的策略描述
        params: 策略参数
        trades: 交易记录列表
        equity_curve: 净值曲线
        summary: 回测结果摘要
        reflection: AI反思结果（可选）

    Returns:
        Markdown格式的策略日志
    """
    lines = []

    # 标题
    lines.append("# 回测策略报告")
    lines.append("")
    lines.append(f"**任务ID**: {task_id[:8]}")
    lines.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # 1. 策略描述
    lines.append("## 策略描述")
    lines.append("")
    lines.append(f"**用户输入**：{description}")
    lines.append("")
    lines.append("**解析参数**：")
    lines.append("")

    # 参数表格
    param_items = [
        ("起始日期", params.get("start_date", "N/A")),
        ("结束日期", params.get("end_date", "N/A")),
        ("初始资金", f"{params.get('initial_capital', 100000):,.0f} 元"),
        ("止盈阈值", f"{params.get('profit_target', 8)}%"),
        ("止损阈值", f"{params.get('stop_loss', -3)}%"),
        ("最大持仓", f"{params.get('max_positions', 5)}只"),
        ("买入频率", params.get("buy_frequency", "每周")),
        ("每周期买入限制", f"{params.get('buy_limit', 3)}只"),
        ("买入比例", f"{params.get('buy_ratio', 0.1)*100}%"),
        ("市场过滤", params.get("market_filter", "无")),
        ("排除ST股", "是" if params.get("exclude_st", True) else "否"),
        ("排除次新股", f"上市<{params.get('min_list_days', 60)}天"),
    ]

    for name, value in param_items:
        lines.append(f"- {name}：{value}")

    lines.append("")
    lines.append("---")
    lines.append("")

    # 2. 执行日志
    lines.append("## 执行日志")
    lines.append("")
    lines.append("### 交易记录")
    lines.append("")

    # 格式化每笔交易
    for trade in trades:
        lines.append(_format_trade_for_log(trade))

    lines.append("---")
    lines.append("")

    # 3. 月度结算
    lines.append("## 月度结算")
    lines.append("")

    settlements = calculate_monthly_settlements(
        trades=trades,
        equity_curve=equity_curve,
        start_date=params.get("start_date", "2020-01-01"),
        end_date=params.get("end_date", datetime.now().strftime("%Y-%m-%d")),
    )

    for s in settlements:
        lines.append(format_settlement_for_log(s))

    lines.append("---")
    lines.append("")

    # 4. 最终汇总
    lines.append("## 最终汇总")
    lines.append("")
    lines.append("| 指标 | 数值 |")
    lines.append("|------|------|")

    summary_items = [
        ("总收益率", f"{summary.get('total_return', 0):+.2f}%"),
        ("年化收益", f"{summary.get('annual_return', 0):+.2f}%"),
        ("最大回撤", f"{summary.get('max_drawdown', 0):.2f}%"),
        ("夏普比率", f"{summary.get('sharpe_ratio', 0):.2f}"),
        ("总交易次数", f"{summary.get('total_trades', 0)}"),
        ("胜率", f"{summary.get('win_rate', 0):.2f}%"),
        ("盈亏比", f"{summary.get('profit_ratio', 0):.2f}"),
        ("回测天数", f"{summary.get('total_days', 0)}"),
    ]

    for name, value in summary_items:
        lines.append(f"| {name} | {value} |")

    lines.append("")
    lines.append("---")
    lines.append("")

    # 5. Reflection反思
    if reflection:
        lines.append("## 策略反思 (Reflection)")
        lines.append("")

        # 优势
        if reflection.get("strengths"):
            lines.append("### 策略优势")
            lines.append("")
            for i, s in enumerate(reflection["strengths"], 1):
                lines.append(f"{i}. {s}")
            lines.append("")

        # 劣势
        if reflection.get("weaknesses"):
            lines.append("### 策略劣势")
            lines.append("")
            for i, w in enumerate(reflection["weaknesses"], 1):
                lines.append(f"{i}. {w}")
            lines.append("")

        # 改进建议
        if reflection.get("improvements"):
            lines.append("### 改进建议")
            lines.append("")
            for i, imp in enumerate(reflection["improvements"], 1):
                lines.append(f"{i}. {imp}")
            lines.append("")

        # 风险提示
        if reflection.get("risk_warnings"):
            lines.append("### 风险提示")
            lines.append("")
            for i, r in enumerate(reflection["risk_warnings"], 1):
                lines.append(f"{i}. {r}")
            lines.append("")

    else:
        lines.append("## 策略反思 (Reflection)")
        lines.append("")
        lines.append("*Reflection将在任务完成后生成...*")
        lines.append("")

    return "\n".join(lines)


def _format_trade_for_log(trade: Dict) -> str:
    """格式化单笔交易为日志文本"""
    lines = []

    trade_type = trade.get("trade_type", "buy")
    date = trade.get("date", "N/A")
    code = trade.get("code", "N/A")
    name = trade.get("name", "N/A")
    price = trade.get("price", 0)
    shares = trade.get("shares", 0)
    amount = trade.get("amount", 0)
    reason = trade.get("reason", "")

    if trade_type == "buy":
        lines.append(f"#### {date} 买入")
        lines.append(f"- 股票：{code} {name}")
        lines.append(f"- 价格：{price:.2f} 元")
        lines.append(f"- 股数：{shares}股")
        lines.append(f"- 金额：{amount:,.0f} 元")
        if reason:
            lines.append(f"- 原因：{reason}")
    else:
        # 卖出
        profit_pct = trade.get("profit_pct", 0)
        profit_amount = trade.get("profit_amount", 0)

        lines.append(f"#### {date} 卖出")
        lines.append(f"- 股票：{code} {name}")
        lines.append(f"- 价格：{price:.2f} 元")
        lines.append(f"- 收入：{amount:,.0f} 元")
        lines.append(f"- 盈亏：{profit_pct:+.2f}% ({profit_amount:+,.0f}元)")
        if reason:
            lines.append(f"- 原因：{reason}")

    lines.append("")
    return "\n".join(lines)


def save_strategy_log(log_content: str, folder_path: Path) -> Path:
    """保存策略日志到文件

    Args:
        log_content: 日志内容
        folder_path: 任务文件夹路径

    Returns:
        日志文件路径
    """
    log_file = folder_path / "strategy_log.md"
    log_file.write_text(log_content, encoding="utf-8")
    logger.info(f"[日志生成] 策略日志保存到: {log_file}")
    return log_file


def save_trades_csv(trades: List[Dict], folder_path: Path) -> Path:
    """保存交易记录CSV

    Args:
        trades: 交易记录
        folder_path: 任务文件夹

    Returns:
        CSV文件路径
    """
    if not trades:
        return None

    trades_file = folder_path / "trades.csv"

    # DataFrame格式
    df_data = []
    for t in trades:
        df_data.append({
            "日期": t.get("date", ""),
            "类型": t.get("trade_type", ""),
            "代码": t.get("code", ""),
            "名称": t.get("name", ""),
            "价格": t.get("price", 0),
            "股数": t.get("shares", 0),
            "金额": t.get("amount", 0),
            "盈亏%": t.get("profit_pct", 0) if t.get("trade_type") == "sell" else "",
            "盈亏金额": t.get("profit_amount", 0) if t.get("trade_type") == "sell" else "",
            "原因": t.get("reason", ""),
        })

    import pandas as pd
    df = pd.DataFrame(df_data)
    df.to_csv(trades_file, index=False, encoding="utf-8-sig")

    logger.info(f"[日志生成] 交易记录保存到: {trades_file}")
    return trades_file


def save_equity_csv(equity_curve: List[Dict], folder_path: Path) -> Path:
    """保存净值曲线CSV

    Args:
        equity_curve: 净值曲线
        folder_path: 任务文件夹

    Returns:
        CSV文件路径
    """
    if not equity_curve:
        return None

    equity_file = folder_path / "equity.csv"

    import pandas as pd
    df = pd.DataFrame(equity_curve)
    df.to_csv(equity_file, index=False, encoding="utf-8-sig")

    logger.info(f"[日志生成] 净值曲线保存到: {equity_file}")
    return equity_file