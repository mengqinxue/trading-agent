"""
Akshare data integration module

Provides access to stock data from akshare Python library.
Includes mock data fallback for development/testing.

Akshare is a Python library for Chinese stock market data,
providing A-share market quotes, financial data, and technical indicators.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger("trading_agent.data_sources.akshare_data")


# ============== Pydantic Models ==============


class StockInfo(BaseModel):
    """Stock basic information"""

    code: str = Field(..., description="Stock code (e.g., '000001')")
    name: str = Field(..., description="Stock name (e.g., '平安银行')")
    market: str = Field(..., description="Market (SH/SZ)")
    sector: Optional[str] = Field(None, description="Industry sector")
    industry: Optional[str] = Field(None, description="Specific industry")
    list_date: Optional[str] = Field(None, description="Listing date")
    total_shares: Optional[float] = Field(None, description="Total shares (亿股)")
    float_shares: Optional[float] = Field(None, description="Float shares (亿股)")


class KlineData(BaseModel):
    """K-line (candlestick) data point"""

    date: str = Field(..., description="Trading date")
    open: float = Field(..., description="Opening price")
    close: float = Field(..., description="Closing price")
    high: float = Field(..., description="Highest price")
    low: float = Field(..., description="Lowest price")
    volume: float = Field(..., description="Trading volume (手)")
    amount: float = Field(..., description="Trading amount (万元)")
    turnover_rate: Optional[float] = Field(None, description="Turnover rate %")
    pct_change: Optional[float] = Field(None, description="Price change %")


class KlineResponse(BaseModel):
    """Response from get_kline_data"""

    success: bool = Field(True, description="Whether the request succeeded")
    data: list[KlineData] = Field(default_factory=list, description="K-line data points")
    stock_code: str = Field(..., description="Stock code")
    stock_name: Optional[str] = Field(None, description="Stock name")
    source: str = Field("mock", description="Data source (mock/akshare)")
    error: Optional[str] = Field(None, description="Error message if failed")


class FinancialData(BaseModel):
    """Financial statement data"""

    code: str = Field(..., description="Stock code")
    name: str = Field(..., description="Stock name")
    report_date: str = Field(..., description="Report date")
    revenue: float = Field(..., description="Revenue (亿元)")
    net_profit: float = Field(..., description="Net profit (亿元)")
    gross_margin: Optional[float] = Field(None, description="Gross margin %")
    net_margin: Optional[float] = Field(None, description="Net margin %")
    roe: Optional[float] = Field(None, description="Return on equity %")
    debt_ratio: Optional[float] = Field(None, description="Debt ratio %")
    pe_ratio: Optional[float] = Field(None, description="P/E ratio")
    pb_ratio: Optional[float] = Field(None, description="P/B ratio")


class FinancialResponse(BaseModel):
    """Response from get_financial_data"""

    success: bool = Field(True, description="Whether the request succeeded")
    data: list[FinancialData] = Field(default_factory=list, description="Financial reports")
    stock_code: str = Field(..., description="Stock code")
    stock_name: Optional[str] = Field(None, description="Stock name")
    source: str = Field("mock", description="Data source (mock/akshare)")
    error: Optional[str] = Field(None, description="Error message if failed")


# ============== Mock Data ==============


# Mock stock info database (A-share stocks)
MOCK_STOCK_INFO: dict[str, dict[str, Any]] = {
    "000001": {
        "code": "000001",
        "name": "平安银行",
        "market": "SZ",
        "sector": "金融",
        "industry": "银行",
        "list_date": "1991-04-03",
        "total_shares": 194.05,
        "float_shares": 194.05,
    },
    "000002": {
        "code": "000002",
        "name": "万科A",
        "market": "SZ",
        "sector": "房地产",
        "industry": "房地产开发",
        "list_date": "1991-01-29",
        "total_shares": 110.39,
        "float_shares": 110.39,
    },
    "000063": {
        "code": "000063",
        "name": "中兴通讯",
        "market": "SZ",
        "sector": "科技",
        "industry": "通信设备",
        "list_date": "1997-11-18",
        "total_shares": 46.13,
        "float_shares": 46.13,
    },
    "000333": {
        "code": "000333",
        "name": "美的集团",
        "market": "SZ",
        "sector": "消费",
        "industry": "家电",
        "list_date": "2013-09-18",
        "total_shares": 69.86,
        "float_shares": 69.86,
    },
    "000651": {
        "code": "000651",
        "name": "格力电器",
        "market": "SZ",
        "sector": "消费",
        "industry": "家电",
        "list_date": "1996-11-18",
        "total_shares": 56.31,
        "float_shares": 56.31,
    },
    "000858": {
        "code": "000858",
        "name": "五粮液",
        "market": "SZ",
        "sector": "消费",
        "industry": "白酒",
        "list_date": "1998-04-21",
        "total_shares": 38.82,
        "float_shares": 38.82,
    },
    "600000": {
        "code": "600000",
        "name": "浦发银行",
        "market": "SH",
        "sector": "金融",
        "industry": "银行",
        "list_date": "1999-11-10",
        "total_shares": 293.52,
        "float_shares": 293.52,
    },
    "600036": {
        "code": "600036",
        "name": "招商银行",
        "market": "SH",
        "sector": "金融",
        "industry": "银行",
        "list_date": "2002-04-09",
        "total_shares": 252.20,
        "float_shares": 252.20,
    },
    "600519": {
        "code": "600519",
        "name": "贵州茅台",
        "market": "SH",
        "sector": "消费",
        "industry": "白酒",
        "list_date": "2001-08-27",
        "total_shares": 12.56,
        "float_shares": 12.56,
    },
    "600900": {
        "code": "600900",
        "name": "长江电力",
        "market": "SH",
        "sector": "公用事业",
        "industry": "水电",
        "list_date": "2003-11-18",
        "total_shares": 224.49,
        "float_shares": 224.49,
    },
}

# Mock K-line data generator
def _generate_mock_kline(code: str, days: int) -> list[KlineData]:
    """Generate mock K-line data for testing"""
    # Base prices for different stocks
    base_prices: dict[str, float] = {
        "000001": 12.50,  # 平安银行
        "000002": 8.20,  # 万科A
        "000063": 28.50,  # 中兴通讯
        "000333": 58.80,  # 美的集团
        "000651": 35.50,  # 格力电器
        "000858": 140.00,  # 五粮液
        "600000": 8.50,  # 浦发银行
        "600036": 32.00,  # 招商银行
        "600519": 1500.00,  # 贵州茅台
        "600900": 26.50,  # 长江电力
    }

    base_price = base_prices.get(code, 10.0)
    today = datetime.now()

    klines: list[KlineData] = []
    price = base_price

    for i in range(days):
        # Simulate price movement with random variation
        date = today - timedelta(days=days - i - 1)
        date_str = date.strftime("%Y-%m-%d")

        # Skip weekends (simplified)
        if date.weekday() >= 5:
            continue

        # Generate price variation
        import random

        pct_change = random.uniform(-3.0, 3.0)
        price = price * (1 + pct_change / 100)

        high = price * (1 + random.uniform(0.5, 2.0) / 100)
        low = price * (1 - random.uniform(0.5, 2.0) / 100)
        open_price = price * (1 + random.uniform(-1.0, 1.0) / 100)

        volume = random.uniform(50000, 200000)  # 手
        amount = volume * price / 100  # 万元

        klines.append(
            KlineData(
                date=date_str,
                open=round(open_price, 2),
                close=round(price, 2),
                high=round(high, 2),
                low=round(low, 2),
                volume=round(volume, 0),
                amount=round(amount, 2),
                turnover_rate=round(random.uniform(0.5, 5.0), 2),
                pct_change=round(pct_change, 2),
            )
        )

    return klines


# Mock financial data
MOCK_FINANCIAL_DATA: dict[str, list[dict[str, Any]]] = {
    "000001": [
        {
            "report_date": "2024-09-30",
            "revenue": 388.63,
            "net_profit": 142.52,
            "gross_margin": 45.2,
            "net_margin": 36.7,
            "roe": 10.5,
            "debt_ratio": 92.1,
            "pe_ratio": 6.2,
            "pb_ratio": 0.65,
        },
        {
            "report_date": "2024-06-30",
            "revenue": 245.21,
            "net_profit": 95.28,
            "gross_margin": 44.8,
            "net_margin": 36.5,
            "roe": 7.2,
            "debt_ratio": 92.0,
            "pe_ratio": 6.3,
            "pb_ratio": 0.66,
        },
    ],
    "600519": [
        {
            "report_date": "2024-09-30",
            "revenue": 123.15,
            "net_profit": 60.82,
            "gross_margin": 91.5,
            "net_margin": 49.5,
            "roe": 26.8,
            "debt_ratio": 19.2,
            "pe_ratio": 25.5,
            "pb_ratio": 6.8,
        },
        {
            "report_date": "2024-06-30",
            "revenue": 81.5,
            "net_profit": 40.5,
            "gross_margin": 91.2,
            "net_margin": 49.8,
            "roe": 18.5,
            "debt_ratio": 18.8,
            "pe_ratio": 26.2,
            "pb_ratio": 7.0,
        },
    ],
}


# ============== Public API Functions ==============


def get_stock_info(code: str, use_real: bool = False) -> StockInfo:
    """
    Get stock basic information

    By default returns mock data for development/testing.
    Set use_real=True to fetch from real akshare library.

    Args:
        code: Stock code (e.g., '000001', '600519')
        use_real: Whether to use real akshare API (default False)

    Returns:
        StockInfo containing:
        - code: Stock code
        - name: Stock name (e.g., '平安银行')
        - market: Market (SH/SZ)
        - sector: Industry sector
        - industry: Specific industry
        - list_date: Listing date
        - total_shares: Total shares
        - float_shares: Float shares

    Raises:
        ValueError: If stock code not found

    Example:
        >>> info = get_stock_info("000001")
        >>> print(info.name)
        平安银行
        >>> print(info.market)
        SZ
    """
    if use_real:
        return _get_stock_info_real(code)
    return _get_stock_info_mock(code)


def _get_stock_info_mock(code: str) -> StockInfo:
    """Mock implementation of get_stock_info"""
    if code not in MOCK_STOCK_INFO:
        raise ValueError(f"Stock code '{code}' not found in mock database")

    data = MOCK_STOCK_INFO[code]
    return StockInfo(**data)


def _get_stock_info_real(code: str) -> StockInfo:
    """Real akshare implementation (placeholder)"""
    # TODO: Implement real akshare API call
    # Example akshare code:
    # import akshare as ak
    # stock_info_df = ak.stock_individual_info_em(symbol=code)
    # ...

    logger.warning("Real akshare API not yet implemented, falling back to mock")
    return _get_stock_info_mock(code)


def get_kline_data(
    code: str,
    days: int = 30,
    use_real: bool = False,
) -> KlineResponse:
    """
    Get K-line (candlestick) data

    By default returns mock data for development/testing.
    Set use_real=True to fetch from real akshare library.

    Args:
        code: Stock code (e.g., '000001')
        days: Number of trading days (default 30)
        use_real: Whether to use real akshare API (default False)

    Returns:
        KlineResponse containing:
        - success: Whether request succeeded
        - data: List of KlineData points
        - stock_code: Stock code
        - stock_name: Stock name (if available)
        - source: Data source (mock/akshare)
        - error: Error message if failed

    Example:
        >>> response = get_kline_data("000001", days=10)
        >>> print(len(response.data))
        10
        >>> print(response.data[0].close)
        12.50
    """
    if use_real:
        return _get_kline_data_real(code, days)
    return _get_kline_data_mock(code, days)


def _get_kline_data_mock(code: str, days: int) -> KlineResponse:
    """Mock implementation of get_kline_data"""
    try:
        stock_info = _get_stock_info_mock(code)
        klines = _generate_mock_kline(code, days)

        return KlineResponse(
            success=True,
            data=klines,
            stock_code=code,
            stock_name=stock_info.name,
            source="mock",
            error=None,
        )
    except ValueError as e:
        return KlineResponse(
            success=False,
            data=[],
            stock_code=code,
            stock_name=None,
            source="mock",
            error=str(e),
        )


def _get_kline_data_real(code: str, days: int) -> KlineResponse:
    """Real akshare implementation (placeholder)"""
    # TODO: Implement real akshare API call
    # Example akshare code:
    # import akshare as ak
    # stock_zh_a_hist_df = ak.stock_zh_a_hist(
    #     symbol=code,
    #     period="daily",
    #     start_date=start_date,
    #     end_date=end_date,
    #     adjust="qfq"
    # )
    # ...

    logger.warning("Real akshare API not yet implemented, falling back to mock")
    return _get_kline_data_mock(code, days)


def get_financial_data(
    code: str,
    use_real: bool = False,
) -> FinancialResponse:
    """
    Get financial statement data

    By default returns mock data for development/testing.
    Set use_real=True to fetch from real akshare library.

    Args:
        code: Stock code (e.g., '000001')
        use_real: Whether to use real akshare API (default False)

    Returns:
        FinancialResponse containing:
        - success: Whether request succeeded
        - data: List of FinancialData reports
        - stock_code: Stock code
        - stock_name: Stock name (if available)
        - source: Data source (mock/akshare)
        - error: Error message if failed

    Example:
        >>> response = get_financial_data("000001")
        >>> print(response.data[0].revenue)
        388.63
        >>> print(response.data[0].net_profit)
        142.52
    """
    if use_real:
        return _get_financial_data_real(code)
    return _get_financial_data_mock(code)


def _get_financial_data_mock(code: str) -> FinancialResponse:
    """Mock implementation of get_financial_data"""
    try:
        stock_info = _get_stock_info_mock(code)
        financials = MOCK_FINANCIAL_DATA.get(code, [])

        # Generate default financial data if not in database
        if not financials:
            import random

            financials = [
                {
                    "report_date": "2024-09-30",
                    "revenue": round(random.uniform(50, 500), 2),
                    "net_profit": round(random.uniform(5, 50), 2),
                    "gross_margin": round(random.uniform(20, 60), 2),
                    "net_margin": round(random.uniform(5, 30), 2),
                    "roe": round(random.uniform(5, 20), 2),
                    "debt_ratio": round(random.uniform(20, 80), 2),
                    "pe_ratio": round(random.uniform(5, 50), 2),
                    "pb_ratio": round(random.uniform(0.5, 10), 2),
                },
            ]

        data = [
            FinancialData(
                code=code,
                name=stock_info.name,
                **fin,
            )
            for fin in financials
        ]

        return FinancialResponse(
            success=True,
            data=data,
            stock_code=code,
            stock_name=stock_info.name,
            source="mock",
            error=None,
        )
    except ValueError as e:
        return FinancialResponse(
            success=False,
            data=[],
            stock_code=code,
            stock_name=None,
            source="mock",
            error=str(e),
        )


def _get_financial_data_real(code: str) -> FinancialResponse:
    """Real akshare implementation (placeholder)"""
    # TODO: Implement real akshare API call
    # Example akshare code:
    # import akshare as ak
    # stock_financial_df = ak.stock_financial_analysis_indicator(symbol=code)
    # ...

    logger.warning("Real akshare API not yet implemented, falling back to mock")
    return _get_financial_data_mock(code)


# ============== Utility Functions ==============


def is_valid_stock_code(code: str) -> bool:
    """
    Check if stock code format is valid

    Args:
        code: Stock code string

    Returns:
        True if valid format (SH/SZ 6-digit code)
    """
    if not code or len(code) != 6:
        return False
    return code.isdigit()


def get_market_from_code(code: str) -> str:
    """
    Determine market from stock code

    Args:
        code: Stock code

    Returns:
        Market string ('SH' for Shanghai, 'SZ' for Shenzhen)
    """
    if code.startswith("6"):
        return "SH"
    elif code.startswith("0") or code.startswith("3"):
        return "SZ"
    else:
        return "Unknown"