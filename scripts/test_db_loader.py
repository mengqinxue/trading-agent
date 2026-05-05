#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试 SQLite 数据加载器性能"""

import sys
from pathlib import Path
import time

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_db_loader():
    """测试数据库加载器"""
    from src.data.loaders import DailyLoader

    db_path = project_root / "data" / "market" / "daily" / "stocks.db"

    if not db_path.exists():
        print("数据库不存在，请先运行迁移脚本")
        return

    loader = DailyLoader(db_path)

    # 测试 1: 按日期加载所有股票
    print("\n=== 测试 1: 按日期加载 ===")
    # 使用数据库中最近的日期
    test_date = loader.get_latest_date()
    print(f"最新日期: {test_date}")
    start = time.time()
    data = loader.load_date(test_date)
    elapsed = time.time() - start
    print(f"加载日期 {test_date}: {len(data)} 条股票, 耗时 {elapsed:.3f}s")

    # 测试 2: 按股票加载日期范围
    print("\n=== 测试 2: 按股票加载 ===")
    test_code = "000001"
    # 使用数据库实际存在的日期范围
    start = time.time()
    data = loader.load_stock(test_code)  # 加载全部数据
    elapsed = time.time() - start
    print(f"加载股票 {test_code} 全部数据: {len(data)} 条, 耗时 {elapsed:.3f}s")
    if data:
        print(f"日期范围: {data[0]['date']} ~ {data[-1]['date']}")

    # 测试 3: 获取可用日期
    print("\n=== 测试 3: 可用日期 ===")
    start = time.time()
    dates = loader.get_available_dates()
    elapsed = time.time() - start
    print(f"总交易日: {len(dates)} 条, 耗时 {elapsed:.3f}s")
    print(f"日期范围: {dates[0]} ~ {dates[-1]}")

    # 测试 4: 模拟回测（加载 100 天数据）
    print("\n=== 测试 4: 模拟回测 ===")
    test_dates = dates[-100:]  # 最近 100 天
    start = time.time()
    total_records = 0
    for date in test_dates:
        data = loader.load_date(date)
        total_records += len(data)
    elapsed = time.time() - start
    print(f"加载 100 天数据: {total_records} 条记录, 耗时 {elapsed:.3f}s")
    print(f"平均每秒加载: {total_records / elapsed:.0f} 条")

    loader.close()


def test_csv_loader_comparison():
    """对比 CSV 和 SQLite 性能"""
    import pandas as pd

    csv_dir = project_root / "data" / "CN_A" / "stock_daily"
    db_path = project_root / "data" / "market" / "daily" / "stocks.db"

    if not db_path.exists():
        print("数据库不存在")
        return

    test_date = "2023-12-29"

    # CSV 方式
    print("\n=== CSV 方式 ===")
    start = time.time()
    csv_count = 0
    for file in list(csv_dir.glob("*.csv"))[:100]:  # 只测试前 100 个文件
        df = pd.read_csv(file)
        if "date" in df.columns:
            row = df[df["date"].astype(str) == test_date]
            if not row.empty:
                csv_count += 1
    csv_elapsed = time.time() - start
    print(f"CSV 加载: {csv_count} 条, 耗时 {csv_elapsed:.3f}s")

    # SQLite 方式
    print("\n=== SQLite 方式 ===")
    from src.data.loaders import DailyLoader
    loader = DailyLoader(db_path)
    start = time.time()
    data = loader.load_date(test_date)
    db_elapsed = time.time() - start
    print(f"SQLite 加载: {len(data)} 条, 耗时 {db_elapsed:.3f}s")
    loader.close()

    # 性能对比
    print("\n=== 性能对比 ===")
    if csv_elapsed > 0:
        speedup = csv_elapsed / db_elapsed
        print(f"SQLite 性能提升: {speedup:.1f}x")


if __name__ == "__main__":
    print("=" * 60)
    print("数据加载器性能测试")
    print("=" * 60)

    test_db_loader()
    test_csv_loader_comparison()