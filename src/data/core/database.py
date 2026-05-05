# -*- coding: utf-8 -*-
"""数据库管理模块 - SQLite 数据库核心功能"""

import sqlite3
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class DatabaseManager:
    """SQLite 数据库管理器"""

    def __init__(self, db_path: Path | str):
        self.db_path = Path(db_path)
        self.conn: Optional[sqlite3.Connection] = None

    def connect(self) -> sqlite3.Connection:
        """连接数据库"""
        if self.conn is None:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row
            logger.info(f"数据库连接成功: {self.db_path}")
        return self.conn

    def close(self) -> None:
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
            self.conn = None
            logger.info(f"数据库连接关闭: {self.db_path}")

    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        """执行 SQL 语句"""
        conn = self.connect()
        return conn.execute(sql, params)

    def executemany(self, sql: str, params_list: list[tuple]) -> sqlite3.Cursor:
        """批量执行 SQL 语句"""
        conn = self.connect()
        return conn.executemany(sql, params_list)

    def commit(self) -> None:
        """提交事务"""
        if self.conn:
            self.conn.commit()

    def create_tables(self) -> None:
        """创建数据表"""
        conn = self.connect()

        # 股票日线表
        conn.execute("""
            CREATE TABLE IF NOT EXISTS stock_daily (
                code TEXT NOT NULL,
                date TEXT NOT NULL,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume REAL,
                amount REAL,
                pct_chg REAL,
                turnover REAL,
                PRIMARY KEY (code, date)
            )
        """)

        # 创建索引
        conn.execute("CREATE INDEX IF NOT EXISTS idx_daily_date ON stock_daily(date)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_daily_code ON stock_daily(code)")

        # 指数日线表
        conn.execute("""
            CREATE TABLE IF NOT EXISTS index_daily (
                code TEXT NOT NULL,
                date TEXT NOT NULL,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume REAL,
                amount REAL,
                pct_chg REAL,
                PRIMARY KEY (code, date)
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_index_date ON index_daily(date)")

        # 板块日线表
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sector_daily (
                code TEXT NOT NULL,
                date TEXT NOT NULL,
                name TEXT,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume REAL,
                amount REAL,
                pct_chg REAL,
                lead_stock TEXT,
                PRIMARY KEY (code, date)
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_sector_date ON sector_daily(date)")

        conn.commit()
        logger.info("数据表创建完成")

    def insert_daily_data(
        self,
        table: str,
        data: list[dict],
        batch_size: int = 1000
    ) -> int:
        """批量插入日线数据

        Args:
            table: 表名 (stock_daily, index_daily, sector_daily)
            data: 数据列表，每条包含 code, date, open, high, low, close 等
            batch_size: 批量插入大小

        Returns:
            插入记录数
        """
        conn = self.connect()
        inserted = 0

        # 根据表名选择插入 SQL
        if table == "stock_daily":
            sql = """
                INSERT OR REPLACE INTO stock_daily
                (code, date, open, high, low, close, volume, amount, pct_chg, turnover)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
        elif table == "index_daily":
            sql = """
                INSERT OR REPLACE INTO index_daily
                (code, date, open, high, low, close, volume, amount, pct_chg)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
        elif table == "sector_daily":
            sql = """
                INSERT OR REPLACE INTO sector_daily
                (code, date, name, open, high, low, close, volume, amount, pct_chg, lead_stock)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
        else:
            raise ValueError(f"未知表名: {table}")

        # 批量插入
        for i in range(0, len(data), batch_size):
            batch = data[i:i + batch_size]

            if table == "stock_daily":
                params = [
                    (
                        row.get("code"),
                        row.get("date"),
                        row.get("open"),
                        row.get("high"),
                        row.get("low"),
                        row.get("close"),
                        row.get("volume"),
                        row.get("amount"),
                        row.get("pct_chg"),
                        row.get("turnover"),
                    )
                    for row in batch
                ]
            elif table == "index_daily":
                params = [
                    (
                        row.get("code"),
                        row.get("date"),
                        row.get("open"),
                        row.get("high"),
                        row.get("low"),
                        row.get("close"),
                        row.get("volume"),
                        row.get("amount"),
                        row.get("pct_chg"),
                    )
                    for row in batch
                ]
            elif table == "sector_daily":
                params = [
                    (
                        row.get("code"),
                        row.get("date"),
                        row.get("name"),
                        row.get("open"),
                        row.get("high"),
                        row.get("low"),
                        row.get("close"),
                        row.get("volume"),
                        row.get("amount"),
                        row.get("pct_chg"),
                        row.get("lead_stock"),
                    )
                    for row in batch
                ]

            conn.executemany(sql, params)
            inserted += len(batch)

            if i % (batch_size * 10) == 0:
                conn.commit()
                logger.info(f"已插入 {inserted}/{len(data)} 条记录")

        conn.commit()
        logger.info(f"数据插入完成: {inserted} 条")
        return inserted

    def query_by_date(self, table: str, date: str) -> list[dict]:
        """按日期查询数据"""
        conn = self.connect()
        cursor = conn.execute(
            f"SELECT * FROM {table} WHERE date = ?",
            (date,)
        )
        return [dict(row) for row in cursor.fetchall()]

    def query_by_code(
        self,
        table: str,
        code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> list[dict]:
        """按股票代码查询数据"""
        conn = self.connect()

        if start_date and end_date:
            cursor = conn.execute(
                f"SELECT * FROM {table} WHERE code = ? AND date BETWEEN ? AND ? ORDER BY date",
                (code, start_date, end_date)
            )
        elif start_date:
            cursor = conn.execute(
                f"SELECT * FROM {table} WHERE code = ? AND date >= ? ORDER BY date",
                (code, start_date)
            )
        elif end_date:
            cursor = conn.execute(
                f"SELECT * FROM {table} WHERE code = ? AND date <= ? ORDER BY date",
                (code, end_date)
            )
        else:
            cursor = conn.execute(
                f"SELECT * FROM {table} WHERE code = ? ORDER BY date",
                (code,)
            )

        return [dict(row) for row in cursor.fetchall()]

    def get_latest_date(self, table: str, code: Optional[str] = None) -> Optional[str]:
        """获取最新日期"""
        conn = self.connect()

        if code:
            cursor = conn.execute(
                f"SELECT MAX(date) as max_date FROM {table} WHERE code = ?",
                (code,)
            )
        else:
            cursor = conn.execute(
                f"SELECT MAX(date) as max_date FROM {table}"
            )

        row = cursor.fetchone()
        return row["max_date"] if row else None

    def get_stock_list(self) -> list[dict]:
        """获取所有股票列表（从日线数据中提取）"""
        conn = self.connect()
        cursor = conn.execute("""
            SELECT DISTINCT code, MAX(date) as latest_date
            FROM stock_daily
            GROUP BY code
            ORDER BY code
        """)
        return [dict(row) for row in cursor.fetchall()]

    def get_date_range(self, table: str) -> tuple[Optional[str], Optional[str]]:
        """获取数据的日期范围"""
        conn = self.connect()
        cursor = conn.execute(f"SELECT MIN(date) as min_date, MAX(date) as max_date FROM {table}")
        row = cursor.fetchone()
        return (row["min_date"], row["max_date"]) if row else (None, None)