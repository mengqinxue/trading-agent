# -*- coding: utf-8 -*-
"""mootdx 数据源 - 通达信行情数据"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import pandas as pd

from mootdx.quotes import Quotes

logger = logging.getLogger(__name__)


class MootdxSource:
    """mootdx 数据源 - 通达信行情接口"""

    def __init__(
        self,
        server: str = "public",
        host: Optional[str] = None,
        port: Optional[int] = None
    ):
        """初始化 mootdx 数据源

        Args:
            server: 服务器类型 (public/local)
            host: 本地通达信地址 (可选)
            port: 本地通达信端口 (可选)
        """
        if server == "local" and host and port:
            self.client = Quotes.factory(market="std", host=host, port=port)
            logger.info(f"连接本地通达信: {host}:{port}")
        else:
            # 使用公共服务器
            self.client = Quotes.factory(market="std")
            logger.info("连接公共通达信服务器")

    def get_stock_daily(
        self,
        code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """获取股票日线数据

        Args:
            code: 股票代码 (如 000001)
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)

        Returns:
            日线数据列表
        """
        # mootdx 使用市场代码
        market = self._get_market(code)

        try:
            # 获取日线数据
            df = self.client.security_bars(
                market=market,
                code=code,
                start=0,
                count=800  # 获取最近800条
            )

            if df is None or df.empty:
                logger.warning(f"未获取到数据: {code}")
                return []

            # 转换格式
            data = []
            for _, row in df.iterrows():
                date_str = row.get("datetime", "").strftime("%Y-%m-%d")

                # 日期过滤
                if start_date and date_str < start_date:
                    continue
                if end_date and date_str > end_date:
                    continue

                data.append({
                    "code": code,
                    "date": date_str,
                    "open": float(row.get("open", 0)),
                    "high": float(row.get("high", 0)),
                    "low": float(row.get("low", 0)),
                    "close": float(row.get("close", 0)),
                    "volume": float(row.get("vol", 0)),
                    "amount": float(row.get("amount", 0)),
                    "pct_chg": self._calc_pct_chg(row),
                })

            logger.info(f"获取日线数据: {code}, {len(data)} 条")
            return data

        except Exception as e:
            logger.error(f"获取日线数据失败 {code}: {e}")
            return []

    def get_index_daily(
        self,
        code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """获取指数日线数据

        Args:
            code: 指数代码 (如 000001 为上证指数)
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            指数日线数据列表
        """
        try:
            # 指数市场代码
            market = 1 if code.startswith("000") or code.startswith("88") else 0

            df = self.client.index_bars(
                market=market,
                code=code,
                start=0,
                count=800
            )

            if df is None or df.empty:
                return []

            data = []
            for _, row in df.iterrows():
                date_str = row.get("datetime", "").strftime("%Y-%m-%d")

                if start_date and date_str < start_date:
                    continue
                if end_date and date_str > end_date:
                    continue

                data.append({
                    "code": code,
                    "date": date_str,
                    "open": float(row.get("open", 0)),
                    "high": float(row.get("high", 0)),
                    "low": float(row.get("low", 0)),
                    "close": float(row.get("close", 0)),
                    "volume": float(row.get("vol", 0)),
                    "amount": float(row.get("amount", 0)),
                    "pct_chg": self._calc_pct_chg(row),
                })

            return data

        except Exception as e:
            logger.error(f"获取指数数据失败 {code}: {e}")
            return []

    def get_realtime_quotes(self, codes: List[str]) -> List[Dict[str, Any]]:
        """获取实时行情

        Args:
            codes: 股票代码列表

        Returns:
            实时行情数据列表
        """
        results = []

        for code in codes:
            market = self._get_market(code)

            try:
                quotes = self.client.quotes(market=market, code=code)

                if quotes:
                    results.append({
                        "code": code,
                        "price": float(quotes.get("price", 0)),
                        "open": float(quotes.get("open", 0)),
                        "high": float(quotes.get("high", 0)),
                        "low": float(quotes.get("low", 0)),
                        "volume": float(quotes.get("vol", 0)),
                        "amount": float(quotes.get("amount", 0)),
                        "bid1": float(quotes.get("bid1", 0)),
                        "ask1": float(quotes.get("ask1", 0)),
                        "last_close": float(quotes.get("last_close", 0)),
                    })

            except Exception as e:
                logger.error(f"获取实时行情失败 {code}: {e}")

        return results

    def get_minute_data(
        self,
        code: str,
        date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """获取分时数据

        Args:
            code: 股票代码
            date: 日期 (可选，默认今天)

        Returns:
            分时数据列表
        """
        market = self._get_market(code)

        try:
            df = self.client.minute_data(market=market, code=code)

            if df is None or df.empty:
                return []

            data = []
            for _, row in df.iterrows():
                time_str = row.get("datetime", "").strftime("%H:%M")
                data.append({
                    "code": code,
                    "time": time_str,
                    "price": float(row.get("price", 0)),
                    "volume": float(row.get("vol", 0)),
                    "amount": float(row.get("amount", 0)),
                })

            return data

        except Exception as e:
            logger.error(f"获取分时数据失败 {code}: {e}")
            return []

    def get_auction_data(self, code: str) -> Dict[str, Any]:
        """获取集合竞价数据

        Args:
            code: 股票代码

        Returns:
            竞价数据
        """
        market = self._get_market(code)

        try:
            quotes = self.client.quotes(market=market, code=code)

            if quotes:
                return {
                    "code": code,
                    "call_price": float(quotes.get("call_price", 0)),
                    "call_volume": float(quotes.get("call_vol", 0)),
                    "bid1": float(quotes.get("bid1", 0)),
                    "bid1_vol": float(quotes.get("bid1_vol", 0)),
                    "ask1": float(quotes.get("ask1", 0)),
                    "ask1_vol": float(quotes.get("ask1_vol", 0)),
                }

        except Exception as e:
            logger.error(f"获取竞价数据失败 {code}: {e}")

        return {}

    def get_stock_list(self) -> List[Dict[str, str]]:
        """获取股票列表"""
        try:
            # 获取深市股票列表
            sz_list = self.client.stocks(market=0)
            # 获取沪市股票列表
            sh_list = self.client.stocks(market=1)

            results = []

            if sz_list:
                for row in sz_list:
                    results.append({
                        "code": row.get("code", ""),
                        "name": row.get("name", ""),
                        "market": "SZ",
                    })

            if sh_list:
                for row in sh_list:
                    results.append({
                        "code": row.get("code", ""),
                        "name": row.get("name", ""),
                        "market": "SH",
                    })

            logger.info(f"获取股票列表: {len(results)} 只")
            return results

        except Exception as e:
            logger.error(f"获取股票列表失败: {e}")
            return []

    def _get_market(self, code: str) -> int:
        """判断股票市场代码

        Args:
            code: 股票代码

        Returns:
            市场代码 (0=深市, 1=沪市)
        """
        # 深市: 00, 30 开头
        # 沪市: 60, 68 开头
        if code.startswith("6"):
            return 1
        else:
            return 0

    def _calc_pct_chg(self, row: pd.Series) -> float:
        """计算涨跌幅"""
        close = row.get("close", 0)
        last_close = row.get("last_close", 0)

        if last_close > 0:
            return (close - last_close) / last_close * 100
        return 0.0