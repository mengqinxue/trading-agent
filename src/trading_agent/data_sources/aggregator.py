"""
Data aggregator module

Aggregates data from multiple sources (TrendRadar, Akshare) into unified format
for Agent consumption.
"""

import logging
from typing import Optional

from pydantic import BaseModel, Field

from .akshare_data import (
    FinancialData,
    FinancialResponse,
    KlineData,
    KlineResponse,
    StockInfo,
    get_financial_data,
    get_kline_data,
    get_stock_info,
)
from .trendradar import HotNewsItem, get_hot_news

logger = logging.getLogger("trading_agent.data_sources.aggregator")


# ============== Unified Data Models ==============


class StockDataBundle(BaseModel):
    """
    Unified stock data bundle containing all information for a single stock.

    This model aggregates data from multiple sources into a single structure
    that is convenient for Agent consumption.
    """

    # Basic stock information
    stock_info: StockInfo = Field(
        ..., description="Basic stock information (code, name, sector, etc.)"
    )

    # Price/K-line data
    kline_data: Optional[KlineResponse] = Field(
        None, description="Recent K-line (price) data"
    )

    # Financial data
    financial_data: Optional[FinancialResponse] = Field(
        None, description="Financial statement data"
    )

    # Related news
    related_news: list[HotNewsItem] = Field(
        default_factory=list,
        description="Hot news potentially related to this stock's sector",
    )

    # Metadata
    aggregation_success: bool = Field(
        True, description="Whether all data sources were fetched successfully"
    )
    errors: list[str] = Field(
        default_factory=list, description="List of errors encountered during aggregation"
    )


class MarketOverview(BaseModel):
    """
    Market overview data containing hot news and general market sentiment.
    """

    hot_news: list[HotNewsItem] = Field(
        default_factory=list, description="Current hot news across platforms"
    )
    news_count: int = Field(0, description="Total number of news items")
    top_sectors: list[str] = Field(
        default_factory=list, description="Top sectors mentioned in news"
    )


# ============== Data Aggregator Class ==============


class DataAggregator:
    """
    Aggregates data from multiple sources into unified format.

    This class provides methods to fetch and combine data from:
    - TrendRadar: Hot news and market sentiment
    - Akshare: Stock info, K-line data, financial data

    Example:
        >>> agg = DataAggregator()
        >>> data = agg.aggregate_stock_data("000001")
        >>> print(data.stock_info.name)
        '平安银行'
    """

    def __init__(
        self,
        kline_days: int = 30,
        news_limit: int = 50,
    ):
        """
        Initialize DataAggregator.

        Args:
            kline_days: Number of days for K-line data (default 30)
            news_limit: Maximum number of news items to fetch (default 50)
        """
        self.kline_days = kline_days
        self.news_limit = news_limit

    def aggregate_stock_data(self, code: str) -> StockDataBundle:
        """
        Get complete stock data bundle for a given stock code.

        Fetches and aggregates:
        1. Basic stock information (StockInfo)
        2. K-line/price data (KlineResponse)
        3. Financial data (FinancialResponse)
        4. Related hot news (HotNewsItem list)

        Args:
            code: Stock code (e.g., '000001', '600519')

        Returns:
            StockDataBundle containing all aggregated data

        Example:
            >>> agg = DataAggregator()
            >>> data = agg.aggregate_stock_data("000001")
            >>> print(data.stock_info.name)
            '平安银行'
            >>> print(data.kline_data.stock_name)
            '平安银行'
        """
        errors: list[str] = []

        # 1. Fetch stock info (required)
        try:
            stock_info = get_stock_info(code)
        except ValueError as e:
            logger.error(f"Failed to get stock info for {code}: {e}")
            return StockDataBundle(
                stock_info=StockInfo(
                    code=code,
                    name="Unknown",
                    market="Unknown",
                ),
                aggregation_success=False,
                errors=[f"Stock info fetch failed: {e}"],
            )

        # 2. Fetch K-line data
        kline_data: Optional[KlineResponse] = None
        try:
            kline_data = get_kline_data(code, days=self.kline_days)
            if not kline_data.success:
                errors.append(f"K-line data error: {kline_data.error}")
        except Exception as e:
            logger.warning(f"Failed to get K-line data for {code}: {e}")
            errors.append(f"K-line data fetch failed: {e}")

        # 3. Fetch financial data
        financial_data: Optional[FinancialResponse] = None
        try:
            financial_data = get_financial_data(code)
            if not financial_data.success:
                errors.append(f"Financial data error: {financial_data.error}")
        except Exception as e:
            logger.warning(f"Failed to get financial data for {code}: {e}")
            errors.append(f"Financial data fetch failed: {e}")

        # 4. Fetch related hot news
        related_news: list[HotNewsItem] = []
        try:
            all_news = get_hot_news(limit=self.news_limit)
            # Filter news related to the stock's sector
            stock_sector = stock_info.sector
            if stock_sector:
                related_news = [
                    news
                    for news in all_news
                    if news.sector and news.sector == stock_sector
                ]
            # Also include news mentioning the stock name
            if stock_info.name:
                name_related = [
                    news
                    for news in all_news
                    if stock_info.name in news.title
                ]
                # Combine and deduplicate
                seen_titles = {news.title for news in related_news}
                for news in name_related:
                    if news.title not in seen_titles:
                        related_news.append(news)
                        seen_titles.add(news.title)
        except Exception as e:
            logger.warning(f"Failed to get hot news: {e}")
            errors.append(f"Hot news fetch failed: {e}")

        # Determine overall success
        aggregation_success = len(errors) == 0

        return StockDataBundle(
            stock_info=stock_info,
            kline_data=kline_data,
            financial_data=financial_data,
            related_news=related_news,
            aggregation_success=aggregation_success,
            errors=errors,
        )

    def get_market_overview(self) -> MarketOverview:
        """
        Get market overview with hot news and sector trends.

        Returns:
            MarketOverview containing hot news and top sectors

        Example:
            >>> agg = DataAggregator()
            >>> overview = agg.get_market_overview()
            >>> print(len(overview.hot_news))
            10
        """
        try:
            hot_news = get_hot_news(limit=self.news_limit)

            # Extract top sectors from news
            sector_counts: dict[str, int] = {}
            for news in hot_news:
                if news.sector:
                    sector_counts[news.sector] = sector_counts.get(news.sector, 0) + 1

            # Sort by count and get top sectors
            top_sectors = sorted(
                sector_counts.keys(),
                key=lambda s: sector_counts[s],
                reverse=True,
            )[:5]

            return MarketOverview(
                hot_news=hot_news,
                news_count=len(hot_news),
                top_sectors=top_sectors,
            )
        except Exception as e:
            logger.error(f"Failed to get market overview: {e}")
            return MarketOverview(
                hot_news=[],
                news_count=0,
                top_sectors=[],
            )


# ============== Convenience Functions ==============


def get_stock_bundle(code: str, kline_days: int = 30) -> StockDataBundle:
    """
    Convenience function to get stock data bundle.

    Args:
        code: Stock code (e.g., '000001')
        kline_days: Number of days for K-line data

    Returns:
        StockDataBundle with all stock data

    Example:
        >>> data = get_stock_bundle("000001")
        >>> print(data.stock_info.name)
        '平安银行'
    """
    aggregator = DataAggregator(kline_days=kline_days)
    return aggregator.aggregate_stock_data(code)


def get_market_summary(news_limit: int = 50) -> MarketOverview:
    """
    Convenience function to get market overview.

    Args:
        news_limit: Maximum news items to fetch

    Returns:
        MarketOverview with hot news and sector trends

    Example:
        >>> overview = get_market_summary()
        >>> print(overview.top_sectors)
        ['半导体', '新能源汽车', '金融']
    """
    aggregator = DataAggregator(news_limit=news_limit)
    return aggregator.get_market_overview()