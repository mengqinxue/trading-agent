# -*- coding: utf-8 -*-
"""财务数据获取器 - Akshare 财务报表"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
import pandas as pd
import akshare as ak

logger = logging.getLogger(__name__)


class FinancialFetcher:
    """财务数据获取器"""

    def __init__(self):
        self.cache: Dict[str, Any] = {}

    def get_balance_sheet(self, code: str) -> List[Dict[str, Any]]:
        """获取资产负债表

        Args:
            code: 股票代码 (如 000001)

        Returns:
            资产负债表数据列表
        """
        try:
            # Akshare 资产负债表接口
            df = ak.stock_balance_sheet_by_report_em(symbol=code)

            if df is None or df.empty:
                logger.warning(f"未获取到资产负债表: {code}")
                return []

            # 转换格式
            data = []
            for _, row in df.iterrows():
                report_date = row.get("报告期")
                if report_date is None:
                    continue
                data.append({
                    "code": code,
                    "report_date": str(report_date),
                    "total_assets": float(row.get("资产总计", 0) or 0),
                    "total_liabilities": float(row.get("负债合计", 0) or 0),
                    "total_equity": float(row.get("所有者权益合计", 0) or 0),
                    "current_assets": float(row.get("流动资产合计", 0) or 0),
                    "current_liabilities": float(row.get("流动负债合计", 0) or 0),
                })

            logger.info(f"获取资产负债表: {code}, {len(data)} 条")
            return data

        except Exception as e:
            logger.error(f"获取资产负债表失败 {code}: {e}")
            return []

    def get_income_statement(self, code: str) -> List[Dict[str, Any]]:
        """获取利润表

        Args:
            code: 股票代码

        Returns:
            利润表数据列表
        """
        try:
            df = ak.stock_profit_sheet_by_report_em(symbol=code)

            if df is None or df.empty:
                return []

            data = []
            for _, row in df.iterrows():
                report_date = row.get("报告期")
                if report_date is None:
                    continue
                data.append({
                    "code": code,
                    "report_date": str(report_date),
                    "revenue": float(row.get("营业总收入", 0) or 0),
                    "operating_profit": float(row.get("营业利润", 0) or 0),
                    "net_profit": float(row.get("净利润", 0) or 0),
                    "net_profit_parent": float(row.get("归属于母公司所有者的净利润", 0) or 0),
                    "gross_profit": float(row.get("营业总收入-营业成本", 0) or 0),
                })

            logger.info(f"获取利润表: {code}, {len(data)} 条")
            return data

        except Exception as e:
            logger.error(f"获取利润表失败 {code}: {e}")
            return []

    def get_cash_flow(self, code: str) -> List[Dict[str, Any]]:
        """获取现金流量表

        Args:
            code: 股票代码

        Returns:
            现金流量表数据列表
        """
        try:
            df = ak.stock_cash_flow_sheet_by_report_em(symbol=code)

            if df is None or df.empty:
                return []

            data = []
            for _, row in df.iterrows():
                report_date = row.get("报告期")
                if report_date is None:
                    continue
                data.append({
                    "code": code,
                    "report_date": str(report_date),
                    "operating_cash_flow": float(row.get("经营活动产生的现金流量净额", 0) or 0),
                    "investing_cash_flow": float(row.get("投资活动产生的现金流量净额", 0) or 0),
                    "financing_cash_flow": float(row.get("筹资活动产生的现金流量净额", 0) or 0),
                    "net_cash_flow": float(row.get("现金及现金等价物净增加额", 0) or 0),
                })

            logger.info(f"获取现金流量表: {code}, {len(data)} 条")
            return data

        except Exception as e:
            logger.error(f"获取现金流量表失败 {code}: {e}")
            return []

    def get_financial_indicators(self, code: str) -> List[Dict[str, Any]]:
        """获取财务指标

        Args:
            code: 股票代码

        Returns:
            财务指标数据列表
        """
        try:
            df = ak.stock_financial_analysis_indicator(symbol=code)

            if df is None or df.empty:
                return []

            data = []
            for _, row in df.iterrows():
                date_val = row.get("日期")
                if date_val is None:
                    continue
                data.append({
                    "code": code,
                    "date": str(date_val),
                    "roe": float(row.get("净资产收益率", 0) or 0),
                    "roa": float(row.get("总资产净利率", 0) or 0),
                    "gross_margin": float(row.get("销售毛利率", 0) or 0),
                    "net_margin": float(row.get("销售净利率", 0) or 0),
                    "debt_ratio": float(row.get("资产负债率", 0) or 0),
                    "current_ratio": float(row.get("流动比率", 0) or 0),
                    "quick_ratio": float(row.get("速动比率", 0) or 0),
                })

            return data

        except Exception as e:
            logger.error(f"获取财务指标失败 {code}: {e}")
            return []

    def get_performance_forecast(self, code: str) -> List[Dict[str, Any]]:
        """获取业绩预告

        Args:
            code: 股票代码

        Returns:
            业绩预告数据
        """
        try:
            df = ak.stock_em_yjyg_df(symbol=code)

            if df is None or df.empty:
                return []

            data = []
            for _, row in df.iterrows():
                data.append({
                    "code": code,
                    "report_date": str(row.get("报告期", "")),
                    "forecast_type": row.get("预告类型", ""),
                    "forecast_change": row.get("预告净利润变动幅度", ""),
                    "forecast_amount": row.get("预告净利润", ""),
                    "announcement_date": str(row.get("公告日期", "")),
                })

            return data

        except Exception as e:
            logger.error(f"获取业绩预告失败 {code}: {e}")
            return []

    def get_all_financials(self, code: str) -> Dict[str, List[Dict]]:
        """获取完整财务数据

        Args:
            code: 股票代码

        Returns:
            {
                "balance_sheet": [...],
                "income_statement": [...],
                "cash_flow": [...],
                "indicators": [...]
            }
        """
        return {
            "balance_sheet": self.get_balance_sheet(code),
            "income_statement": self.get_income_statement(code),
            "cash_flow": self.get_cash_flow(code),
            "indicators": self.get_financial_indicators(code),
        }