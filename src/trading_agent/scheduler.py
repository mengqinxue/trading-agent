"""
Trading Agent Scheduler

Provides scheduled execution for:
- Pre-market run (09:00): init → screener → END
- Post-market run (15:30): full workflow

Uses APScheduler for reliable scheduling with:
- Job persistence
- Error handling
- Logging
"""

import logging
from datetime import datetime
from typing import Optional
from enum import Enum

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR

from trading_agent.graph.workflow import build_workflow, build_pre_market_workflow
from trading_agent.graph.state import create_initial_state, RunType

logger = logging.getLogger("SCHEDULER")


class ScheduleType(str, Enum):
    """Schedule type enum"""
    PRE_MARKET = "pre_market"
    POST_MARKET = "post_market"


class TradingScheduler:
    """
    Trading agent scheduler

    Manages scheduled execution of trading analysis workflows.

    Example:
        >>> scheduler = TradingScheduler()
        >>> scheduler.start()
        >>> # Runs automatically at scheduled times
        >>> scheduler.stop()  # Stop when needed
    """

    def __init__(self):
        """Initialize scheduler"""
        self._scheduler = BackgroundScheduler()
        self._setup_jobs()
        self._setup_event_handlers()

        logger.info("TradingScheduler initialized")

    def _setup_jobs(self):
        """Setup scheduled jobs"""
        # Pre-market run: 09:00 every weekday (Mon-Fri)
        self._scheduler.add_job(
            self._run_pre_market,
            CronTrigger(hour=9, minute=0, day_of_week="mon-fri"),
            id="pre_market_run",
            name="Pre-Market Analysis",
            replace_existing=True,
        )

        # Post-market run: 15:30 every weekday (Mon-Fri)
        self._scheduler.add_job(
            self._run_post_market,
            CronTrigger(hour=15, minute=30, day_of_week="mon-fri"),
            id="post_market_run",
            name="Post-Market Analysis",
            replace_existing=True,
        )

        logger.info("Scheduled jobs setup: pre_market (09:00), post_market (15:30)")

    def _setup_event_handlers(self):
        """Setup event handlers for job execution"""
        self._scheduler.add_listener(
            self._on_job_executed,
            EVENT_JOB_EXECUTED | EVENT_JOB_ERROR
        )

    def _on_job_executed(self, event):
        """Handle job execution events"""
        if event.exception:
            logger.error(
                f"Job {event.job_id} failed: {event.exception}",
                exc_info=event.exception
            )
        else:
            logger.info(f"Job {event.job_id} completed successfully")

    def _run_pre_market(self):
        """
        Execute pre-market workflow

        Runs: init → screener → END
        Purpose: Generate candidate pool before market opens
        """
        run_id = datetime.now().strftime("%Y%m%d-%H%M%S")
        logger.info(f"[{run_id}] Starting pre-market run")

        try:
            # Create initial state
            state = create_initial_state(run_type=RunType.PRE_MARKET)

            # Build and execute workflow
            app = build_pre_market_workflow()
            result = app.invoke(state)

            # Log results
            candidates = result.get("candidate_stocks", [])
            logger.info(f"[{run_id}] Pre-market completed: {len(candidates)} candidates")

            return result

        except Exception as e:
            logger.error(f"[{run_id}] Pre-market run failed: {e}", exc_info=True)
            raise

    def _run_post_market(self):
        """
        Execute post-market workflow

        Runs: full workflow (init → screener → analysts → aggregator → debater → judge → position → push)
        Purpose: Complete analysis after market closes
        """
        run_id = datetime.now().strftime("%Y%m%d-%H%M%S")
        logger.info(f"[{run_id}] Starting post-market run")

        try:
            # Create initial state
            state = create_initial_state(run_type=RunType.POST_MARKET)

            # Build and execute workflow
            app = build_workflow()
            result = app.invoke(state)

            # Log results
            decision = result.get("decision", {})
            push_result = result.get("push_result", {})
            logger.info(f"[{run_id}] Post-market completed: decision={decision.get('action')}")
            logger.info(f"[{run_id}] Push result: {push_result.get('status', 'unknown')}")

            return result

        except Exception as e:
            logger.error(f"[{run_id}] Post-market run failed: {e}", exc_info=True)
            raise

    def start(self):
        """Start the scheduler"""
        if not self._scheduler.running:
            self._scheduler.start()
            logger.info("Scheduler started")
        else:
            logger.warning("Scheduler already running")

    def stop(self):
        """Stop the scheduler"""
        if self._scheduler.running:
            self._scheduler.shutdown(wait=True)
            logger.info("Scheduler stopped")
        else:
            logger.warning("Scheduler not running")

    def run_once(self, schedule_type: ScheduleType):
        """
        Run a single workflow manually

        Args:
            schedule_type: Type of workflow to run

        Returns:
            Workflow result
        """
        if schedule_type == ScheduleType.PRE_MARKET:
            return self._run_pre_market()
        elif schedule_type == ScheduleType.POST_MARKET:
            return self._run_post_market()
        else:
            raise ValueError(f"Unknown schedule type: {schedule_type}")

    def get_jobs(self):
        """Get list of scheduled jobs"""
        jobs = self._scheduler.get_jobs()
        return [
            {
                "id": job.id,
                "name": job.name,
                "next_run": str(job.next_run_time),
                "trigger": str(job.trigger),
            }
            for job in jobs
        ]

    def is_running(self) -> bool:
        """Check if scheduler is running"""
        return self._scheduler.running


# ============== CLI Entry Point ==============


def main():
    """CLI entry point for scheduler"""
    import argparse

    parser = argparse.ArgumentParser(description="Trading Agent Scheduler")
    parser.add_argument(
        "--run",
        choices=["pre_market", "post_market"],
        help="Run workflow once (pre_market or post_market)"
    )
    parser.add_argument(
        "--start",
        action="store_true",
        help="Start scheduled execution"
    )
    parser.add_argument(
        "--jobs",
        action="store_true",
        help="List scheduled jobs"
    )

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    scheduler = TradingScheduler()

    if args.run:
        # Run once
        schedule_type = ScheduleType(args.run)
        result = scheduler.run_once(schedule_type)
        print(f"Run completed: {schedule_type.value}")

    elif args.start:
        # Start scheduler
        scheduler.start()
        print("Scheduler started. Press Ctrl+C to stop.")

        try:
            # Keep running
            import time
            while True:
                time.sleep(60)
        except KeyboardInterrupt:
            scheduler.stop()
            print("Scheduler stopped")

    elif args.jobs:
        # List jobs
        jobs = scheduler.get_jobs()
        for job in jobs:
            print(f"{job['id']}: {job['name']} - next run: {job['next_run']}")

    else:
        # Default: show help
        parser.print_help()


if __name__ == "__main__":
    main()