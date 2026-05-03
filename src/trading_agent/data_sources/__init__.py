"""数据源模块"""

from .akshare_data import AkshareDataSource
from .trendradar import TrendRadarMCPClient
from .data_adapter import DataAdapter, get_adapter

# 多数据源管理器（可选使用）
from .providers import DataFetcherManager

__all__ = [
    "AkshareDataSource",
    "TrendRadarMCPClient",
    "DataAdapter",
    "get_adapter",
    "DataFetcherManager",
]