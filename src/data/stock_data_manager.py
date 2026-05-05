"""股票数据管理脚本

功能：
1. 下载所有 A 股列表，保存为 stock_list.csv
2. 批量更新所有股票日线数据（使用多数据源）
3. 归档已退市/不交易股票到 archive 目录
"""

import csv
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

# 多数据源管理器
from src.data.providers import DataFetcherManager

console = Console()

# 数据目录
DATA_DIR = Path(__file__).parent.parent.parent.parent / "data" / "CN_A"
STOCK_DAILY_DIR = DATA_DIR / "stock_daily"
ARCHIVE_DIR = DATA_DIR / "archive"
STOCK_LIST_FILE = DATA_DIR / "stock_list.csv"

# 全局数据管理器
_data_manager: Optional[DataFetcherManager] = None


def get_data_manager() -> DataFetcherManager:
    """获取数据管理器单例"""
    global _data_manager
    if _data_manager is None:
        _data_manager = DataFetcherManager()
    return _data_manager


def download_stock_list() -> pd.DataFrame:
    """下载所有 A 股列表

    Returns:
        DataFrame with columns: code, name, market, industry, list_date, status
    """
    import akshare as ak  # 股票列表下载仍使用 akshare

    console.print("[bold blue]下载 A 股列表...[/]")

    # 使用东财全市场实时行情接口（最快最全）
    console.print("  使用东财实时行情接口...")
    df = ak.stock_zh_a_spot_em()

    df = df.rename(columns={
        "代码": "code",
        "名称": "name"
    })

    # 根据代码判断市场
    df["market"] = df["code"].apply(lambda x:
        "SH" if x.startswith("6") else
        "SZ" if x.startswith("0") or x.startswith("3") else
        "BJ" if x.startswith("4") or x.startswith("8") else
        "UNKNOWN"
    )

    df["industry"] = ""
    df["list_date"] = ""
    df["status"] = "正常"

    console.print(f"  SH: {len(df[df['market']=='SH'])} 只")
    console.print(f"  SZ: {len(df[df['market']=='SZ'])} 只")
    console.print(f"  BJ: {len(df[df['market']=='BJ'])} 只")

    # 确保必要列存在
    for col in ["code", "name", "market", "industry", "list_date", "status"]:
        if col not in df.columns:
            df[col] = ""

    # 清理数据
    df["code"] = df["code"].astype(str).str.strip()
    df["name"] = df["name"].astype(str).str.strip()

    # 过滤无效代码（必须是6位数字）
    df = df[df["code"].str.match(r"^\d{6}$")]

    # 添加状态标记（ST、退市等）
    df["is_st"] = df["name"].str.contains("ST", case=False, na=False)
    df["is_delisted"] = df["name"].str.contains("退", case=False, na=False)

    console.print(f"[green]总计: {len(df)} 只股票[/]")

    return df


def save_stock_list(df: pd.DataFrame) -> Path:
    """保存股票列表为 CSV

    Args:
        df: 股票列表 DataFrame

    Returns:
        CSV 文件路径
    """
    STOCK_LIST_FILE.parent.mkdir(parents=True, exist_ok=True)

    # 选择输出列
    output_cols = ["code", "name", "market", "industry", "list_date", "is_st", "is_delisted"]
    output_df = df[[col for col in output_cols if col in df.columns]]

    output_df.to_csv(STOCK_LIST_FILE, index=False, encoding="utf-8")
    console.print(f"[green]保存到: {STOCK_LIST_FILE}[/]")

    return STOCK_LIST_FILE


def load_stock_list() -> pd.DataFrame:
    """加载股票列表

    Returns:
        DataFrame
    """
    if STOCK_LIST_FILE.exists():
        return pd.read_csv(STOCK_LIST_FILE, dtype={"code": str})
    else:
        return download_stock_list()


def get_existing_files() -> dict:
    """获取已有的 CSV 文件

    Returns:
        {code: filename} dict
    """
    existing = {}

    if STOCK_DAILY_DIR.exists():
        for f in STOCK_DAILY_DIR.glob("*.csv"):
            # 解析文件名：000001_平安银行_Daily_To2026.csv
            parts = f.name.split("_")
            if len(parts) >= 2:
                code = parts[0]
                existing[code] = f.name

    return existing


def identify_archived_stocks(stock_list: pd.DataFrame, existing_files: dict) -> list:
    """识别需要归档的股票

    条件：
    1. 股票名称包含"退"
    2. 在现有文件中但不在最新列表中
    3. ST 股票（可选）

    Returns:
        需要归档的股票代码列表
    """
    to_archive = []

    # 1. 名称包含"退"的股票
    delisted = stock_list[stock_list["is_delisted"]]["code"].tolist()
    to_archive.extend(delisted)

    # 2. 在现有文件中但不在最新列表中
    current_codes = set(stock_list["code"].tolist())
    for code in existing_files.keys():
        if code not in current_codes:
            # 检查文件名是否包含"退"
            filename = existing_files[code]
            if "退" in filename or "退市" in filename:
                to_archive.append(code)

    console.print(f"[yellow]需要归档: {len(to_archive)} 只[/]")

    return to_archive


def archive_stocks(codes: list) -> int:
    """归档股票数据

    Args:
        codes: 需要归档的股票代码列表

    Returns:
        归档数量
    """
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

    archived_count = 0

    for code in codes:
        # 查找匹配的文件
        pattern = f"{code}_*_Daily_*.csv"
        matches = list(STOCK_DAILY_DIR.glob(pattern))

        for src_file in matches:
            dst_file = ARCHIVE_DIR / src_file.name
            shutil.move(str(src_file), str(dst_file))
            console.print(f"  归档: {src_file.name}")
            archived_count += 1

    console.print(f"[green]归档完成: {archived_count} 个文件[/]")

    return archived_count


def update_stock_daily(code: str, name: str, existing_file: Optional[str] = None) -> bool:
    """更新单只股票日线数据（使用多数据源）

    Args:
        code: 股票代码
        name: 股票名称
        existing_file: 已有文件名（如果有）

    Returns:
        是否成功
    """
    try:
        # 使用多数据源管理器获取日线数据
        manager = get_data_manager()
        df, source = manager.get_daily_data(code, days=365)

        if df is None or df.empty:
            return False

        # 确保 date 列为字符串格式（便于合并）
        if "date" in df.columns:
            df["date"] = df["date"].astype(str)

        # 生成文件名
        if existing_file:
            filename = existing_file
        else:
            filename = f"{code}_{name}_Daily_To2026.csv"

        filepath = STOCK_DAILY_DIR / filename

        # 如果文件存在，合并数据
        if filepath.exists():
            old_df = pd.read_csv(filepath)
            # 确保 old_df 的 date 列也是字符串
            if "date" in old_df.columns:
                old_df["date"] = old_df["date"].astype(str)
            df = pd.concat([old_df, df], ignore_index=True)
            df = df.drop_duplicates(subset=["date"], keep="last")
            df = df.sort_values("date")

        # 保存
        STOCK_DAILY_DIR.mkdir(parents=True, exist_ok=True)
        df.to_csv(filepath, index=False, encoding="utf-8")

        console.print(f"[green]{code} 更新成功 (来源: {source})[/]")
        return True

    except Exception as e:
        console.print(f"[red]更新 {code} 失败: {e}[/]")
        return False


def batch_update_all_stocks(max_workers: int = 1, limit: Optional[int] = None):
    """批量更新所有股票数据

    Args:
        max_workers: 并发数（建议 1，避免被限流）
        limit: 限制更新数量（用于测试）
    """
    # 加载股票列表
    stock_list = load_stock_list()

    if limit:
        stock_list = stock_list.head(limit)
        console.print(f"[yellow]测试模式: 仅更新前 {limit} 只[/]")

    # 获取已有文件
    existing_files = get_existing_files()

    console.print(f"[bold blue]开始批量更新 {len(stock_list)} 只股票...[/]")

    success_count = 0
    fail_count = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console
    ) as progress:
        task = progress.add_task("更新股票数据...", total=len(stock_list))

        for idx, row in stock_list.iterrows():
            code = row["code"]
            name = row["name"]
            existing_file = existing_files.get(code)

            progress.update(task, description=f"[{idx+1}/{len(stock_list)}] {code} {name}")

            # 跳过退市股票
            if row.get("is_delisted", False):
                progress.advance(task)
                continue

            success = update_stock_daily(code, name, existing_file)

            if success:
                success_count += 1
            else:
                fail_count += 1

            progress.advance(task)

            # 避免请求过快
            import time
            time.sleep(0.5)

    console.print(f"[green]成功: {success_count}[/] [red]失败: {fail_count}[/]")


def main():
    """主函数"""
    console.print("[bold]A股数据管理[/]")
    console.print("=" * 50)

    # 1. 下载股票列表
    console.print("\n[bold]Step 1: 下载股票列表[/]")
    stock_list = download_stock_list()
    save_stock_list(stock_list)

    # 2. 归档不交易股票
    console.print("\n[bold]Step 2: 归档不交易股票[/]")
    existing_files = get_existing_files()
    to_archive = identify_archived_stocks(stock_list, existing_files)
    archive_stocks(to_archive)

    # 3. 批量更新数据
    console.print("\n[bold]Step 3: 批量更新数据[/]")
    batch_update_all_stocks()

    console.print("\n[bold green]完成！[/]")


if __name__ == "__main__":
    main()