"""
Push node - 推送报告

Responsibilities:
- Format decision report
- Push to Feishu webhook
- Log push status
"""

from datetime import datetime
from typing import Dict

from trading_agent.graph.state import WorkflowState, StepStatus
from trading_agent.utils.logger import get_logger

logger = get_logger("PUSH")


def push_node(state: WorkflowState) -> Dict:
    """
    Push node entry function

    This node pushes final decisions to notification channels.

    Args:
        state: Current workflow state

    Returns:
        Dict with updated state fields
    """
    run_id = state.get("run_id", "unknown")
    logger.info(f"[{run_id}] Push node started")
    logger.info(f"[{run_id}] Step status: {state.get('push_status')}")

    # Update status to RUNNING
    updates = {
        "push_status": StepStatus.RUNNING.value,
        "current_step_start": datetime.now().isoformat(),
    }

    # Load decisions
    decisions = state.get("decisions", [])
    logger.info(f"[{run_id}] Loaded {len(decisions)} decisions to push")

    # TODO: Business logic placeholder
    # 1. Format decision report
    logger.info(f"[{run_id}] TODO: Format decision report")

    # 2. Push to Feishu webhook
    logger.info(f"[{run_id}] TODO: Push to Feishu webhook")

    # 3. Optional: push to email
    logger.info(f"[{run_id}] TODO: Optional email push")

    # Update status to COMPLETED
    updates["push_status"] = StepStatus.COMPLETED.value
    updates["status"] = StepStatus.COMPLETED.value
    updates["end_time"] = datetime.now().isoformat()

    logger.info(f"[{run_id}] Push node completed")
    logger.info(f"[{run_id}] Workflow finished")

    return updates