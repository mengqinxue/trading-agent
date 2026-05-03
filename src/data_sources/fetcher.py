# -*- coding: utf-8 -*-
"""
数据获取统一入口

整合所有数据类型的获取方法，提供简洁的对外接口。
"""

import logging
from typing import Optional, Dict, Any, List, Tuple

import pandas as pd

from .types import (
    RealtimeQuote, ChipDistribution, DailyBar,
    DragonTigerRecord, ResearchReport,
    DataSource, safe_float
)
from .trade_daily import get_daily, get_daily_as_bars
from .trade_realtime import get_realtime, get_realtime_as_dict, clear_realtime_cache
from .sources import CircuitBreaker, get_realtime_breaker, get_daily_breaker

logger = logging.getLogger(__name__)


# ============================================
# 筹码分布获取（待实现）
# ============================================

def get_chip_distribution(code: str) -> Optional[ChipDistribution]:
    """
    获取筹码分布数据

    Args:
        code: 股票代码

    Returns:
        ChipDistribution 或 None
    """
    # TODO: 实现筹码分布获取
    logger.warning(f"[筹码分布] {code} 暂未实现")
    return None


# ============================================
# 龙虎榜获取（待实现）
# ============================================

def get_dragon_tiger(code: str, days: int = 30) -> List[DragonTigerRecord]:
    """
    获取龙虎榜数据

    Args:
        code: 股票代码
        days: 查询天数

    Returns:
        龙虎榜记录列表
    """
    # TODO: 实现龙虎榜获取
    logger.warning(f"[龙虎榜] {code} 暂未实现")
    return []


# ============================================
# 研报评级获取（待实现）
# ============================================

def get_research_reports(code: str) -> List[ResearchReport]:
    """
    获取研报评级数据

    Args:
        code: 股票代码

    Returns:
        研报列表
    """
    # TODO: 实现研报评级获取
    logger.warning(f"[研报评级] {code} 暂未实现")
    return []


# ============================================
# 市场指数获取（待实现）
# ============================================

def get_main_indices() -> List[Dict[str, Any]]:
    """
    获取主要指数行情

    Returns:
        指数列表：上证、深证、创业板等
    """
    # TODO: 实现指数获取
    logger.warning("[指数] 暂未实现")
    return []


def get_market_stats() -> Dict[str, Any]:
    """
    获取市场涨跌统计

    Returns:
        涨跌家数、涨停跌停数等
    """
    # TODO: 实现市场统计获取
    logger.warning("[市场统计] 暂未实现")
    return {}


def get_sector_rankings(n: int = 10) -> Tuple[List[Dict], List[Dict]]:
    """
    获取板块涨跌榜

    Args:
        n: 返回板块数量

    Returns:
        (涨幅榜, 跌幅榜)
    """
    # TODO: 实现板块获取
    logger.warning("[板块] 暂未实现")
    return [], []


# ============================================
# 股票基本信息获取（待实现）
# ============================================

def get_stock_name(code: str) -> str:
    """获取股票名称"""
    quote = get_realtime(code)
    if quote:
        return quote.name
    return ""


def get_stock_info(code: str) -> Dict[str, Any]:
    """获取股票基本信息"""
    quote = get_realtime(code)
    if quote:
        return {
            'code': code,
            'name': quote.name,
            'price': quote.price,
            'change_pct': quote.change_pct,
            'pe_ratio': quote.pe_ratio,
            'pb_ratio': quote.pb_ratio,
            'total_mv': quote.total_mv,
        }
    return {'code': code, 'error': '获取失败'}


# ============================================
# DataFetcher 主类
# ============================================

class DataFetcher:
    """
    数据获取统一入口

    整合所有数据类型的获取方法。
    """

    def __init__(self):
        pass

    # === 日线数据 ===
    def get_daily(self, code: str, days: int = 60) -> Tuple[Optional[pd.DataFrame], str]:
        return get_daily(code, days)

    def get_daily_bars(self, code: str, days: int = 60) -> List[DailyBar]:
        return get_daily_as_bars(code, days)

    # === 实时行情 ===
    def get_realtime(self, code: str) -> Optional[RealtimeQuote]:
        return get_realtime(code)

    def get_realtime_dict(self, code: str) -> Dict[str, Any]:
        return get_realtime_as_dict(code)

    # === 筹码分布 ===
    def get_chip(self, code: str) -> Optional[ChipDistribution]:
        return get_chip_distribution(code)

    # === 龙虎榜 ===
    def get_dragon_tiger(self, code: str, days: int = 30) -> List[DragonTigerRecord]:
        return get_dragon_tiger(code, days)

    # === 研报评级 ===
    def get_research(self, code: str) -> List[ResearchReport]:
        return get_research_reports(code)

    # === 市场数据 ===
    def get_indices(self) -> List[Dict[str, Any]]:
        return get_main_indices()

    def get_market_stats(self) -> Dict[str, Any]:
        return get_market_stats()

    def get_sectors(self, n: int = 10) -> Tuple[List[Dict], List[Dict]]:
        return get_sector_rankings(n)

    # === 股票信息 ===
    def get_name(self, code: str) -> str:
        return get_stock_name(code)

    def get_info(self, code: str) -> Dict[str, Any]:
        return get_stock_info(code)

    # === 熔断器状态 ===
    def get_breaker_status(self) -> Dict[str, str]:
        """获取熔断器状态"""
        realtime_status = get_realtime_breaker().get_status()
        daily_status = get_daily_breaker().get_status()
        return {**realtime_status, **daily_status}


# ============================================
# 全局实例
# ============================================

_fetcher: Optional[DataFetcher] = None


def get_fetcher() -> DataFetcher:
    """获取全局 DataFetcher 单例"""
    global _fetcher
    if _fetcher is None:
        _fetcher = DataFetcher()
    return _fetcher


def reset_fetcher() -> None:
    """重置全局实例"""
    global _fetcher
    _fetcher = None
    clear_realtime_cache()