# -*- coding: utf-8 -*-
"""
研报评级获取模块

获取机构研报评级数据：评级、目标价、机构名称等。
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

import pandas as pd

from .types import ResearchReport, safe_float
from .sources import random_sleep

logger = logging.getLogger(__name__)


# ============================================
# Akshare 研报评级获取
# ============================================

def _get_research_akshare(code: str, days: int = 90) -> List[ResearchReport]:
    """使用 Akshare 获取研报评级"""
    try:
        import akshare as ak

        random_sleep()

        # 获取研报数据
        # stock_rank_forecast_cninfo - 研报预测
        # stock_em_hsgt_north_net_flow_in - 无研报接口

        reports = []

        # 方法1：东方财富研报
        try:
            df = ak.stock_rank_forecast_cninfo(symbol=code)

            if df is not None and not df.empty:
                for _, row in df.head(20).iterrows():
                    report = ResearchReport(
                        code=code,
                        name=str(row.get('名称', '')),
                        date=str(row.get('发布日期', '')),
                        rating=str(row.get('评级', '')),
                        target_price=safe_float(row.get('目标价', 0)),
                        institution=str(row.get('机构', '')),
                        analyst=str(row.get('分析师', '')),
                    )
                    reports.append(report)

        except Exception as e:
            logger.debug(f"[研报Akshare-预测] {code}: {e}")

        # 方法2：研报评级统计
        if not reports:
            try:
                df = ak.stock_rank_rating_predict(symbol=code)

                if df is not None and not df.empty:
                    for _, row in df.head(10).iterrows():
                        report = ResearchReport(
                            code=code,
                            date=str(row.get('日期', '')),
                            rating=str(row.get('评级', '')),
                            institution=str(row.get('机构', '')),
                        )
                        reports.append(report)

            except Exception as e:
                logger.debug(f"[研报Akshare-评级] {code}: {e}")

        # 过滤最近 days 天
        cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        reports = [r for r in reports if r.date >= cutoff_date]

        return reports

    except Exception as e:
        logger.warning(f"[研报Akshare] {code} 获取失败: {e}")
        return []


# ============================================
# Tushare 研报评级获取
# ============================================

def _get_research_tushare(code: str, days: int = 90) -> List[ResearchReport]:
    """使用 Tushare 获取研报评级"""
    try:
        import tushare as ts

        pro = ts.pro_api()

        # 获取研报评级
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y%m%d')

        # 需要足够积分才能访问
        df = pro.report(ts_code=f"{code}.SH", start_date=start_date, end_date=end_date)

        if df is None or df.empty:
            df = pro.report(ts_code=f"{code}.SZ", start_date=start_date, end_date=end_date)

        if df is None or df.empty:
            return []

        reports = []
        for _, row in df.iterrows():
            report = ResearchReport(
                code=code,
                date=str(row.get('ann_date', '')),
                rating=str(row.get('rating', '')),
                target_price=safe_float(row.get('target_price', 0)),
                institution=str(row.get('org_name', '')),
            )
            reports.append(report)

        return reports

    except Exception as e:
        logger.warning(f"[研报Tushare] {code} 获取失败: {e}")
        return []


# ============================================
# 统一接口
# ============================================

def get_research_reports(code: str, days: int = 90) -> List[ResearchReport]:
    """
    获取研报评级数据

    Args:
        code: 股票代码
        days: 查询天数

    Returns:
        研报列表
    """
    for source in ['akshare', 'tushare']:
        try:
            logger.info(f"[研报] 尝试 {source} 获取 {code}...")

            if source == 'akshare':
                reports = _get_research_akshare(code, days)
            elif source == 'tushare':
                reports = _get_research_tushare(code, days)
            else:
                continue

            if reports:
                logger.info(f"[研报] {code} 使用 {source} 获取成功: {len(reports)} 条")
                return reports

        except Exception as e:
            logger.warning(f"[研报] {source} 失败: {e}")

    logger.warning(f"[研报] {code} 所有数据源失败")
    return []


def get_research_summary(code: str, days: int = 90) -> Dict[str, Any]:
    """
    获取研报评级汇总

    Args:
        code: 股票代码
        days: 查询天数

    Returns:
        汇总信息：平均评级、目标价范围等
    """
    reports = get_research_reports(code, days)

    if not reports:
        return {'code': code, 'count': 0, 'avg_rating': '无数据'}

    # 统计评级分布
    rating_counts = {}
    target_prices = []

    for r in reports:
        rating = r.rating.strip()
        if rating:
            rating_counts[rating] = rating_counts.get(rating, 0) + 1
        if r.target_price > 0:
            target_prices.append(r.target_price)

    # 主要评级
    avg_rating = max(rating_counts.items(), key=lambda x: x[1])[0] if rating_counts else ''

    # 目标价范围
    target_price_range = {
        'min': min(target_prices) if target_prices else 0,
        'max': max(target_prices) if target_prices else 0,
        'avg': sum(target_prices) / len(target_prices) if target_prices else 0,
    }

    return {
        'code': code,
        'count': len(reports),
        'avg_rating': avg_rating,
        'rating_distribution': rating_counts,
        'target_price_range': target_price_range,
        'institutions': [r.institution for r in reports[:5]],
    }


def get_rating_score(code: str) -> float:
    """
    获取评级评分（-1到1）

    Args:
        code: 股票代码

    Returns:
        评分：买入=1, 增持=0.5, 中性=0, 减持=-0.5, 卖出=-1
    """
    summary = get_research_summary(code)

    if summary['count'] == 0:
        return 0.0

    distribution = summary.get('rating_distribution', {})

    # 计算加权评分
    score = 0.0
    total = sum(distribution.values())

    rating_weights = {
        '买入': 1.0,
        '增持': 0.5,
        '推荐': 0.5,
        '中性': 0.0,
        '持有': 0.0,
        '减持': -0.5,
        '卖出': -1.0,
    }

    for rating, count in distribution.items():
        weight = rating_weights.get(rating, 0.0)
        score += weight * count / total

    return score