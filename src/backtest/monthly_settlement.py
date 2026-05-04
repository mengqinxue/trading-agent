# -*- coding: utf-8 -*-
"""月度结算计算"""

from datetime import datetime
from typing import Any, Dict, List
from collections import defaultdict

import pandas as pd


def calculate_monthly_settlements(
    trades: List[Dict],
    equity_curve: List[Dict],
    start_date: str,
    end_date: str,
) -> List[Dict]:
    """计算月度结算

    Args:
        trades: 交易记录列表
        equity_curve: 净值曲线
        start_date: 回测起始日期
        end_date: 回测结束日期

    Returns:
        月度结算列表
    """
    # 按月分组交易
    monthly_trades = _group_trades_by_month(trades)

    # 按月分组净值
    monthly_equity = _group_equity_by_month(equity_curve)

    # 生成月度结算
    settlements = []
    months = _get_months_range(start_date, end_date)

    prev_capital = None
    for month in months:
        month_trades = monthly_trades.get(month, [])
        month_equity = monthly_equity.get(month, [])

        if not month_equity:
            continue

        # 月初月末净值
        month_start_equity = month_equity[0]["equity"] if month_equity else 0
        month_end_equity = month_equity[-1]["equity"] if month_equity else 0

        # 计算月度收益
        if prev_capital is None:
            prev_capital = month_start_equity

        month_return = (month_end_equity - prev_capital) / prev_capital * 100 if prev_capital > 0 else 0

        # 交易统计
        buy_trades = [t for t in month_trades if t["trade_type"] == "buy"]
        sell_trades = [t for t in month_trades if t["trade_type"] == "sell"]

        # 胜率计算（只算卖出）
        win_count = 0
        loss_count = 0
        for t in sell_trades:
            if "profit_pct" in t:
                if t["profit_pct"] > 0:
                    win_count += 1
                else:
                    loss_count += 1

        win_rate = win_count / (win_count + loss_count) * 100 if (win_count + loss_count) > 0 else 0

        # 月末持仓
        month_end_positions = month_equity[-1].get("positions", 0) if month_equity else 0

        settlement = {
            "month": month,
            "month_label": _format_month_label(month),
            "start_capital": prev_capital,
            "end_capital": month_end_equity,
            "month_return": month_return,
            "buy_count": len(buy_trades),
            "sell_count": len(sell_trades),
            "total_trades": len(month_trades),
            "win_count": win_count,
            "loss_count": loss_count,
            "win_rate": win_rate,
            "positions": month_end_positions,
        }

        settlements.append(settlement)
        prev_capital = month_end_equity

    return settlements


def _group_trades_by_month(trades: List[Dict]) -> Dict[str, List[Dict]]:
    """按月分组交易"""
    monthly = defaultdict(list)

    for trade in trades:
        date = trade.get("date", "")
        if date:
            month = date[:7]  # YYYY-MM
            monthly[month].append(trade)

    return monthly


def _group_equity_by_month(equity_curve: List[Dict]) -> Dict[str, List[Dict]]:
    """按月分组净值"""
    monthly = defaultdict(list)

    for eq in equity_curve:
        date = eq.get("date", "")
        if date:
            month = date[:7]
            monthly[month].append(eq)

    return monthly


def _get_months_range(start_date: str, end_date: str) -> List[str]:
    """获取日期范围内的月份列表"""
    start_dt = datetime.strptime(start_date[:7], "%Y-%m")
    end_dt = datetime.strptime(end_date[:7], "%Y-%m")

    months = []
    current = start_dt
    while current <= end_dt:
        months.append(current.strftime("%Y-%m"))
        # 下个月
        if current.month == 12:
            current = datetime(current.year + 1, 1, 1)
        else:
            current = datetime(current.year, current.month + 1, 1)

    return months


def _format_month_label(month: str) -> str:
    """格式化月份标签"""
    year, mon = month.split("-")
    return f"{year}年{int(mon)}月"


def format_settlement_for_log(settlement: Dict) -> str:
    """格式化月度结算为日志文本"""
    lines = []
    lines.append(f"### {settlement['month_label']}")
    lines.append(f"- 期初资金：{settlement['start_capital']:,.0f} 元")
    lines.append(f"- 期末资金：{settlement['end_capital']:,.0f} 元")
    lines.append(f"- 月度收益：{settlement['month_return']:+.2f}%")
    lines.append(f"- 买入次数：{settlement['buy_count']}次")
    lines.append(f"- 卖出次数：{settlement['sell_count']}次")
    lines.append(f"- 胜率：{settlement['win_rate']:.1f}%")
    lines.append(f"- 持仓：{settlement['positions']}只")
    lines.append("")

    return "\n".join(lines)