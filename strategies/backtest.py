# -*- coding: utf-8 -*-
"""回测引擎 - 模拟交易执行和收益计算"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class Position:
    """持仓记录"""

    def __init__(
        self,
        code: str,
        name: str,
        shares: int,
        buy_price: float,
        buy_date: str,
        buy_amount: float,
    ):
        self.code = code
        self.name = name
        self.shares = shares
        self.buy_price = buy_price
        self.buy_date = buy_date
        self.buy_amount = buy_amount  # 买入金额（不含手续费）
        self.sell_price: Optional[float] = None
        self.sell_date: Optional[str] = None
        self.sell_amount: Optional[float] = None
        self.profit_pct: Optional[float] = None
        self.profit_amount: Optional[float] = None
        self.hold_days: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "name": self.name,
            "shares": self.shares,
            "buy_price": self.buy_price,
            "buy_date": self.buy_date,
            "buy_amount": self.buy_amount,
            "sell_price": self.sell_price,
            "sell_date": self.sell_date,
            "sell_amount": self.sell_amount,
            "profit_pct": self.profit_pct,
            "profit_amount": self.profit_amount,
            "hold_days": self.hold_days,
        }


class Trade:
    """交易记录"""

    def __init__(
        self,
        trade_type: str,  # 'buy' or 'sell'
        code: str,
        name: str,
        price: float,
        shares: int,
        amount: float,
        date: str,
        reason: str = "",
    ):
        self.trade_type = trade_type
        self.code = code
        self.name = name
        self.price = price
        self.shares = shares
        self.amount = amount
        self.date = date
        self.reason = reason

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trade_type": self.trade_type,
            "code": self.code,
            "name": self.name,
            "price": self.price,
            "shares": self.shares,
            "amount": self.amount,
            "date": self.date,
            "reason": self.reason,
        }


class BacktestEngine:
    """回测引擎

    功能：
    - 模拟交易账户（资金、持仓）
    - 按日期遍历执行策略
    - 记录交易日志
    - 计算收益统计

    参数：
    - initial_capital: 初始资金（默认100000）
    - commission_rate: 手续费率（默认0.0003，即万三）
    - stamp_duty: 印花税（默认0.001，即千一，仅卖出时收取）
    - slippage_pct: 滑点百分比（默认0.01，即1%）
    """

    def __init__(
        self,
        initial_capital: float = 100000,
        commission_rate: float = 0.0003,
        stamp_duty: float = 0.001,
        slippage_pct: float = 0.01,
    ):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.commission_rate = commission_rate
        self.stamp_duty = stamp_duty
        self.slippage_pct = slippage_pct

        # 持仓字典 {code: Position}
        self.positions: Dict[str, Position] = {}

        # 交易记录列表
        self.trades: List[Trade] = []

        # 每日净值曲线
        self.equity_curve: List[Dict[str, Any]] = []

        # 统计信息
        self.total_trades = 0
        self.win_trades = 0
        self.loss_trades = 0

    def get_equity(self, current_prices: Dict[str, float] = None) -> float:
        """计算总资产

        Args:
            current_prices: 各股票当前价格字典

        Returns:
            总资产 = 现金 + 持仓市值
        """
        equity = self.cash

        for code, pos in self.positions.items():
            if current_prices and code in current_prices:
                price = current_prices[code]
            else:
                price = pos.buy_price  # 无法获取当前价，使用买入价

            equity += pos.shares * price

        return equity

    def buy(
        self,
        code: str,
        name: str,
        price: float,
        date: str,
        amount: float,
        reason: str = "",
    ) -> bool:
        """买入股票

        Args:
            code: 股票代码
            name: 股票名称
            price: 买入价格（开盘价）
            date: 买入日期
            amount: 买入金额
            reason: 买入原因

        Returns:
            是否成功买入
        """
        # 检查资金是否足够
        # 加上滑点后的实际买入价
        actual_price = price * (1 + self.slippage_pct)

        # 计算手续费
        commission = amount * self.commission_rate
        if commission < 5:
            commission = 5  # 最低5元手续费

        # 总花费
        total_cost = amount + commission

        if total_cost > self.cash:
            logger.warning(f"[回测] {date} 买入 {code} 资金不足: 需要{total_cost:.2f}, 可用{self.cash:.2f}")
            return False

        # 计算买入股数（100股一手）
        shares = int(amount / actual_price / 100) * 100
        if shares < 100:
            logger.warning(f"[回测] {date} 买入 {code} 金额不足一手")
            return False

        # 实际买入金额
        actual_amount = shares * actual_price

        # 执行买入
        self.cash -= actual_amount + commission

        pos = Position(
            code=code,
            name=name,
            shares=shares,
            buy_price=actual_price,
            buy_date=date,
            buy_amount=actual_amount,
        )
        self.positions[code] = pos

        # 记录交易
        trade = Trade(
            trade_type="buy",
            code=code,
            name=name,
            price=actual_price,
            shares=shares,
            amount=actual_amount,
            date=date,
            reason=reason,
        )
        self.trades.append(trade)
        self.total_trades += 1

        logger.info(
            f"[回测] {date} 买入 {code} {name}: "
            f"价格{actual_price:.2f}, 股数{shares}, 金额{actual_amount:.2f}, 手续费{commission:.2f}"
        )

        return True

    def sell(
        self,
        code: str,
        price: float,
        date: str,
        reason: str = "",
    ) -> bool:
        """卖出股票

        Args:
            code: 股票代码
            price: 卖出价格
            date: 卖出日期
            reason: 卖出原因（止盈/止损）

        Returns:
            是否成功卖出
        """
        if code not in self.positions:
            logger.warning(f"[回测] {date} 卖出 {code} 无持仓")
            return False

        pos = self.positions[code]

        # 加上滑点后的实际卖出价（滑点使卖出价更低）
        actual_price = price * (1 - self.slippage_pct)

        # 计算卖出金额
        sell_amount = pos.shares * actual_price

        # 计算手续费和印花税
        commission = sell_amount * self.commission_rate
        if commission < 5:
            commission = 5

        stamp_duty = sell_amount * self.stamp_duty

        # 实际收入
        actual_income = sell_amount - commission - stamp_duty

        # 执行卖出
        self.cash += actual_income

        # 更新持仓记录
        pos.sell_price = actual_price
        pos.sell_date = date
        pos.sell_amount = actual_income
        pos.profit_amount = actual_income - pos.buy_amount
        pos.profit_pct = pos.profit_amount / pos.buy_amount * 100

        # 计算持仓天数
        try:
            buy_dt = datetime.strptime(pos.buy_date, "%Y-%m-%d")
            sell_dt = datetime.strptime(date, "%Y-%m-%d")
            pos.hold_days = (sell_dt - buy_dt).days
        except Exception:
            pos.hold_days = 0

        # 统计胜率
        if pos.profit_amount > 0:
            self.win_trades += 1
        else:
            self.loss_trades += 1

        # 记录交易
        trade = Trade(
            trade_type="sell",
            code=code,
            name=pos.name,
            price=actual_price,
            shares=pos.shares,
            amount=actual_income,
            date=date,
            reason=f"{reason}, 盈亏{pos.profit_pct:.2f}%",
        )
        self.trades.append(trade)

        logger.info(
            f"[回测] {date} 卖出 {code} {pos.name}: "
            f"价格{actual_price:.2f}, 股数{pos.shares}, 收入{actual_income:.2f}, "
            f"盈亏{pos.profit_pct:.2f}% ({pos.profit_amount:.2f}), 原因:{reason}"
        )

        # 删除持仓
        del self.positions[code]

        return True

    def record_equity(self, date: str, current_prices: Dict[str, float] = None):
        """记录当日净值

        Args:
            date: 日期
            current_prices: 各股票当前价格
        """
        equity = self.get_equity(current_prices)
        self.equity_curve.append({
            "date": date,
            "equity": equity,
            "cash": self.cash,
            "positions": len(self.positions),
        })

    def get_summary(self) -> Dict[str, Any]:
        """获取回测统计摘要

        Returns:
            统计摘要字典
        """
        if not self.equity_curve:
            return {}

        # 基本统计
        initial = self.initial_capital
        final = self.equity_curve[-1]["equity"]
        total_return = (final - initial) / initial * 100

        # 计算年化收益
        start_date = self.equity_curve[0]["date"]
        end_date = self.equity_curve[-1]["date"]
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            years = (end_dt - start_dt).days / 365
            annual_return = total_return / years if years > 0 else 0
        except Exception:
            annual_return = 0

        # 计算最大回撤
        equities = [e["equity"] for e in self.equity_curve]
        peak = equities[0]
        max_drawdown = 0
        for e in equities:
            if e > peak:
                peak = e
            drawdown = (peak - e) / peak * 100
            if drawdown > max_drawdown:
                max_drawdown = drawdown

        # 计算夏普比率（简化版，假设无风险利率为3%）
        returns = []
        for i in range(1, len(equities)):
            r = (equities[i] - equities[i - 1]) / equities[i - 1] * 100
            returns.append(r)

        if returns:
            avg_return = np.mean(returns)
            std_return = np.std(returns)
            sharpe = (avg_return - 3 / 252 * 100) / std_return if std_return > 0 else 0
        else:
            sharpe = 0

        # 交易统计
        win_rate = self.win_trades / self.total_trades * 100 if self.total_trades > 0 else 0

        # 计算平均盈亏
        profit_trades = [t for t in self.trades if t.trade_type == "sell"]
        avg_profit = 0
        avg_loss = 0
        profit_ratio = 0

        if profit_trades:
            profits = []
            losses = []
            for t in profit_trades:
                # 从reason中提取盈亏百分比
                reason = t.reason
                if "盈亏" in reason:
                    try:
                        pct_str = reason.split("盈亏")[1].split("%")[0]
                        pct = float(pct_str)
                        if pct > 0:
                            profits.append(pct)
                        else:
                            losses.append(abs(pct))
                    except Exception:
                        pass

            if profits:
                avg_profit = np.mean(profits)
            if losses:
                avg_loss = np.mean(losses)
            if avg_loss > 0:
                profit_ratio = avg_profit / avg_loss

        # 持仓天数统计
        hold_days_list = []
        for t in profit_trades:
            # 从完整交易记录中获取持仓天数
            pass

        return {
            "initial_capital": initial,
            "final_equity": final,
            "total_return": total_return,
            "annual_return": annual_return,
            "max_drawdown": max_drawdown,
            "sharpe_ratio": sharpe,
            "total_trades": self.total_trades,
            "win_trades": self.win_trades,
            "loss_trades": self.loss_trades,
            "win_rate": win_rate,
            "avg_profit": avg_profit,
            "avg_loss": avg_loss,
            "profit_ratio": profit_ratio,
            "total_days": len(self.equity_curve),
        }

    def print_summary(self):
        """打印回测结果摘要"""
        summary = self.get_summary()

        print("\n" + "=" * 60)
        print("回测结果摘要")
        print("=" * 60)

        print(f"\n资金统计:")
        print(f"  初始资金: {summary['initial_capital']:,.2f} 元")
        print(f"  结束资金: {summary['final_equity']:,.2f} 元")
        print(f"  总收益率: {summary['total_return']:.2f}%")
        print(f"  年化收益: {summary['annual_return']:.2f}%")
        print(f"  最大回撤: {summary['max_drawdown']:.2f}%")
        print(f"  夏普比率: {summary['sharpe_ratio']:.2f}")

        print(f"\n交易统计:")
        print(f"  总交易次数: {summary['total_trades']}")
        print(f"  盈利次数: {summary['win_trades']}")
        print(f"  亏损次数: {summary['loss_trades']}")
        print(f"  胜率: {summary['win_rate']:.2f}%")
        print(f"  平均盈利: {summary['avg_profit']:.2f}%")
        print(f"  平均亏损: {summary['avg_loss']:.2f}%")
        print(f"  盈亏比: {summary['profit_ratio']:.2f}")

        print(f"\n回测天数: {summary['total_days']} 天")
        print("=" * 60)

    def export_trades(self, filepath: str):
        """导出交易记录到CSV

        Args:
            filepath: 文件路径
        """
        if not self.trades:
            return

        df = pd.DataFrame([t.to_dict() for t in self.trades])
        df.to_csv(filepath, index=False)
        logger.info(f"[回测] 交易记录导出到 {filepath}")

    def export_equity_curve(self, filepath: str):
        """导出净值曲线到CSV

        Args:
            filepath: 文件路径
        """
        if not self.equity_curve:
            return

        df = pd.DataFrame(self.equity_curve)
        df.to_csv(filepath, index=False)
        logger.info(f"[回测] 净值曲线导出到 {filepath}")