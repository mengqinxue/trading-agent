"""数据源模块"""

# === 新模块（推荐使用）===
from .fetcher import DataFetcher, get_fetcher, reset_fetcher
from .types import (
    RealtimeQuote, ChipDistribution, DailyBar,
    DragonTigerRecord, ResearchReport, DataSource
)
from .trade_daily import get_daily, get_daily_as_bars
from .trade_realtime import get_realtime, get_realtime_as_dict

# === 旧模块（兼容保留）===
from .akshare_data import AkshareDataSource
from .trendradar import TrendRadarMCPClient
from .data_adapter import DataAdapter, get_adapter

# === providers（内部实现，后续删除）===
from .providers import DataFetcherManager

__all__ = [
    # 新模块
    "DataFetcher",
    "get_fetcher",
    "reset_fetcher",
    "RealtimeQuote",
    "ChipDistribution",
    "DailyBar",
    "DragonTigerRecord",
    "ResearchReport",
    "DataSource",
    "get_daily",
    "get_daily_as_bars",
    "get_realtime",
    "get_realtime_as_dict",
    # 旧模块（兼容）
    "AkshareDataSource",
    "TrendRadarMCPClient",
    "DataAdapter",
    "get_adapter",
    "DataFetcherManager",
]