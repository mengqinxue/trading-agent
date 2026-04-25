"""
Aggregator node - 分析结果汇总

Responsibilities:
- Merge tech_results + fund_results
- Calculate combined score
- Extract buy/sell arguments
- Generate analysis summary
"""

from datetime import datetime
from typing import Dict, List, Any

from trading_agent.graph.state import (
    WorkflowState,
    StepStatus,
    AnalysisSummary,
    TechAnalysisResult,
    FundAnalysisResult,
    Recommendation,
    Stock,
)
from trading_agent.utils.logger import get_logger

logger = get_logger("AGGREGATOR")


def aggregator_node(state: WorkflowState) -> Dict:
    """
    Aggregator node entry function

    This node waits for both tech_analyst and fund_analyst to complete,
    then merges and summarizes their results.

    Args:
        state: Current workflow state

    Returns:
        Dict with updated state fields
    """
    run_id = state.get("run_id", "unknown")
    logger.info(f"[{run_id}] Aggregator node started")

    # Check prerequisites
    tech_status = state.get("tech_analyst_status")
    fund_status = state.get("fund_analyst_status")

    logger.info(f"[{run_id}] Prerequisites: tech={tech_status}, fund={fund_status}")

    # Update status to RUNNING
    updates: Dict[str, Any] = {
        "aggregator_status": StepStatus.RUNNING.value,
        "current_step_start": datetime.now().isoformat(),
    }

    try:
        # Load analysis results
        tech_results = state.get("tech_results", [])
        fund_results = state.get("fund_results", [])
        candidates = state.get("candidate_stocks", [])

        logger.info(f"[{run_id}] Tech results: {len(tech_results)}")
        logger.info(f"[{run_id}] Fund results: {len(fund_results)}")
        logger.info(f"[{run_id}] Total candidates: {len(candidates)}")

        if not tech_results and not fund_results:
            logger.warning(f"[{run_id}] No analysis results to aggregate")
            updates["analysis_summary"] = []
            updates["aggregator_status"] = StepStatus.COMPLETED.value
            return updates

        # Step 1: Match results by stock_code
        logger.info(f"[{run_id}] Step 1: Matching results by stock_code")
        matched_results = _match_results(tech_results, fund_results, candidates, run_id)

        # Step 2-5: Generate analysis summaries
        logger.info(f"[{run_id}] Step 2: Generating analysis summaries")
        analysis_summaries = []

        for matched in matched_results:
            stock_code = matched.get("stock_code", "unknown")
            logger.info(f"[{run_id}] Aggregating {stock_code}")

            # Calculate combined score
            logger.info(f"[{run_id}] Step 3: Calculating combined score")
            tech_score, fund_score, combined_score = _calculate_combined_score(
                matched.get("tech_result"),
                matched.get("fund_result"),
                run_id,
            )

            # Extract buy arguments
            logger.info(f"[{run_id}] Step 4: Extracting buy arguments")
            buy_arguments = _extract_buy_arguments(
                matched.get("tech_result"),
                matched.get("fund_result"),
                run_id,
            )

            # Extract sell arguments
            logger.info(f"[{run_id}] Step 5: Extracting sell arguments")
            sell_arguments = _extract_sell_arguments(
                matched.get("tech_result"),
                matched.get("fund_result"),
                run_id,
            )

            # Build AnalysisSummary
            summary = AnalysisSummary(
                stock_code=stock_code,
                stock_name=matched.get("stock_name", ""),
                tech_score=tech_score,
                fund_score=fund_score,
                combined_score=combined_score,
                buy_arguments=buy_arguments,
                sell_arguments=sell_arguments,
            )
            analysis_summaries.append(summary)

            logger.info(
                f"[{run_id}] Summary for {stock_code}: "
                f"tech={tech_score:.1f}, fund={fund_score:.1f}, combined={combined_score:.1f}"
            )

        # Update state with summaries
        updates["analysis_summary"] = analysis_summaries
        updates["aggregator_status"] = StepStatus.COMPLETED.value

        logger.info(f"[{run_id}] Aggregator node completed successfully")
        logger.info(f"[{run_id}] Summary entries: {len(analysis_summaries)}")

    except Exception as e:
        logger.error(f"[{run_id}] Aggregator node failed: {e}")
        updates["aggregator_status"] = StepStatus.FAILED.value
        updates["error_step"] = "aggregator"
        updates["error_message"] = str(e)
        updates["analysis_summary"] = []

    return updates


# ============== Result Matching ==============


def _match_results(
    tech_results: List[Any],
    fund_results: List[Any],
    candidates: List[Any],
    run_id: str,
) -> List[Dict[str, Any]]:
    """
    Match tech and fund results by stock_code

    Args:
        tech_results: List of TechAnalysisResult
        fund_results: List of FundAnalysisResult
        candidates: List of candidate stocks
        run_id: Run ID for logging

    Returns:
        List of matched result dicts
    """
    # Convert to dicts if needed
    tech_by_code: Dict[str, Any] = {}
    for result in tech_results:
        if isinstance(result, dict):
            tech_by_code[result.get("stock_code")] = result
        else:
            tech_by_code[result.stock_code] = result

    fund_by_code: Dict[str, Any] = {}
    for result in fund_results:
        if isinstance(result, dict):
            fund_by_code[result.get("stock_code")] = result
        else:
            fund_by_code[result.stock_code] = result

    # Get all stock codes from candidates
    candidate_codes: set = set()
    stock_names: Dict[str, str] = {}

    for candidate in candidates:
        if isinstance(candidate, dict):
            code = candidate.get("code")
            name = candidate.get("name", "")
        else:
            code = candidate.code
            name = candidate.name
        candidate_codes.add(code)
        stock_names[code] = name

    # Also include codes from results
    for code in list(tech_by_code.keys()) + list(fund_by_code.keys()):
        if code not in stock_names:
            # Get name from result
            tech_r = tech_by_code.get(code)
            fund_r = fund_by_code.get(code)
            if tech_r:
                if isinstance(tech_r, dict):
                    stock_names[code] = tech_r.get("stock_name", "")
                else:
                    stock_names[code] = tech_r.stock_name
            elif fund_r:
                if isinstance(fund_r, dict):
                    stock_names[code] = fund_r.get("stock_name", "")
                else:
                    stock_names[code] = fund_r.stock_name

    matched: List[Dict[str, Any]] = []

    for code in set(list(candidate_codes) + list(tech_by_code.keys()) + list(fund_by_code.keys())):
        matched.append({
            "stock_code": code,
            "stock_name": stock_names.get(code, ""),
            "tech_result": tech_by_code.get(code),
            "fund_result": fund_by_code.get(code),
        })

    logger.info(f"[{run_id}] Matched {len(matched)} stock results")

    return matched


# ============== Score Calculation ==============


def _calculate_combined_score(
    tech_result: Any,
    fund_result: Any,
    run_id: str,
) -> tuple[float, float, float]:
    """
    Calculate combined score from tech and fund results

    Score weighting:
    - Technical score: 40% weight
    - Fundamental score: 60% weight

    Args:
        tech_result: TechAnalysisResult or None
        fund_result: FundAnalysisResult or None
        run_id: Run ID for logging

    Returns:
        Tuple of (tech_score, fund_score, combined_score)
    """
    tech_score = 50.0  # Default neutral
    fund_score = 50.0  # Default neutral

    # Calculate tech score (0-100)
    if tech_result:
        if isinstance(tech_result, dict):
            recommendation = tech_result.get("recommendation", "hold")
            confidence = tech_result.get("confidence", 0.5)
            trend = tech_result.get("trend_direction", "neutral")
        else:
            recommendation = tech_result.recommendation.value if tech_result.recommendation else "hold"
            confidence = tech_result.confidence
            trend = tech_result.trend_direction

        # Convert recommendation + confidence to score
        if recommendation == "buy":
            tech_score = 50 + confidence * 50  # 50-100
        elif recommendation == "sell":
            tech_score = 50 - confidence * 50  # 0-50
        else:
            tech_score = 50

        # Adjust by trend
        if trend == "up":
            tech_score += 10
        elif trend == "down":
            tech_score -= 10

        tech_score = min(100, max(0, tech_score))

    # Calculate fund score (0-100)
    if fund_result:
        if isinstance(fund_result, dict):
            fundamentals_score = fund_result.get("fundamentals_score", 50)
            recommendation = fund_result.get("recommendation", "hold")
            confidence = fund_result.get("confidence", 0.5)
        else:
            fundamentals_score = fund_result.fundamentals_score
            recommendation = fund_result.recommendation.value if fund_result.recommendation else "hold"
            confidence = fund_result.confidence

        # Use fundamentals_score as base
        fund_score = fundamentals_score

        # Adjust by recommendation
        if recommendation == "buy":
            fund_score += 5
        elif recommendation == "sell":
            fund_score -= 5

        # Adjust by confidence (high confidence = stronger signal)
        if confidence > 0.7:
            fund_score = fund_score * 1.1
        elif confidence < 0.4:
            fund_score = fund_score * 0.9

        fund_score = min(100, max(0, fund_score))

    # Combined score: 40% tech + 60% fund
    combined_score = tech_score * 0.4 + fund_score * 0.6

    logger.info(
        f"[{run_id}] Scores: tech={tech_score:.1f}, fund={fund_score:.1f}, combined={combined_score:.1f}"
    )

    return (round(tech_score, 1), round(fund_score, 1), round(combined_score, 1))


# ============== Argument Extraction ==============


def _extract_buy_arguments(
    tech_result: Any,
    fund_result: Any,
    run_id: str,
) -> List[str]:
    """
    Extract buy-supporting arguments from analysis results

    Args:
        tech_result: TechAnalysisResult or None
        fund_result: FundAnalysisResult or None
        run_id: Run ID for logging

    Returns:
        List of buy arguments
    """
    buy_arguments: List[str] = []

    # From tech result
    if tech_result:
        if isinstance(tech_result, dict):
            recommendation = tech_result.get("recommendation", "hold")
            arguments = tech_result.get("arguments", [])
            signals = tech_result.get("signals", [])
            trend = tech_result.get("trend_direction", "neutral")
        else:
            recommendation = tech_result.recommendation.value if tech_result.recommendation else "hold"
            arguments = tech_result.arguments or []
            signals = tech_result.signals or []
            trend = tech_result.trend_direction

        if recommendation == "buy":
            buy_arguments.extend(arguments)

        # Add trend signals
        if trend == "up":
            buy_arguments.append("技术面趋势向上")

        # Add bullish signals
        for signal in signals:
            if any(kw in signal for kw in ["金叉", "超卖", "流入", "突破", "阳包阴", "连阳"]):
                buy_arguments.append(f"[技术] {signal}")

    # From fund result
    if fund_result:
        if isinstance(fund_result, dict):
            recommendation = fund_result.get("recommendation", "hold")
            positives = fund_result.get("positives", [])
            fundamentals_score = fund_result.get("fundamentals_score", 50)
        else:
            recommendation = fund_result.recommendation.value if fund_result.recommendation else "hold"
            positives = fund_result.positives or []
            fundamentals_score = fund_result.fundamentals_score

        if recommendation == "buy":
            buy_arguments.extend(positives)

        # Add fundamentals arguments
        if fundamentals_score >= 70:
            buy_arguments.append("基本面评分优秀")

    # Deduplicate
    buy_arguments = list(set(buy_arguments))

    logger.info(f"[{run_id}] Buy arguments: {len(buy_arguments)}")

    return buy_arguments


def _extract_sell_arguments(
    tech_result: Any,
    fund_result: Any,
    run_id: str,
) -> List[str]:
    """
    Extract sell-supporting arguments from analysis results

    Args:
        tech_result: TechAnalysisResult or None
        fund_result: FundAnalysisResult or None
        run_id: Run ID for logging

    Returns:
        List of sell arguments
    """
    sell_arguments: List[str] = []

    # From tech result
    if tech_result:
        if isinstance(tech_result, dict):
            recommendation = tech_result.get("recommendation", "hold")
            arguments = tech_result.get("arguments", [])
            signals = tech_result.get("signals", [])
            trend = tech_result.get("trend_direction", "neutral")
        else:
            recommendation = tech_result.recommendation.value if tech_result.recommendation else "hold"
            arguments = tech_result.arguments or []
            signals = tech_result.signals or []
            trend = tech_result.trend_direction

        if recommendation == "sell":
            sell_arguments.extend(arguments)

        # Add trend signals
        if trend == "down":
            sell_arguments.append("技术面趋势向下")

        # Add bearish signals
        for signal in signals:
            if any(kw in signal for kw in ["死叉", "超买", "流出", "阴包阳", "连阴"]):
                sell_arguments.append(f"[技术] {signal}")

    # From fund result
    if fund_result:
        if isinstance(fund_result, dict):
            recommendation = fund_result.get("recommendation", "hold")
            risks = fund_result.get("risks", [])
            fundamentals_score = fund_result.get("fundamentals_score", 50)
        else:
            recommendation = fund_result.recommendation.value if fund_result.recommendation else "hold"
            risks = fund_result.risks or []
            fundamentals_score = fund_result.fundamentals_score

        if recommendation == "sell":
            sell_arguments.extend(risks)

        # Add fundamentals arguments
        if fundamentals_score < 40:
            sell_arguments.append("基本面评分偏低")

        # Always include risks as sell factors
        for risk in risks:
            sell_arguments.append(f"[风险] {risk}")

    # Deduplicate
    sell_arguments = list(set(sell_arguments))

    logger.info(f"[{run_id}] Sell arguments: {len(sell_arguments)}")

    return sell_arguments