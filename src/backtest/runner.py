# -*- coding: utf-8 -*-
"""回测执行器 - 执行策略回测"""

import importlib.util
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

import pandas as pd

from strategies.base import StrategyBase
from strategies.backtest import BacktestEngine
from strategies.market_trend import MarketTrendStrategy
from .strategy_parser import StrategyParams, parse_strategy_description
from .strategy_generator import generate_strategy_code, save_strategy, validate_generated_code

logger = logging.getLogger(__name__)

# 数据路径
DATA_DIR = Path("data/CN_A")
DAILY_DIR = DATA_DIR / "stock_daily"
STOCK_LIST_FILE = DATA_DIR / "stock_list.csv"
INDEX_FILE = DATA_DIR / "index_daily" / "000001_上证指数_Daily.csv"
GENERATED_DIR = Path(__file__).parent.parent.parent / "strategies" / "generated"

# SQLite 数据库路径
DB_PATH = Path("data/market/daily/stocks.db")
INDEX_DB_PATH = Path("data/market/daily/index.db")


class BacktestRunner:
    """回测执行器"""

    def __init__(self, use_db: bool = True):
        self.use_db = use_db
        self.index_df: Optional[pd.DataFrame] = None
        self.stock_list: Optional[pd.DataFrame] = None
        self.trading_days: List[str] = []
        self.valid_codes: set = set()

        # SQLite 数据加载器
        self.db_loader: Optional[Any] = None
        if use_db and DB_PATH.exists():
            from src.data.loaders import DailyLoader
            self.db_loader = DailyLoader(DB_PATH)
            logger.info("[数据加载] 使用 SQLite 数据库")

    def load_data(self, start_date: str, end_date: str) -> bool:
        """加载必要数据

        Args:
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            是否成功加载
        """
        # 加载上证指数
        from src.data_sources import load_index_daily

        logger.info("[数据加载] 加载上证指数...")
        self.index_df = load_index_daily("000001")

        if self.index_df is None or self.index_df.empty:
            logger.error("[数据加载] 无法加载上证指数数据")
            return False

        # 标准化日期列
        if "date" in self.index_df.columns:
            self.index_df["date"] = self.index_df["date"].astype(str)

        # 获取交易日
        self.trading_days = self._get_trading_days(start_date, end_date)
        logger.info(f"[数据加载] 交易日数量: {len(self.trading_days)}")

        # 加载股票列表
        logger.info("[数据加载] 加载股票列表...")
        if STOCK_LIST_FILE.exists():
            self.stock_list = pd.read_csv(STOCK_LIST_FILE)
            self.stock_list["code"] = self.stock_list["code"].astype(str)
            logger.info(f"[数据加载] 股票数量: {len(self.stock_list)}")

            # 预筛选有效股票
            self._pre_filter_stocks(start_date)
        else:
            logger.warning(f"[数据加载] 股票列表文件不存在: {STOCK_LIST_FILE}")
            self.stock_list = None

        return True

    def _get_trading_days(self, start_date: str, end_date: str) -> List[str]:
        """获取交易日列表"""
        df = self.index_df[
            (self.index_df["date"] >= start_date) & (self.index_df["date"] <= end_date)
        ]
        return df["date"].tolist()

    def _pre_filter_stocks(self, start_date: str):
        """预筛选股票"""
        if self.stock_list is None:
            return

        # 筛选上市较早的股票和非ST股
        self.stock_list["list_date"] = self.stock_list["list_date"].astype(str)
        valid_stocks = self.stock_list[
            (self.stock_list["list_date"] <= start_date) |
            (self.stock_list["list_date"] == "") |
            (self.stock_list["is_st"] == False)
        ]
        self.valid_codes = set(valid_stocks["code"].tolist())
        logger.info(f"[数据加载] 预筛选股票: {len(self.valid_codes)} 只")

    def load_stock_data_for_date(self, date: str) -> Dict[str, Any]:
        """加载指定日期的股票数据

        Args:
            date: 日期

        Returns:
            {code: row_dict} 字典
        """
        # 优先使用 SQLite 数据库
        if self.db_loader:
            data = self.db_loader.load_date(date)

            # 过滤有效股票
            if self.valid_codes:
                data = {code: row for code, row in data.items() if code in self.valid_codes}

            logger.debug(f"[数据加载] SQLite 加载 {date}: {len(data)} 条")
            return data

        # 兜底：从 CSV 文件加载
        return self._load_stock_data_from_csv(date)

    def _load_stock_data_from_csv(self, date: str) -> Dict[str, Any]:
        """从 CSV 文件加载股票数据（兜底方案）"""
        stock_data = {}

        if not DAILY_DIR.exists():
            return stock_data

        for file in DAILY_DIR.glob("*.csv"):
            code = file.name.split("_")[0]

            # 快速过滤
            if self.valid_codes and code not in self.valid_codes:
                continue

            try:
                df = pd.read_csv(file, nrows=1000)

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
                        if date_col != "date":
                            row_dict["date"] = row_dict.get(date_col)
                        stock_data[code] = row_dict

            except Exception:
                continue

        return stock_data

    def run_from_description(
        self,
        description: str,
        start_date: str = "2020-01-01",
        end_date: str = None,
        initial_capital: float = 100000,
        save_strategy_code: bool = False,
    ) -> Dict[str, Any]:
        """从自然语言描述运行回测

        Args:
            description: 自然语言策略描述
            start_date: 开始日期
            end_date: 结束日期（默认今天）
            initial_capital: 初始资金
            save_strategy_code: 是否保存生成的策略代码

        Returns:
            回测结果
        """
        # 1. 解析策略描述
        logger.info(f"[回测] 解析策略描述: {description[:50]}...")
        params = parse_strategy_description(description)
        params.start_date = start_date
        params.end_date = end_date or datetime.now().strftime("%Y-%m-%d")
        params.initial_capital = initial_capital

        # 2. 生成策略代码
        logger.info("[回测] 生成策略代码...")
        code = generate_strategy_code(params)

        if not validate_generated_code(code):
            logger.warning("[回测] 策略代码验证失败，使用默认策略")
            code = generate_strategy_code(StrategyParams())

        # 3. 保存策略（可选）
        if save_strategy_code:
            save_strategy(code, params.name)

        # 4. 动态加载策略
        strategy = self._load_strategy_from_code(code, params.name)

        if strategy is None:
            logger.error("[回测] 策略加载失败")
            return {"success": False, "error": "策略加载失败"}

        # 5. 运行回测
        return self.run_from_strategy(
            strategy=strategy,
            start_date=params.start_date,
            end_date=params.end_date,
            initial_capital=params.initial_capital,
        )

    def run_from_strategy(
        self,
        strategy: StrategyBase,
        start_date: str = "2020-01-01",
        end_date: str = None,
        initial_capital: float = 100000,
    ) -> Dict[str, Any]:
        """从策略对象运行回测

        Args:
            strategy: 策略实例
            start_date: 开始日期
            end_date: 结束日期
            initial_capital: 初始资金

        Returns:
            回测结果
        """
        end_date = end_date or datetime.now().strftime("%Y-%m-%d")

        # 加载数据
        if not self.load_data(start_date, end_date):
            return {"success": False, "error": "数据加载失败"}

        # 创建回测引擎
        engine = BacktestEngine(initial_capital=initial_capital)
        logger.info(f"[回测] 初始资金: {initial_capital:,.2f} 元")

        # 运行回测
        logger.info(f"[回测] 开始回测: {start_date} ~ {end_date}")
        total_days = len(self.trading_days)
        progress_interval = max(total_days // 20, 1)

        for i, date in enumerate(self.trading_days):
            # 打印进度
            if i % progress_interval == 0:
                pct = i / total_days * 100
                equity = engine.get_equity()
                positions = len(engine.positions)
                trades = engine.total_trades
                logger.info(
                    f"[回测进度] {pct:.0f}% ({i}/{total_days}) | "
                    f"日期: {date} | "
                    f"净值: {equity:,.0f} | "
                    f"持仓: {positions} | "
                    f"交易: {trades}"
                )

            # 加载当日股票数据
            stock_data = self.load_stock_data_for_date(date)

            # 执行策略
            context = {
                "date": date,
                "index_df": self.index_df,
                "stock_data": stock_data,
                "engine": engine,
                "stock_list": self.stock_list,
                "daily_dir": DAILY_DIR,
            }

            result = strategy.run(context)

            # 执行卖出
            for sell in result.get("sells", []):
                engine.sell(
                    code=sell["code"],
                    price=sell["price"],
                    date=date,
                    reason=sell["reason"],
                )

            # 执行买入（第二天开盘价）
            for buy in result.get("buys", []):
                buy_price = None
                next_day_idx = i + 1

                if next_day_idx < len(self.trading_days):
                    next_day = self.trading_days[next_day_idx]
                    next_stock_data = self.load_stock_data_for_date(next_day)

                    if buy["code"] in next_stock_data:
                        next_row = next_stock_data[buy["code"]]
                        buy_price = float(next_row.get("open", next_row.get("开盘", 0)))

                if buy_price is None or buy_price <= 0:
                    if buy["code"] in stock_data:
                        buy_price = float(stock_data[buy["code"]].get("close", 0))
                    else:
                        continue

                # 计算买入金额
                buy_amount = engine.cash * strategy.get_param("buy_ratio", 0.1)

                # 执行买入
                success = engine.buy(
                    code=buy["code"],
                    name=buy["name"],
                    price=buy_price,
                    date=self.trading_days[next_day_idx] if next_day_idx < len(self.trading_days) else date,
                    amount=buy_amount,
                    reason=buy["reason"],
                )

                if success and hasattr(strategy, "increment_weekly_buy"):
                    strategy.increment_weekly_buy()

            # 记录净值
            current_prices = {}
            for code in engine.positions.keys():
                if code in stock_data:
                    current_prices[code] = float(stock_data[code].get("close", 0))

            engine.record_equity(date, current_prices)

        # 获取结果
        summary = engine.get_summary()

        logger.info("[回测] 回测完成")
        engine.print_summary()

        return {
            "success": True,
            "summary": summary,
            "trades": [t.to_dict() for t in engine.trades],
            "equity_curve": engine.equity_curve,
        }

    def run_from_saved_strategy(
        self,
        strategy_name: str,
        start_date: str = "2020-01-01",
        end_date: str = None,
        initial_capital: float = 100000,
    ) -> Dict[str, Any]:
        """从已保存的策略运行回测

        Args:
            strategy_name: 策略名称
            start_date: 开始日期
            end_date: 结束日期
            initial_capital: 初始资金

        Returns:
            回测结果
        """
        strategy_class = self._load_saved_strategy(strategy_name)

        if strategy_class is None:
            return {"success": False, "error": f"策略 {strategy_name} 不存在"}

        strategy = strategy_class()
        return self.run_from_strategy(strategy, start_date, end_date, initial_capital)

    def _load_strategy_from_code(self, code: str, name: str) -> Optional[StrategyBase]:
        """从代码字符串动态加载策略

        Args:
            code: 策略代码
            name: 策略名称

        Returns:
            策略实例
        """
        # 确保目录存在
        GENERATED_DIR.mkdir(parents=True, exist_ok=True)

        # 创建临时模块
        module_name = f"temp_strategy_{datetime.now().strftime('%H%M%S')}"
        temp_file = GENERATED_DIR / f"_temp_{name}.py"

        try:
            # 写入临时文件
            temp_file.write_text(code, encoding="utf-8")
            logger.info(f"[策略加载] 临时文件写入成功: {temp_file}")

            # 动态导入
            spec = importlib.util.spec_from_file_location(module_name, temp_file)
            if spec is None or spec.loader is None:
                logger.error("[策略加载] 无法创建模块spec")
                return None

            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)

            # 查找策略类
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if isinstance(attr, type) and issubclass(attr, StrategyBase) and attr is not StrategyBase:
                    # 创建实例
                    instance = attr()
                    logger.info(f"[策略加载] 策略类加载成功: {attr.__name__}")
                    # 不删除临时文件，以便调试
                    return instance

            logger.warning("[策略加载] 未找到策略类")
            return None

        except Exception as e:
            logger.error(f"[策略加载] 加载失败: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _load_saved_strategy(self, name: str) -> Optional[Type[StrategyBase]]:
        """加载已保存的策略

        Args:
            name: 策略名称

        Returns:
            策略类（不是实例）
        """
        strategy_file = GENERATED_DIR / f"{name}.py"

        if not strategy_file.exists():
            logger.warning(f"[策略加载] 策略文件不存在: {strategy_file}")
            return None

        try:
            module_name = f"strategies.generated.{name}"
            spec = importlib.util.spec_from_file_location(module_name, strategy_file)

            if spec is None or spec.loader is None:
                return None

            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)

            # 查找策略类
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if isinstance(attr, type) and issubclass(attr, StrategyBase) and attr is not StrategyBase:
                    return attr

            return None

        except Exception as e:
            logger.error(f"[策略加载] 加载失败: {e}")
            return None

    def list_saved_strategies(self) -> List[str]:
        """列出已保存的策略

        Returns:
            策略名称列表
        """
        strategies = []
        for file in GENERATED_DIR.glob("*.py"):
            if not file.name.startswith("_") and file.name != "__init__.py":
                strategies.append(file.stem)
        return strategies