"""
TrendRadar MCP integration module

Provides access to hot news data from TrendRadar via MCP protocol.
Includes mock data fallback for development/testing.
"""

import json
import logging
from datetime import datetime
from typing import Any, Optional

import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger("trading_agent.data_sources.trendradar")


# ============== Pydantic Models ==============


class HotNewsItem(BaseModel):
    """Hot news item from TrendRadar"""

    title: str = Field(..., description="News title")
    source: str = Field(..., description="Platform source (e.g., 'zhihu', 'weibo')")
    url: Optional[str] = Field(None, description="News URL if available")
    heat_score: float = Field(0.0, description="Heat/popularity score")
    sector: Optional[str] = Field(None, description="Related sector/topic")
    rank: Optional[int] = Field(None, description="Ranking position")
    timestamp: Optional[str] = Field(None, description="Fetch timestamp")

    # Additional metadata from TrendRadar
    platform_name: Optional[str] = Field(None, description="Platform display name")
    hot_tag: Optional[str] = Field(None, description="Hot tag label")


class HotNewsResponse(BaseModel):
    """Response from get_hot_news"""

    success: bool = Field(True, description="Whether the request succeeded")
    data: list[HotNewsItem] = Field(default_factory=list, description="News items")
    source: str = Field("mock", description="Data source (mock/mcp)")
    error: Optional[str] = Field(None, description="Error message if failed")


# ============== Mock Data ==============


MOCK_HOT_NEWS: list[dict[str, Any]] = [
    {
        "title": "AI芯片需求激增，英伟达股价创历史新高",
        "source": "zhihu",
        "url": None,
        "heat_score": 95.5,
        "sector": "半导体",
        "rank": 1,
        "platform_name": "知乎",
        "hot_tag": "科技",
    },
    {
        "title": "新能源汽车销量突破百万，比亚迪领跑市场",
        "source": "weibo",
        "url": None,
        "heat_score": 88.2,
        "sector": "新能源汽车",
        "rank": 2,
        "platform_name": "微博",
        "hot_tag": "汽车",
    },
    {
        "title": "央行降准释放流动性，A股市场迎来利好",
        "source": "toutiao",
        "url": None,
        "heat_score": 82.0,
        "sector": "金融",
        "rank": 3,
        "platform_name": "今日头条",
        "hot_tag": "财经",
    },
    {
        "title": "茅台年报公布，净利润同比增长15%",
        "source": "zhihu",
        "url": None,
        "heat_score": 75.8,
        "sector": "白酒",
        "rank": 4,
        "platform_name": "知乎",
        "hot_tag": "消费",
    },
    {
        "title": "光伏组件价格触底，行业整合加速",
        "source": "weibo",
        "url": None,
        "heat_score": 70.3,
        "sector": "光伏",
        "rank": 5,
        "platform_name": "微博",
        "hot_tag": "能源",
    },
    {
        "title": "医药板块异动，创新药获批引发关注",
        "source": "toutiao",
        "url": None,
        "heat_score": 65.5,
        "sector": "医药",
        "rank": 6,
        "platform_name": "今日头条",
        "hot_tag": "医疗",
    },
    {
        "title": "地产政策松绑信号，房企融资环境改善",
        "source": "zhihu",
        "url": None,
        "heat_score": 60.0,
        "sector": "房地产",
        "rank": 7,
        "platform_name": "知乎",
        "hot_tag": "房产",
    },
    {
        "title": "ChatGPT商业化加速，AI应用赛道爆发",
        "source": "weibo",
        "url": None,
        "heat_score": 55.8,
        "sector": "AI应用",
        "rank": 8,
        "platform_name": "微博",
        "hot_tag": "科技",
    },
    {
        "title": "锂矿价格企稳，电池厂商库存压力缓解",
        "source": "toutiao",
        "url": None,
        "heat_score": 50.2,
        "sector": "锂电",
        "rank": 9,
        "platform_name": "今日头条",
        "hot_tag": "能源",
    },
    {
        "title": "军工订单饱满，国防信息化提速",
        "source": "zhihu",
        "url": None,
        "heat_score": 45.5,
        "sector": "军工",
        "rank": 10,
        "platform_name": "知乎",
        "hot_tag": "国防",
    },
]


# ============== MCP Client ==============


class TrendRadarClient:
    """Client for TrendRadar MCP server"""

    def __init__(
        self,
        base_url: str = "http://localhost:3333",
        timeout: float = 30.0,
    ):
        """
        Initialize TrendRadar MCP client

        Args:
            base_url: MCP server base URL
            timeout: Request timeout in seconds
        """
        self.base_url = base_url
        self.timeout = timeout
        self._session_id: Optional[str] = None

    def _build_request(
        self,
        method: str,
        params: Optional[dict[str, Any]] = None,
        request_id: int = 1,
    ) -> dict[str, Any]:
        """
        Build MCP JSON-RPC request

        Args:
            method: MCP method name (e.g., "tools/call")
            params: Method parameters
            request_id: Request ID for JSON-RPC

        Returns:
            JSON-RPC request dictionary
        """
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params or {},
        }

    async def call_tool(
        self,
        tool_name: str,
        arguments: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """
        Call a MCP tool

        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments

        Returns:
            Tool result as dictionary

        Raises:
            httpx.HTTPError: HTTP request failed
            ValueError: MCP response error
        """
        request = self._build_request(
            method="tools/call",
            params={
                "name": tool_name,
                "arguments": arguments or {},
            },
        )

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/mcp",
                json=request,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
            )
            response.raise_for_status()

            result = response.json()

            # Check for JSON-RPC error
            if "error" in result:
                error = result.get("error", {})
                raise ValueError(
                    f"MCP tool call error: {error.get('message', 'Unknown error')}"
                )

            # Extract tool result from MCP response
            content = result.get("result", {}).get("content", [])
            if content and len(content) > 0:
                # Parse text content as JSON
                text_content = content[0].get("text", "")
                if text_content:
                    return json.loads(text_content)

            return {}

    async def get_latest_news(
        self,
        platforms: Optional[list[str]] = None,
        limit: int = 50,
        include_url: bool = False,
    ) -> list[HotNewsItem]:
        """
        Get latest hot news from TrendRadar

        Args:
            platforms: Platform IDs to filter (e.g., ['zhihu', 'weibo'])
            limit: Maximum number of news items to return
            include_url: Whether to include URL in results

        Returns:
            List of HotNewsItem
        """
        try:
            result = await self.call_tool(
                tool_name="get_latest_news",
                arguments={
                    "platforms": platforms,
                    "limit": limit,
                    "include_url": include_url,
                },
            )

            if result.get("success"):
                raw_data = result.get("data", [])
                return [HotNewsItem(**item) for item in raw_data]
            else:
                error = result.get("error", {})
                logger.warning(
                    f"TrendRadar get_latest_news failed: {error.get('message', 'Unknown')}"
                )
                return []

        except Exception as e:
            logger.error(f"Failed to get latest news from TrendRadar: {e}")
            return []

    async def get_trending_topics(
        self,
        top_n: int = 10,
        mode: str = "current",
        extract_mode: str = "keywords",
    ) -> dict[str, Any]:
        """
        Get trending topics from TrendRadar

        Args:
            top_n: Number of top topics to return
            mode: Time mode ("daily" or "current")
            extract_mode: Extract mode ("keywords" or "auto_extract")

        Returns:
            Trending topics with frequency counts
        """
        try:
            result = await self.call_tool(
                tool_name="get_trending_topics",
                arguments={
                    "top_n": top_n,
                    "mode": mode,
                    "extract_mode": extract_mode,
                },
            )
            return result
        except Exception as e:
            logger.error(f"Failed to get trending topics from TrendRadar: {e}")
            return {}

    async def health_check(self) -> bool:
        """
        Check if TrendRadar MCP server is running

        Returns:
            True if server is healthy, False otherwise
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/mcp")
                return response.status_code == 200
        except Exception:
            return False


# ============== Default Client & Mock Fallback ==============


_default_client: Optional[TrendRadarClient] = None
_use_mock: bool = True  # Default to mock mode


def get_client(base_url: str = "http://localhost:3333") -> TrendRadarClient:
    """
    Get or create default TrendRadar client

    Args:
        base_url: MCP server base URL

    Returns:
        TrendRadarClient instance
    """
    global _default_client
    if _default_client is None or _default_client.base_url != base_url:
        _default_client = TrendRadarClient(base_url=base_url)
    return _default_client


def set_mock_mode(use_mock: bool) -> None:
    """
    Set whether to use mock data

    Args:
        use_mock: True to use mock data, False to use MCP
    """
    global _use_mock
    _use_mock = use_mock


def get_mock_news(limit: int = 50) -> list[HotNewsItem]:
    """
    Get mock hot news data

    Args:
        limit: Maximum number of items to return

    Returns:
        List of mock HotNewsItem
    """
    now = datetime.now().isoformat()
    items = MOCK_HOT_NEWS[:limit]

    return [
        HotNewsItem(
            title=item["title"],
            source=item["source"],
            url=item.get("url"),
            heat_score=item["heat_score"],
            sector=item["sector"],
            rank=item["rank"],
            platform_name=item["platform_name"],
            hot_tag=item["hot_tag"],
            timestamp=now,
        )
        for item in items
    ]


def get_hot_news(
    platforms: Optional[list[str]] = None,
    limit: int = 50,
    use_mcp: bool = False,
) -> list[HotNewsItem]:
    """
    Get hot news - synchronous version with mock fallback

    This is the main entry point for the Screener node.
    By default returns mock data for development/testing.
    Set use_mcp=True to connect to real TrendRadar MCP server.

    Args:
        platforms: Optional platform filter (e.g., ['zhihu', 'weibo', 'toutiao'])
        limit: Maximum number of news items (default 50)
        use_mcp: Whether to use MCP server (default False, uses mock)

    Returns:
        List of HotNewsItem, each containing:
        - title: News title
        - source: Platform ID (e.g., 'zhihu')
        - heat_score: Heat/popularity score
        - sector: Related sector/topic
        - url: News URL (optional)
        - rank: Ranking position
        - timestamp: Fetch timestamp

    Example:
        >>> news = get_hot_news(limit=10)
        >>> print(len(news))
        10
        >>> print(news[0].title)
        'AI芯片需求激增，英伟达股价创历史新高'
    """
    if _use_mock and not use_mcp:
        # Return mock data
        return get_mock_news(limit)

    # Try to use MCP server
    try:
        import asyncio

        try:
            loop = asyncio.get_running_loop()
            # If there's already a running loop, use ThreadPoolExecutor
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run,
                    _get_hot_news_async(platforms=platforms, limit=limit),
                )
                return future.result()
        except RuntimeError:
            # No running loop, use asyncio.run directly
            return asyncio.run(_get_hot_news_async(platforms=platforms, limit=limit))
    except Exception as e:
        logger.warning(f"MCP call failed, falling back to mock: {e}")
        return get_mock_news(limit)


async def _get_hot_news_async(
    platforms: Optional[list[str]] = None,
    limit: int = 50,
) -> list[HotNewsItem]:
    """
    Async implementation for MCP hot news fetch

    Args:
        platforms: Platform filter
        limit: Maximum items

    Returns:
        List of HotNewsItem
    """
    client = get_client()

    # Check MCP health first
    if not await client.health_check():
        logger.warning("TrendRadar MCP server not available, using mock data")
        return get_mock_news(limit)

    return await client.get_latest_news(platforms=platforms, limit=limit)


# Keep async version for backward compatibility
async def get_hot_news_async(
    platforms: Optional[list[str]] = None,
    limit: int = 50,
) -> list[HotNewsItem]:
    """
    Async version of get_hot_news

    Args:
        platforms: Optional platform filter
        limit: Maximum number of news items

    Returns:
        List of HotNewsItem
    """
    if _use_mock:
        return get_mock_news(limit)
    return await _get_hot_news_async(platforms=platforms, limit=limit)


# Backward compatibility alias
get_hot_news_sync = get_hot_news