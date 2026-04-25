"""
Data sources module

Provides interfaces to external data sources like TrendRadar and Akshare.
"""

from .trendradar import (
    get_hot_news,
    get_hot_news_async,
    get_hot_news_sync,
    get_client,
    get_mock_news,
    set_mock_mode,
    TrendRadarClient,
    HotNewsItem,
    HotNewsResponse,
)

from .akshare_data import (
    get_stock_info,
    get_kline_data,
    get_financial_data,
    is_valid_stock_code,
    get_market_from_code,
    StockInfo,
    KlineData,
    KlineResponse,
    FinancialData,
    FinancialResponse,
)

__all__ = [
    # TrendRadar
    "get_hot_news",
    "get_hot_news_async",
    "get_hot_news_sync",
    "get_client",
    "get_mock_news",
    "set_mock_mode",
    "TrendRadarClient",
    "HotNewsItem",
    "HotNewsResponse",
    # Akshare
    "get_stock_info",
    "get_kline_data",
    "get_financial_data",
    "is_valid_stock_code",
    "get_market_from_code",
    "StockInfo",
    "KlineData",
    "KlineResponse",
    "FinancialData",
    "FinancialResponse",
]