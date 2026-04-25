"""
Screener node - 热点发现 & 粗筛

Responsibilities:
- Get hot news from TrendRadar MCP
- Identify hot sectors
- Generate candidate stock pool
- Save candidates to data/
"""

from datetime import datetime
from typing import Dict

from trading_agent.graph.state import WorkflowState, StepStatus
from trading_agent.utils.logger import get_logger

logger = get_logger("SCREENER")


def screener_node(state: WorkflowState) -> Dict:
    """
    Screener node entry function

    This node:
    1. Updates state status to RUNNING
    2. Logs entry
    3. Placeholder for business logic (TODO)
    4. Updates state status to COMPLETED
    5. Logs exit and returns updated state

    Args:
        state: Current workflow state

    Returns:
        Dict with updated state fields
    """
    # Log entry
    run_id = state.get("run_id", "unknown")
    logger.info(f"[{run_id}] Screener node started")
    logger.info(f"[{run_id}] Step status: {state.get('screener_status')}")

    # Update status to RUNNING
    updates = {
        "screener_status": StepStatus.RUNNING.value,
        "current_step_start": datetime.now().isoformat(),
    }

    # TODO: Business logic placeholder
    # 1. Call TrendRadar MCP to get hot news
    logger.info(f"[{run_id}] TODO: Get hot news from TrendRadar MCP")

    # 2. Analyze hot sectors
    logger.info(f"[{run_id}] TODO: Analyze hot sectors")

    # 3. Generate candidate stock pool
    logger.info(f"[{run_id}] TODO: Generate candidate stocks")

    # 4. Save candidates to data/candidates/YYYY-MM-DD.json
    logger.info(f"[{run_id}] TODO: Save candidates to data/")

    # Placeholder: create empty candidate list for now
    updates["hot_news"] = []
    updates["hot_sectors"] = []
    updates["candidate_stocks"] = []

    # Update status to COMPLETED
    updates["screener_status"] = StepStatus.COMPLETED.value

    # Log exit
    logger.info(f"[{run_id}] Screener node completed")
    logger.info(f"[{run_id}] Candidates generated: {len(updates.get('candidate_stocks', []))}")

    return updates