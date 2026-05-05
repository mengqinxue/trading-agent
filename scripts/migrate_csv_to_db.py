#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CSV 数据迁移脚本 - 将股票日线 CSV 文件迁移到 SQLite 数据库

用法：
    python scripts/migrate_csv_to_db.py

数据源：data/CN_A/stock_daily/*.csv
目标：data/market/daily/stocks.db
"""

import csv
import sqlite3
import sys
from pathlib import Path
from typing import List
import logging

# 添加项目根目录到 path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.data.core.database import DatabaseManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def parse_csv_filename(filename: str) -> tuple[str, str]:
    """解析 CSV 文件名，提取代码和名称

    格式: 000001_平安银行_Daily_To2026.csv
    """
    parts = filename.replace(".csv", "").split("_")
    if len(parts) >= 2:
        code = parts[0]
        name = parts[1]
        return code, name
    return filename.replace(".csv", ""), ""


def read_stock_csv(csv_path: Path) -> list[dict]:
    """读取股票 CSV 文件"""
    data = []

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # 标准化字段名
            record = {
                "code": row.get("code") or row.get("股票代码") or "",
                "date": row.get("date") or row.get("日期") or "",
                "open": float(row.get("open") or row.get("开盘") or 0),
                "high": float(row.get("high") or row.get("最高") or 0),
                "low": float(row.get("low") or row.get("最低") or 0),
                "close": float(row.get("close") or row.get("收盘") or 0),
                "volume": float(row.get("volume") or row.get("成交量") or 0),
                "amount": float(row.get("amount") or row.get("成交额") or 0),
                "pct_chg": float(row.get("pct_chg") or row.get("涨跌幅") or 0),
                "turnover": float(row.get("turnover") or row.get("换手率") or 0),
            }
            # 确保日期格式正确
            if record["date"]:
                data.append(record)

    return data


def read_index_csv(csv_path: Path) -> list[dict]:
    """读取指数 CSV 文件"""
    data = []

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            record = {
                "code": row.get("code") or row.get("指数代码") or "",
                "date": row.get("date") or row.get("日期") or "",
                "open": float(row.get("open") or row.get("开盘点位") or 0),
                "high": float(row.get("high") or row.get("最高点位") or 0),
                "low": float(row.get("low") or row.get("最低点位") or 0),
                "close": float(row.get("close") or row.get("收盘点位") or 0),
                "volume": float(row.get("volume") or row.get("成交量") or 0),
                "amount": float(row.get("amount") or row.get("成交额") or 0),
                "pct_chg": float(row.get("pct_chg") or row.get("涨跌幅") or 0),
            }
            if record["date"]:
                data.append(record)

    return data


def migrate_stock_daily(
    csv_dir: Path,
    db_path: Path,
    batch_size: int = 1000
) -> int:
    """迁移股票日线数据"""
    logger.info(f"开始迁移股票日线数据: {csv_dir}")

    # 创建数据库
    db = DatabaseManager(db_path)
    db.connect()
    db.create_tables()

    # 获取所有 CSV 文件
    csv_files = list(csv_dir.glob("*.csv"))
    total_files = len(csv_files)
    logger.info(f"发现 {total_files} 个 CSV 文件")

    if total_files == 0:
        logger.warning("没有找到 CSV 文件")
        return 0

    total_records = 0
    processed_files = 0

    # 批量处理
    all_data = []

    for csv_file in csv_files:
        code, name = parse_csv_filename(csv_file.name)

        try:
            data = read_stock_csv(csv_file)

            # 补充代码（如果 CSV 中缺失）
            for record in data:
                if not record["code"]:
                    record["code"] = code

            all_data.extend(data)
            processed_files += 1

            # 每 100 个文件批量插入一次
            if len(all_data) >= batch_size * 100:
                inserted = db.insert_daily_data("stock_daily", all_data, batch_size)
                total_records += inserted
                all_data = []
                logger.info(f"进度: {processed_files}/{total_files} 文件, {total_records} 条记录")

        except Exception as e:
            logger.error(f"处理文件失败 {csv_file}: {e}")
            continue

    # 插入剩余数据
    if all_data:
        inserted = db.insert_daily_data("stock_daily", all_data, batch_size)
        total_records += inserted

    db.close()
    logger.info(f"迁移完成: {processed_files} 文件, {total_records} 条记录")
    return total_records


def migrate_index_daily(
    csv_dir: Path,
    db_path: Path
) -> int:
    """迁移指数日线数据"""
    logger.info(f"开始迁移指数日线数据: {csv_dir}")

    db = DatabaseManager(db_path)
    db.connect()
    db.create_tables()

    csv_files = list(csv_dir.glob("*.csv"))
    total_files = len(csv_files)
    logger.info(f"发现 {total_files} 个指数 CSV 文件")

    total_records = 0
    all_data = []

    for csv_file in csv_files:
        try:
            data = read_index_csv(csv_file)
            all_data.extend(data)
        except Exception as e:
            logger.error(f"处理文件失败 {csv_file}: {e}")

    if all_data:
        total_records = db.insert_daily_data("index_daily", all_data)

    db.close()
    logger.info(f"迁移完成: {total_records} 条记录")
    return total_records


def main():
    """主函数"""
    # 数据路径
    data_root = project_root / "data" / "CN_A"
    stock_csv_dir = data_root / "stock_daily"
    index_csv_dir = data_root / "index_daily"

    # 目标数据库路径
    db_dir = project_root / "data" / "market" / "daily"
    db_dir.mkdir(parents=True, exist_ok=True)

    stock_db_path = db_dir / "stocks.db"
    index_db_path = db_dir / "index.db"

    logger.info("=" * 60)
    logger.info("CSV 数据迁移脚本")
    logger.info("=" * 60)

    # 迁移股票数据
    if stock_csv_dir.exists():
        stock_records = migrate_stock_daily(stock_csv_dir, stock_db_path)
        logger.info(f"股票日线迁移完成: {stock_records} 条")
    else:
        logger.warning(f"股票 CSV 目录不存在: {stock_csv_dir}")

    # 迁移指数数据
    if index_csv_dir.exists():
        index_records = migrate_index_daily(index_csv_dir, index_db_path)
        logger.info(f"指数日线迁移完成: {index_records} 条")
    else:
        logger.warning(f"指数 CSV 目录不存在: {index_csv_dir}")

    logger.info("=" * 60)
    logger.info("迁移完成")
    logger.info(f"股票数据库: {stock_db_path}")
    logger.info(f"指数数据库: {index_db_path}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()