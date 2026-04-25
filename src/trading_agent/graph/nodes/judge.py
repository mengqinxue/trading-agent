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
from typing import Dict, List

from trading_agent.graph.state import (
    WorkflowState, StepStatus,
    CausalChain, CounterfactualAnalysis, CounterfactualScenario,
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
    """
    run_id = state.get("run_id", "unknown")
    logger.info(f"[{run_id}] Judge node started")
    logger.info(f"[{run_id}] Status: {state.get('judge_status')}")
    
    # Update status to RUNNING
    updates = {
        "judge_status": StepStatus.RUNNING.value,
        "current_step_start": datetime.now().isoformat(),
    }
    
    # Load all previous results
    analysis_summary = state.get("analysis_summary", [])
    debate_log = state.get("debate_log", [])
    buyer_score = state.get("buyer_score", 0.0)
    seller_score = state.get("seller_score", 0.0)
    portfolio = state.get("portfolio", {})
    hot_sectors = state.get("hot_sectors", [])
    
    logger.info(f"[{run_id}] Analysis: {len(analysis_summary)} entries")
    logger.info(f"[{run_id}] Debate rounds: {len(debate_log)}")
    logger.info(f"[{run_id}] Buyer score: {buyer_score}, Seller score: {seller_score}")
    logger.info(f"[{run_id}] Hot sectors: {len(hot_sectors)}")
    
    # TODO: Judge logic
    # 1. Combine all analysis results
    logger.info(f"[{run_id}] TODO: Combine analysis results")
    
    # 2. Consider debate scores
    logger.info(f"[{run_id}] TODO: Consider debate scores")
    
    # 3. Check portfolio position
    logger.info(f"[{run_id}] TODO: Check portfolio position")
    
    # 4. Evaluate risk/reward
    logger.info(f"[{run_id}] TODO: Evaluate risk/reward")
    
    # 5. Attribution Analysis (归因分析)
    logger.info(f"[{run_id}] TODO: Attribution analysis - build causal chain")
    causal_chain = _build_causal_chain(
        hot_sectors, analysis_summary, buyer_score, seller_score
    )
    
    # 6. Counterfactual Analysis (反事实推断)
    logger.info(f"[{run_id}] TODO: Counterfactual analysis - what if stock drops")
    counterfactual = _build_counterfactual_analysis(
        analysis_summary, portfolio
    )
    
    # 7. Generate final decision
    logger.info(f"[{run_id}] TODO: Generate final decision")
    
    # Placeholder: decision with attribution and counterfactual
    decision = {
        "stock_code": "",
        "stock_name": "",
        "action": "hold",
        "confidence": 0.0,
        "reasoning": "TODO",
        "should_enter": False,
        "risk_level": "medium",
        "causal_chain": causal_chain,
        "counterfactual": counterfactual,
    }
    updates["decision"] = decision
    
    # Update status to COMPLETED
    updates["judge_status"] = StepStatus.COMPLETED.value
    
    logger.info(f"[{run_id}] Judge node completed")
    logger.info(f"[{run_id}] Decision: {decision.get('action')}")
    logger.info(f"[{run_id}] Causal chain: {len(causal_chain.get('chain', []))} steps")
    logger.info(f"[{run_id}] Counterfactual scenarios: {len(counterfactual.get('scenarios', []))}")
    
    return updates


def _build_causal_chain(
    hot_sectors: List,
    analysis_summary: List,
    buyer_score: float,
    seller_score: float,
) -> dict:
    """
    Build attribution causal chain
    
    Example:
    A(热点板块炒作) → B(龙头股关注度提升) → C(技术面突破信号) → D(基本面支撑) → E(买入建议)
    
    Each step should have evidence/data support.
    """
    # TODO: Build causal chain based on actual analysis
    
    chain = [
        {"step": "A", "description": "热点板块炒作", "evidence": "TrendRadar热度数据"},
        {"step": "B", "description": "龙头股关注度提升", "evidence": "龙虎榜/资金流数据"},
        {"step": "C", "description": "技术面突破信号", "evidence": "akshare K线数据"},
        {"step": "D", "description": "基本面支撑", "evidence": "akshare 财务数据"},
        {"step": "E", "description": "综合评分", "evidence": f"买入方得分{buyer_score}/卖出方得分{seller_score}"},
    ]
    
    final_conclusion = "建议观望" if buyer_score <= seller_score else "建议买入"
    confidence = abs(buyer_score - seller_score) / 100
    
    return {
        "chain": chain,
        "final_conclusion": final_conclusion,
        "confidence": confidence,
    }


def _build_counterfactual_analysis(
    analysis_summary: List,
    portfolio: dict,
) -> dict:
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
    """
    # TODO: Build counterfactual based on actual analysis
    
    scenarios = [
        {
            "scenario": "下跌5%",
            "impact": "持仓市值减少，短期波动",
            "probability": 0.3,
            "expected_behavior": "可能回调，属于正常波动范围",
            "recommendation": "观望，等待企稳信号",
        },
        {
            "scenario": "下跌10%",
            "impact": "触发止损线，技术面可能破位",
            "probability": 0.2,
            "expected_behavior": "需要关注支撑位是否有效",
            "recommendation": "减仓50%，保留观察仓位",
        },
        {
            "scenario": "下跌20%",
            "impact": "严重亏损，基本面可能有问题",
            "probability": 0.1,
            "expected_behavior": "需要重新评估投资逻辑",
            "recommendation": "清仓止损，等待新信号",
        },
    ]
    
    worst_case = "下跌20%以上，需要清仓止损"
    mitigation = "分批建仓，控制单只股票仓位不超过30%"
    exit_strategy = "下跌10%减仓，下跌20%清仓"
    
    return {
        "scenarios": scenarios,
        "worst_case": worst_case,
        "mitigation": mitigation,
        "exit_strategy": exit_strategy,
    }