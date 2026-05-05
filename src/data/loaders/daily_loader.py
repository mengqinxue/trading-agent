# -*- coding: utf-8 -*-
"""日线数据加载器 - 高性能 SQLite 数据查询"""

import sqlite3
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class DailyLoader:
    """日线数据加载器（SQLite 版本）"""

    def __init__(self, db_path: Path | str):
        self.db_path = Path(db_path)
        self.conn: Optional[sqlite3.Connection] = None

    def connect(self) -> sqlite3.Connection:
        """连接数据库"""
        if self.conn is None:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row
        return self.conn

    def close(self) -> None:
        """关闭连接"""
        if self.conn:
            self.conn.close()
            self.conn = None

    def load_date(self, date: str) -> dict[str, dict]:
        """按日期加载所有股票数据 - 单次查询

        Args:
            date: 日期字符串 (YYYY-MM-DD)

        Returns:
            {code: {data_dict}} 格式的数据
        """
        conn = self.connect()
        cursor = conn.execute(
            "SELECT * FROM stock_daily WHERE date = ?",
            (date,)
        )
        rows = cursor.fetchall()
        return {row["code"]: dict(row) for row in rows}

    def load_stock(
        self,
        code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> list[dict]:
        """按股票加载日期范围 - 单次查询

        Args:
            code: 股票代码
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            按日期排序的数据列表
        """
        conn = self.connect()

        if start_date and end_date:
            cursor = conn.execute(
                "SELECT * FROM stock_daily WHERE code = ? AND date BETWEEN ? AND ? ORDER BY date",
                (code, start_date, end_date)
            )
        elif start_date:
            cursor = conn.execute(
                "SELECT * FROM stock_daily WHERE code = ? AND date >= ? ORDER BY date",
                (code, start_date)
            )
        elif end_date:
            cursor = conn.execute(
                "SELECT * FROM stock_daily WHERE code = ? AND date <= ? ORDER BY date",
                (code, end_date)
            )
        else:
            cursor = conn.execute(
                "SELECT * FROM stock_daily WHERE code = ? ORDER BY date",
                (code,)
            )

        return [dict(row) for row in cursor.fetchall()]

    def load_multiple_stocks(
        self,
        codes: list[str],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> dict[str, list[dict]]:
        """批量加载多只股票数据

        Args:
            codes: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            {code: [data_list]} 格式的数据
        """
        result = {}
        for code in codes:
            result[code] = self.load_stock(code, start_date, end_date)
        return result

    def load_date_range(
        self,
        start_date: str,
        end_date: str
    ) -> dict[str, dict[str, dict]]:
        """加载日期范围内的所有股票数据

        Args:
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            {date: {code: {data}}} 格式的数据
        """
        conn = self.connect()
        cursor = conn.execute(
            "SELECT * FROM stock_daily WHERE date BETWEEN ? AND ? ORDER BY date, code",
            (start_date, end_date)
        )

        result = {}
        for row in cursor.fetchall():
            date = row["date"]
            code = row["code"]
            if date not in result:
                result[date] = {}
            result[date][code] = dict(row)

        return result

    def get_available_dates(self) -> list[str]:
        """获取所有可用日期"""
        conn = self.connect()
        cursor = conn.execute(
            "SELECT DISTINCT date FROM stock_daily ORDER BY date"
        )
        return [row["date"] for row in cursor.fetchall()]

    def get_latest_date(self) -> Optional[str]:
        """获取最新日期"""
        conn = self.connect()
        cursor = conn.execute("SELECT MAX(date) as max_date FROM stock_daily")
        row = cursor.fetchone()
        return row["max_date"] if row else None


class IndexLoader:
    """指数数据加载器"""

    def __init__(self, db_path: Path | str):
        self.db_path = Path(db_path)
        self.conn: Optional[sqlite3.Connection] = None

    def connect(self) -> sqlite3.Connection:
        if self.conn is None:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row
        return self.conn

    def load_index(
        self,
        code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> list[dict]:
        """加载指数数据"""
        conn = self.connect()

        if start_date and end_date:
            cursor = conn.execute(
                "SELECT * FROM index_daily WHERE code = ? AND date BETWEEN ? AND ? ORDER BY date",
                (code, start_date, end_date)
            )
        else:
            cursor = conn.execute(
                "SELECT * FROM index_daily WHERE code = ? ORDER BY date",
                (code,)
            )

        return [dict(row) for row in cursor.fetchall()]