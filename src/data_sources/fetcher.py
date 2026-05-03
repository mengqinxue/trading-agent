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
from .trade_chip import get_chip_distribution, get_chip_status
from .trade_dragon_tiger import get_dragon_tiger, get_dragon_tiger_summary
from .market_index import get_main_indices, get_index_by_code, get_index_overview
from .market_sector import (
    get_sector_rankings, get_hot_sectors, get_weak_sectors,
    get_stock_belong_sectors, get_sector_stocks
)
from .fundamental_financial import get_financial_data, get_financial_history, get_financial_summary
from .fundamental_research import get_research_reports, get_research_summary, get_rating_score
from .sources import CircuitBreaker, get_realtime_breaker, get_daily_breaker, get_chip_breaker

logger = logging.getLogger(__name__)


# ============================================
# 市场统计（从实时行情计算）
# ============================================

def get_market_stats() -> Dict[str, Any]:
    """
    获取市场涨跌统计

    Returns:
        涨跌家数、涨停跌停数等
    """
    try:
        import akshare as ak

        df = ak.stock_zh_a_spot_em()

        if df is None or df.empty:
            return {}

        # 统计涨跌
        up_count = len(df[df['涨跌幅'] > 0])
        down_count = len(df[df['涨跌幅'] < 0])
        flat_count = len(df[df['涨跌幅'] == 0])

        # 涨停跌停（涨跌幅 >= 9.9% 或 <= -9.9%）
        limit_up_count = len(df[df['涨跌幅'] >= 9.9])
        limit_down_count = len(df[df['涨跌幅'] <= -9.9])

        return {
            'total': len(df),
            'up_count': up_count,
            'down_count': down_count,
            'flat_count': flat_count,
            'limit_up_count': limit_up_count,
            'limit_down_count': limit_down_count,
            'up_ratio': up_count / len(df) if len(df) > 0 else 0,
        }

    except Exception as e:
        logger.warning(f"[市场统计] 获取失败: {e}")
        return {}


# ============================================
# 股票基本信息
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


def batch_get_stock_names(codes: List[str]) -> Dict[str, str]:
    """批量获取股票名称"""
    result = {}
    for code in codes:
        name = get_stock_name(code)
        if name:
            result[code] = name
    return result


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
        """获取日线数据"""
        return get_daily(code, days)

    def get_daily_bars(self, code: str, days: int = 60) -> List[DailyBar]:
        """获取日线数据（对象格式）"""
        return get_daily_as_bars(code, days)

    # === 实时行情 ===
    def get_realtime(self, code: str) -> Optional[RealtimeQuote]:
        """获取实时行情"""
        return get_realtime(code)

    def get_realtime_dict(self, code: str) -> Dict[str, Any]:
        """获取实时行情（字典格式）"""
        return get_realtime_as_dict(code)

    # === 筹码分布 ===
    def get_chip(self, code: str) -> Optional[ChipDistribution]:
        """获取筹码分布"""
        return get_chip_distribution(code)

    def get_chip_status(self, code: str, price: Optional[float] = None) -> str:
        """获取筹码状态描述"""
        return get_chip_status(code, price)

    # === 龙虎榜 ===
    def get_dragon_tiger(self, code: str, days: int = 30) -> List[DragonTigerRecord]:
        """获取龙虎榜"""
        return get_dragon_tiger(code, days)

    def get_dragon_tiger_summary(self, code: str, days: int = 30) -> Dict[str, Any]:
        """获取龙虎榜汇总"""
        return get_dragon_tiger_summary(code, days)

    # === 研报评级 ===
    def get_research(self, code: str, days: int = 90) -> List[ResearchReport]:
        """获取研报评级"""
        return get_research_reports(code, days)

    def get_research_summary(self, code: str, days: int = 90) -> Dict[str, Any]:
        """获取研报汇总"""
        return get_research_summary(code, days)

    def get_rating_score(self, code: str) -> float:
        """获取评级评分"""
        return get_rating_score(code)

    # === 市场数据 ===
    def get_indices(self) -> List[Dict[str, Any]]:
        """获取主要指数"""
        return get_main_indices()

    def get_index(self, code: str) -> Optional[Dict[str, Any]]:
        """获取单个指数"""
        return get_index_by_code(code)

    def get_index_overview(self) -> Dict[str, Any]:
        """获取指数概览（兼容旧接口）"""
        return get_index_overview()

    def get_market_stats(self) -> Dict[str, Any]:
        """获取市场统计"""
        return get_market_stats()

    def get_sectors(self, n: int = 10) -> Tuple[List[Dict], List[Dict]]:
        """获取板块涨跌榜"""
        return get_sector_rankings(n)

    def get_hot_sectors(self, n: int = 10) -> List[Dict[str, Any]]:
        """获取热点板块"""
        return get_hot_sectors(n)

    def get_weak_sectors(self, n: int = 10) -> List[Dict[str, Any]]:
        """获取弱势板块"""
        return get_weak_sectors(n)

    def get_belong_sectors(self, code: str) -> List[Dict[str, Any]]:
        """获取股票所属板块"""
        return get_stock_belong_sectors(code)

    def get_sector_stocks(self, sector_name: str, sector_type: str = 'concept') -> List[str]:
        """获取板块成分股"""
        return get_sector_stocks(sector_name, sector_type)

    # === 财务数据 ===
    def get_financial(self, code: str) -> Dict[str, Any]:
        """获取财务数据"""
        return get_financial_data(code)

    def get_financial_history(self, code: str, years: int = 3) -> List[Dict[str, Any]]:
        """获取历史财务数据"""
        return get_financial_history(code, years)

    def get_financial_summary(self, code: str) -> str:
        """获取财务摘要"""
        return get_financial_summary(code)

    # === 股票信息 ===
    def get_name(self, code: str) -> str:
        """获取股票名称"""
        return get_stock_name(code)

    def get_info(self, code: str) -> Dict[str, Any]:
        """获取股票信息"""
        return get_stock_info(code)

    def get_names(self, codes: List[str]) -> Dict[str, str]:
        """批量获取名称"""
        return batch_get_stock_names(codes)

    # === 熔断器状态 ===
    def get_breaker_status(self) -> Dict[str, str]:
        """获取熔断器状态"""
        realtime_status = get_realtime_breaker().get_status()
        daily_status = get_daily_breaker().get_status()
        chip_status = get_chip_breaker().get_status()
        return {**realtime_status, **daily_status, **chip_status}

    def reset_breakers(self) -> None:
        """重置所有熔断器"""
        get_realtime_breaker().reset()
        get_daily_breaker().reset()
        get_chip_breaker().reset()
        logger.info("[熔断器] 所有熔断器已重置")


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