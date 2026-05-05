# -*- coding: utf-8 -*-
"""涨停板追涨策略 - 回测版"""

import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import numpy as np

from .base import StrategyBase
from .market_trend import MarketTrendStrategy
from .backtest import BacktestEngine

logger = logging.getLogger(__name__)


class LimitUpStrategy(StrategyBase):
    """涨停板追涨策略

    策略逻辑：
    1. 判断市场状态，熊市不参与
    2. 发现涨停板股票，第二天买入
    3. 盈利8%止盈，亏损3%止损

    参数：
    - profit_target: 止盈阈值（默认8%）
    - stop_loss: 止损阈值（默认-3%）
    - max_positions: 最大持仓数（默认5）
    - buy_ratio: 买入资金比例（默认0.1）
    - weekly_buy_limit: 每周买入限制（默认3）
    - min_list_days: 最小上市天数（默认60，排除次新股）
    - limit_up_threshold: 涨停阈值（默认9.9%）
    """

    name = "limit_up_strategy"
    default_params = {
        "profit_target": 8.0,
        "stop_loss": -3.0,
        "max_positions": 5,
        "buy_ratio": 0.1,
        "weekly_buy_limit": 3,
        "min_list_days": 60,
        "limit_up_threshold": 9.9,
    }

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        super().__init__(params)
        self.trend_strategy = MarketTrendStrategy()

        # 本周买入计数
        self.weekly_buy_count = 0
        self.current_week = None

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """执行策略

        Args:
            context: {
                'date': 当前日期,
                'index_df': 上证指数数据,
                'stock_data': 当日所有股票数据（字典 {code: row}）,
                'engine': BacktestEngine实例,
                'stock_list': 股票列表DataFrame,
                'daily_dir': 日线数据目录路径,
            }

        Returns:
            {'buys': [{'code', 'name', 'reason'}], 'sells': [{'code', 'reason'}]}
        """
        date = context["date"]
        engine = context["engine"]
        stock_data = context.get("stock_data", {})
        stock_list = context.get("stock_list")
        index_df = context.get("index_df")

        result = {"buys": [], "sells": []}

        # 1. 检查卖出条件（先检查卖出，腾出资金和持仓位）
        sells = self.check_sell_conditions(engine, stock_data, date)
        result["sells"] = sells

        # 2. 判断市场状态
        market_status = self.get_market_status(index_df, date)
        if market_status == "熊市":
            logger.info(f"[策略] {date} 市场状态为熊市，跳过买入")
            return result

        # 3. 检查买入限制
        if len(engine.positions) >= self.get_param("max_positions"):
            logger.info(f"[策略] {date} 持仓数已达上限 {self.get_param('max_positions')}")
            return result

        # 检查本周买入限制
        self._update_week_counter(date)
        if self.weekly_buy_count >= self.get_param("weekly_buy_limit"):
            logger.info(f"[策略] {date} 本周买入已达上限 {self.get_param('weekly_buy_limit')}")
            return result

        # 4. 找出涨停板股票（当日涨停）
        limit_ups = self.find_limit_up_stocks(stock_data, date, stock_list)

        if not limit_ups:
            logger.debug(f"[策略] {date} 无涨停板股票")
            return result

        # 5. 筛选买入候选（排除已持仓）
        candidates = []
        for item in limit_ups:
            if item["code"] not in engine.positions:
                candidates.append(item)

        if not candidates:
            logger.debug(f"[策略] {date} 涨停板股票均已持仓")
            return result

        # 6. 选择涨幅最大的一只
        best = max(candidates, key=lambda x: x["change_pct"])
        result["buys"] = [{
            "code": best["code"],
            "name": best["name"],
            "reason": f"涨停板追涨，涨幅{best['change_pct']:.2f}%",
            "change_pct": best["change_pct"],
        }]

        return result

    def check_sell_conditions(
        self,
        engine: BacktestEngine,
        stock_data: Dict[str, Any],
        date: str,
    ) -> List[Dict[str, Any]]:
        """检查卖出条件

        Args:
            engine: 回测引擎
            stock_data: 当日股票数据
            date: 当前日期

        Returns:
            需要卖出的股票列表
        """
        sells = []
        profit_target = self.get_param("profit_target")
        stop_loss = self.get_param("stop_loss")

        for code, pos in engine.positions.items():
            # 获取当前价格
            if code not in stock_data:
                logger.warning(f"[策略] {date} 无法获取 {code} 当前价格")
                continue

            row = stock_data[code]
            current_price = float(row.get("close", row.get("close", 0)))

            if current_price <= 0:
                continue

            # 计算盈亏百分比
            profit_pct = (current_price - pos.buy_price) / pos.buy_price * 100

            # 判断卖出条件
            reason = None
            if profit_pct >= profit_target:
                reason = f"止盈（盈利{profit_pct:.2f}% >= {profit_target}%）"
            elif profit_pct <= stop_loss:
                reason = f"止损（亏损{profit_pct:.2f}% <= {stop_loss}%）"

            if reason:
                sells.append({
                    "code": code,
                    "price": current_price,
                    "reason": reason,
                    "profit_pct": profit_pct,
                })

        return sells

    def find_limit_up_stocks(
        self,
        stock_data: Dict[str, Any],
        date: str,
        stock_list: Optional[pd.DataFrame] = None,
    ) -> List[Dict[str, Any]]:
        """找出涨停板股票

        Args:
            stock_data: 当日股票数据 {code: row}
            date: 当前日期
            stock_list: 股票列表（用于过滤ST、次新股）

        Returns:
            涨停板股票列表 [{'code', 'name', 'change_pct', 'close'}]
        """
        threshold = self.get_param("limit_up_threshold")
        min_list_days = self.get_param("min_list_days")
        limit_ups = []

        for code, row in stock_data.items():
            # 获取涨跌幅
            change_pct = float(row.get("change_pct", row.get("pct_chg", 0)))

            # 检查是否涨停（>= 9.9%）
            if change_pct < threshold:
                continue

            # 检查ST状态
            if stock_list is not None:
                stock_info = stock_list[stock_list["code"] == code]
                if not stock_info.empty:
                    is_st = stock_info.iloc[0].get("is_st", False)
                    if is_st:
                        logger.debug(f"[策略] {code} 为ST股，排除")
                        continue

                    # 检查上市天数（次新股过滤）
                    list_date = stock_info.iloc[0].get("list_date", "")
                    if list_date:
                        try:
                            list_dt = datetime.strptime(str(list_date), "%Y-%m-%d")
                            current_dt = datetime.strptime(date, "%Y-%m-%d")
                            list_days = (current_dt - list_dt).days
                            if list_days < min_list_days:
                                logger.debug(
                                    f"[策略] {code} 上市天数{list_days} < {min_list_days}, 排除"
                                )
                                continue
                        except Exception:
                            pass

            # 获取股票名称
            name = row.get("name", stock_list[stock_list["code"] == code].iloc[0].get("name", code) if stock_list is not None and not stock_list[stock_list["code"] == code].empty else code)
            close = float(row.get("close", 0))

            limit_ups.append({
                "code": code,
                "name": name,
                "change_pct": change_pct,
                "close": close,
            })

        logger.info(f"[策略] {date} 发现涨停板股票 {len(limit_ups)} 只")
        return limit_ups

    def get_market_status(
        self,
        index_df: Optional[pd.DataFrame],
        date: str,
    ) -> str:
        """判断市场状态

        Args:
            index_df: 上证指数日线数据
            date: 当前日期

        Returns:
            市场状态：牛市/熊市/震荡市/偏强震荡/偏弱震荡
        """
        if index_df is None or index_df.empty:
            return "震荡市"  # 默认可参与

        # 确保日期格式一致
        if "date" in index_df.columns:
            index_df["date"] = index_df["date"].astype(str)

        # 截取到当前日期的数据
        df = index_df[index_df["date"] <= date].tail(250)

        if len(df) < 60:
            return "震荡市"  # 数据不足，默认可参与

        # 使用 MarketTrendStrategy 判断
        try:
            result = self.trend_strategy.analyze(df)
            status = result.get("status", "震荡市")
            return status
        except Exception as e:
            logger.warning(f"[策略] {date} 市场状态判断失败: {e}")
            return "震荡市"

    def _update_week_counter(self, date: str):
        """更新每周买入计数

        Args:
            date: 当前日期
        """
        try:
            dt = datetime.strptime(date, "%Y-%m-%d")
            week = dt.isocalendar()[1]  # 周数
            year = dt.year

            current_week_key = f"{year}-{week}"

            if self.current_week != current_week_key:
                self.current_week = current_week_key
                self.weekly_buy_count = 0

        except Exception:
            pass

    def increment_weekly_buy(self):
        """增加本周买入计数"""
        self.weekly_buy_count += 1


def load_stock_data_for_date(
    daily_dir: Path,
    date: str,
    stock_list: Optional[pd.DataFrame] = None,
) -> Dict[str, Any]:
    """加载指定日期的所有股票数据

    Args:
        daily_dir: 日线数据目录
        date: 日期
        stock_list: 股票列表（可选，用于过滤）

    Returns:
        {code: row_dict} 字典
    """
    stock_data = {}

    # 遍历所有日线文件
    for file in daily_dir.glob("*.csv"):
        # 提取股票代码
        filename = file.name
        code = filename.split("_")[0]

        # 检查是否在股票列表中
        if stock_list is not None:
            if code not in stock_list["code"].values:
                continue

        try:
            # 读取文件，查找指定日期的数据
            df = pd.read_csv(file)

            # 标准化日期列
            if "date" in df.columns:
                df["date"] = df["date"].astype(str)
            elif "时间" in df.columns:
                df["date"] = df["时间"].astype(str)

            # 查找指定日期
            row = df[df["date"] == date]

            if not row.empty:
                stock_data[code] = row.iloc[0].to_dict()

        except Exception as e:
            logger.debug(f"[数据加载] {file.name} 读取失败: {e}")
            continue

    logger.info(f"[数据加载] {date} 加载 {len(stock_data)} 只股票数据")
    return stock_data


def get_next_day_open_price(
    daily_dir: Path,
    code: str,
    current_date: str,
    stock_data: Dict[str, Any],
) -> Optional[float]:
    """获取第二天开盘价

    Args:
        daily_dir: 日线数据目录
        code: 股票代码
        current_date: 当前日期
        stock_data: 当日股票数据（用于 fallback）

    Returns:
        第二天开盘价，如果无法获取则返回当日收盘价
    """
    # 尝试从 stock_data 中获取下一天数据
    # 由于数据加载是按日期进行的，这里需要单独读取文件

    try:
        file = daily_dir / f"{code}_*.csv"
        files = list(daily_dir.glob(f"{code}_*.csv"))

        if not files:
            return None

        df = pd.read_csv(files[0])

        if "date" in df.columns:
            df["date"] = df["date"].astype(str)

        # 找到当前日期的下一行
        current_idx = df[df["date"] == current_date].index

        if len(current_idx) > 0:
            next_idx = current_idx[0] + 1
            if next_idx < len(df):
                next_row = df.iloc[next_idx]
                open_price = float(next_row.get("open", next_row.get("open", 0)))
                if open_price > 0:
                    return open_price

        # 无法获取第二天开盘价，使用当日收盘价估算
        if code in stock_data:
            return float(stock_data[code].get("close", 0))

    except Exception as e:
        logger.debug(f"[数据加载] {code} 下一天开盘价获取失败: {e}")

    return None