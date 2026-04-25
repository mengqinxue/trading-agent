"""
Fund Analyst node - 基本面分析

Responsibilities:
- Financial data analysis
- Industry position evaluation
- News/policy impact analysis
- Risk assessment
- Generate buy/sell/hold recommendation
"""

from datetime import datetime
from typing import Dict, List, Any

from trading_agent.graph.state import (
    WorkflowState,
    StepStatus,
    FundAnalysisResult,
    Recommendation,
    Stock,
)
from trading_agent.data_sources import DataAggregator
from trading_agent.data_sources.akshare_data import FinancialData
from trading_agent.utils.logger import get_logger

logger = get_logger("FUND_ANALYST")


def fund_analyst_node(state: WorkflowState) -> Dict:
    """
    Fund Analyst node entry function

    This node runs in parallel with tech_analyst.
    Performs fundamental analysis on candidate stocks.

    Args:
        state: Current workflow state

    Returns:
        Dict with updated state fields
    """
    run_id = state.get("run_id", "unknown")
    logger.info(f"[{run_id}] Fund Analyst node started")
    logger.info(f"[{run_id}] Status: {state.get('fund_analyst_status')}")

    # Update status to RUNNING
    updates: Dict[str, Any] = {
        "fund_analyst_status": StepStatus.RUNNING.value,
        "current_step_start": datetime.now().isoformat(),
    }

    try:
        # Load candidate stocks from screener
        candidates = state.get("candidate_stocks", [])
        logger.info(f"[{run_id}] Loaded {len(candidates)} candidate stocks")

        if not candidates:
            logger.warning(f"[{run_id}] No candidate stocks to analyze")
            updates["fund_results"] = []
            updates["fund_analyst_status"] = StepStatus.COMPLETED.value
            return updates

        # Initialize data aggregator
        aggregator = DataAggregator()

        # Analyze each candidate stock
        fund_results: List[FundAnalysisResult] = []

        for candidate in candidates:
            # Convert dict to Stock if needed
            if isinstance(candidate, dict):
                stock = Stock(**candidate)
            else:
                stock = candidate

            logger.info(f"[{run_id}] Analyzing {stock.code} - {stock.name}")

            try:
                # Step 1: Get financial data
                logger.info(f"[{run_id}] Step 1: Fetching financial data for {stock.code}")
                stock_bundle = aggregator.aggregate_stock_data(stock.code)
                financial_data = stock_bundle.financial_data

                if not financial_data or not financial_data.success:
                    logger.warning(
                        f"[{run_id}] Financial data fetch failed for {stock.code}: "
                        f"{financial_data.error if financial_data else 'No data'}"
                    )
                    # Create fallback result
                    fund_result = _create_fallback_result(stock, run_id)
                    fund_results.append(fund_result)
                    continue

                financials = financial_data.data
                logger.info(f"[{run_id}] Got {len(financials)} financial reports")

                # Step 2: Analyze financial indicators
                logger.info(f"[{run_id}] Step 2: Analyzing financial indicators")
                indicators_analysis = _analyze_financial_indicators(financials, run_id)

                # Step 3: Evaluate industry position
                logger.info(f"[{run_id}] Step 3: Evaluating industry position")
                industry_position = _evaluate_industry_position(stock, financials, run_id)

                # Step 4: Check news/policy impact
                logger.info(f"[{run_id}] Step 4: Checking news/policy impact")
                news_impact = _analyze_news_impact(stock_bundle.related_news, stock, run_id)

                # Step 5: Assess risks
                logger.info(f"[{run_id}] Step 5: Assessing risks")
                risks = _assess_risks(financials, indicators_analysis, industry_position, run_id)

                # Step 6: Identify positives
                logger.info(f"[{run_id}] Step 6: Identifying positives")
                positives = _identify_positives(financials, indicators_analysis, industry_position, run_id)

                # Step 7: Calculate fundamentals score
                logger.info(f"[{run_id}] Step 7: Calculating fundamentals score")
                fundamentals_score = _calculate_fundamentals_score(
                    indicators_analysis, industry_position, news_impact, run_id
                )

                # Step 8: Generate recommendation
                logger.info(f"[{run_id}] Step 8: Generating recommendation")
                recommendation, confidence, arguments = _generate_recommendation(
                    fundamentals_score, risks, positives, indicators_analysis, run_id
                )

                # Build FundAnalysisResult
                fund_result = FundAnalysisResult(
                    stock_code=stock.code,
                    stock_name=stock.name,
                    fundamentals_score=fundamentals_score,
                    risks=risks,
                    positives=positives,
                    recommendation=recommendation,
                    confidence=confidence,
                    arguments=arguments,
                )
                fund_results.append(fund_result)

                logger.info(
                    f"[{run_id}] Analysis complete for {stock.code}: "
                    f"score={fundamentals_score:.1f}, recommendation={recommendation.value}, "
                    f"confidence={confidence:.2f}"
                )

            except Exception as e:
                logger.error(f"[{run_id}] Failed to analyze {stock.code}: {e}")
                # Create fallback result on error
                fund_result = _create_fallback_result(stock, run_id, str(e))
                fund_results.append(fund_result)

        # Update state with results
        updates["fund_results"] = fund_results
        updates["fund_analyst_status"] = StepStatus.COMPLETED.value

        logger.info(f"[{run_id}] Fund Analyst node completed successfully")
        logger.info(f"[{run_id}] Results: {len(fund_results)} stocks analyzed")

    except Exception as e:
        logger.error(f"[{run_id}] Fund Analyst node failed: {e}")
        updates["fund_analyst_status"] = StepStatus.FAILED.value
        updates["error_step"] = "fund_analyst"
        updates["error_message"] = str(e)
        updates["fund_results"] = []

    return updates


# ============== Financial Indicator Analysis ==============


def _analyze_financial_indicators(
    financials: List[FinancialData],
    run_id: str,
) -> Dict[str, Any]:
    """
    Analyze financial indicators from financial reports

    Args:
        financials: List of financial reports
        run_id: Run ID for logging

    Returns:
        Dict containing indicator analysis results
    """
    if not financials:
        return _get_default_indicators()

    # Use latest report for analysis
    latest = financials[0]

    indicators: Dict[str, Any] = {
        "revenue": latest.revenue,
        "net_profit": latest.net_profit,
        "gross_margin": latest.gross_margin or 0,
        "net_margin": latest.net_margin or 0,
        "roe": latest.roe or 0,
        "debt_ratio": latest.debt_ratio or 0,
        "pe_ratio": latest.pe_ratio or 0,
        "pb_ratio": latest.pb_ratio or 0,
    }

    # Calculate revenue growth (if multiple reports available)
    if len(financials) >= 2:
        prev = financials[1]
        if prev.revenue > 0:
            revenue_growth = (latest.revenue - prev.revenue) / prev.revenue * 100
            indicators["revenue_growth"] = round(revenue_growth, 2)
        else:
            indicators["revenue_growth"] = 0.0

        # Calculate net profit growth
        if prev.net_profit > 0:
            profit_growth = (latest.net_profit - prev.net_profit) / prev.net_profit * 100
            indicators["profit_growth"] = round(profit_growth, 2)
        else:
            indicators["profit_growth"] = 0.0
    else:
        indicators["revenue_growth"] = 0.0
        indicators["profit_growth"] = 0.0

    logger.info(
        f"[{run_id}] Financial indicators: "
        f"revenue={indicators['revenue']:.2f}亿, "
        f"net_profit={indicators['net_profit']:.2f}亿, "
        f"revenue_growth={indicators['revenue_growth']:.2f}%, "
        f"profit_growth={indicators['profit_growth']:.2f}%, "
        f"roe={indicators['roe']:.2f}%, "
        f"pe={indicators['pe_ratio']:.2f}"
    )

    return indicators


def _get_default_indicators() -> Dict[str, Any]:
    """Return default neutral indicators when calculation fails"""
    return {
        "revenue": 0.0,
        "net_profit": 0.0,
        "gross_margin": 0.0,
        "net_margin": 0.0,
        "roe": 0.0,
        "debt_ratio": 0.0,
        "pe_ratio": 0.0,
        "pb_ratio": 0.0,
        "revenue_growth": 0.0,
        "profit_growth": 0.0,
    }


# ============== Industry Position Evaluation ==============


def _evaluate_industry_position(
    stock: Stock,
    financials: List[FinancialData],
    run_id: str,
) -> Dict[str, Any]:
    """
    Evaluate industry position and competitive advantage

    Simplified implementation for MVP.

    Args:
        stock: Stock information
        financials: Financial data
        run_id: Run ID for logging

    Returns:
        Dict containing industry position analysis
    """
    # Mock industry position evaluation
    sector = stock.sector or "未知"

    # Basic evaluation based on financial metrics
    if not financials:
        return {
            "sector": sector,
            "position": "unknown",
            "competitive_advantage": "unknown",
            "position_score": 50,
        }

    latest = financials[0]
    position_score = 50  # Default neutral score

    # Adjust score based on metrics
    if latest.roe and latest.roe > 15:
        position_score += 15  # High ROE indicates strong position
    elif latest.roe and latest.roe < 5:
        position_score -= 10  # Low ROE indicates weak position

    if latest.net_margin and latest.net_margin > 20:
        position_score += 10  # High margin indicates pricing power
    elif latest.net_margin and latest.net_margin < 5:
        position_score -= 10  # Low margin indicates weak competitive position

    # Determine position description
    if position_score >= 70:
        position = "leader"  # Industry leader
        advantage = "strong"
    elif position_score >= 50:
        position = "challenger"  # Industry challenger
        advantage = "moderate"
    else:
        position = "follower"  # Industry follower
        advantage = "weak"

    result = {
        "sector": sector,
        "position": position,
        "competitive_advantage": advantage,
        "position_score": min(100, max(0, position_score)),
    }

    logger.info(
        f"[{run_id}] Industry position: sector={sector}, position={position}, "
        f"advantage={advantage}, score={position_score}"
    )

    return result


# ============== News Impact Analysis ==============


def _analyze_news_impact(
    related_news: List[Any],
    stock: Stock,
    run_id: str,
) -> Dict[str, Any]:
    """
    Analyze news and policy impact on stock

    Simplified implementation for MVP.

    Args:
        related_news: List of related hot news
        stock: Stock information
        run_id: Run ID for logging

    Returns:
        Dict containing news impact analysis
    """
    if not related_news:
        logger.info(f"[{run_id}] No related news found for {stock.code}")
        return {
            "impact": "neutral",
            "news_count": 0,
            "positive_news": 0,
            "negative_news": 0,
            "impact_score": 0,
        }

    # Count news items (simplified - mock positive/negative classification)
    news_count = len(related_news)
    # Mock: assume 60% positive, 40% negative for demo
    positive_news = int(news_count * 0.6)
    negative_news = news_count - positive_news

    # Calculate impact score
    impact_score = positive_news - negative_news

    if impact_score > 2:
        impact = "positive"
    elif impact_score < -2:
        impact = "negative"
    else:
        impact = "neutral"

    result = {
        "impact": impact,
        "news_count": news_count,
        "positive_news": positive_news,
        "negative_news": negative_news,
        "impact_score": impact_score,
    }

    logger.info(
        f"[{run_id}] News impact: impact={impact}, "
        f"positive={positive_news}, negative={negative_news}, score={impact_score}"
    )

    return result


# ============== Risk Assessment ==============


def _assess_risks(
    financials: List[FinancialData],
    indicators_analysis: Dict[str, Any],
    industry_position: Dict[str, Any],
    run_id: str,
) -> List[str]:
    """
    Assess potential risks from financial and industry analysis

    Args:
        financials: Financial data
        indicators_analysis: Financial indicators analysis
        industry_position: Industry position analysis
        run_id: Run ID for logging

    Returns:
        List of identified risk factors
    """
    risks: List[str] = []

    # Financial risks
    debt_ratio = indicators_analysis.get("debt_ratio", 0)
    if debt_ratio > 70:
        risks.append(f"高负债率风险({debt_ratio:.1f}%)")

    profit_growth = indicators_analysis.get("profit_growth", 0)
    if profit_growth < -10:
        risks.append(f"利润下滑风险(同比{profit_growth:.1f}%)")

    revenue_growth = indicators_analysis.get("revenue_growth", 0)
    if revenue_growth < -5:
        risks.append(f"营收下滑风险(同比{revenue_growth:.1f}%)")

    pe_ratio = indicators_analysis.get("pe_ratio", 0)
    if pe_ratio > 50:
        risks.append(f"估值偏高风险(PE={pe_ratio:.1f})")

    # Industry risks
    position = industry_position.get("position", "unknown")
    if position == "follower":
        risks.append("行业地位较弱，竞争压力大")

    advantage = industry_position.get("competitive_advantage", "unknown")
    if advantage == "weak":
        risks.append("竞争优势不明显")

    logger.info(f"[{run_id}] Identified risks: {risks}")

    return risks


# ============== Positives Identification ==============


def _identify_positives(
    financials: List[FinancialData],
    indicators_analysis: Dict[str, Any],
    industry_position: Dict[str, Any],
    run_id: str,
) -> List[str]:
    """
    Identify positive factors from financial and industry analysis

    Args:
        financials: Financial data
        indicators_analysis: Financial indicators analysis
        industry_position: Industry position analysis
        run_id: Run ID for logging

    Returns:
        List of identified positive factors
    """
    positives: List[str] = []

    # Financial positives
    roe = indicators_analysis.get("roe", 0)
    if roe > 15:
        positives.append(f"高ROE表现({roe:.1f}%)，盈利能力强")

    net_margin = indicators_analysis.get("net_margin", 0)
    if net_margin > 20:
        positives.append(f"高净利率({net_margin:.1f}%)，经营效率高")

    profit_growth = indicators_analysis.get("profit_growth", 0)
    if profit_growth > 15:
        positives.append(f"利润快速增长(同比{profit_growth:.1f}%)")

    revenue_growth = indicators_analysis.get("revenue_growth", 0)
    if revenue_growth > 10:
        positives.append(f"营收稳健增长(同比{revenue_growth:.1f}%)")

    pe_ratio = indicators_analysis.get("pe_ratio", 0)
    if pe_ratio < 15 and pe_ratio > 0:
        positives.append(f"估值合理(PE={pe_ratio:.1f})，具备安全边际")

    debt_ratio = indicators_analysis.get("debt_ratio", 0)
    if debt_ratio < 40:
        positives.append(f"低负债率({debt_ratio:.1f}%)，财务稳健")

    # Industry positives
    position = industry_position.get("position", "unknown")
    if position == "leader":
        positives.append("行业龙头地位，竞争优势明显")

    advantage = industry_position.get("competitive_advantage", "unknown")
    if advantage == "strong":
        positives.append("竞争优势强劲，护城河深厚")

    logger.info(f"[{run_id}] Identified positives: {positives}")

    return positives


# ============== Fundamentals Score Calculation ==============


def _calculate_fundamentals_score(
    indicators_analysis: Dict[str, Any],
    industry_position: Dict[str, Any],
    news_impact: Dict[str, Any],
    run_id: str,
) -> float:
    """
    Calculate overall fundamentals score (0-100)

    Args:
        indicators_analysis: Financial indicators analysis
        industry_position: Industry position analysis
        news_impact: News impact analysis
        run_id: Run ID for logging

    Returns:
        Fundamentals score (0-100)
    """
    score = 50.0  # Base score

    # Financial indicators contribution (max +30/-30)
    roe = indicators_analysis.get("roe", 0)
    if roe > 20:
        score += 10
    elif roe > 15:
        score += 7
    elif roe > 10:
        score += 3
    elif roe < 5:
        score -= 8

    revenue_growth = indicators_analysis.get("revenue_growth", 0)
    if revenue_growth > 20:
        score += 10
    elif revenue_growth > 10:
        score += 5
    elif revenue_growth > 0:
        score += 2
    elif revenue_growth < -10:
        score -= 10
    elif revenue_growth < 0:
        score -= 5

    profit_growth = indicators_analysis.get("profit_growth", 0)
    if profit_growth > 20:
        score += 10
    elif profit_growth > 10:
        score += 5
    elif profit_growth > 0:
        score += 2
    elif profit_growth < -15:
        score -= 10
    elif profit_growth < 0:
        score -= 5

    # Industry position contribution (max +20/-20)
    position_score = industry_position.get("position_score", 50)
    position_adjustment = (position_score - 50) * 0.4
    score += position_adjustment

    # News impact contribution (max +10/-10)
    news_impact_score = news_impact.get("impact_score", 0)
    score += news_impact_score * 2

    # Clamp to 0-100
    final_score = min(100, max(0, score))

    logger.info(f"[{run_id}] Fundamentals score: {final_score:.1f}")

    return round(final_score, 1)


# ============== Recommendation Generation ==============


def _generate_recommendation(
    fundamentals_score: float,
    risks: List[str],
    positives: List[str],
    indicators_analysis: Dict[str, Any],
    run_id: str,
) -> tuple[Recommendation, float, List[str]]:
    """
    Generate buy/sell/hold recommendation based on fundamentals

    Args:
        fundamentals_score: Overall fundamentals score (0-100)
        risks: List of identified risks
        positives: List of identified positives
        indicators_analysis: Financial indicators analysis
        run_id: Run ID for logging

    Returns:
        Tuple of (Recommendation, confidence, arguments)
    """
    arguments: List[str] = []

    # Build arguments from positives and risks
    if positives:
        arguments.extend(positives)

    if risks:
        # Add risks as warnings
        arguments.append(f"风险因素: {', '.join(risks)}")

    # Determine recommendation based on score
    if fundamentals_score >= 70:
        recommendation = Recommendation.BUY
        confidence = 0.7 + (fundamentals_score - 70) * 0.005
        if not any(p for p in positives if "龙头" in p or "竞争优势" in p):
            arguments.append("基本面综合评分优秀")
    elif fundamentals_score >= 50:
        recommendation = Recommendation.HOLD
        confidence = 0.5 + (fundamentals_score - 50) * 0.01
        arguments.append("基本面表现稳健，建议持有观察")
    else:
        recommendation = Recommendation.SELL
        confidence = 0.6 + (50 - fundamentals_score) * 0.005
        arguments.append("基本面综合评分偏低，建议谨慎")

    # Adjust confidence based on risk count
    if len(risks) > 3:
        confidence = max(0.3, confidence - 0.1)
        arguments.append("存在多项风险因素，降低置信度")

    # Adjust confidence based on PE ratio
    pe_ratio = indicators_analysis.get("pe_ratio", 0)
    if pe_ratio > 100:
        confidence = max(0.3, confidence - 0.15)
        arguments.append(f"估值过高(PE={pe_ratio:.1f})，投资风险较大")
    elif pe_ratio < 0:
        # Negative PE means negative earnings (loss)
        confidence = max(0.2, confidence - 0.2)
        arguments.append("公司处于亏损状态，基本面风险较高")

    confidence = min(0.95, confidence)

    logger.info(
        f"[{run_id}] Recommendation: {recommendation.value}, "
        f"confidence: {confidence:.2f}"
    )

    return (recommendation, round(confidence, 2), arguments)


# ============== Fallback Result ==============


def _create_fallback_result(
    stock: Stock,
    run_id: str,
    error_msg: str = "财务数据获取失败",
) -> FundAnalysisResult:
    """
    Create a fallback FundAnalysisResult when analysis fails

    Args:
        stock: Stock info
        run_id: Run ID for logging
        error_msg: Error message

    Returns:
        FundAnalysisResult with HOLD recommendation and low confidence
    """
    logger.warning(f"[{run_id}] Creating fallback result for {stock.code}: {error_msg}")

    return FundAnalysisResult(
        stock_code=stock.code,
        stock_name=stock.name,
        fundamentals_score=30.0,
        risks=[f"分析失败: {error_msg}"],
        positives=["数据不足，无法判断"],
        recommendation=Recommendation.HOLD,
        confidence=0.3,
        arguments=["基本面分析数据不足，建议观望或结合技术面分析"],
    )