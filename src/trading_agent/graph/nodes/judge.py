"""
Judge node - 评委决策

Responsibilities:
- Combine analysis results + debate results
- Consider portfolio positions
- Evaluate risk/reward ratio
- Generate final decision
- Determine if should enter market
"""

from datetime import datetime
from typing import Dict

from trading_agent.graph.state import WorkflowState, StepStatus
from trading_agent.utils.logger import get_logger

logger = get_logger("JUDGE")


def judge_node(state: WorkflowState) -> Dict:
    """
    Judge node entry function
    
    This node makes final decision based on all previous analysis.
    
    Args:
        state: Current workflow state
    
    Returns:
        Dict with updated state fields
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
    
    logger.info(f"[{run_id}] Analysis: {len(analysis_summary)} entries")
    logger.info(f"[{run_id}] Debate rounds: {len(debate_log)}")
    logger.info(f"[{run_id}] Buyer score: {buyer_score}, Seller score: {seller_score}")
    logger.info(f"[{run_id}] Portfolio: {len(portfolio.get('positions', []))} positions")
    
    # TODO: Judge logic
    # 1. Combine all analysis results
    logger.info(f"[{run_id}] TODO: Combine analysis results")
    
    # 2. Consider debate scores
    logger.info(f"[{run_id}] TODO: Consider debate scores")
    
    # 3. Check portfolio position
    logger.info(f"[{run_id}] TODO: Check portfolio position")
    
    # 4. Evaluate risk/reward
    logger.info(f"[{run_id}] TODO: Evaluate risk/reward")
    
    # 5. Generate final decision
    logger.info(f"[{run_id}] TODO: Generate final decision")
    
    # 6. Determine if should enter
    logger.info(f"[{run_id}] TODO: Determine if should enter market")
    
    # Placeholder: empty decision for now
    decision = {
        "stock_code": "",
        "action": "hold",
        "confidence": 0.0,
        "reasoning": "TODO",
        "should_enter": False,
        "risk_level": "medium",
    }
    updates["decision"] = decision
    
    # Update status to COMPLETED
    updates["judge_status"] = StepStatus.COMPLETED.value
    
    logger.info(f"[{run_id}] Judge node completed")
    logger.info(f"[{run_id}] Decision: {decision.get('action')}")
    
    return updates