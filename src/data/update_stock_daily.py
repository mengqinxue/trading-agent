"""A股日线数据更新脚本

功能：
1. 遍历 data/CN_A/stock_daily 目录下的所有 CSV 文件
2. 解析文件名获取股票代码
3. 使用 akshare 获取最新数据（从文件最后日期到今天）
4. 追加新数据到现有文件
"""

import os
import csv
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

import akshare as ak


DATA_DIR = Path("data/CN_A/stock_daily")
DEFAULT_START_DATE = "20260418"  # 默认从 4-18 开始更新


def parse_filename(filename: str) -> tuple[str, str]:
    """解析文件名获取股票代码和名称

    格式：代码_名称_Daily_To2026.csv
    例如：600036_招商银行_Daily_To2026.csv

    Returns:
        (股票代码, 股票名称)
    """
    basename = filename.replace(".csv", "")
    parts = basename.split("_")
    if len(parts) >= 2:
        code = parts[0]
        name = parts[1]
        return code, name
    return "", ""


def get_last_date_from_file(filepath: Path) -> Optional[str]:
    """从 CSV 文件获取最后一条数据的日期

    Returns:
        日期字符串，格式：YYYY-MM-DD
    """
    try:
        with open(filepath, 'r', encoding='utf-8-sig') as f:
            lines = f.readlines()
            if len(lines) < 2:
                return None

            # 最后一行数据
            last_line = lines[-1].strip()
            if not last_line:
                last_line = lines[-2].strip()

            # 解析 CSV 行
            parts = last_line.split(',')
            if len(parts) >= 3:
                # 时间列（第3列），去掉空格前缀
                date_str = parts[2].strip()
                return date_str

    except Exception as e:
        print(f"读取文件失败 {filepath}: {e}")

    return None


def fetch_new_data(code: str, start_date: str, end_date: str) -> list[dict]:
    """使用 akshare 获取新数据

    Args:
        code: 股票代码（如 600036）
        start_date: 开始日期 YYYYMMDD
        end_date: 结束日期 YYYYMMDD

    Returns:
        数据列表
    """
    try:
        # akshare 接口
        df = ak.stock_zh_a_hist(
            symbol=code,
            period="daily",
            start_date=start_date,
            end_date=end_date,
            adjust="qfq"  # 前复权
        )

        if df.empty:
            return []

        # 转换为列表
        data_list = []
        for _, row in df.iterrows():
            # 成交量单位转换：akshare 返回的是手，转换为股数（乘100）
            volume = float(row["成交量"]) * 100
            data_list.append({
                "code": code,
                "name": "",  # 名称需要从文件获取
                "date": row["日期"],
                "open": row["开盘"],
                "close": row["收盘"],
                "high": row["最高"],
                "low": row["最低"],
                "volume": volume,  # 股数
                "money": row["成交额"]  # 元
            })

        return data_list

    except Exception as e:
        print(f"获取数据失败 {code}: {e}")
        return []


def append_data_to_file(filepath: Path, data_list: list[dict], stock_name: str):
    """追加新数据到 CSV 文件

    Args:
        filepath: 文件路径
        data_list: 新数据列表
        stock_name: 股票名称
    """
    if not data_list:
        return

    try:
        with open(filepath, 'a', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)

            for item in data_list:
                # 格式与原文件一致
                row = [
                    item["code"],
                    stock_name,
                    f" {item['date']}",  # 时间有空格前缀
                    item["open"],
                    item["close"],
                    item["high"],
                    item["low"],
                    float(item["volume"]),
                    round(float(item["money"]), 2)  # 成交额保留两位小数
                ]
                writer.writerow(row)

        print(f"追加 {len(data_list)} 条数据到 {filepath.name}")

    except Exception as e:
        print(f"写入文件失败 {filepath}: {e}")


def update_single_stock(filepath: Path, end_date: str) -> bool:
    """更新单个股票数据

    Args:
        filepath: CSV 文件路径
        end_date: 结束日期 YYYYMMDD

    Returns:
        是否成功更新
    """
    filename = filepath.name
    code, name = parse_filename(filename)

    if not code:
        print(f"无法解析文件名: {filename}")
        return False

    # 获取文件最后日期
    last_date_str = get_last_date_from_file(filepath)

    if last_date_str:
        # 从最后日期的下一天开始
        last_date = datetime.strptime(last_date_str, "%Y-%m-%d")
        start_date = (last_date + timedelta(days=1)).strftime("%Y%m%d")
    else:
        # 使用默认开始日期
        start_date = DEFAULT_START_DATE

    # 如果开始日期 >= 结束日期，无需更新
    if start_date >= end_date:
        print(f"无需更新: {filename} (最后日期: {last_date_str})")
        return False

    print(f"更新 {code} {name}: {start_date} -> {end_date}")

    # 获取新数据
    new_data = fetch_new_data(code, start_date, end_date)

    if new_data:
        append_data_to_file(filepath, new_data, name)
        return True

    return False


def update_all_stocks(end_date: Optional[str] = None, batch_size: int = 50, delay: float = 0.5):
    """更新所有股票数据

    Args:
        end_date: 结束日期 YYYYMMDD，默认今天
        batch_size: 每批次处理数量
        delay: 每批次间隔秒数（避免请求过快）
    """
    if not end_date:
        end_date = datetime.now().strftime("%Y%m%d")

    print(f"开始更新A股日线数据到 {end_date}")
    print(f"数据目录: {DATA_DIR}")

    # 获取所有 CSV 文件
    csv_files = list(DATA_DIR.glob("*.csv"))
    total = len(csv_files)

    print(f"共 {total} 个股票文件")

    success_count = 0
    skip_count = 0
    fail_count = 0

    # 分批处理
    for i, filepath in enumerate(csv_files):
        try:
            result = update_single_stock(filepath, end_date)
            if result:
                success_count += 1
            else:
                skip_count += 1

        except Exception as e:
            print(f"处理失败 {filepath.name}: {e}")
            fail_count += 1

        # 每批次暂停
        if (i + 1) % batch_size == 0:
            print(f"进度: {i + 1}/{total} (成功: {success_count}, 跳过: {skip_count}, 失败: {fail_count})")
            time.sleep(delay)

    print("\n更新完成!")
    print(f"总计: {total}")
    print(f"成功: {success_count}")
    print(f"跳过: {skip_count}")
    print(f"失败: {fail_count}")


def update_specific_stocks(codes: list[str], end_date: Optional[str] = None):
    """更新指定股票数据

    Args:
        codes: 股票代码列表
        end_date: 结束日期 YYYYMMDD
    """
    if not end_date:
        end_date = datetime.now().strftime("%Y%m%d")

    print(f"更新指定股票: {codes}")

    for code in codes:
        # 查找对应文件
        pattern = f"{code}_*_Daily_To2026.csv"
        matches = list(DATA_DIR.glob(pattern))

        if not matches:
            print(f"未找到股票 {code} 的文件")
            continue

        filepath = matches[0]
        update_single_stock(filepath, end_date)


def cli_main():
    """CLI 入口"""
    import argparse

    parser = argparse.ArgumentParser(description="A股日线数据更新工具")
    parser.add_argument("--all", action="store_true", help="更新所有股票")
    parser.add_argument("--codes", nargs="+", help="指定股票代码（如 600036 000001）")
    parser.add_argument("--end-date", help="结束日期 YYYYMMDD（默认今天）")
    parser.add_argument("--batch-size", type=int, default=50, help="每批次数量")
    parser.add_argument("--delay", type=float, default=0.5, help="批次间隔秒数")

    args = parser.parse_args()

    if args.all:
        update_all_stocks(
            end_date=args.end_date,
            batch_size=args.batch_size,
            delay=args.delay
        )
    elif args.codes:
        update_specific_stocks(args.codes, args.end_date)
    else:
        parser.print_help()


if __name__ == "__main__":
    cli_main()