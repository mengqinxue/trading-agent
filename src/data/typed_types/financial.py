# -*- coding: utf-8 -*-
"""财务数据类型定义"""

from typing import TypedDict, Optional


class BalanceSheet(TypedDict):
    """资产负债表"""
    code: str
    report_date: str
    total_assets: float
    total_liabilities: float
    total_equity: float
    current_assets: float
    current_liabilities: float


class IncomeStatement(TypedDict):
    """利润表"""
    code: str
    report_date: str
    revenue: float
    operating_profit: float
    net_profit: float
    net_profit_parent: float
    gross_profit: float


class CashFlow(TypedDict):
    """现金流量表"""
    code: str
    report_date: str
    operating_cash_flow: float
    investing_cash_flow: float
    financing_cash_flow: float
    net_cash_flow: float


class FinancialIndicator(TypedDict):
    """财务指标"""
    code: str
    date: str
    roe: float
    roa: float
    gross_margin: float
    net_margin: float
    debt_ratio: float
    current_ratio: float
    quick_ratio: float


class PerformanceForecast(TypedDict):
    """业绩预告"""
    code: str
    report_date: str
    forecast_type: str
    forecast_change: str
    forecast_amount: str
    announcement_date: str