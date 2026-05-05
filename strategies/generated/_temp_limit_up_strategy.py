# -*- coding: utf-8 -*-
"""涨停板追涨策略 - 由策略生成器生成"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from strategies.base import StrategyBase
from strategies.market_trend import MarketTrendStrategy
from strategies.backtest import BacktestEngine

logger = logging.getLogger(__name__)


class LimitUpStrategy(StrategyBase):
    """涨停板追涨策略

    策略逻辑：
    1. 判断市场状态，熊市不参与
    2. 发现涨停板股票，第二天买入
    3. 盈利10.0%止盈，亏损-5.0%止损
    """

    name = "limit_up_strategy"
    default_params = {
        "profit_target": 10.0,
        "stop_loss": -5.0,
        "max_positions": 5,
        "buy_ratio": 0.1,
        "weekly_buy_limit": 3,
        "min_list_days": 60,
        "limit_up_threshold": 9.9,
    }

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        super().__init__(params)
        self.trend_strategy = MarketTrendStrategy()
        self.weekly_buy_count = 0
        self.current_week = None

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """执行策略"""
        date = context["date"]
        engine = context["engine"]
        stock_data = context.get("stock_data", {})
        stock_list = context.get("stock_list")
        index_df = context.get("index_df")

        result = {"buys": [], "sells": []}

        # 1. 检查卖出条件
        sells = self.check_sell_conditions(engine, stock_data, date)
        result["sells"] = sells

        # 2. 判断市场状态
        if "非熊市" == "非熊市":
            market_status = self.get_market_status(index_df, date)
            if market_status == "熊市":
                logger.info(f"[策略] {date} 市场状态为熊市，跳过买入")
                return result

        # 3. 检查买入限制
        if len(engine.positions) >= self.get_param("max_positions"):
            return result

        self._update_week_counter(date)
        if self.weekly_buy_count >= self.get_param("weekly_buy_limit"):
            return result

        # 4. 找出涨停板股票
        limit_ups = self.find_limit_up_stocks(stock_data, date, stock_list)

        if not limit_ups:
            return result

        # 5. 选择涨幅最大的1只
        candidates = [x for x in limit_ups if x["code"] not in engine.positions]
        if not candidates:
            return result

        best = max(candidates, key=lambda x: x["change_pct"])
        result["buys"] = [{
            "code": best["code"],
            "name": best["name"],
            "reason": f"涨停板追涨，涨幅{best['change_pct']:.2f}%",
        }]

        return result

    def check_sell_conditions(self, engine, stock_data, date) -> List[Dict]:
        """检查卖出条件"""
        sells = []
        profit_target = self.get_param("profit_target")
        stop_loss = self.get_param("stop_loss")

        for code, pos in engine.positions.items():
            if code not in stock_data:
                continue

            current_price = float(stock_data[code].get("close", 0))
            if current_price <= 0:
                continue

            profit_pct = (current_price - pos.buy_price) / pos.buy_price * 100

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
                })

        return sells

    def find_limit_up_stocks(self, stock_data, date, stock_list) -> List[Dict]:
        """找出涨停板股票"""
        threshold = self.get_param("limit_up_threshold")
        min_list_days = self.get_param("min_list_days")
        limit_ups = []

        for code, row in stock_data.items():
            change_pct = float(row.get("change_pct", row.get("pct_chg", 0)))
            if change_pct < threshold:
                continue

            # ST过滤
            if stock_list is not None:
                stock_info = stock_list[stock_list["code"] == code]
                if not stock_info.empty:
                    if stock_info.iloc[0].get("is_st", False):
                        continue

                    # 次新股过滤
                    list_date = stock_info.iloc[0].get("list_date", "")
                    if list_date:
                        try:
                            list_dt = datetime.strptime(str(list_date), "%Y-%m-%d")
                            current_dt = datetime.strptime(date, "%Y-%m-%d")
                            list_days = (current_dt - list_dt).days
                            if list_days < min_list_days:
                                continue
                        except:
                            pass

            name = row.get("name", code)
            close = float(row.get("close", 0))

            limit_ups.append({
                "code": code,
                "name": name,
                "change_pct": change_pct,
                "close": close,
            })

        return limit_ups

    def get_market_status(self, index_df, date) -> str:
        """判断市场状态"""
        if index_df is None or index_df.empty:
            return "震荡市"

        if "date" in index_df.columns:
            index_df["date"] = index_df["date"].astype(str)

        df = index_df[index_df["date"] <= date].tail(250)
        if len(df) < 60:
            return "震荡市"

        try:
            result = self.trend_strategy.analyze(df)
            return result.get("status", "震荡市")
        except:
            return "震荡市"

    def _update_week_counter(self, date):
        """更新每周买入计数"""
        try:
            dt = datetime.strptime(date, "%Y-%m-%d")
            week = dt.isocalendar()[1]
            year = dt.year
            current_week_key = f"{year}-{week}"

            if self.current_week != current_week_key:
                self.current_week = current_week_key
                self.weekly_buy_count = 0
        except:
            pass

    def increment_weekly_buy(self):
        """增加本周买入计数"""
        self.weekly_buy_count += 1
