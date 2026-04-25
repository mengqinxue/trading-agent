"""
Screener node - 热点发现 & 粗筛

Responsibilities:
- Get hot news from TrendRadar MCP
- AI analyze hot sectors
- Identify hype leaders (not fundamentals leaders)
- Generate candidate stock pool
- Save candidates to data/
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

from trading_agent.graph.state import WorkflowState, StepStatus, Stock, Sector
from trading_agent.data_sources import (
    get_hot_news,
    HotNewsItem,
    DataAggregator,
)
from trading_agent.utils.logger import get_logger
from trading_agent.utils.config import get_settings

logger = get_logger("SCREENER")

# Sector-leader mapping (mock data for development)
# Maps sector names to their typical leader stocks
SECTOR_LEADERS: Dict[str, List[Dict[str, str]]] = {
    "半导体": [
        {"code": "600519", "name": "贵州茅台", "market": "SH"},  # Mock placeholder
        {"code": "000063", "name": "中兴通讯", "market": "SZ"},
    ],
    "新能源汽车": [
        {"code": "000333", "name": "美的集团", "market": "SZ"},  # Mock placeholder
    ],
    "金融": [
        {"code": "000001", "name": "平安银行", "market": "SZ"},
        {"code": "600036", "name": "招商银行", "market": "SH"},
    ],
    "白酒": [
        {"code": "600519", "name": "贵州茅台", "market": "SH"},
        {"code": "000858", "name": "五粮液", "market": "SZ"},
    ],
    "光伏": [
        {"code": "600900", "name": "长江电力", "market": "SH"},  # Mock placeholder
    ],
    "医药": [
        {"code": "000651", "name": "格力电器", "market": "SZ"},  # Mock placeholder
    ],
    "房地产": [
        {"code": "000002", "name": "万科A", "market": "SZ"},
    ],
    "AI应用": [
        {"code": "000063", "name": "中兴通讯", "market": "SZ"},  # Mock placeholder
    ],
    "锂电": [
        {"code": "000333", "name": "美的集团", "market": "SZ"},  # Mock placeholder
    ],
    "军工": [
        {"code": "000063", "name": "中兴通讯", "market": "SZ"},  # Mock placeholder
    ],
}


def screener_node(state: WorkflowState) -> Dict:
    """
    Screener node entry function

    This node:
    1. Updates status to RUNNING
    2. Gets hot news from TrendRadar MCP
    3. Identifies hot sectors
    4. Generates candidate stock pool
    5. Updates status to COMPLETED
    6. Returns updated state

    Args:
        state: Current workflow state

    Returns:
        Dict with updated state fields
    """
    run_id = state.get("run_id", "unknown")
    logger.info(f"[{run_id}] Screener node started")
    logger.info(f"[{run_id}] Status: {state.get('screener_status')}")

    # Update status to RUNNING
    updates: Dict[str, Any] = {
        "screener_status": StepStatus.RUNNING.value,
        "current_step_start": datetime.now().isoformat(),
    }

    try:
        # Step 1: Get hot news from TrendRadar
        logger.info(f"[{run_id}] Step 1: Fetching hot news from TrendRadar")
        hot_news = _fetch_hot_news(run_id)
        updates["hot_news"] = [news.model_dump() for news in hot_news]
        logger.info(f"[{run_id}] Fetched {len(hot_news)} hot news items")

        # Step 2: Analyze hot sectors using LLM
        logger.info(f"[{run_id}] Step 2: Analyzing hot sectors")
        hot_sectors = _analyze_hot_sectors(hot_news, run_id)
        updates["hot_sectors"] = [sector.model_dump() for sector in hot_sectors]
        logger.info(f"[{run_id}] Identified {len(hot_sectors)} hot sectors")

        # Step 3: Identify sector leaders (hype-based)
        logger.info(f"[{run_id}] Step 3: Identifying hype leaders")
        candidate_stocks = _identify_leaders(hot_sectors, hot_news, run_id)
        updates["candidate_stocks"] = [stock.model_dump() for stock in candidate_stocks]
        logger.info(f"[{run_id}] Generated {len(candidate_stocks)} candidate stocks")

        # Step 4: Save candidates to data/candidates/
        logger.info(f"[{run_id}] Step 4: Saving candidates")
        _save_candidates(candidate_stocks, hot_sectors, hot_news, run_id)

        # Update status to COMPLETED
        updates["screener_status"] = StepStatus.COMPLETED.value

        logger.info(f"[{run_id}] Screener node completed successfully")
        logger.info(f"[{run_id}] Candidates: {len(updates.get('candidate_stocks', []))}")

    except Exception as e:
        logger.error(f"[{run_id}] Screener node failed: {e}")
        updates["screener_status"] = StepStatus.FAILED.value
        updates["error_step"] = "screener"
        updates["error_message"] = str(e)

        # Set empty results on failure
        updates["hot_news"] = []
        updates["hot_sectors"] = []
        updates["candidate_stocks"] = []

    return updates


def _fetch_hot_news(run_id: str) -> List[HotNewsItem]:
    """
    Fetch hot news from TrendRadar

    Args:
        run_id: Run ID for logging

    Returns:
        List of HotNewsItem
    """
    try:
        aggregator = DataAggregator(news_limit=50)
        market_overview = aggregator.get_market_overview()
        return market_overview.hot_news
    except Exception as e:
        logger.warning(f"[{run_id}] Failed to fetch from DataAggregator: {e}, using direct call")
        return get_hot_news(limit=50)


def _analyze_hot_sectors(hot_news: List[HotNewsItem], run_id: str) -> List[Sector]:
    """
    Analyze hot news to identify hot sectors

    This uses a simple keyword-based approach for now.
    Can be enhanced with LLM analysis later.

    Args:
        hot_news: List of hot news items
        run_id: Run ID for logging

    Returns:
        List of Sector objects with heat scores
    """
    # Count sector occurrences and calculate heat
    sector_data: Dict[str, Dict[str, Any]] = {}

    for news in hot_news:
        sector = news.sector
        if not sector:
            continue

        if sector not in sector_data:
            sector_data[sector] = {
                "name": sector,
                "heat_score": 0.0,
                "news_count": 0,
                "total_heat": 0.0,
                "news_titles": [],
            }

        sector_data[sector]["news_count"] += 1
        sector_data[sector]["total_heat"] += news.heat_score
        sector_data[sector]["news_titles"].append(news.title)

    # Calculate average heat score and build Sector objects
    hot_sectors: List[Sector] = []
    for sector_name, data in sector_data.items():
        avg_heat = data["total_heat"] / data["news_count"] if data["news_count"] > 0 else 0

        # Get leaders from mapping
        leaders = SECTOR_LEADERS.get(sector_name, [])
        leader_codes = [l["code"] for l in leaders]

        hot_sectors.append(
            Sector(
                name=sector_name,
                heat_score=round(avg_heat, 2),
                leaders=leader_codes,
                news_count=data["news_count"],
            )
        )

    # Sort by heat score descending
    hot_sectors.sort(key=lambda s: s.heat_score, reverse=True)

    # Limit to top 5 sectors for now
    return hot_sectors[:5]


def _identify_leaders(
    hot_sectors: List[Sector],
    hot_news: List[HotNewsItem],
    run_id: str,
) -> List[Stock]:
    """
    Identify hype leaders for each hot sector

    For now, uses the pre-defined SECTOR_LEADERS mapping.
    Can be enhanced with real-time analysis later.

    Args:
        hot_sectors: List of identified hot sectors
        hot_news: List of hot news (for context)
        run_id: Run ID for logging

    Returns:
        List of Stock objects as candidates
    """
    candidate_stocks: List[Stock] = []
    seen_codes: set = set()

    for sector in hot_sectors:
        # Get leaders from mapping
        leaders_data = SECTOR_LEADERS.get(sector.name, [])

        for leader in leaders_data:
            code = leader["code"]
            if code in seen_codes:
                continue

            seen_codes.add(code)
            candidate_stocks.append(
                Stock(
                    code=code,
                    name=leader["name"],
                    market=leader["market"],
                    sector=sector.name,
                )
            )

    # Ensure at least 3 candidates (use top stocks if needed)
    if len(candidate_stocks) < 3:
        fallback_stocks = [
            Stock(code="600519", name="贵州茅台", market="SH", sector="消费"),
            Stock(code="000001", name="平安银行", market="SZ", sector="金融"),
            Stock(code="000333", name="美的集团", market="SZ", sector="消费"),
        ]
        for stock in fallback_stocks:
            if stock.code not in seen_codes:
                candidate_stocks.append(stock)
                seen_codes.add(stock.code)

    logger.info(f"[{run_id}] Identified {len(candidate_stocks)} leaders from {len(hot_sectors)} sectors")

    return candidate_stocks


def _save_candidates(
    candidate_stocks: List[Stock],
    hot_sectors: List[Sector],
    hot_news: List[HotNewsItem],
    run_id: str,
) -> None:
    """
    Save candidate stocks to data/candidates/

    Args:
        candidate_stocks: List of candidate stocks
        hot_sectors: List of hot sectors
        hot_news: List of hot news items
        run_id: Run ID for logging
    """
    settings = get_settings()
    candidates_dir = Path(settings.paths.candidates_dir)
    candidates_dir.mkdir(parents=True, exist_ok=True)

    # Generate filename with run_id
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"candidates_{timestamp}_{run_id}.json"
    filepath = candidates_dir / filename

    # Build save data
    save_data = {
        "run_id": run_id,
        "timestamp": timestamp,
        "generated_at": datetime.now().isoformat(),
        "candidate_count": len(candidate_stocks),
        "hot_sectors": [s.model_dump() for s in hot_sectors],
        "hot_news_summary": [
            {
                "title": n.title,
                "sector": n.sector,
                "heat_score": n.heat_score,
            }
            for n in hot_news[:10]  # Save top 10 news summary
        ],
        "candidates": [s.model_dump() for s in candidate_stocks],
    }

    # Write to file
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(save_data, f, ensure_ascii=False, indent=2)

    logger.info(f"[{run_id}] Saved candidates to {filepath}")


# ============== LLM Analysis (Optional Enhancement) ==============


def _analyze_sectors_with_llm(hot_news: List[HotNewsItem], run_id: str) -> List[Sector]:
    """
    Analyze hot sectors using LLM (optional enhancement)

    This function uses the configured LLM to analyze news and identify
    hot sectors with reasoning. Falls back to keyword-based analysis if
    LLM fails.

    Args:
        hot_news: List of hot news items
        run_id: Run ID for logging

    Returns:
        List of Sector objects
    """
    try:
        settings = get_settings()
        llm_config = settings.llm

        # Build prompt
        news_summary = "\n".join(
            [f"- {n.title} (热度: {n.heat_score}, 板块: {n.sector})" for n in hot_news[:20]]
        )

        prompt = f"""分析以下热点新闻，识别出当前的热门板块。

热点新闻列表:
{news_summary}

请分析：
1. 哪些板块最热门？
2. 每个板块的热度分数（0-100）
3. 每个板块的龙头股代码

请以JSON格式输出，格式如下：
[
  {{
    "name": "板块名称",
    "heat_score": 85.5,
    "leaders": ["股票代码1", "股票代码2"],
    "news_count": 5
  }}
]

只输出JSON数组，不要其他内容。"""

        # Call LLM (simplified - will be enhanced with proper client)
        # For now, fall back to keyword-based analysis
        logger.info(f"[{run_id}] LLM analysis not yet implemented, using keyword-based")

        return _analyze_hot_sectors(hot_news, run_id)

    except Exception as e:
        logger.warning(f"[{run_id}] LLM analysis failed: {e}, falling back to keyword-based")
        return _analyze_hot_sectors(hot_news, run_id)