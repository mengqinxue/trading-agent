"""
Init node - 系统初始化 & 检测

Responsibilities:
- System check: API connections, data sources
- Config loading: settings, portfolio, keywords
- State initialization: create workflow state
- Portfolio loading: read current positions
"""

from datetime import datetime
from typing import Dict
import os

from trading_agent.graph.state import WorkflowState, StepStatus, RunType
from trading_agent.utils.logger import get_logger
from trading_agent.utils.config import load_config

logger = get_logger("INIT")


def init_node(state: WorkflowState) -> Dict:
    """
    Init node entry function
    
    This node:
    1. Checks system status (APIs, data sources)
    2. Loads configuration files
    3. Initializes workflow state
    4. Logs all checks
    
    Args:
        state: Current workflow state (may be empty on first run)
    
    Returns:
        Dict with updated state fields
    """
    run_id = state.get("run_id", datetime.now().strftime("%Y%m%d-%H%M%S"))
    logger.info(f"[{run_id}] Init node started")
    
    # Update status to RUNNING
    updates = {
        "init_status": StepStatus.RUNNING.value,
        "current_step_start": datetime.now().isoformat(),
    }
    
    # TODO: System checks
    # 1. Check akshare API
    logger.info(f"[{run_id}] TODO: Check akshare API connection")
    
    # 2. Check TrendRadar MCP
    logger.info(f"[{run_id}] TODO: Check TrendRadar MCP connection")
    
    # 3. Check Feishu webhook
    logger.info(f"[{run_id}] TODO: Check Feishu webhook connection")
    
    # 4. Check LLM API
    logger.info(f"[{run_id}] TODO: Check LLM API connection")
    
    # TODO: Load config
    logger.info(f"[{run_id}] TODO: Load config.yaml")
    logger.info(f"[{run_id}] TODO: Load portfolio.yaml")
    logger.info(f"[{run_id}] TODO: Load keywords.yaml")
    
    # Placeholder: system status
    system_status = {
        "akshare": "OK",
        "trendradar": "OK",
        "feishu": "OK",
        "llm": "OK",
        "check_time": datetime.now().isoformat(),
    }
    updates["system_status"] = system_status
    
    # Placeholder: portfolio
    portfolio = {
        "positions": [],
        "keywords": [],
    }
    updates["portfolio"] = portfolio
    
    # Update status to COMPLETED
    updates["init_status"] = StepStatus.COMPLETED.value
    
    logger.info(f"[{run_id}] Init node completed")
    logger.info(f"[{run_id}] System status: {system_status}")
    
    return updates