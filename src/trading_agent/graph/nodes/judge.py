"""
Judge node - 评委决策 V2

Responsibilities:
- Combine analysis results + debate results
- Evaluate risk/reward ratio
- **Attribution Analysis**: Explain buy reasons with causal chain
- **Counterfactual Analysis**: Analyze impact if stock drops
- Generate final decision
"""

from datetime import datetime
from typing import Dict, List, Any

from trading_agent.graph.state import (
    WorkflowState,
    StepStatus,
    Decision,
    Recommendation,
    CausalChain,
    CounterfactualAnalysis,
    CounterfactualScenario,
    AnalysisSummary,
    Sector,
)
from trading_agent.utils.logger import get_logger

logger = get_logger("JUDGE")


def judge_node(state: WorkflowState) -> Dict:
    """
    Judge node entry function

    This node makes final decision based on all previous analysis.
    Includes:
    1. Attribution analysis (causal chain)
    2. Counterfactual analysis (what if stock drops)

    Args:
        state: Current workflow state

    Returns:
        Dict with updated state fields
    """
    run_id = state.get("run_id", "unknown")
    logger.info(f"[{run_id}] Judge node started")
    logger.info(f"[{run_id}] Status: {state.get('judge_status')}")

    # Update status to RUNNING
    updates: Dict[str, Any] = {
        "judge_status": StepStatus.RUNNING.value,
        "current_step_start": datetime.now().isoformat(),
    }

    try:
        # Load all previous results
        analysis_summary = state.get("analysis_summary", [])
        debate_log = state.get("debate_log", [])
        buyer_score = state.get("buyer_score", 0.0)
        seller_score = state.get("seller_score", 0.0)
        portfolio = state.get("portfolio", {})
        hot_sectors = state.get("hot_sectors", [])
        tech_results = state.get("tech_results", [])
        fund_results = state.get("fund_results", [])

        logger.info(f"[{run_id}] Analysis: {len(analysis_summary)} entries")
        logger.info(f"[{run_id}] Debate rounds: {len(debate_log)}")
        logger.info(f"[{run_id}] Buyer score: {buyer_score}, Seller score: {seller_score}")
        logger.info(f"[{run_id}] Hot sectors: {len(hot_sectors)}")

        if not analysis_summary:
            logger.warning(f"[{run_id}] No analysis summary to judge")
            updates["decision"] = {}
            updates["judge_status"] = StepStatus.COMPLETED.value
            return updates

        # Pick the most promising stock for decision
        # Sort by combined_score descending
        summaries = []
        for s in analysis_summary:
            if isinstance(s, dict):
                summaries.append(AnalysisSummary(**s))
            else:
                summaries.append(s)

        summaries.sort(key=lambda x: x.combined_score, reverse=True)
        target_summary = summaries[0]

        stock_code = target_summary.stock_code
        stock_name = target_summary.stock_name

        logger.info(f"[{run_id}] Target stock: {stock_code} - {stock_name}")
        logger.info(f"[{run_id}] Combined score: {target_summary.combined_score:.1f}")

        # Step 1: Combine all analysis results
        logger.info(f"[{run_id}] Step 1: Combining analysis results")
        combined_analysis = _combine_analysis(
            target_summary, tech_results, fund_results, buyer_score, seller_score, run_id
        )

        # Step 2: Consider debate scores
        logger.info(f"[{run_id}] Step 2: Considering debate scores")
        debate_influence = _calculate_debate_influence(buyer_score, seller_score, run_id)

        # Step 3: Check portfolio position
        logger.info(f"[{run_id}] Step 3: Checking portfolio position")
        current_position = _check_portfolio_position(stock_code, portfolio, run_id)

        # Step 4: Evaluate risk/reward
        logger.info(f"[{run_id}] Step 4: Evaluating risk/reward")
        risk_reward = _evaluate_risk_reward(
            target_summary, current_position, debate_influence, run_id
        )

        # Step 5: Attribution Analysis (归因分析)
        logger.info(f"[{run_id}] Step 5: Building attribution causal chain")
        causal_chain = _build_causal_chain(
            hot_sectors, target_summary, buyer_score, seller_score, combined_analysis, run_id
        )

        # Step 6: Counterfactual Analysis (反事实推断)
        logger.info(f"[{run_id}] Step 6: Building counterfactual analysis")
        counterfactual = _build_counterfactual_analysis(
            target_summary, portfolio, current_position, run_id
        )

        # Step 7: Generate final decision
        logger.info(f"[{run_id}] Step 7: Generating final decision")
        decision = _generate_decision(
            stock_code,
            stock_name,
            target_summary,
            debate_influence,
            risk_reward,
            causal_chain,
            counterfactual,
            current_position,
            run_id,
        )

        updates["decision"] = decision.model_dump()

        # Update status to COMPLETED
        updates["judge_status"] = StepStatus.COMPLETED.value

        logger.info(f"[{run_id}] Judge node completed successfully")
        logger.info(f"[{run_id}] Decision: {decision.action.value}")
        logger.info(f"[{run_id}] Confidence: {decision.confidence:.2f}")
        logger.info(f"[{run_id}] Should enter: {decision.should_enter}")
        logger.info(f"[{run_id}] Risk level: {decision.risk_level}")

    except Exception as e:
        logger.error(f"[{run_id}] Judge node failed: {e}")
        updates["judge_status"] = StepStatus.FAILED.value
        updates["error_step"] = "judge"
        updates["error_message"] = str(e)
        updates["decision"] = {}

    return updates


# ============== Analysis Combination ==============


def _combine_analysis(
    summary: AnalysisSummary,
    tech_results: List[Any],
    fund_results: List[Any],
    buyer_score: float,
    seller_score: float,
    run_id: str,
) -> Dict[str, Any]:
    """
    Combine all analysis results into a unified view

    Args:
        summary: Analysis summary
        tech_results: Technical analysis results
        fund_results: Fundamental analysis results
        buyer_score: Buyer debate score
        seller_score: Seller debate score
        run_id: Run ID for logging

    Returns:
        Combined analysis dict
    """
    combined = {
        "tech_score": summary.tech_score,
        "fund_score": summary.fund_score,
        "combined_score": summary.combined_score,
        "buy_arguments": summary.buy_arguments,
        "sell_arguments": summary.sell_arguments,
        "buyer_score": buyer_score,
        "seller_score": seller_score,
    }

    # Find tech result for this stock
    for result in tech_results:
        if isinstance(result, dict):
            if result.get("stock_code") == summary.stock_code:
                combined["tech_recommendation"] = result.get("recommendation", "hold")
                combined["tech_confidence"] = result.get("confidence", 0.5)
                combined["tech_trend"] = result.get("trend_direction", "neutral")
                break
        else:
            if result.stock_code == summary.stock_code:
                combined["tech_recommendation"] = result.recommendation.value
                combined["tech_confidence"] = result.confidence
                combined["tech_trend"] = result.trend_direction
                break

    # Find fund result for this stock
    for result in fund_results:
        if isinstance(result, dict):
            if result.get("stock_code") == summary.stock_code:
                combined["fund_recommendation"] = result.get("recommendation", "hold")
                combined["fund_confidence"] = result.get("confidence", 0.5)
                combined["fund_risks"] = result.get("risks", [])
                break
        else:
            if result.stock_code == summary.stock_code:
                combined["fund_recommendation"] = result.recommendation.value
                combined["fund_confidence"] = result.confidence
                combined["fund_risks"] = result.risks
                break

    logger.info(f"[{run_id}] Combined analysis score: {combined['combined_score']:.1f}")

    return combined


def _calculate_debate_influence(
    buyer_score: float,
    seller_score: float,
    run_id: str,
) -> Dict[str, Any]:
    """
    Calculate debate influence on decision

    Args:
        buyer_score: Buyer's debate score
        seller_score: Seller's debate score
        run_id: Run ID for logging

    Returns:
        Debate influence dict
    """
    # Calculate winner and margin
    if buyer_score > seller_score:
        winner = "buyer"
        margin = buyer_score - seller_score
    else:
        winner = "seller"
        margin = seller_score - buyer_score

    # Strong signal if margin > 20
    strong_signal = margin > 20

    # Influence weight (0-1)
    influence_weight = min(margin / 50, 0.3)

    logger.info(
        f"[{run_id}] Debate winner: {winner}, margin: {margin:.1f}, "
        f"strong: {strong_signal}, weight: {influence_weight:.2f}"
    )

    return {
        "winner": winner,
        "margin": margin,
        "strong_signal": strong_signal,
        "influence_weight": influence_weight,
        "buyer_score": buyer_score,
        "seller_score": seller_score,
    }


def _check_portfolio_position(
    stock_code: str,
    portfolio: dict,
    run_id: str,
) -> Dict[str, Any]:
    """
    Check if stock is already in portfolio

    Args:
        stock_code: Stock code to check
        portfolio: Current portfolio state
        run_id: Run ID for logging

    Returns:
        Current position info dict
    """
    positions = portfolio.get("positions", [])

    for pos in positions:
        if pos.get("symbol") == stock_code:
            position = {
                "holding": True,
                "quantity": pos.get("quantity", 0),
                "avg_cost": pos.get("avg_cost", 0),
                "current_price": pos.get("current_price", 0),
                "pnl_pct": pos.get("pnl_pct", 0),
                "weight": pos.get("weight", 0),
            }
            logger.info(
                f"[{run_id}] Holding {stock_code}: "
                f"qty={position['quantity']}, pnl={position['pnl_pct']:.1f}%"
            )
            return position

    logger.info(f"[{run_id}] Not holding {stock_code}")

    return {
        "holding": False,
        "quantity": 0,
        "avg_cost": 0,
        "current_price": 0,
        "pnl_pct": 0,
        "weight": 0,
    }


def _evaluate_risk_reward(
    summary: AnalysisSummary,
    current_position: Dict[str, Any],
    debate_influence: Dict[str, Any],
    run_id: str,
) -> Dict[str, Any]:
    """
    Evaluate risk/reward ratio

    Args:
        summary: Analysis summary
        current_position: Current position info
        debate_influence: Debate influence
        run_id: Run ID for logging

    Returns:
        Risk/reward evaluation dict
    """
    # Base risk level from scores
    if summary.combined_score >= 70:
        base_risk = "low"
        reward_potential = "high"
    elif summary.combined_score >= 50:
        base_risk = "medium"
        reward_potential = "medium"
    else:
        base_risk = "high"
        reward_potential = "low"

    # Adjust for debate result
    if debate_influence["winner"] == "seller" and debate_influence["strong_signal"]:
        # Seller won strongly - higher risk
        if base_risk == "low":
            base_risk = "medium"
        elif base_risk == "medium":
            base_risk = "high"

    # Calculate risk/reward ratio
    reward_score = summary.combined_score
    risk_score = 100 - summary.combined_score + (len(summary.sell_arguments) * 5)

    risk_reward_ratio = reward_score / risk_score if risk_score > 0 else 1.0

    logger.info(
        f"[{run_id}] Risk/reward: risk={base_risk}, reward={reward_potential}, "
        f"ratio={risk_reward_ratio:.2f}"
    )

    return {
        "risk_level": base_risk,
        "reward_potential": reward_potential,
        "risk_reward_ratio": round(risk_reward_ratio, 2),
        "risk_score": risk_score,
        "reward_score": reward_score,
    }


# ============== Attribution Analysis ==============


def _build_causal_chain(
    hot_sectors: List[Any],
    summary: AnalysisSummary,
    buyer_score: float,
    seller_score: float,
    combined_analysis: Dict[str, Any],
    run_id: str,
) -> CausalChain:
    """
    Build attribution causal chain

    Example:
    A(热点板块炒作) → B(龙头股关注度提升) → C(技术面突破信号) → D(基本面支撑) → E(买入建议)

    Each step should have evidence/data support.

    Args:
        hot_sectors: List of hot sectors
        summary: Analysis summary
        buyer_score: Buyer debate score
        seller_score: Seller debate score
        combined_analysis: Combined analysis
        run_id: Run ID for logging

    Returns:
        CausalChain object
    """
    chain: List[dict] = []

    # Step A: Market/Sector context
    sector_heat = 0
    sector_name = ""
    for sector in hot_sectors:
        if isinstance(sector, dict):
            name = sector.get("name", "")
            heat = sector.get("heat_score", 0)
        else:
            name = sector.name
            heat = sector.heat_score
        if heat > sector_heat:
            sector_heat = heat
            sector_name = name

    if sector_heat > 50:
        chain.append({
            "step": "A",
            "description": f"板块'{sector_name}'热度炒作({sector_heat:.1f}分)",
            "evidence": "TrendRadar热点数据",
        })
    else:
        chain.append({
            "step": "A",
            "description": "市场整体情绪中性",
            "evidence": "TrendRadar数据无明显热点",
        })

    # Step B: Stock attention
    tech_trend = combined_analysis.get("tech_trend", "neutral")
    if tech_trend == "up":
        chain.append({
            "step": "B",
            "description": f"{summary.stock_name}技术面呈现上涨趋势",
            "evidence": f"akshare K线数据, 趋势={tech_trend}",
        })
    else:
        chain.append({
            "step": "B",
            "description": f"{summary.stock_name}技术面趋势不明",
            "evidence": f"akshare K线数据, 趋势={tech_trend}",
        })

    # Step C: Technical signal
    tech_rec = combined_analysis.get("tech_recommendation", "hold")
    tech_conf = combined_analysis.get("tech_confidence", 0.5)
    chain.append({
        "step": "C",
        "description": f"技术分析建议'{tech_rec}'(置信度{tech_conf:.2f})",
        "evidence": f"MACD/RSI/MA指标分析",
    })

    # Step D: Fundamental support
    fund_rec = combined_analysis.get("fund_recommendation", "hold")
    fund_score = summary.fund_score
    chain.append({
        "step": "D",
        "description": f"基本面评分{fund_score:.1f}，建议'{fund_rec}'",
        "evidence": f"akshare财务数据, ROE/PE分析",
    })

    # Step E: Debate result
    chain.append({
        "step": "E",
        "description": f"辩论结果: 买入方{buyer_score:.1f}分 vs 卖出方{seller_score:.1f}分",
        "evidence": f"多轮辩论分析, 共{abs(buyer_score - seller_score):.1f}分差距",
    })

    # Final conclusion
    if buyer_score > seller_score + 15:
        final_conclusion = "强烈建议买入"
    elif buyer_score > seller_score:
        final_conclusion = "建议买入"
    elif seller_score > buyer_score + 15:
        final_conclusion = "建议卖出"
    elif seller_score > buyer_score:
        final_conclusion = "建议观望/减仓"
    else:
        final_conclusion = "建议观望"

    # Confidence based on chain strength
    confidence = (summary.combined_score / 100) * (1 - abs(buyer_score - seller_score) / 100)

    causal_chain = CausalChain(
        chain=chain,
        final_conclusion=final_conclusion,
        confidence=round(confidence, 2),
    )

    logger.info(f"[{run_id}] Causal chain: {len(chain)} steps")
    logger.info(f"[{run_id}] Final conclusion: {final_conclusion}")

    return causal_chain


# ============== Counterfactual Analysis ==============


def _build_counterfactual_analysis(
    summary: AnalysisSummary,
    portfolio: dict,
    current_position: Dict[str, Any],
    run_id: str,
) -> CounterfactualAnalysis:
    """
    Build counterfactual analysis - what if stock drops

    Analyze multiple scenarios:
    - Scenario 1: Drop 5%
    - Scenario 2: Drop 10%
    - Scenario 3: Drop 20%

    For each scenario:
    - Impact (what happens)
    - Probability (how likely)
    - Expected behavior
    - Recommendation

    Args:
        summary: Analysis summary
        portfolio: Current portfolio
        current_position: Current position info
        run_id: Run ID for logging

    Returns:
        CounterfactualAnalysis object
    """
    scenarios: List[CounterfactualScenario] = []

    # Calculate position value impact if holding
    holding = current_position.get("holding", False)
    quantity = current_position.get("quantity", 0)
    current_price = current_position.get("current_price", 0)
    position_value = quantity * current_price if holding else 0

    # Scenario 1: Drop 5%
    impact_5pct = position_value * 0.05 if holding else 0
    scenarios.append(CounterfactualScenario(
        scenario="下跌5%",
        impact=f"持仓市值减少{impact_5pct:.0f}元" if holding else "未持仓无影响",
        probability=0.30,
        expected_behavior="正常波动范围，技术面可能短期回调",
        recommendation="观望，等待企稳信号",
    ))

    # Scenario 2: Drop 10%
    impact_10pct = position_value * 0.10 if holding else 0
    scenarios.append(CounterfactualScenario(
        scenario="下跌10%",
        impact=f"持仓市值减少{impact_10pct:.0f}元，触发止损线" if holding else "未持仓无影响",
        probability=0.20,
        expected_behavior="技术面破位，需关注支撑位有效性",
        recommendation="减仓50%，保留观察仓位",
    ))

    # Scenario 3: Drop 20%
    impact_20pct = position_value * 0.20 if holding else 0
    scenarios.append(CounterfactualScenario(
        scenario="下跌20%",
        impact=f"持仓市值减少{impact_20pct:.0f}元，严重亏损" if holding else "未持仓无影响",
        probability=0.10,
        expected_behavior="基本面可能有问题，投资逻辑需重新评估",
        recommendation="清仓止损，等待新信号",
    ))

    # Worst case
    worst_case = "下跌超过20%，基本面严重恶化，需要彻底退出"

    # Mitigation strategy
    mitigation = "建议分批建仓，单只股票仓位不超过总资金的30%，设置止损线"

    # Exit strategy
    if holding:
        pnl_pct = current_position.get("pnl_pct", 0)
        if pnl_pct > 0:
            exit_strategy = f"当前盈利{pnl_pct:.1f}%，下跌10%止盈离场，下跌20%清仓止损"
        else:
            exit_strategy = f"当前亏损{pnl_pct:.1f}%，下跌10%减仓止损，下跌20%清仓"
    else:
        exit_strategy = "买入后设置10%止损线，严格执行"

    counterfactual = CounterfactualAnalysis(
        scenarios=scenarios,
        worst_case=worst_case,
        mitigation=mitigation,
        exit_strategy=exit_strategy,
    )

    logger.info(f"[{run_id}] Counterfactual scenarios: {len(scenarios)}")
    logger.info(f"[{run_id}] Worst case: {worst_case}")

    return counterfactual


# ============== Decision Generation ==============


def _generate_decision(
    stock_code: str,
    stock_name: str,
    summary: AnalysisSummary,
    debate_influence: Dict[str, Any],
    risk_reward: Dict[str, Any],
    causal_chain: CausalChain,
    counterfactual: CounterfactualAnalysis,
    current_position: Dict[str, Any],
    run_id: str,
) -> Decision:
    """
    Generate final decision based on all factors

    Args:
        stock_code: Stock code
        stock_name: Stock name
        summary: Analysis summary
        debate_influence: Debate influence
        risk_reward: Risk/reward evaluation
        causal_chain: Attribution causal chain
        counterfactual: Counterfactual analysis
        current_position: Current position info
        run_id: Run ID for logging

    Returns:
        Decision object
    """
    # Determine action
    action = Recommendation.HOLD
    confidence = 0.5
    should_enter = False
    risk_level = risk_reward["risk_level"]

    # Combined score influence (40%)
    if summary.combined_score >= 70:
        action = Recommendation.BUY
        confidence += 0.2
        should_enter = True
    elif summary.combined_score < 40:
        action = Recommendation.SELL
        confidence += 0.1

    # Debate influence (30%)
    debate_weight = debate_influence["influence_weight"]
    if debate_influence["winner"] == "buyer":
        if action == Recommendation.HOLD:
            action = Recommendation.BUY
        confidence += debate_weight
    elif debate_influence["winner"] == "seller":
        if action == Recommendation.HOLD:
            action = Recommendation.SELL
        elif action == Recommendation.BUY:
            action = Recommendation.HOLD
            confidence -= 0.1

    # Current position influence (20%)
    if current_position["holding"]:
        pnl_pct = current_position.get("pnl_pct", 0)
        if pnl_pct < -15:
            # Heavy loss - suggest reduce/clear
            if action != Recommendation.SELL:
                action = Recommendation.HOLD
            confidence = max(0.4, confidence)
            risk_level = "high"
        elif pnl_pct > 20:
            # Good profit - suggest reduce to lock in
            if action == Recommendation.BUY:
                action = Recommendation.HOLD
            confidence = min(0.9, confidence)

    # Risk level influence (10%)
    if risk_level == "high":
        should_enter = False
        if action == Recommendation.BUY:
            action = Recommendation.HOLD
            confidence = max(0.3, confidence - 0.1)

    # Clamp confidence
    confidence = min(0.95, max(0.25, confidence))

    # Build reasoning
    reasoning_parts = []

    reasoning_parts.append(f"综合评分{summary.combined_score:.1f}")
    reasoning_parts.append(f"辩论结果{debate_influence['winner']}胜出({debate_influence['margin']:.1f}分差距)")
    reasoning_parts.append(f"风险等级'{risk_level}'")

    if current_position["holding"]:
        reasoning_parts.append(f"当前持仓盈亏{current_position['pnl_pct']:.1f}%")

    reasoning_parts.append(f"因果链结论: {causal_chain.final_conclusion}")

    reasoning = "; ".join(reasoning_parts)

    decision = Decision(
        stock_code=stock_code,
        stock_name=stock_name,
        action=action,
        confidence=round(confidence, 2),
        reasoning=reasoning,
        should_enter=should_enter,
        risk_level=risk_level,
        causal_chain=causal_chain,
        counterfactual=counterfactual,
    )

    logger.info(f"[{run_id}] Decision: {action.value}, confidence={confidence:.2f}")

    return decision