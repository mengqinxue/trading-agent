"""
Logger utility

Provides structured logging for workflow nodes and agents.
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

from rich.logging import RichHandler


# Global logger registry
_loggers: dict[str, logging.Logger] = {}


def setup_logger(
    name: str = "trading_agent",
    level: int = logging.INFO,
    log_dir: Optional[Path] = None,
) -> logging.Logger:
    """
    Setup logger with Rich console output and optional file output

    Args:
        name: Logger name
        level: Logging level
        log_dir: Optional directory for log files

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Remove existing handlers
    logger.handlers.clear()

    # Console handler with Rich formatting
    console_handler = RichHandler(
        show_time=True,
        show_path=False,
        markup=True,
        rich_tracebacks=True,
    )
    console_handler.setLevel(level)
    logger.addHandler(console_handler)

    # File handler if log_dir specified
    if log_dir:
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / f"{datetime.now().strftime('%Y-%m-%d')}.log"

        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(level)
        file_formatter = logging.Formatter(
            "%(asctime)s [%(name)s] %(levelname)s %(message)s",
            datefmt="%H:%M:%S",
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get or create a logger by name

    Args:
        name: Logger name (typically the node/agent name)

    Returns:
        Logger instance
    """
    if name not in _loggers:
        # Create child logger under main trading_agent logger
        full_name = f"trading_agent.{name}"
        logger = logging.getLogger(full_name)
        logger.setLevel(logging.INFO)

        # Inherit handlers from parent if exists
        parent = logging.getLogger("trading_agent")
        if parent.handlers:
            logger.handlers = parent.handlers

        _loggers[name] = logger

    return _loggers[name]


# Initialize root logger on module load
_root_logger = setup_logger("trading_agent")