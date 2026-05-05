# -*- coding: utf-8 -*-
"""
筹码分布获取模块

获取股票筹码分布数据，反映持仓成本分布。
"""

import logging
from typing import Optional

from .types import ChipDistribution, safe_float
from .sources import get_chip_breaker, random_sleep, CHIP_SOURCE_PRIORITY

logger = logging.getLogger(__name__)


# ============================================
# Tushare 筹码分布获取
# ============================================

def _get_chip_tushare(code: str) -> Optional[ChipDistribution]:
    """使用 Tushare 获取筹码分布"""
    try:
        from .providers import DataFetcherManager
        manager = DataFetcherManager()
        chip = manager.get_chip_distribution(code)
        if chip:
            breaker = get_chip_breaker()
            breaker.record_success("tushare")
        return chip
    except Exception as e:
        logger.warning(f"[Tushare筹码] {code} 获取失败: {e}")
        return None


# ============================================
# Akshare 筹码分布获取（待实现）
# ============================================

def _get_chip_akshare(code: str) -> Optional[ChipDistribution]:
    """使用 Akshare 获取筹码分布"""
    try:
        import akshare as ak

        random_sleep(2.0, 4.0)

        # Akshare 暂无直接筹码分布接口
        logger.warning(f"[Akshare筹码] {code} 暂无筹码分布接口")
        return None

    except Exception as e:
        logger.warning(f"[Akshare筹码] {code} 获取失败: {e}")
        return None


# ============================================
# 统一接口
# ============================================

def get_chip_distribution(code: str) -> Optional[ChipDistribution]:
    """
    获取筹码分布数据

    Args:
        code: 股票代码

    Returns:
        ChipDistribution 或 None
    """
    breaker = get_chip_breaker()

    # 按优先级尝试各数据源
    for source, priority in CHIP_SOURCE_PRIORITY:
        if not breaker.is_available(source):
            logger.debug(f"[筹码] {source} 熔断中，跳过")
            continue

        try:
            logger.info(f"[筹码] 尝试 {source} 获取 {code}...")

            if source == "tushare":
                chip = _get_chip_tushare(code)
            elif source == "akshare":
                chip = _get_chip_akshare(code)
            else:
                continue

            if chip and chip.avg_cost > 0:
                breaker.record_success(source)
                logger.info(f"[筹码] {code} 使用 {source} 获取成功")
                return chip

            breaker.record_inconclusive(source)

        except Exception as e:
            breaker.record_failure(source, str(e))
            logger.warning(f"[筹码] {source} 失败: {e}")

    logger.warning(f"[筹码] {code} 所有数据源失败")
    return None


def get_chip_status(code: str, current_price: Optional[float] = None) -> str:
    """
    获取筹码状态描述

    Args:
        code: 股票代码
        current_price: 当前价格（可选）

    Returns:
        状态描述文本
    """
    from .trade_realtime import get_realtime

    chip = get_chip_distribution(code)

    if chip is None:
        return "无法获取筹码数据"

    # 获取当前价格
    if current_price is None:
        quote = get_realtime(code)
        if quote:
            current_price = quote.price

    if current_price is None or current_price <= 0:
        return "无法获取当前价格"

    return chip.get_chip_status(current_price)