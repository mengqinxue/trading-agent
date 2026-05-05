# -*- coding: utf-8 -*-
"""
查询引擎

执行数据查询，返回结构化结果。
"""

import logging
import time
from typing import Dict, Any, List, Optional
import pandas as pd

from .templates import QUERY_TEMPLATES, get_template

logger = logging.getLogger(__name__)


# ============================================
# 查询引擎
# ============================================

class QueryEngine:
    """智能查询引擎"""

    def __init__(self):
        self._market_data_cache: Optional[pd.DataFrame] = None
        self._cache_time: float = 0
        self._cache_ttl: float = 600  # 10分钟缓存

    # === 数据获取 ===

    def _get_market_data(self) -> pd.DataFrame:
        """获取全市场实时数据（带缓存）"""
        current = time.time()

        if self._market_data_cache is not None and current - self._cache_time < self._cache_ttl:
            logger.debug(f"[查询] 使用缓存数据: elapsed={current - self._cache_time:.0f}s")
            return self._market_data_cache

        try:
            import akshare as ak
            df = ak.stock_zh_a_spot_em()

            if df is None or df.empty:
                logger.warning("[查询] 获取市场数据失败")
                return pd.DataFrame()

            self._market_data_cache = df
            self._cache_time = current
            logger.info(f"[查询] 获取全市场数据成功: rows={len(df)}, 缓存 {self._cache_ttl}s")
            return df

        except Exception as e:
            logger.error(f"[查询] 获取市场数据失败: {e}")
            return pd.DataFrame()

    def clear_cache(self) -> None:
        """清除缓存"""
        self._market_data_cache = None
        self._cache_time = 0
        logger.info("[查询] 缓存已清除")

    # === 查询执行 ===

    def query(self, template_id: str, **params) -> Dict[str, Any]:
        """执行查询

        Args:
            template_id: 模板ID（如 limit_up, high_turnover）
            **params: 查询参数（如 threshold=10, n=20）

        Returns:
            查询结果：count, stocks, date
        """
        template = get_template(template_id)
        if template is None:
            return {"error": f"未知模板: {template_id}"}

        # 获取数据
        df = self._get_market_data()
        if df.empty:
            return {"error": "无法获取市场数据"}

        # 应用条件
        try:
            condition = template['condition']
            if 'params' in template:
                # 带参数的模板
                result_df = condition(df, **params)
            else:
                result_df = condition(df)

            if callable(result_df):
                # 有些 lambda 返回的是 callable，需要再调用
                result_df = condition(df)

        except Exception as e:
            logger.error(f"[查询] 应用条件失败: {e}")
            return {"error": str(e)}

        # 格式化结果
        stocks = self._format_result(result_df, template['fields'])

        # 添加额外字段（所属板块）
        if 'extra_fields' in template and '所属板块' in template['extra_fields']:
            for stock in stocks:
                stock['sector'] = self._get_sector(stock['code'])

        return {
            "template": template_id,
            "name": template['name'],
            "count": len(stocks),
            "stocks": stocks,
            "date": self._get_current_date(),
            "params": params,
        }

    def _format_result(self, df: pd.DataFrame, fields: List[str]) -> List[Dict[str, Any]]:
        """格式化结果"""
        if df.empty:
            return []

        stocks = []
        for _, row in df.iterrows():
            stock = {}
            for field in fields:
                # 字段名映射
                field_map = {
                    '代码': 'code',
                    '名称': 'name',
                    '涨跌幅': 'change_pct',
                    '换手率': 'turnover_rate',
                    '流通市值': 'circ_mv',
                    '成交额': 'amount',
                    '市盈率-动态': 'pe_ratio',
                    '市净率': 'pb_ratio',
                }
                key = field_map.get(field, field)
                try:
                    stock[key] = row.get(field, None)
                    # 数值类型转换
                    if stock[key] is not None and isinstance(stock[key], (int, float)):
                        if field in ['流通市值', '成交额']:
                            stock[key] = float(stock[key])
                        elif field in ['涨跌幅', '换手率', '市盈率-动态', '市净率']:
                            stock[key] = float(stock[key])
                except Exception:
                    stock[key] = None
            stocks.append(stock)

        return stocks

    def _get_sector(self, code: str) -> str:
        """获取股票所属板块"""
        try:
            from src.data import get_stock_belong_sectors
            sectors = get_stock_belong_sectors(code)
            if sectors:
                return sectors[0].get('name', '')
        except Exception:
            pass
        return ''

    def _get_current_date(self) -> str:
        """获取当前日期"""
        return time.strftime('%Y-%m-%d')

    # === 市场统计 ===

    def get_market_stats(self) -> Dict[str, Any]:
        """获取市场涨跌统计"""
        df = self._get_market_data()
        if df.empty:
            return {}

        total = len(df)
        up_count = len(df[df['涨跌幅'] > 0])
        down_count = len(df[df['涨跌幅'] < 0])
        flat_count = len(df[df['涨跌幅'] == 0])
        limit_up_count = len(df[df['涨跌幅'] >= 9.9])
        limit_down_count = len(df[df['涨跌幅'] <= -9.9])

        return {
            "total": total,
            "up_count": up_count,
            "down_count": down_count,
            "flat_count": flat_count,
            "limit_up_count": limit_up_count,
            "limit_down_count": limit_down_count,
            "up_ratio": round(up_count / total * 100, 2) if total > 0 else 0,
            "date": self._get_current_date(),
        }

    # === 板块查询 ===

    def query_sector(self, sector_name: str, sort_by: str = '涨跌幅', n: int = 50) -> Dict[str, Any]:
        """查询板块成分股"""
        try:
            from src.data import get_sector_stocks
            codes = get_sector_stocks(sector_name)

            if not codes:
                return {"error": f"未找到板块: {sector_name}"}

            df = self._get_market_data()
            sector_df = df[df['代码'].isin(codes)]

            if sector_df.empty:
                return {"error": f"板块 {sector_name} 无股票数据"}

            # 排序
            ascending = sort_by in ['涨跌幅']  # 涨跌幅降序
            sector_df = sector_df.sort_values(sort_by, ascending=ascending).head(n)

            stocks = self._format_result(sector_df, ['代码', '名称', '涨跌幅', '换手率', '流通市值'])

            return {
                "sector": sector_name,
                "count": len(stocks),
                "stocks": stocks,
                "date": self._get_current_date(),
            }

        except Exception as e:
            logger.error(f"[查询板块] {sector_name} 失败: {e}")
            return {"error": str(e)}

    def get_sector_rankings(self, n: int = 10) -> Dict[str, Any]:
        """获取板块涨跌榜"""
        try:
            from src.data import get_sector_rankings
            top, bottom = get_sector_rankings(n)

            return {
                "hot_sectors": top,
                "weak_sectors": bottom,
                "date": self._get_current_date(),
            }

        except Exception as e:
            logger.error(f"[板块榜] 获取失败: {e}")
            return {"error": str(e)}


# ============================================
# 全局实例
# ============================================

_engine: Optional[QueryEngine] = None


def get_engine() -> QueryEngine:
    """获取查询引擎单例"""
    global _engine
    if _engine is None:
        _engine = QueryEngine()
    return _engine


def reset_engine() -> None:
    """重置引擎"""
    global _engine
    if _engine:
        _engine.clear_cache()
    _engine = None