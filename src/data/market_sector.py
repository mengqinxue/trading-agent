# -*- coding: utf-8 -*-
"""
板块数据获取模块

获取板块涨跌榜、概念板块、行业板块数据。
"""

import logging
from typing import List, Dict, Any, Tuple, Optional

import pandas as pd

from .types import safe_float, safe_int
from .sources import random_sleep

logger = logging.getLogger(__name__)


# ============================================
# 板块涨跌榜获取
# ============================================

def _get_sector_rankings_akshare(n: int = 10) -> Tuple[List[Dict], List[Dict]]:
    """使用 Akshare 获取板块涨跌榜"""
    try:
        import akshare as ak

        random_sleep()

        # 概念板块
        df_concept = ak.stock_board_concept_name_em()
        # 行业板块
        df_industry = ak.stock_board_industry_name_em()

        top_list = []
        bottom_list = []

        # 概念板块涨跌榜
        if df_concept is not None and not df_concept.empty:
            df_concept = df_concept.sort_values('涨跌幅', ascending=False)
            for _, row in df_concept.head(n).iterrows():
                top_list.append({
                    'name': str(row.get('板块名称', '')),
                    'type': 'concept',
                    'change': safe_float(row.get('涨跌幅', 0)),
                    'up_count': safe_int(row.get('上涨家数', 0)),
                    'down_count': safe_int(row.get('下跌家数', 0)),
                    'leading_stock': str(row.get('领涨股票', '')),
                })

            for _, row in df_concept.tail(n).iterrows():
                bottom_list.append({
                    'name': str(row.get('板块名称', '')),
                    'type': 'concept',
                    'change': safe_float(row.get('涨跌幅', 0)),
                    'up_count': safe_int(row.get('上涨家数', 0)),
                    'down_count': safe_int(row.get('下跌家数', 0)),
                })

        return top_list, bottom_list

    except Exception as e:
        logger.warning(f"[板块Akshare] 获取失败: {e}")
        return [], []


# ============================================
# 统一接口
# ============================================

def get_sector_rankings(n: int = 10) -> Tuple[List[Dict], List[Dict]]:
    """
    获取板块涨跌榜

    Args:
        n: 返回板块数量

    Returns:
        (涨幅榜, 跌幅榜)
    """
    try:
        logger.info(f"[板块] 尝试 akshare 获取涨跌榜...")
        top, bottom = _get_sector_rankings_akshare(n)
        if top or bottom:
            logger.info(f"[板块] 使用 akshare 获取成功: 涨幅榜{len(top)}个, 跌幅榜{len(bottom)}个")
            return top, bottom
    except Exception as e:
        logger.warning(f"[板块] akshare 失败: {e}")

    logger.warning("[板块] 所有数据源失败")
    return [], []


def get_hot_sectors(n: int = 10) -> List[Dict[str, Any]]:
    """
    获取热点板块（涨幅榜前N个）

    Args:
        n: 返回数量

    Returns:
        热点板块列表
    """
    top, _ = get_sector_rankings(n)
    return top


def get_weak_sectors(n: int = 10) -> List[Dict[str, Any]]:
    """
    获取弱势板块（跌幅榜前N个）

    Args:
        n: 返回数量

    Returns:
        弱势板块列表
    """
    _, bottom = get_sector_rankings(n)
    return bottom


# ============================================
# 股票所属板块
# ============================================

def get_stock_belong_sectors(code: str) -> List[Dict[str, Any]]:
    """
    获取股票所属板块

    Args:
        code: 股票代码

    Returns:
        板块列表：概念板块 + 行业板块
    """
    try:
        import akshare as ak

        random_sleep()

        boards = []

        # 概念板块
        try:
            df_concept = ak.stock_individual_info_em(symbol=code)
            if df_concept is not None and not df_concept.empty:
                for _, row in df_concept.iterrows():
                    item = row.get('item', '')
                    value = row.get('value', '')
                    if '概念' in item or '板块' in item:
                        boards.append({
                            'name': str(value),
                            'type': 'concept',
                        })
        except Exception:
            pass

        # 行业分类
        try:
            df_industry = ak.stock_board_industry_cons_em(symbol=code)
            if df_industry is not None and not df_industry.empty:
                for _, row in df_industry.head(3).iterrows():
                    boards.append({
                        'name': str(row.get('板块名称', '')),
                        'type': 'industry',
                    })
        except Exception:
            pass

        return boards

    except Exception as e:
        logger.warning(f"[所属板块] {code} 获取失败: {e}")
        return []


# ============================================
# 板块成分股
# ============================================

def get_sector_stocks(sector_name: str, sector_type: str = 'concept') -> List[str]:
    """
    获取板块成分股

    Args:
        sector_name: 板块名称
        sector_type: 板块类型（concept/industry）

    Returns:
        股票代码列表
    """
    try:
        import akshare as ak

        random_sleep()

        codes = []

        if sector_type == 'concept':
            df = ak.stock_board_concept_cons_em(symbol=sector_name)
        else:
            df = ak.stock_board_industry_cons_em(symbol=sector_name)

        if df is not None and not df.empty:
            codes = df['代码'].tolist()

        return codes

    except Exception as e:
        logger.warning(f"[板块成分] {sector_name} 获取失败: {e}")
        return []