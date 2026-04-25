"""
Debater node - 博弈辩论引擎 V2

Responsibilities:
- Buyer agent vs Seller agent debate
- Max 20 rounds
- Early termination: 5 rounds no new arguments
- Score both sides
- Generate debate log
"""

from datetime import datetime
from typing import Dict, List

from trading_agent.graph.state import WorkflowState, StepStatus
from trading_agent.utils.logger import get_logger

logger = get_logger("DEBATER")

# Debate configuration
MAX_ROUNDS = 20
NO_NEW_ARGS_THRESHOLD = 5  # Stop if 5 rounds no new arguments


def debater_node(state: WorkflowState) -> Dict:
    """
    Debater node entry function
    
    This node runs buyer vs seller debate on analysis summary.
    
    Debate mechanism:
    - Round 1: Both sides state core arguments
    - Round 2-N: Counter-arguments and rebuttals
    - Early stop: 5 consecutive rounds with no new arguments
    - Max rounds: 20
    
    Args:
        state: Current workflow state
    
    Returns:
        Dict with updated state fields
    """
    run_id = state.get("run_id", "unknown")
    logger.info(f"[{run_id}] Debater node started")
    
    # Check prerequisites
    aggregator_status = state.get("aggregator_status")
    logger.info(f"[{run_id}] Prerequisites: aggregator={aggregator_status}")
    
    # Update status to RUNNING
    updates = {
        "debater_status": StepStatus.RUNNING.value,
        "current_step_start": datetime.now().isoformat(),
    }
    
    # Load analysis summary
    analysis_summary = state.get("analysis_summary", [])
    portfolio = state.get("portfolio", {})
    
    logger.info(f"[{run_id}] Analysis entries: {len(analysis_summary)}")
    
    # Initialize debate log
    debate_log: List[Dict] = []
    
    # TODO: Run debate for each stock
    for summary in analysis_summary:
        stock_code = summary.get("stock_code", "unknown")
        logger.info(f"[{run_id}] Starting debate for {stock_code}")
        
        # TODO: Initialize buyer and seller agents
        logger.info(f"[{run_id}] TODO: Initialize buyer agent")
        logger.info(f"[{run_id}] TODO: Initialize seller agent")
        
        # Run debate rounds
        no_new_args_count = 0
        buyer_arguments: List[str] = []
        seller_arguments: List[str] = []
        
        for round_num in range(1, MAX_ROUNDS + 1):
            logger.info(f"[{run_id}] Round {round_num} for {stock_code}")
            
            # TODO: Buyer argument
            buyer_arg = f"TODO: Buyer argument for round {round_num}"
            logger.info(f"[{run_id}] Buyer: {buyer_arg[:50]}...")
            
            # TODO: Seller argument
            seller_arg = f"TODO: Seller argument for round {round_num}"
            logger.info(f"[{run_id}] Seller: {seller_arg[:50]}...")
            
            # Check for new arguments
            if buyer_arg in buyer_arguments and seller_arg in seller_arguments:
                no_new_args_count += 1
                logger.info(f"[{run_id}] No new arguments count: {no_new_args_count}")
            else:
                no_new_args_count = 0
                buyer_arguments.append(buyer_arg)
                seller_arguments.append(seller_arg)
            
            # Record round
            debate_log.append({
                "stock_code": stock_code,
                "round": round_num,
                "buyer_argument": buyer_arg,
                "seller_argument": seller_arg,
                "buyer_new": buyer_arg not in buyer_arguments[:-1],
                "seller_new": seller_arg not in seller_arguments[:-1],
            })
            
            # Early termination check
            if no_new_args_count >= NO_NEW_ARGS_THRESHOLD:
                logger.info(f"[{run_id}] Early termination: {NO_NEW_ARGS_THRESHOLD} rounds no new args")
                break
        
        logger.info(f"[{run_id}] Debate completed for {stock_code}, total rounds: {round_num}")
    
    # TODO: Calculate scores
    logger.info(f"[{run_id}] TODO: Calculate buyer/seller scores")
    
    # Placeholder: scores and results
    buyer_score = 50.0
    seller_score = 50.0
    consensus = False
    
    updates["debate_log"] = debate_log
    updates["buyer_score"] = buyer_score
    updates["seller_score"] = seller_score
    updates["consensus"] = consensus
    
    # Update status to COMPLETED
    updates["debater_status"] = StepStatus.COMPLETED.value
    
    logger.info(f"[{run_id}] Debater node completed")
    logger.info(f"[{run_id}] Buyer score: {buyer_score}, Seller score: {seller_score}")
    logger.info(f"[{run_id}] Debate rounds: {len(debate_log)}")
    
    return updates