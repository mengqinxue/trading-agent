# -*- coding: utf-8 -*-
"""
筹码分布获取模块

获取股票筹码分布数据，反映持仓成本分布。
"""

import logging
from typing import Optional

from .types import ChipDistribution, safe_float
from .sources import get_chip_breaker, random_sleep

logger = logging.getLogger(__name__)


# ============================================
# Efinance 筹码分布获取
# ============================================

def _get_chip_efinance(code: str) -> Optional[ChipDistribution]:
    """使用 Efinance 获取筹码分布"""
    try:
        import efinance as ef

        random_sleep(2.0, 4.0)  # 筹码接口更慢，多等待

        # 获取筹码分布数据
        df = ef.stock.get_chip_distribution(code)

        if df is None or df.empty:
            return None

        # 解析数据
        row = df.iloc[-1]  # 最新数据

        chip = ChipDistribution(
            code=code,
            date=str(row.get('日期', '')),
            source='efinance',
            profit_ratio=safe_float(row.get('获利比例', 0)),
            avg_cost=safe_float(row.get('平均成本', 0)),
            cost_90_low=safe_float(row.get('90%成本下限', 0)),
            cost_90_high=safe_float(row.get('90%成本上限', 0)),
            concentration_90=safe_float(row.get('90%集中度', 0)),
        )

        return chip

    except Exception as e:
        logger.warning(f"[Efinance筹码] {code} 获取失败: {e}")
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
        # 可通过 stock_em_hsgt_north_net_flow_in 等间接获取
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

    # Efinance 为首选
    for source in ['efinance', 'akshare']:
        if not breaker.is_available(source):
            logger.debug(f"[筹码] {source} 熔断中，跳过")
            continue

        try:
            logger.info(f"[筹码] 尝试 {source} 获取 {code}...")

            if source == 'efinance':
                chip = _get_chip_efinance(code)
            elif source == 'akshare':
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