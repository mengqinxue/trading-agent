#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""每日数据更新脚本 - 使用 mootdx 更新日线数据

用法：
    python scripts/update_daily_data.py
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import logging

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.data.core.database import DatabaseManager
from src.data.sources.mootdx_source import MootdxSource

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def update_stock_daily(db_path: Path, days: int = 30) -> int:
    """更新股票日线数据

    Args:
        db_path: 数据库路径
        days: 更最近多少天的数据

    Returns:
        更新记录数
    """
    logger.info("开始更新股票日线数据")

    db = DatabaseManager(db_path)
    db.connect()

    # 获取最新日期
    latest_date = db.get_latest_date("stock_daily")
    logger.info(f"数据库最新日期: {latest_date}")

    # 计算需要更新的日期范围
    end_date = datetime.now().strftime("%Y-%m-%d")
    if latest_date:
        start_date = latest_date
    else:
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    logger.info(f"更新日期范围: {start_date} ~ {end_date}")

    # 获取股票列表
    stocks = db.get_stock_list()
    logger.info(f"股票数量: {len(stocks)}")

    if len(stocks) == 0:
        logger.warning("数据库中没有股票数据，请先运行迁移脚本")
        return 0

    # 使用 mootdx 获取数据
    source = MootdxSource()
    total_updated = 0

    for stock in stocks[:100]:  # 先更新前100只测试
        code = stock.get("code")
        logger.info(f"更新股票: {code}")

        try:
            data = source.get_stock_daily(code, start_date, end_date)

            if data:
                inserted = db.insert_daily_data("stock_daily", data)
                total_updated += inserted

        except Exception as e:
            logger.error(f"更新股票 {code} 失败: {e}")
            continue

    db.close()
    logger.info(f"更新完成: {total_updated} 条记录")
    return total_updated


def main():
    """主函数"""
    db_dir = project_root / "data" / "market" / "daily"
    db_path = db_dir / "stocks.db"

    if not db_path.exists():
        logger.error(f"数据库不存在: {db_path}")
        logger.info("请先运行 migrate_csv_to_db.py 创建数据库")
        return

    logger.info("=" * 60)
    logger.info("每日数据更新脚本")
    logger.info("=" * 60)

    updated = update_stock_daily(db_path)

    logger.info("=" * 60)
    logger.info(f"更新完成: {updated} 条")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()