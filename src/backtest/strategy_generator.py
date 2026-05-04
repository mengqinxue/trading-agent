# -*- coding: utf-8 -*-
"""策略代码生成器 - 将StrategyParams转换为策略Python代码"""

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.core.llm import get_llm
from .strategy_parser import StrategyParams

logger = logging.getLogger(__name__)

# 策略生成目录
GENERATED_DIR = Path(__file__).parent.parent.parent / "strategies" / "generated"


# GLM-5生成提示词
GENERATE_PROMPT = """你是一个量化交易策略代码生成器。请根据以下参数生成策略Python代码。

策略参数：
{params_json}

生成的策略需要满足以下要求：
1. 继承自 strategies.base.StrategyBase
2. 实现 run(context) 方法，返回字典包含 buys 和 sells 列表
3. buys列表元素包含 code, name, reason 字段
4. sells列表元素包含 code, price, reason 字段
5. 包含必要的买入、卖出逻辑
6. 如果market_filter是"非熊市"，使用 MarketTrendStrategy 判断市场状态
7. 使用 check_sell_conditions 检查止盈止损

请生成完整的Python代码，使用markdown代码块包裹。代码需要包含：
- 类定义继承StrategyBase
- default_params设置策略参数
- run方法执行策略逻辑
- check_sell_conditions检查卖出
- find_xxx_stocks找符合条件的股票
- get_market_status判断市场状态

只返回Python代码，不要其他内容。
"""


def get_limit_up_template() -> str:
    """获取涨停板策略模板"""
    return '''# -*- coding: utf-8 -*-
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
    3. 盈利PROFIT_TARGET%止盈，亏损STOP_LOSS%止损
    """

    name = "limit_up_strategy"
    default_params = {
        "profit_target": PROFIT_TARGET,
        "stop_loss": STOP_LOSS,
        "max_positions": MAX_POSITIONS,
        "buy_ratio": BUY_RATIO,
        "weekly_buy_limit": BUY_LIMIT,
        "min_list_days": MIN_LIST_DAYS,
        "limit_up_threshold": BUY_THRESHOLD,
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
        if MARKET_FILTER_CHECK:
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
'''


# 策略模板映射
STRATEGY_TEMPLATES = {
    "limit_up_strategy": get_limit_up_template,
}


def generate_strategy_code(params: StrategyParams) -> str:
    """生成策略代码

    Args:
        params: 策略参数

    Returns:
        策略Python代码字符串
    """
    # 检查是否有预定义模板
    if params.name in STRATEGY_TEMPLATES:
        logger.info(f"[策略生成] 使用模板生成: {params.name}")
        return _apply_template(params)

    # 使用GLM-5生成
    logger.info("[策略生成] 使用GLM-5生成策略代码...")
    return _llm_generate(params)


def _apply_template(params: StrategyParams) -> str:
    """应用模板生成代码

    Args:
        params: 策略参数

    Returns:
        策略代码
    """
    template_func = STRATEGY_TEMPLATES.get(params.name)
    if template_func is None:
        template_func = get_limit_up_template  # 默认使用涨停板模板

    template = template_func()

    # 使用标记替换，避免format解析问题
    replacements = {
        "PROFIT_TARGET": str(params.profit_target),
        "STOP_LOSS": str(params.stop_loss),
        "MAX_POSITIONS": str(params.max_positions),
        "BUY_RATIO": str(params.buy_ratio),
        "BUY_LIMIT": str(params.buy_limit),
        "MIN_LIST_DAYS": str(params.min_list_days),
        "BUY_THRESHOLD": str(params.buy_threshold),
        "MARKET_FILTER_CHECK": f'"{params.market_filter}" == "非熊市"' if params.market_filter else "False",
    }

    code = template
    for key, value in replacements.items():
        code = code.replace(key, value)

    return code


def _llm_generate(params: StrategyParams) -> str:
    """使用GLM-5生成代码

    Args:
        params: 策略参数

    Returns:
        策略代码
    """
    llm = get_llm(temperature=0.3)

    params_json = json.dumps(params.to_dict(), ensure_ascii=False, indent=2)
    prompt = GENERATE_PROMPT.format(params_json=params_json)

    try:
        response = llm.invoke(prompt)
        content = response.content

        # 提取Python代码
        code_match = re.search(r"```python\s*([\s\S]*?)\s*```", content)
        if code_match:
            code = code_match.group(1)
        else:
            # 尝试提取整个代码块
            code_match = re.search(r"```([\s\S]*?)\s*```", content)
            if code_match:
                code = code_match.group(1)
            else:
                code = content

        # 清理代码
        code = code.strip()
        if not code.startswith("# -*- coding"):
            code = f"# -*- coding: utf-8 -*-\n\"\"\"{params.name} - 由GLM-5生成\"\"\"\n\n{code}"

        logger.info(f"[策略生成] GLM-5生成成功: {len(code)} 字符")
        return code

    except Exception as e:
        logger.error(f"[策略生成] GLM-5生成失败: {e}")
        # 返回基础策略模板
        return _apply_template(StrategyParams())


def save_strategy(code: str, name: str) -> Path:
    """保存策略代码到文件

    Args:
        code: 策略代码
        name: 策略名称

    Returns:
        保存的文件路径
    """
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)

    # 清理名称
    safe_name = re.sub(r"[^a-zA-Z0-9_]", "_", name.lower())
    if not safe_name:
        safe_name = f"strategy_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    filepath = GENERATED_DIR / f"{safe_name}.py"

    # 避免覆盖
    if filepath.exists():
        timestamp = datetime.now().strftime('%H%M%S')
        filepath = GENERATED_DIR / f"{safe_name}_{timestamp}.py"

    filepath.write_text(code, encoding="utf-8")
    logger.info(f"[策略保存] 策略已保存到: {filepath}")

    return filepath


def validate_generated_code(code: str) -> bool:
    """验证生成的代码

    Args:
        code: 策略代码

    Returns:
        是否有效
    """
    # 检查必要结构
    if "class" not in code:
        logger.warning("[代码验证] 缺少类定义")
        return False

    if "StrategyBase" not in code:
        logger.warning("[代码验证] 未继承StrategyBase")
        return False

    if "def run" not in code:
        logger.warning("[代码验证] 缺少run方法")
        return False

    # 检查危险操作
    dangerous_patterns = [
        "import os",
        "import sys",
        "exec(",
        "eval(",
        "__import__",
        "subprocess",
        "rm -rf",
    ]

    for pattern in dangerous_patterns:
        if pattern in code:
            logger.warning(f"[代码验证] 包含危险操作: {pattern}")
            return False

    return True