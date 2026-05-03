"""日志模块"""

import logging
import sys
from pathlib import Path

from .config import config


def setup_logger(name: str = "trading_agent") -> logging.Logger:
    """设置日志器"""
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    logger.setLevel(config.log_level)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    config.log_dir.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(
        config.log_dir / "trading_agent.log",
        encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    logger.propagate = False

    return logger


logger = setup_logger()