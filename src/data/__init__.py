# -*- coding: utf-8 -*-
"""数据模块 - 统一的数据获取和管理接口"""

# === 本地数据管理（原 src/data）===
from src.data.core import DatabaseManager
from src.data.loaders import DailyLoader, IndexLoader
from src.data.fetchers import MarketFetcher, FinancialFetcher, NewsFetcher, AnnouncementFetcher
from src.data.collectors import StockInfoCollector

# === 数据获取层（原 src/data_sources）===
from .fetcher import DataFetcher, get_fetcher, reset_fetcher
from .types import (
    RealtimeQuote, ChipDistribution, DailyBar,
    DragonTigerRecord, ResearchReport, DataSource
)
from .sources import CircuitBreaker, get_realtime_breaker, get_daily_breaker, get_chip_breaker

# === 数据获取函数 ===
from .trade_daily import get_daily, get_daily_as_bars
from .trade_realtime import get_realtime, get_realtime_as_dict
from .trade_chip import get_chip_distribution, get_chip_status
from .trade_dragon_tiger import get_dragon_tiger, get_dragon_tiger_summary
from .market_index import get_main_indices, get_index_by_code, get_index_overview
from .index_daily import (
    get_index_daily_akshare,
    analyze_market_trend,
    get_market_overview,
    update_all_index_daily,
    load_index_daily,
)
from .market_sector import (
    get_sector_rankings, get_hot_sectors, get_weak_sectors,
    get_stock_belong_sectors, get_sector_stocks
)
from .fundamental_financial import get_financial_data, get_financial_history, get_financial_summary
from .fundamental_research import get_research_reports, get_research_summary, get_rating_score

# === 兼容模块 ===
from .akshare_data import AkshareDataSource
from .trendradar import TrendRadarMCPClient
from .data_adapter import DataAdapter, get_adapter

# === providers（内部实现）===
from .providers import DataFetcherManager

__all__ = [
    # 本地数据管理
    "DatabaseManager",
    "DailyLoader",
    "IndexLoader",
    "MarketFetcher",
    "FinancialFetcher",
    "NewsFetcher",
    "AnnouncementFetcher",
    "StockInfoCollector",
    # 数据获取 - 主类
    "DataFetcher",
    "get_fetcher",
    "reset_fetcher",
    # 数据获取 - 类型
    "RealtimeQuote",
    "ChipDistribution",
    "DailyBar",
    "DragonTigerRecord",
    "ResearchReport",
    "DataSource",
    # 数据获取 - 熔断器
    "CircuitBreaker",
    "get_realtime_breaker",
    "get_daily_breaker",
    "get_chip_breaker",
    # 数据获取 - 函数
    "get_daily",
    "get_daily_as_bars",
    "get_realtime",
    "get_realtime_as_dict",
    "get_chip_distribution",
    "get_chip_status",
    "get_dragon_tiger",
    "get_dragon_tiger_summary",
    "get_main_indices",
    "get_index_by_code",
    "get_index_overview",
    "get_index_daily_akshare",
    "analyze_market_trend",
    "get_market_overview",
    "update_all_index_daily",
    "load_index_daily",
    "get_sector_rankings",
    "get_hot_sectors",
    "get_weak_sectors",
    "get_stock_belong_sectors",
    "get_sector_stocks",
    "get_financial_data",
    "get_financial_history",
    "get_financial_summary",
    "get_research_reports",
    "get_research_summary",
    "get_rating_score",
    # 兼容模块
    "AkshareDataSource",
    "TrendRadarMCPClient",
    "DataAdapter",
    "get_adapter",
    "DataFetcherManager",
]