# -*- coding: utf-8 -*-
"""数据获取器模块"""

from src.data.fetchers.market_fetcher import MarketFetcher
from src.data.fetchers.financial_fetcher import FinancialFetcher
from src.data.fetchers.news_fetcher import NewsFetcher
from src.data.fetchers.announcement_fetcher import AnnouncementFetcher

__all__ = [
    "MarketFetcher",
    "FinancialFetcher",
    "NewsFetcher",
    "AnnouncementFetcher",
]