# -*- coding: utf-8 -*-
"""
日线数据获取模块

获取股票日线数据，支持多数据源自动切换。
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Optional, Tuple, List

import pandas as pd
import numpy as np

from .types import DailyBar, DataSource, safe_float
from .sources import get_daily_breaker, random_sleep, DAILY_SOURCE_PRIORITY

logger = logging.getLogger(__name__)


# ============================================
# Akshare 日线获取
# ============================================

def _get_daily_akshare(code: str, days: int) -> Optional[pd.DataFrame]:
    """使用 Akshare 获取日线数据"""
    try:
        import akshare as ak

        # 随机休眠防封禁
        random_sleep()

        # 计算日期范围
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=days * 2)).strftime('%Y%m%d')

        # 获取数据
        df = ak.stock_zh_a_hist(
            symbol=code,
            period="daily",
            start_date=start_date,
            end_date=end_date,
            adjust="qfq"  # 前复权
        )

        if df is None or df.empty:
            return None

        # 标准化列名
        df = df.rename(columns={
            '日期': 'date',
            '开盘': 'open',
            '收盘': 'close',
            '最高': 'high',
            '最低': 'low',
            '成交量': 'volume',
            '成交额': 'amount',
            '涨跌幅': 'pct_chg',
            '换手率': 'turnover'
        })

        # 确保日期格式
        df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')

        # 按日期排序，取最近 days 天
        df = df.sort_values('date').tail(days)

        return df

    except Exception as e:
        logger.warning(f"[Akshare] {code} 日线获取失败: {e}")
        return None


# ============================================
# Baostock 日线获取（兜底）
# ============================================

def _get_daily_baostock(code: str, days: int) -> Optional[pd.DataFrame]:
    """使用 Baostock 获取日线数据"""
    try:
        import baostock as bs
    except ImportError:
        logger.warning("[Baostock] baostock 库未安装，跳过此数据源")
        return None

    try:
        # 登录
        lg = bs.login()
        if lg.error_code != '0':
            return None

        # 获取数据
        rs = bs.query_history_k_data_plus(
            code,
            "date,open,close,high,low,volume,amount,pctChg",
            start_date=(datetime.now() - timedelta(days=days * 2)).strftime('%Y-%m-%d'),
            end_date=datetime.now().strftime('%Y-%m-%d'),
            frequency="d",
            adjustflag="2"  # 前复权
        )

        if rs.error_code != '0':
            bs.logout()
            return None

        data_list = []
        while (rs.error_code == '0') & rs.next():
            data_list.append(rs.get_row_data())

        bs.logout()

        if not data_list:
            return None

        df = pd.DataFrame(data_list, columns=['date', 'open', 'close', 'high', 'low', 'volume', 'amount', 'pct_chg'])

        # 类型转换
        for col in ['open', 'close', 'high', 'low', 'volume', 'amount', 'pct_chg']:
            df[col] = pd.to_numeric(df[col], errors='coerce')

        df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
        df = df.sort_values('date').tail(days)

        return df

    except Exception as e:
        logger.warning(f"[Baostock] {code} 日线获取失败: {e}")
        return None


# ============================================
# 技术指标计算
# ============================================

def _calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """计算技术指标：均线、量比"""
    if df.empty:
        return df

    # 均线
    df['ma5'] = df['close'].rolling(window=5, min_periods=1).mean()
    df['ma10'] = df['close'].rolling(window=10, min_periods=1).mean()
    df['ma20'] = df['close'].rolling(window=20, min_periods=1).mean()

    # 量比（相对5日均量）
    vol_ma5 = df['volume'].rolling(window=5, min_periods=1).mean()
    df['volume_ratio'] = df['volume'] / vol_ma5.replace(0, 1)

    # 填充 NaN
    df = df.fillna(0)

    return df


# ============================================
# 统一接口
# ============================================

def get_daily(
    code: str,
    days: int = 60,
    include_indicators: bool = True
) -> Tuple[Optional[pd.DataFrame], str]:
    """
    获取日线数据（自动切换数据源）

    Args:
        code: 股票代码
        days: 获取天数
        include_indicators: 是否计算技术指标

    Returns:
        Tuple[DataFrame, source_name]: 日线数据 + 成功的数据源名称
    """
    breaker = get_daily_breaker()
    errors = []

    # 按优先级尝试各数据源
    for source, priority in DAILY_SOURCE_PRIORITY:
        if not breaker.is_available(source):
            logger.debug(f"[日线] {source} 熔断中，跳过")
            continue

        try:
            logger.info(f"[日线] 尝试 {source} 获取 {code}...")

            if source == "tushare":
                # Tushare 通过 DataFetcherManager 处理
                from .providers import DataFetcherManager
                manager = DataFetcherManager()
                df = manager.get_daily_data(code, days=days)
                source = manager._fetchers[0].name if manager._fetchers else "tushare"
            elif source == "akshare":
                df = _get_daily_akshare(code, days)
            elif source == "pytdx":
                # Pytdx 通过 DataFetcherManager 处理
                from .providers import DataFetcherManager, PytdxFetcher
                manager = DataFetcherManager()
                for f in manager._fetchers:
                    if f.name == "PytdxFetcher":
                        df = f.get_daily_data(code, days=days)
                        break
                else:
                    continue
            elif source == "baostock":
                df = _get_daily_baostock(code, days)
            else:
                continue

            if df is not None and not df.empty:
                breaker.record_success(source)

                if include_indicators:
                    df = _calculate_indicators(df)

                logger.info(f"[日线] {code} 使用 {source} 获取成功: rows={len(df)}")
                return df, source

            # 返回空数据视为不确定
            breaker.record_inconclusive(source)

        except Exception as e:
            breaker.record_failure(source, str(e))
            errors.append(f"{source}: {e}")
            logger.warning(f"[日线] {source} 失败: {e}")

    # 所有数据源失败
    error_msg = f"日线数据 {code} 获取失败:\n" + "\n".join(errors)
    logger.error(error_msg)
    return None, ""


def get_daily_as_bars(code: str, days: int = 60) -> List[DailyBar]:
    """获取日线数据并转换为 DailyBar 对象列表"""
    df, source = get_daily(code, days)

    if df is None or df.empty:
        return []

    bars = []
    for _, row in df.iterrows():
        bar = DailyBar(
            date=str(row.get('date', '')),
            open=safe_float(row.get('open', 0)),
            close=safe_float(row.get('close', 0)),
            high=safe_float(row.get('high', 0)),
            low=safe_float(row.get('low', 0)),
            volume=safe_float(row.get('volume', 0)),
            amount=safe_float(row.get('amount', 0)),
            pct_chg=safe_float(row.get('pct_chg', 0)),
            ma5=safe_float(row.get('ma5', 0)),
            ma10=safe_float(row.get('ma10', 0)),
            ma20=safe_float(row.get('ma20', 0)),
            volume_ratio=safe_float(row.get('volume_ratio', 1)),
        )
        bars.append(bar)

    return bars