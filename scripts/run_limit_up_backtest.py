# -*- coding: utf-8 -*-
"""
涨停板回测运行脚本

从2000年1月1日开始，初始资金100,000元，
在非熊市时买入涨停板股票，盈利8%止盈，亏损3%止损。

用法：
    uv run python scripts/run_limit_up_backtest.py
"""

import sys
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List

import pandas as pd
import numpy as np

# 设置路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from strategies import (
    BacktestEngine,
    LimitUpStrategy,
    load_stock_data_for_date,
)
from src.data_sources import load_index_daily

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)8s | %(message)s",
)
logger = logging.getLogger(__name__)

# 数据路径
DATA_DIR = Path("data/CN_A")
DAILY_DIR = DATA_DIR / "stock_daily"
STOCK_LIST_FILE = DATA_DIR / "stock_list.csv"
INDEX_FILE = DATA_DIR / "index_daily" / "000001_上证指数_Daily.csv"


def get_trading_days(index_df: pd.DataFrame, start_date: str, end_date: str) -> List[str]:
    """获取交易日列表

    Args:
        index_df: 上证指数数据
        start_date: 开始日期
        end_date: 结束日期

    Returns:
        交易日列表
    """
    if "date" in index_df.columns:
        index_df["date"] = index_df["date"].astype(str)

    df = index_df[
        (index_df["date"] >= start_date) & (index_df["date"] <= end_date)
    ]

    return df["date"].tolist()


def load_stock_data_for_date_fast(
    daily_dir: Path,
    date: str,
    valid_codes: set,
) -> Dict[str, Any]:
    """快速加载指定日期的股票数据（使用预筛选的股票代码）

    Args:
        daily_dir: 日线数据目录
        date: 日期
        valid_codes: 有效股票代码集合

    Returns:
        {code: row_dict} 字典
    """
    stock_data = {}

    # 遍历日线文件（只处理有效代码）
    for file in daily_dir.glob("*.csv"):
        filename = file.name
        code = filename.split("_")[0]

        # 快速过滤：只处理有效代码
        if code not in valid_codes:
            continue

        try:
            # 使用 pandas 读取单行
            df = pd.read_csv(file, nrows=1000)  # 只读取前1000行用于查找

            # 标准化日期列
            date_col = None
            for col in ["date", "时间", "日期"]:
                if col in df.columns:
                    date_col = col
                    break

            if date_col:
                df[date_col] = df[date_col].astype(str)
                row = df[df[date_col] == date]

                if not row.empty:
                    row_dict = row.iloc[0].to_dict()
                    # 标准化 date 字段
                    if date_col != "date":
                        row_dict["date"] = row_dict.get(date_col)
                    stock_data[code] = row_dict

        except Exception:
            continue

    return stock_data


def run_backtest():
    """运行回测"""
    print("=" * 70)
    print("涨停板回测策略")
    print("=" * 70)

    # 回测参数
    start_date = "2020-01-01"  # 先测试最近6年
    end_date = "2026-04-30"
    initial_capital = 100000

    print(f"\n回测参数:")
    print(f"  起始日期: {start_date}")
    print(f"  结束日期: {end_date}")
    print(f"  初始资金: {initial_capital:,} 元")
    print(f"  买入条件: 涨停板（涨幅>=9.9%）")
    print(f"  止盈阈值: 8%")
    print(f"  止损阈值: -3%")
    print(f"  最大持仓: 5只")
    print(f"  每周买入: 最多3只")
    print(f"  资金比例: 每次10%")
    print(f"  排除ST股: 是")
    print(f"  排除次新股: 上市<60天")

    # 1. 加载上证指数数据
    print("\n[1] 加载上证指数数据...")
    index_df = load_index_daily("000001")

    if index_df is None or index_df.empty:
        print("❌ 无法加载上证指数数据")
        return

    print(f"✅ 数据范围: {index_df.iloc[0]['date']} ~ {index_df.iloc[-1]['date']}")

    # 2. 加载股票列表
    print("\n[2] 加载股票列表...")
    stock_list = pd.read_csv(STOCK_LIST_FILE)
    stock_list["code"] = stock_list["code"].astype(str)
    print(f"✅ 股票数量: {len(stock_list)}")

    # 预筛选：2000年前上市的股票（减少遍历数量）
    print("\n[3] 预筛选股票...")
    stock_list["list_date"] = stock_list["list_date"].astype(str)
    valid_stocks = stock_list[
        (stock_list["list_date"] <= start_date) |  # 2000年前上市
        (stock_list["list_date"] == "") |          # 无上市日期
        (stock_list["is_st"] == False)             # 非ST股
    ]
    valid_codes = set(valid_stocks["code"].tolist())
    print(f"✅ 预筛选股票: {len(valid_codes)} 只（减少遍历数量）")

    # 3. 获取交易日列表
    print("\n[4] 获取交易日列表...")
    trading_days = get_trading_days(index_df, start_date, end_date)
    print(f"✅ 交易日数量: {len(trading_days)}")

    # 4. 创建回测引擎和策略
    print("\n[5] 初始化回测引擎...")
    engine = BacktestEngine(initial_capital=initial_capital)
    strategy = LimitUpStrategy()
    print(f"✅ 初始资金: {engine.cash:,.2f} 元")

    # 5. 运行回测
    print("\n[6] 开始回测...")
    print("-" * 70)

    total_days = len(trading_days)
    progress_interval = max(total_days // 20, 1)  # 每5%打印进度

    for i, date in enumerate(trading_days):
        # 打印进度
        if i % progress_interval == 0:
            pct = i / total_days * 100
            equity = engine.get_equity()
            positions = len(engine.positions)
            trades = engine.total_trades
            print(
                f"进度: {pct:.0f}% ({i}/{total_days}) | "
                f"日期: {date} | "
                f"净值: {equity:,.0f} | "
                f"持仓: {positions} | "
                f"交易: {trades}"
            )

        # 快速加载当日股票数据
        stock_data = load_stock_data_for_date_fast(DAILY_DIR, date, valid_codes)

        # 执行策略
        context = {
            "date": date,
            "index_df": index_df,
            "stock_data": stock_data,
            "engine": engine,
            "stock_list": stock_list,
            "daily_dir": DAILY_DIR,
        }

        result = strategy.run(context)

        # 执行卖出
        for sell in result["sells"]:
            engine.sell(
                code=sell["code"],
                price=sell["price"],
                date=date,
                reason=sell["reason"],
            )

        # 执行买入（第二天开盘价）
        for buy in result["buys"]:
            # 获取第二天开盘价（涨停板第二天买入）
            buy_price = None

            # 尝试获取第二天数据
            next_day_idx = i + 1
            if next_day_idx < len(trading_days):
                next_day = trading_days[next_day_idx]
                next_stock_data = load_stock_data_for_date_fast(DAILY_DIR, next_day, valid_codes)

                if buy["code"] in next_stock_data:
                    next_row = next_stock_data[buy["code"]]
                    buy_price = float(next_row.get("open", next_row.get("open", 0)))

            if buy_price is None or buy_price <= 0:
                # 无法获取第二天开盘价，使用当日收盘价
                if buy["code"] in stock_data:
                    buy_price = float(stock_data[buy["code"]].get("close", 0))
                else:
                    continue

            # 计算买入金额
            buy_amount = engine.cash * strategy.get_param("buy_ratio")

            # 执行买入
            success = engine.buy(
                code=buy["code"],
                name=buy["name"],
                price=buy_price,
                date=trading_days[next_day_idx] if next_day_idx < len(trading_days) else date,
                amount=buy_amount,
                reason=buy["reason"],
            )

            if success:
                strategy.increment_weekly_buy()

        # 记录净值
        current_prices = {}
        for code in engine.positions.keys():
            if code in stock_data:
                current_prices[code] = float(stock_data[code].get("close", 0))

        engine.record_equity(date, current_prices)

    # 6. 输出结果
    print("\n" + "-" * 70)
    print("[6] 回测完成")

    engine.print_summary()

    # 7. 导出数据
    output_dir = DATA_DIR / "backtest"
    output_dir.mkdir(exist_ok=True)

    trades_file = output_dir / "limit_up_trades.csv"
    equity_file = output_dir / "limit_up_equity.csv"

    engine.export_trades(str(trades_file))
    engine.export_equity_curve(str(equity_file))

    print(f"\n交易记录: {trades_file}")
    print(f"净值曲线: {equity_file}")


def main():
    """主函数"""
    try:
        run_backtest()
    except KeyboardInterrupt:
        print("\n用户中断回测")
    except Exception as e:
        logger.error(f"回测失败: {e}")
        raise


if __name__ == "__main__":
    main()