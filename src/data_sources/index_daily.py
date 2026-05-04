# -*- coding: utf-8 -*-
"""
指数日线数据获取模块

获取主要指数的历史日线数据，用于判断大盘趋势（牛市/熊市/震荡市）。
"""

import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

# 数据目录
DATA_DIR = Path("data/CN_A")
INDEX_DAILY_DIR = DATA_DIR / "index_daily"
INDEX_DAILY_DIR.mkdir(exist_ok=True, parents=True)

# 主要指数代码
MAIN_INDEXES = {
    '000001': {'name': '上证指数', 'market': 'sh'},
    '399001': {'name': '深证成指', 'market': 'sz'},
    '399006': {'name': '创业板指', 'market': 'sz'},
    '000016': {'name': '上证50', 'market': 'sh'},
    '000300': {'name': '沪深300', 'market': 'sh'},
    '000905': {'name': '中证500', 'market': 'sh'},
    '000688': {'name': '科创50', 'market': 'sh'},
}


def get_index_daily_akshare(code: str, days: int = 120) -> Optional[pd.DataFrame]:
    """
    使用 Akshare 获取指数日线数据

    Args:
        code: 指数代码（如 000001）
        days: 获取天数（默认120天，约半年）

    Returns:
        日线数据 DataFrame
    """
    try:
        import akshare as ak

        # 根据代码判断市场
        if code.startswith('000') or code.startswith('88'):
            market = 'sh'  # 上海
        else:
            market = 'sz'  # 深圳

        full_code = f"{market}{code}"

        logger.info(f"[指数日线] 获取 {full_code} 最近 {days} 天数据...")

        # 计算日期范围
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=days*1.5)).strftime('%Y%m%d')

        # Akshare 指数日线接口
        df = ak.stock_zh_index_daily(symbol=full_code)

        if df is None or df.empty:
            logger.warning(f"[指数日线] {full_code} 获取失败")
            return None

        # 标准化列名
        df = df.rename(columns={
            'date': 'date',
            'open': 'open',
            'close': 'close',
            'high': 'high',
            'low': 'low',
            'volume': 'volume',
        })

        # 确保日期格式
        df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')

        # 按日期排序，取最近 days 天
        df = df.sort_values('date', ascending=True)
        df = df.tail(days)

        # 计算均线和涨跌幅
        df['ma5'] = df['close'].rolling(5).mean()
        df['ma10'] = df['close'].rolling(10).mean()
        df['ma20'] = df['close'].rolling(20).mean()
        df['ma60'] = df['close'].rolling(60).mean()
        df['pct_chg'] = df['close'].pct_change() * 100

        logger.info(f"[指数日线] {full_code} 获取成功: {len(df)} 条")

        return df

    except Exception as e:
        logger.error(f"[指数日线] 获取失败: {e}")
        return None


def save_index_daily(code: str, df: pd.DataFrame) -> None:
    """
    保存指数日线数据到本地

    Args:
        code: 指数代码
        df: 日线数据
    """
    name = MAIN_INDEXES.get(code, {}).get('name', code)
    filepath = INDEX_DAILY_DIR / f"{code}_{name}_Daily.csv"
    df.to_csv(filepath, index=False)
    logger.info(f"[指数日线] 保存到 {filepath}")


def load_index_daily(code: str) -> Optional[pd.DataFrame]:
    """
    加载本地指数日线数据

    Args:
        code: 指数代码

    Returns:
        日线数据 DataFrame 或 None
    """
    name = MAIN_INDEXES.get(code, {}).get('name', code)
    filepath = INDEX_DAILY_DIR / f"{code}_{name}_Daily.csv"

    if not filepath.exists():
        return None

    df = pd.read_csv(filepath)
    return df


def update_all_index_daily(days: int = 120) -> None:
    """
    更新所有主要指数的日线数据

    Args:
        days: 获取天数
    """
    logger.info(f"[指数日线] 开始更新所有指数，最近 {days} 天")

    for code, info in MAIN_INDEXES.items():
        df = get_index_daily_akshare(code, days)
        if df is not None:
            save_index_daily(code, df)

    logger.info("[指数日线] 全部更新完成")


def analyze_market_trend(code: str = '000001', df: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
    """
    分析指数趋势，判断市场状态（牛市/熊市/震荡市）

    Args:
        code: 指数代码（默认上证指数）
        df: 日线数据（可选，不传则从本地加载或获取）

    Returns:
        趋势分析结果
    """
    # 获取数据
    if df is None:
        df = load_index_daily(code)
        if df is None:
            df = get_index_daily_akshare(code, days=120)
            if df is not None:
                save_index_daily(code, df)

    if df is None or df.empty:
        return {
            'status': 'unknown',
            'message': '无法获取指数数据',
        }

    name = MAIN_INDEXES.get(code, {}).get('name', '未知指数')

    # 取最近数据
    latest = df.iloc[-1]
    close = float(latest['close'])
    ma5 = float(latest['ma5']) if pd.notna(latest['ma5']) else close
    ma10 = float(latest['ma10']) if pd.notna(latest['ma10']) else close
    ma20 = float(latest['ma20']) if pd.notna(latest['ma20']) else close
    ma60 = float(latest['ma60']) if pd.notna(latest['ma60']) else close

    # 计算近期涨跌幅
    recent_5d = df.tail(5)['pct_chg'].sum() if len(df) >= 5 else 0
    recent_10d = df.tail(10)['pct_chg'].sum() if len(df) >= 10 else 0
    recent_20d = df.tail(20)['pct_chg'].sum() if len(df) >= 20 else 0
    recent_60d = df.tail(60)['pct_chg'].sum() if len(df) >= 60 else 0

    # 计算均线位置关系
    above_ma5 = close > ma5
    above_ma10 = close > ma10
    above_ma20 = close > ma20
    above_ma60 = close > ma60

    # 均线多头排列：MA5 > MA10 > MA20 > MA60
    bullish_alignment = ma5 > ma10 and ma10 > ma20 and ma20 > ma60

    # 均线空头排列：MA5 < MA10 < MA20 < MA60
    bearish_alignment = ma5 < ma10 and ma10 < ma20 and ma20 < ma60

    # 判断市场状态
    status = '震荡市'
    trend_strength = 0
    signals = []

    # 牛市信号
    if bullish_alignment and above_ma60:
        if recent_60d > 10:
            status = '牛市'
            trend_strength = 80
            signals.append('均线多头排列，近60日涨幅超10%')
        elif recent_20d > 5:
            status = '偏强震荡'
            trend_strength = 60
            signals.append('均线多头排列，近20日涨幅超5%')
        else:
            status = '震荡偏强'
            trend_strength = 50
            signals.append('均线多头排列')

    # 熊市信号
    elif bearish_alignment and not above_ma60:
        if recent_60d < -10:
            status = '熊市'
            trend_strength = -80
            signals.append('均线空头排列，近60日跌幅超10%')
        elif recent_20d < -5:
            status = '偏弱震荡'
            trend_strength = -60
            signals.append('均线空头排列，近20日跌幅超5%')
        else:
            status = '震荡偏弱'
            trend_strength = -50
            signals.append('均线空头排列')

    # 其他震荡情况
    else:
        if above_ma20 and above_ma60:
            status = '震荡偏强'
            trend_strength = 30
            signals.append('价格在MA20和MA60上方')
        elif not above_ma20 and not above_ma60:
            status = '震荡偏弱'
            trend_strength = -30
            signals.append('价格在MA20和MA60下方')
        else:
            status = '震荡市'
            trend_strength = 0
            signals.append('均线交织，方向不明')

    # 成交量趋势
    vol_recent = df.tail(10)['volume'].mean() if len(df) >= 10 else 0
    vol_prev = df.tail(60).head(30)['volume'].mean() if len(df) >= 60 else vol_recent
    vol_ratio = vol_recent / vol_prev if vol_prev > 0 else 1

    if vol_ratio > 1.2:
        signals.append(f'成交量放大（近10日均量/前30日均量={vol_ratio:.2f}）')
    elif vol_ratio < 0.8:
        signals.append(f'成交量萎缩（近10日均量/前30日均量={vol_ratio:.2f}）')

    return {
        'code': code,
        'name': name,
        'status': status,
        'trend_strength': trend_strength,  # -100 到 100，负数熊市倾向，正数牛市倾向
        'price': close,
        'ma5': ma5,
        'ma10': ma10,
        'ma20': ma20,
        'ma60': ma60,
        'above_ma5': above_ma5,
        'above_ma10': above_ma10,
        'above_ma20': above_ma20,
        'above_ma60': above_ma60,
        'bullish_alignment': bullish_alignment,
        'bearish_alignment': bearish_alignment,
        'recent_5d_pct': recent_5d,
        'recent_10d_pct': recent_10d,
        'recent_20d_pct': recent_20d,
        'recent_60d_pct': recent_60d,
        'vol_ratio': vol_ratio,
        'signals': signals,
        'date': latest['date'],
    }


def get_market_overview() -> Dict[str, Any]:
    """
    获取市场整体概览

    Returns:
        多指数趋势汇总
    """
    results = {}

    # 分析主要指数
    for code in ['000001', '399001', '399006', '000300']:
        trend = analyze_market_trend(code)
        results[code] = trend

    # 综合判断
    sh_trend = results.get('000001', {})
    sz_trend = results.get('399001', {})
    cyb_trend = results.get('399006', {})

    # 计算综合趋势强度
    avg_strength = (
        sh_trend.get('trend_strength', 0) +
        sz_trend.get('trend_strength', 0) +
        cyb_trend.get('trend_strength', 0)
    ) / 3

    # 综合状态
    if avg_strength >= 60:
        overall_status = '牛市'
    elif avg_strength >= 30:
        overall_status = '偏强震荡'
    elif avg_strength <= -60:
        overall_status = '熊市'
    elif avg_strength <= -30:
        overall_status = '偏弱震荡'
    else:
        overall_status = '震荡市'

    return {
        'overall_status': overall_status,
        'overall_strength': avg_strength,
        'indices': results,
        'recommendation': _get_investment_recommendation(overall_status, avg_strength),
    }


def _get_investment_recommendation(status: str, strength: float) -> str:
    """
    根据市场状态给出投资建议
    """
    if status == '牛市':
        return '市场强势，可积极做多，关注龙头股和热点板块'
    elif status == '偏强震荡':
        return '市场偏强，可适度参与，优选业绩确定标的'
    elif status == '震荡市':
        return '市场震荡，宜谨慎操作，控制仓位，快进快出'
    elif status == '偏弱震荡':
        return '市场偏弱，建议轻仓观望，避免追高'
    elif status == '熊市':
        return '市场弱势，建议空仓或极轻仓，等待机会'
    else:
        return '市场状态不明，建议观望'


# CLI 命令
def cli_update_index():
    """CLI: 更新指数日线数据"""
    update_all_index_daily(days=120)


def cli_show_trend():
    """CLI: 显示市场趋势分析"""
    overview = get_market_overview()

    print("=" * 60)
    print(f"市场状态: {overview['overall_status']}")
    print(f"趋势强度: {overview['overall_strength']:.1f}")
    print(f"投资建议: {overview['recommendation']}")
    print("=" * 60)

    for code, trend in overview['indices'].items():
        print(f"\n{trend['name']} ({code}):")
        print(f"  当前价: {trend['price']:.2f}")
        print(f"  MA5: {trend['ma5']:.2f}, MA20: {trend['ma20']:.2f}, MA60: {trend['ma60']:.2f}")
        print(f"  近20日涨跌: {trend['recent_20d_pct']:.2f}%")
        print(f"  近60日涨跌: {trend['recent_60d_pct']:.2f}%")
        print(f"  状态: {trend['status']} (强度: {trend['trend_strength']})")
        for signal in trend['signals']:
            print(f"  - {signal}")