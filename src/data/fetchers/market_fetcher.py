# -*- coding: utf-8 -*-
"""行情数据获取器 - 统一管理行情数据获取"""

import logging
from typing import Optional, List, Dict, Any
from pathlib import Path

from src.data.core.database import DatabaseManager
from src.data.local_sources.mootdx_source import MootdxSource

logger = logging.getLogger(__name__)


class MarketFetcher:
    """行情数据获取器"""

    def __init__(
        self,
        db_path: Path,
        primary_source: str = "mootdx"
    ):
        self.db_path = Path(db_path)
        self.db = DatabaseManager(db_path)
        self.mootdx = MootdxSource()
        self.primary_source = primary_source

    def fetch_stock_daily(
        self,
        code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        use_cache: bool = True
    ) -> List[Dict[str, Any]]:
        """获取股票日线数据

        优先从数据库读取，缺失时从数据源获取

        Args:
            code: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            use_cache: 是否使用数据库缓存

        Returns:
            日线数据列表
        """
        # 优先从数据库读取
        if use_cache:
            data = self.db.query_by_code("stock_daily", code, start_date, end_date)
            if data:
                logger.info(f"从数据库读取 {code}: {len(data)} 条")
                return data

        # 从数据源获取
        logger.info(f"从 mootdx 获取 {code}")
        data = self.mootdx.get_stock_daily(code, start_date, end_date)

        # 存入数据库
        if data:
            self.db.insert_daily_data("stock_daily", data)
            logger.info(f"数据已缓存: {len(data)} 条")

        return data

    def fetch_index_daily(
        self,
        code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """获取指数日线数据"""
        # 从数据库读取
        data = self.db.query_by_code("index_daily", code, start_date, end_date)
        if data:
            return data

        # 从 mootdx 获取
        data = self.mootdx.get_index_daily(code, start_date, end_date)
        if data:
            self.db.insert_daily_data("index_daily", data)

        return data

    def fetch_realtime(self, codes: List[str]) -> List[Dict[str, Any]]:
        """获取实时行情"""
        return self.mootdx.get_realtime_quotes(codes)

    def fetch_minute_data(self, code: str) -> List[Dict[str, Any]]:
        """获取分时数据"""
        return self.mootdx.get_minute_data(code)

    def fetch_auction_data(self, code: str) -> Dict[str, Any]:
        """获取竞价数据"""
        return self.mootdx.get_auction_data(code)

    def get_all_stocks_by_date(self, date: str) -> Dict[str, Dict[str, Any]]:
        """获取某日所有股票数据（用于回测）

        Args:
            date: 日期字符串

        Returns:
            {code: data} 格式的数据
        """
        return self.db.query_by_date("stock_daily", date)

    def close(self):
        """关闭数据库连接"""
        self.db.close()