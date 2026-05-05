# -*- coding: utf-8 -*-
"""
实时行情获取模块

获取股票实时行情数据，支持多数据源自动切换。
"""

import logging
import time
from datetime import datetime
from typing import Optional, Dict, Any

import pandas as pd

from .types import RealtimeQuote, DataSource, safe_float, safe_int
from .sources import get_realtime_breaker, random_sleep, REALTIME_SOURCE_PRIORITY

logger = logging.getLogger(__name__)


# ============================================
# 全量实时行情缓存
# ============================================

_realtime_cache: Dict[str, Any] = {
    'data': None,
    'timestamp': 0,
    'ttl': 600  # 10分钟缓存
}


def _get_all_realtime_akshare() -> Optional[pd.DataFrame]:
    """使用 Akshare 获取全市场实时行情"""
    global _realtime_cache

    # 检查缓存
    current_time = time.time()
    if _realtime_cache['data'] is not None:
        elapsed = current_time - _realtime_cache['timestamp']
        if elapsed < _realtime_cache['ttl']:
            logger.debug(f"[实时行情] 使用缓存数据: elapsed={elapsed:.0f}s")
            return _realtime_cache['data']

    try:
        import akshare as ak

        random_sleep()

        # 获取全市场实时行情
        df = ak.stock_zh_a_spot_em()

        if df is None or df.empty:
            return None

        # 更新缓存
        _realtime_cache['data'] = df
        _realtime_cache['timestamp'] = current_time
        logger.info(f"[实时行情] Akshare 获取成功: rows={len(df)}, 缓存 {_realtime_cache['ttl']}s")

        return df

    except Exception as e:
        logger.warning(f"[实时行情] Akshare 获取失败: {e}")
        return None


# ============================================
# 单只股票实时行情
# ============================================

def _parse_realtime_from_df(df: pd.DataFrame, code: str) -> Optional[RealtimeQuote]:
    """从全量数据中提取单只股票行情"""
    if df is None or df.empty:
        return None

    # 查找股票
    stock_data = df[df['代码'] == code]
    if stock_data.empty:
        return None

    row = stock_data.iloc[0]

    quote = RealtimeQuote(
        code=code,
        name=str(row.get('名称', '')),
        source=DataSource.AKSHARE,

        # 价格
        price=safe_float(row.get('最新价')),
        change_pct=safe_float(row.get('涨跌幅')),
        change_amount=safe_float(row.get('涨跌额')),

        # 量价
        volume=safe_int(row.get('成交量')),
        amount=safe_float(row.get('成交额')),
        volume_ratio=safe_float(row.get('量比')),
        turnover_rate=safe_float(row.get('换手率')),
        amplitude=safe_float(row.get('振幅')),

        # 价格区间
        open_price=safe_float(row.get('今开')),
        high=safe_float(row.get('最高')),
        low=safe_float(row.get('最低')),
        pre_close=safe_float(row.get('昨收')),

        # 估值
        pe_ratio=safe_float(row.get('市盈率-动态')),
        pb_ratio=safe_float(row.get('市净率')),
        total_mv=safe_float(row.get('总市值')),
        circ_mv=safe_float(row.get('流通市值')),
    )

    return quote


# ============================================
# 统一接口
# ============================================

def get_realtime(code: str) -> Optional[RealtimeQuote]:
    """
    获取实时行情

    Args:
        code: 股票代码

    Returns:
        RealtimeQuote 或 None
    """
    breaker = get_realtime_breaker()

    # 按优先级尝试
    for source, priority in REALTIME_SOURCE_PRIORITY:
        if not breaker.is_available(source):
            logger.debug(f"[实时行情] {source} 熔断中，跳过")
            continue

        try:
            logger.info(f"[实时行情] 尝试 {source} 获取 {code}...")

            if source == "akshare":
                df = _get_all_realtime_akshare()
            elif source == "pytdx":
                # Pytdx 通过 DataFetcherManager 处理
                from .providers import DataFetcherManager
                manager = DataFetcherManager()
                quote = manager.get_realtime_quote(code)
                if quote:
                    breaker.record_success(source)
                    logger.info(f"[实时行情] {code} 使用 {source} 获取成功")
                    return quote
                continue
            else:
                continue

            if df is not None:
                quote = _parse_realtime_from_df(df, code)
                if quote and quote.has_basic_data():
                    breaker.record_success(source)
                    logger.info(f"[实时行情] {code} 使用 {source} 获取成功")
                    return quote

            breaker.record_inconclusive(source)

        except Exception as e:
            breaker.record_failure(source, str(e))
            logger.warning(f"[实时行情] {source} 失败: {e}")

    logger.warning(f"[实时行情] {code} 所有数据源失败")
    return None


def get_realtime_as_dict(code: str) -> Dict[str, Any]:
    """获取实时行情并转换为字典"""
    quote = get_realtime(code)
    if quote:
        return quote.to_dict()
    return {'code': code, 'error': '获取失败'}


def clear_realtime_cache() -> None:
    """清除实时行情缓存"""
    global _realtime_cache
    _realtime_cache['data'] = None
    _realtime_cache['timestamp'] = 0
    logger.info("[实时行情] 缓存已清除")