"""
Aggregator node - 分析结果汇总

Responsibilities:
- Merge tech_results + fund_results
- Calculate combined score
- Extract buy/sell arguments
- Generate analysis summary
"""

from datetime import datetime
from typing import Dict

from trading_agent.graph.state import WorkflowState, StepStatus
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
    updates = {
        "aggregator_status": StepStatus.RUNNING.value,
        "current_step_start": datetime.now().isoformat(),
    }
    
    # Load analysis results
    tech_results = state.get("tech_results", [])
    fund_results = state.get("fund_results", [])
    candidates = state.get("candidate_stocks", [])
    
    logger.info(f"[{run_id}] Tech results: {len(tech_results)}")
    logger.info(f"[{run_id}] Fund results: {len(fund_results)}")
    logger.info(f"[{run_id}] Total candidates: {len(candidates)}")
    
    # TODO: Merge and aggregate
    # 1. Match tech and fund results by stock_code
    logger.info(f"[{run_id}] TODO: Match results by stock_code")
    
    # 2. Calculate combined score
    logger.info(f"[{run_id}] TODO: Calculate combined score")
    
    # 3. Extract buy arguments (supporting buy)
    logger.info(f"[{run_id}] TODO: Extract buy arguments")
    
    # 4. Extract sell arguments (supporting sell)
    logger.info(f"[{run_id}] TODO: Extract sell arguments")
    
    # 5. Generate analysis summary
    logger.info(f"[{run_id}] TODO: Generate analysis summary")
    
    # Placeholder: empty summary for now
    analysis_summary = []
    updates["analysis_summary"] = analysis_summary
    
    # Update status to COMPLETED
    updates["aggregator_status"] = StepStatus.COMPLETED.value
    
    logger.info(f"[{run_id}] Aggregator node completed")
    logger.info(f"[{run_id}] Summary entries: {len(updates.get('analysis_summary', []))}")
    
    return updates