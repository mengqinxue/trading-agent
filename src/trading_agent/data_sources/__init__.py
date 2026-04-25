"""
Data sources module

Provides interfaces to external data sources like TrendRadar.
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

__all__ = [
    "get_hot_news",
    "get_hot_news_async",
    "get_hot_news_sync",
    "get_client",
    "get_mock_news",
    "set_mock_mode",
    "TrendRadarClient",
    "HotNewsItem",
    "HotNewsResponse",
]