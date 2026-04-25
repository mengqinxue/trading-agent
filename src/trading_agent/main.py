"""
Trading Agent - Main entry point
"""

import asyncio
from datetime import datetime

from trading_agent.graph import workflow_app, build_workflow
from trading_agent.graph.state import create_initial_state, RunType
from trading_agent.utils import setup_logger, get_logger, load_config
from trading_agent.utils.config import Settings


# Setup logger
logger = setup_logger(
    "trading_agent",
    log_dir=None,  # Will be set after config loaded
)


async def run_workflow(run_type: RunType = RunType.POST_MARKET):
    """
    Run the main workflow

    Args:
        run_type: "pre_market" or "post_market"
    """
    logger.info(f"Starting workflow: {run_type.value}")

    # Load config
    settings = load_config()

    # Setup log directory
    log_dir = settings.log_dir
    log_dir.mkdir(parents=True, exist_ok=True)

    # Create initial state
    state = create_initial_state(run_type)

    logger.info(f"Run ID: {state['run_id']}")
    logger.info(f"Start time: {state['start_time']}")

    # Build and run workflow
    app = build_workflow()

    try:
        # Execute workflow
        result = await app.ainvoke(state)

        logger.info(f"Workflow completed")
        logger.info(f"End time: {result.get('end_time')}")

        return result

    except Exception as e:
        logger.error(f"Workflow failed: {e}")
        raise


async def main():
    """Main entry point"""
    logger.info("Trading Agent starting...")

    # Run post-market workflow for testing
    result = await run_workflow(RunType.POST_MARKET)

    # Print summary
    logger.info("=== Workflow Summary ===")
    logger.info(f"Candidates: {len(result.get('candidate_stocks', []))}")
    logger.info(f"Decisions: {len(result.get('decisions', []))}")

    return result


if __name__ == "__main__":
    asyncio.run(main())