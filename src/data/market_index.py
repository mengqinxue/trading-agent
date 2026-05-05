# -*- coding: utf-8 -*-
"""
市场指数获取模块

获取主要指数行情数据：上证指数、深证成指、创业板指等。
"""

import logging
from typing import List, Dict, Any, Optional

import pandas as pd

from .types import safe_float
from .sources import random_sleep

logger = logging.getLogger(__name__)


# 主要指数代码
MAIN_INDEXES = {
    '000001': '上证指数',
    '399001': '深证成指',
    '399006': '创业板指',
    '000016': '上证50',
    '000300': '沪深300',
    '000905': '中证500',
    '000688': '科创50',
}


# ============================================
# Akshare 指数获取
# ============================================

def _get_indices_akshare() -> Optional[pd.DataFrame]:
    """使用 Akshare 获取指数行情"""
    try:
        import akshare as ak

        random_sleep()

        # 获取A股指数实时行情
        df = ak.stock_zh_index_spot_em()

        if df is None or df.empty:
            return None

        return df

    except Exception as e:
        logger.warning(f"[指数Akshare] 获取失败: {e}")
        return None


# ============================================
# Efinance 指数获取
# ============================================

def _get_indices_efinance() -> Optional[pd.DataFrame]:
    """使用 Efinance 获取指数行情"""
    try:
        import efinance as ef

        random_sleep()

        # 获取指数行情
        df = ef.stock.get_quote_history_realtime()

        if df is None or df.empty:
            return None

        return df

    except Exception as e:
        logger.warning(f"[指数Efinance] 获取失败: {e}")
        return None


# ============================================
# 统一接口
# ============================================

def get_main_indices() -> List[Dict[str, Any]]:
    """
    获取主要指数行情

    Returns:
        指数列表，每个指数包含：code, name, price, change_pct
    """
    for source in ['akshare', 'efinance']:
        try:
            logger.info(f"[指数] 尝试 {source} 获取...")

            if source == 'akshare':
                df = _get_indices_akshare()
            elif source == 'efinance':
                df = _get_indices_efinance()
            else:
                continue

            if df is None or df.empty:
                continue

            indices = []
            for code, name in MAIN_INDEXES.items():
                row = df[df['代码'] == code]
                if row.empty:
                    continue

                r = row.iloc[0]
                index_data = {
                    'code': code,
                    'name': name,
                    'price': safe_float(r.get('最新价', 0)),
                    'change_pct': safe_float(r.get('涨跌幅', 0)),
                    'change_amount': safe_float(r.get('涨跌额', 0)),
                    'volume': safe_float(r.get('成交量', 0)),
                    'amount': safe_float(r.get('成交额', 0)),
                }
                indices.append(index_data)

            if indices:
                logger.info(f"[指数] 使用 {source} 获取成功: {len(indices)} 个指数")
                return indices

        except Exception as e:
            logger.warning(f"[指数] {source} 失败: {e}")

    logger.warning("[指数] 所有数据源失败")
    return []


def get_index_by_code(code: str) -> Optional[Dict[str, Any]]:
    """
    获取单个指数行情

    Args:
        code: 指数代码

    Returns:
        指数数据或 None
    """
    indices = get_main_indices()
    for idx in indices:
        if idx['code'] == code:
            return idx
    return None


def get_index_overview() -> Dict[str, Any]:
    """
    获取指数概览（用于兼容旧接口）

    Returns:
        {code: {name, code, price, change}} 格式
    """
    indices = get_main_indices()
    result = {}
    for idx in indices:
        result[idx['code']] = {
            'name': idx['name'],
            'code': idx['code'],
            'price': idx['price'],
            'change': idx['change_pct'],
        }
    # 添加兼容别名
    if '000001' in result:
        result['sh_composite'] = result['000001']
    if '399001' in result:
        result['sz_component'] = result['399001']
    if '399006' in result:
        result['chinext'] = result['399006']
    return result