"""
Position Advisor node - 持仓建议

Responsibilities:
- Check if stock is already in portfolio
- Determine position action (new_buy/add/reduce/clear)
- Calculate suggested position size
- Set stop-loss and take-profit levels
"""

from datetime import datetime
from typing import Dict

from trading_agent.graph.state import WorkflowState, StepStatus
from trading_agent.utils.logger import get_logger

logger = get_logger("POSITION_ADVISOR")


def position_advisor_node(state: WorkflowState) -> Dict:
    """
    Position Advisor node entry function
    
    This node generates position advice based on decision and current portfolio.
    
    Logic:
    - If holding stock + buy decision → add position
    - If holding stock + sell decision → reduce/clear based on P&L
    - If not holding + buy decision → new buy
    - If not holding + sell decision → skip
    
    Args:
        state: Current workflow state
    
    Returns:
        Dict with updated state fields
    """
    run_id = state.get("run_id", "unknown")
    logger.info(f"[{run_id}] Position Advisor node started")
    
    # Update status to RUNNING
    updates = {
        "position_status": StepStatus.RUNNING.value,
        "current_step_start": datetime.now().isoformat(),
    }
    
    # Load decision and portfolio
    decision = state.get("decision", {})
    portfolio = state.get("portfolio", {})
    positions = portfolio.get("positions", [])
    
    logger.info(f"[{run_id}] Decision: {decision.get('action', 'unknown')}")
    logger.info(f"[{run_id}] Current positions: {len(positions)}")
    
    # TODO: Position logic
    stock_code = decision.get("stock_code", "")
    action = decision.get("action", "hold")
    
    # Check if already holding
    holding = any(p.get("symbol") == stock_code for p in positions)
    
    if holding:
        logger.info(f"[{run_id}] Already holding {stock_code}")
        logger.info(f"[{run_id}] TODO: Calculate position change (add/reduce/clear)")
    else:
        logger.info(f"[{run_id}] Not holding {stock_code}")
        logger.info(f"[{run_id}] TODO: Calculate new position (new_buy/skip)")
    
    # TODO: Calculate suggested amount
    logger.info(f"[{run_id}] TODO: Calculate suggested position size")
    
    # TODO: Set stop-loss
    logger.info(f"[{run_id}] TODO: Set stop-loss level")
    
    # TODO: Set take-profit
    logger.info(f"[{run_id}] TODO: Set take-profit level")
    
    # Placeholder: empty advice for now
    position_advice = {
        "stock_code": stock_code,
        "position_action": "skip",
        "suggested_amount": 0,
        "stop_loss": None,
        "take_profit": None,
        "current_position": None,
    }
    updates["position_advice"] = position_advice
    
    # Update status to COMPLETED
    updates["position_status"] = StepStatus.COMPLETED.value
    
    logger.info(f"[{run_id}] Position Advisor node completed")
    logger.info(f"[{run_id}] Position action: {position_advice.get('position_action')}")
    
    return updates