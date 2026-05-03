# -*- coding: utf-8 -*-
"""
财务数据获取模块

获取股票财务报表数据：营收、利润、ROE、毛利率等。
"""

import logging
from typing import Dict, Any, Optional, List

import pandas as pd

from .types import safe_float
from .sources import random_sleep

logger = logging.getLogger(__name__)


# ============================================
# Akshare 财务数据获取
# ============================================

def _get_financial_akshare(code: str) -> Optional[Dict[str, Any]]:
    """使用 Akshare 获取财务指标"""
    try:
        import akshare as ak

        random_sleep()

        # 获取主要财务指标
        df = ak.stock_financial_analysis_indicator(symbol=code)

        if df is None or df.empty:
            return None

        # 取最新一期
        row = df.iloc[0]

        return {
            'code': code,
            'date': str(row.get('日期', '')),
            # 盈利能力
            'roe': safe_float(row.get('净资产收益率', 0)),
            'roa': safe_float(row.get('总资产收益率', 0)),
            'net_profit_margin': safe_float(row.get('销售净利率', 0)),
            'gross_profit_margin': safe_float(row.get('销售毛利率', 0)),
            # 营运能力
            'asset_turnover': safe_float(row.get('总资产周转率', 0)),
            # 偿债能力
            'debt_ratio': safe_float(row.get('资产负债率', 0)),
            'current_ratio': safe_float(row.get('流动比率', 0)),
            'quick_ratio': safe_float(row.get('速动比率', 0)),
            # 成长能力
            'revenue_growth': safe_float(row.get('营业收入增长率', 0)),
            'profit_growth': safe_float(row.get('净利润增长率', 0)),
        }

    except Exception as e:
        logger.warning(f"[财务Akshare] {code} 获取失败: {e}")
        return None


# ============================================
# Tushare 财务数据获取
# ============================================

def _get_financial_tushare(code: str) -> Optional[Dict[str, Any]]:
    """使用 Tushare 获取财务数据"""
    try:
        import tushare as ts

        # 需要配置 TUSHARE_TOKEN
        pro = ts.pro_api()

        # 获取财务指标
        df = pro.daily_basic(ts_code=f"{code}.SH", fields='pe_ttm,pb,ps_ttm,dv_ratio')

        if df is None or df.empty:
            # 尝试深市代码
            df = pro.daily_basic(ts_code=f"{code}.SZ", fields='pe_ttm,pb,ps_ttm,dv_ratio')

        if df is None or df.empty:
            return None

        row = df.iloc[0]

        return {
            'code': code,
            'pe_ttm': safe_float(row.get('pe_ttm', 0)),
            'pb': safe_float(row.get('pb', 0)),
            'ps_ttm': safe_float(row.get('ps_ttm', 0)),
            'dividend_ratio': safe_float(row.get('dv_ratio', 0)),
        }

    except Exception as e:
        logger.warning(f"[财务Tushare] {code} 获取失败: {e}")
        return None


# ============================================
# 统一接口
# ============================================

def get_financial_data(code: str) -> Dict[str, Any]:
    """
    获取财务数据

    Args:
        code: 股票代码

    Returns:
        财务指标字典
    """
    result = {'code': code}

    # Akshare 为首选
    data = _get_financial_akshare(code)
    if data:
        result.update(data)
        logger.info(f"[财务] {code} Akshare 获取成功")
        return result

    # Tushare 备选
    data = _get_financial_tushare(code)
    if data:
        result.update(data)
        logger.info(f"[财务] {code} Tushare 获取成功")
        return result

    logger.warning(f"[财务] {code} 所有数据源失败")
    return result


def get_financial_history(code: str, years: int = 3) -> List[Dict[str, Any]]:
    """
    获取历史财务数据

    Args:
        code: 股票代码
        years: 年数

    Returns:
        财务数据列表（按日期排序）
    """
    try:
        import akshare as ak

        random_sleep()

        df = ak.stock_financial_analysis_indicator(symbol=code)

        if df is None or df.empty:
            return []

        # 取最近 years 年数据
        records = []
        for _, row in df.head(years * 4).iterrows():  # 每年4期报告
            record = {
                'date': str(row.get('日期', '')),
                'roe': safe_float(row.get('净资产收益率', 0)),
                'net_profit_margin': safe_float(row.get('销售净利率', 0)),
                'gross_profit_margin': safe_float(row.get('销售毛利率', 0)),
                'revenue_growth': safe_float(row.get('营业收入增长率', 0)),
                'profit_growth': safe_float(row.get('净利润增长率', 0)),
            }
            records.append(record)

        return records

    except Exception as e:
        logger.warning(f"[财务历史] {code} 获取失败: {e}")
        return []


def get_financial_summary(code: str) -> str:
    """
    获取财务数据摘要

    Args:
        code: 股票代码

    Returns:
        摘要文本
    """
    data = get_financial_data(code)

    if not data or data.get('roe') is None:
        return "无法获取财务数据"

    parts = []

    # ROE 分析
    roe = data.get('roe', 0)
    if roe >= 15:
        parts.append(f"ROE {roe:.1f}%（优秀）")
    elif roe >= 10:
        parts.append(f"ROE {roe:.1f}%（良好）")
    elif roe >= 5:
        parts.append(f"ROE {roe:.1f}%（一般）")
    else:
        parts.append(f"ROE {roe:.1f}%（较差）")

    # 毛利率分析
    gross = data.get('gross_profit_margin', 0)
    if gross >= 40:
        parts.append(f"毛利率 {gross:.1f}%（高）")
    elif gross >= 20:
        parts.append(f"毛利率 {gross:.1f}%（中）")
    else:
        parts.append(f"毛利率 {gross:.1f}%（低）")

    # 负债率分析
    debt = data.get('debt_ratio', 0)
    if debt >= 70:
        parts.append(f"负债率 {debt:.1f}%（高风险）")
    elif debt >= 50:
        parts.append(f"负债率 {debt:.1f}%（中等）")
    else:
        parts.append(f"负债率 {debt:.1f}%（低风险）")

    return "，".join(parts)