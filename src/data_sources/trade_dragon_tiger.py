# -*- coding: utf-8 -*-
"""
龙虎榜获取模块

获取股票龙虎榜数据，追踪主力资金动向。
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional

import pandas as pd

from .types import DragonTigerRecord, safe_float
from .sources import random_sleep

logger = logging.getLogger(__name__)


# ============================================
# Akshare 龙虎榜获取
# ============================================

def _get_dragon_tiger_akshare(code: str, days: int = 30) -> List[DragonTigerRecord]:
    """使用 Akshare 获取龙虎榜"""
    try:
        import akshare as ak

        random_sleep()

        # 获取龙虎榜数据
        # ak.stock_lhb_detail_em - 龙虎榜明细
        # ak.stock_lhb_statistic_em - 龙虎榜统计

        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y%m%d')

        try:
            # 方法1：按股票查询龙虎榜明细
            df = ak.stock_lhb_detail_em(
                symbol=code,
                start_date=start_date,
                end_date=end_date
            )
        except Exception:
            # 方法2：获取全量龙虎榜后筛选
            df_all = ak.stock_lhb_statistic_em(start_date=start_date, end_date=end_date)
            if df_all is not None and not df_all.empty:
                df = df_all[df_all['代码'] == code]
            else:
                df = None

        if df is None or df.empty:
            return []

        records = []
        for _, row in df.iterrows():
            record = DragonTigerRecord(
                code=code,
                name=str(row.get('名称', '')),
                date=str(row.get('日期', '')),
                buy_amount=safe_float(row.get('买入额', 0)),
                sell_amount=safe_float(row.get('卖出额', 0)),
                net_buy=safe_float(row.get('净买入', 0)),
            )
            records.append(record)

        return records

    except Exception as e:
        logger.warning(f"[龙虎榜Akshare] {code} 获取失败: {e}")
        return []


# ============================================
# Efinance 龙虎榜获取
# ============================================

def _get_dragon_tiger_efinance(code: str, days: int = 30) -> List[DragonTigerRecord]:
    """使用 Efinance 获取龙虎榜"""
    try:
        import efinance as ef

        random_sleep()

        # Efinance 龙虎榜接口
        df = ef.stock.get_lhb_detail(code)

        if df is None or df.empty:
            return []

        records = []
        for _, row in df.iterrows():
            record = DragonTigerRecord(
                code=code,
                name=str(row.get('名称', '')),
                date=str(row.get('日期', '')),
                buy_amount=safe_float(row.get('买入额', 0)),
                sell_amount=safe_float(row.get('卖出额', 0)),
                net_buy=safe_float(row.get('净买入', 0)),
            )
            records.append(record)

        # 按日期排序，取最近 days 天
        records = sorted(records, key=lambda r: r.date, reverse=True)[:days]

        return records

    except Exception as e:
        logger.warning(f"[龙虎榜Efinance] {code} 获取失败: {e}")
        return []


# ============================================
# 统一接口
# ============================================

def get_dragon_tiger(code: str, days: int = 30) -> List[DragonTigerRecord]:
    """
    获取龙虎榜数据

    Args:
        code: 股票代码
        days: 查询天数

    Returns:
        龙虎榜记录列表
    """
    # Akshare 为首选
    for source in ['akshare', 'efinance']:
        try:
            logger.info(f"[龙虎榜] 尝试 {source} 获取 {code}...")

            if source == 'akshare':
                records = _get_dragon_tiger_akshare(code, days)
            elif source == 'efinance':
                records = _get_dragon_tiger_efinance(code, days)
            else:
                continue

            if records:
                logger.info(f"[龙虎榜] {code} 使用 {source} 获取成功: {len(records)} 条")
                return records

        except Exception as e:
            logger.warning(f"[龙虎榜] {source} 失败: {e}")

    logger.warning(f"[龙虎榜] {code} 所有数据源失败")
    return []


def get_dragon_tiger_summary(code: str, days: int = 30) -> dict:
    """
    获取龙虎榜汇总信息

    Args:
        code: 股票代码
        days: 查询天数

    Returns:
        汇总信息：上榜次数、净买入总额等
    """
    records = get_dragon_tiger(code, days)

    if not records:
        return {'code': code, 'count': 0, 'net_buy_total': 0}

    net_buy_total = sum(r.net_buy for r in records)
    buy_total = sum(r.buy_amount for r in records)
    sell_total = sum(r.sell_amount for r in records)

    return {
        'code': code,
        'count': len(records),
        'net_buy_total': net_buy_total,
        'buy_total': buy_total,
        'sell_total': sell_total,
        'avg_net_buy': net_buy_total / len(records) if records else 0,
        'dates': [r.date for r in records],
    }