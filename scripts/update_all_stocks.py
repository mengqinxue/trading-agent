#!/usr/bin/env python
"""股票数据批量更新脚本

用法:
    uv run python scripts/update_all_stocks.py --archive  # 仅归档
    uv run python scripts/update_all_stocks.py --update-limit 10  # 测试更新10只
    uv run python scripts/update_all_stocks.py --update  # 全量更新（耗时很长）
"""

import argparse
import csv
import os
import shutil
import time
from datetime import datetime
from pathlib import Path

import akshare as ak
import pandas as pd
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

console = Console()

DATA_DIR = Path("data/CN_A")
STOCK_DAILY_DIR = DATA_DIR / "stock_daily"
ARCHIVE_DIR = DATA_DIR / "archive"
STOCK_LIST_FILE = DATA_DIR / "stock_list.csv"


def load_stock_list() -> dict:
    """加载股票列表

    Returns:
        {code: {name, market, is_st, is_delisted}}
    """
    stocks = {}

    if STOCK_LIST_FILE.exists():
        with open(STOCK_LIST_FILE, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                code = row["code"]
                stocks[code] = {
                    "name": row["name"],
                    "market": row["market"],
                    "is_st": row["is_st"] == "True",
                    "is_delisted": row["is_delisted"] == "True"
                }

    return stocks


def get_existing_files() -> dict:
    """获取已有 CSV 文件

    Returns:
        {code: {filename, filepath}}
    """
    existing = {}

    if STOCK_DAILY_DIR.exists():
        for f in STOCK_DAILY_DIR.glob("*.csv"):
            parts = f.name.split("_")
            if len(parts) >= 2:
                code = parts[0]
                existing[code] = {
                    "filename": f.name,
                    "filepath": f,
                    "name": parts[1] if len(parts) > 1 else ""
                }

    return existing


def archive_delisted():
    """归档退市/不交易股票"""
    console.print("[bold blue]归档退市/不交易股票...[/]")

    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

    stock_list = load_stock_list()
    existing_files = get_existing_files()

    # 需要归档的股票
    to_archive = []

    # 1. 列表中标记为退市的
    for code, info in stock_list.items():
        if info["is_delisted"]:
            to_archive.append(code)

    # 2. 文件名包含"退"的
    for code, file_info in existing_files.items():
        filename = file_info["filename"]
        if "退" in filename or "退市" in filename:
            if code not in to_archive:
                to_archive.append(code)

    # 3. 已有文件但不在当前列表中的（可能已退市）
    current_codes = set(stock_list.keys())
    for code in existing_files.keys():
        if code not in current_codes:
            # 检查是否是老股票
            filename = existing_files[code]["filename"]
            if "退" not in filename:  # 避免 double-count
                console.print(f"[yellow]不在当前列表: {code} - {filename}[/]")
                # 暂不归档，可能只是列表未包含

    console.print(f"  需要归档: {len(to_archive)} 只股票")

    archived_count = 0
    for code in to_archive:
        if code in existing_files:
            src = existing_files[code]["filepath"]
            dst = ARCHIVE_DIR / src.name

            if not dst.exists():
                shutil.move(str(src), str(dst))
                console.print(f"  归档: {src.name}")
                archived_count += 1
            else:
                console.print(f"  已存在: {dst.name}")

    console.print(f"[green]归档完成: {archived_count} 个文件[/]")
    console.print(f"  archive 目录: {ARCHIVE_DIR}")


def update_stock(code: str, name: str, existing_file: dict = None) -> bool:
    """更新单只股票数据"""
    try:
        # 获取日线数据
        df = ak.stock_zh_a_hist(symbol=code, period="daily", adjust="")

        if df.empty:
            return False

        # 标准化列名
        df = df.rename(columns={
            "日期": "date",
            "开盘": "open",
            "收盘": "close",
            "最高": "high",
            "最低": "low",
            "成交量": "volume",
            "成交额": "amount",
            "振幅": "amplitude",
            "涨跌幅": "change_pct",
            "涨跌额": "change",
            "换手率": "turnover",
        })

        # 确保 date 列是字符串格式
        if "date" in df.columns:
            df["date"] = df["date"].astype(str)

        # 成交量单位转换（手 -> 股数）
        if "volume" in df.columns:
            df["volume"] = df["volume"] * 100

        # 文件名
        if existing_file:
            filename = existing_file["filename"]
        else:
            filename = f"{code}_{name}_Daily_To2026.csv"

        filepath = STOCK_DAILY_DIR / filename

        # 如果文件存在，合并
        if filepath.exists():
            old_df = pd.read_csv(filepath)
            # 确保 old_df 的 date 也是字符串
            if "date" in old_df.columns:
                old_df["date"] = old_df["date"].astype(str)
            df = pd.concat([old_df, df], ignore_index=True)
            df = df.drop_duplicates(subset=["date"], keep="last")
            df = df.sort_values("date")

        STOCK_DAILY_DIR.mkdir(parents=True, exist_ok=True)
        df.to_csv(filepath, index=False, encoding="utf-8")

        return True

    except Exception as e:
        console.print(f"[red]{code} 失败: {str(e)[:50]}[/]")
        return False


def batch_update(limit: int = None):
    """批量更新股票数据"""
    console.print("[bold blue]批量更新股票数据...[/]")

    stock_list = load_stock_list()
    existing_files = get_existing_files()

    # 过滤需要更新的股票
    to_update = []
    for code, info in stock_list.items():
        if info["is_delisted"]:
            continue
        to_update.append((code, info["name"]))

    if limit:
        to_update = to_update[:limit]
        console.print(f"[yellow]测试模式: 更新前 {limit} 只[/]")

    console.print(f"  待更新: {len(to_update)} 只")

    success = 0
    fail = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        console=console
    ) as progress:
        task = progress.add_task("更新...", total=len(to_update))

        for i, (code, name) in enumerate(to_update):
            progress.update(task, description=f"[{i+1}/{len(to_update)}] {code} {name}")

            existing = existing_files.get(code)
            result = update_stock(code, name, existing)

            if result:
                success += 1
            else:
                fail += 1

            progress.advance(task)
            time.sleep(0.3)  # 避免请求过快

    console.print(f"[green]成功: {success}[/] [red]失败: {fail}[/]")


def main():
    parser = argparse.ArgumentParser(description="股票数据管理")
    parser.add_argument("--archive", action="store_true", help="仅归档退市股票")
    parser.add_argument("--update", action="store_true", help="全量更新数据")
    parser.add_argument("--update-limit", type=int, help="测试更新（指定数量）")

    args = parser.parse_args()

    console.print("[bold]A股数据管理[/]")
    console.print("=" * 50)

    if args.archive:
        archive_delisted()

    elif args.update_limit:
        batch_update(limit=args.update_limit)

    elif args.update:
        # 先归档
        archive_delisted()
        # 再更新
        batch_update()

    else:
        # 默认：归档 + 测试更新 10 只
        archive_delisted()
        batch_update(limit=10)

    console.print("[bold green]完成！[/]")


if __name__ == "__main__":
    main()