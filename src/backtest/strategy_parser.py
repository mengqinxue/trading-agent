# -*- coding: utf-8 -*-
"""策略参数解析器 - 使用GLM-5从自然语言提取策略参数"""

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional

from src.core.llm import get_llm

logger = logging.getLogger(__name__)


@dataclass
class StrategyParams:
    """策略参数"""

    # 基本参数
    name: str = "generated_strategy"
    start_date: str = "2020-01-01"
    end_date: str = datetime.now().strftime("%Y-%m-%d")
    initial_capital: float = 100000.0

    # 买入条件
    buy_condition: str = "涨停板"  # 买入条件描述
    buy_threshold: float = 9.9  # 买入阈值（涨停9.9%）
    max_positions: int = 5  # 最大持仓数
    buy_ratio: float = 0.1  # 买入资金比例（10%）
    buy_frequency: str = "每周"  # 买入频率
    buy_limit: int = 3  # 每周期买入限制

    # 卖出条件
    sell_condition: str = "止盈止损"  # 卖出条件描述
    profit_target: float = 8.0  # 止盈阈值（8%）
    stop_loss: float = -3.0  # 止损阈值（-3%）

    # 市场条件
    market_filter: str = "非熊市"  # 市场过滤条件

    # 股票过滤
    exclude_st: bool = True  # 排除ST股
    exclude_new: bool = True  # 排除次新股
    min_list_days: int = 60  # 最小上市天数

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "initial_capital": self.initial_capital,
            "buy_condition": self.buy_condition,
            "buy_threshold": self.buy_threshold,
            "max_positions": self.max_positions,
            "buy_ratio": self.buy_ratio,
            "buy_frequency": self.buy_frequency,
            "buy_limit": self.buy_limit,
            "sell_condition": self.sell_condition,
            "profit_target": self.profit_target,
            "stop_loss": self.stop_loss,
            "market_filter": self.market_filter,
            "exclude_st": self.exclude_st,
            "exclude_new": self.exclude_new,
            "min_list_days": self.min_list_days,
        }


# GLM-5解析提示词
PARSE_PROMPT = """你是一个量化交易策略解析器。请从用户的自然语言描述中提取策略参数。

用户描述：
{description}

请提取以下参数并以JSON格式返回（只返回JSON，不要其他内容）：
{
    "name": "策略名称（英文，如limit_up_strategy）",
    "buy_condition": "买入条件描述（如涨停板、突破均线等）",
    "buy_threshold": "买入阈值百分比（数字，如9.9表示涨停）",
    "profit_target": "止盈百分比（数字，如8表示8%）",
    "stop_loss": "止损百分比（负数，如-3表示-3%）",
    "max_positions": "最大持仓数（整数）",
    "buy_ratio": "每次买入资金比例（0-1之间）",
    "buy_frequency": "买入频率（每日或每周）",
    "buy_limit": "每周期买入限制（整数）",
    "market_filter": "市场过滤条件（如非熊市、牛市等）",
    "exclude_st": "是否排除ST股（true或false）",
    "exclude_new": "是否排除次新股（true或false）",
    "min_list_days": "最小上市天数（整数）"
}

注意：
1. 如果用户没有明确指定某个参数，使用合理的默认值
2. 涨停板策略的buy_threshold默认为9.9
3. 止盈止损的默认值：profit_target=8, stop_loss=-3
4. 默认最大持仓5只，每周最多买3只
5. 默认排除ST股和次新股（上市不足60天）
"""


def parse_strategy_description(description: str) -> StrategyParams:
    """使用GLM-5解析策略描述

    Args:
        description: 自然语言策略描述

    Returns:
        StrategyParams对象
    """
    # 先尝试快速解析常见关键词
    params = _quick_parse(description)

    if params is not None:
        logger.info(f"[策略解析] 快速解析成功: {params.name}")
        return params

    # 使用GLM-5解析
    logger.info("[策略解析] 使用GLM-5解析策略描述...")
    return _llm_parse(description)


def _quick_parse(description: str) -> Optional[StrategyParams]:
    """快速解析常见关键词

    Args:
        description: 自然语言描述

    Returns:
        StrategyParams或None
    """
    desc_lower = description.lower()

    # 检测涨停板策略
    if "涨停" in description or "涨停板" in description:
        params = StrategyParams(name="limit_up_strategy", buy_condition="涨停板")

        # 提取止盈止损
        profit_match = re.search(r"止盈[^\d]*(\d+)[%％]", description)
        if profit_match:
            params.profit_target = float(profit_match.group(1))

        stop_match = re.search(r"止损[^\d]*(-?\d+)[%％]", description)
        if stop_match:
            params.stop_loss = float(stop_match.group(1))
            if params.stop_loss > 0:
                params.stop_loss = -params.stop_loss

        # 提取熊市过滤
        if "熊市" in description and ("非" in description or "不" in description):
            params.market_filter = "非熊市"

        return params

    # 检测均线策略
    if "均线" in description or "ma" in desc_lower:
        params = StrategyParams(name="ma_strategy", buy_condition="突破均线")
        return params

    # 检测突破策略
    if "突破" in description:
        params = StrategyParams(name="breakout_strategy", buy_condition="突破")
        return params

    return None


def _llm_parse(description: str) -> StrategyParams:
    """使用GLM-5解析

    Args:
        description: 自然语言描述

    Returns:
        StrategyParams对象
    """
    llm = get_llm(temperature=0.1)  # 低温度提高一致性

    prompt = PARSE_PROMPT.format(description=description)

    try:
        response = llm.invoke(prompt)
        content = response.content

        # 提取JSON
        json_match = re.search(r"\{[\s\S]*\}", content)
        if json_match:
            json_str = json_match.group(0)
            data = json.loads(json_str)

            # 构建StrategyParams
            params = StrategyParams(
                name=data.get("name", "generated_strategy"),
                buy_condition=data.get("buy_condition", "涨停板"),
                buy_threshold=float(data.get("buy_threshold", 9.9)),
                profit_target=float(data.get("profit_target", 8.0)),
                stop_loss=float(data.get("stop_loss", -3.0)),
                max_positions=int(data.get("max_positions", 5)),
                buy_ratio=float(data.get("buy_ratio", 0.1)),
                buy_frequency=data.get("buy_frequency", "每周"),
                buy_limit=int(data.get("buy_limit", 3)),
                market_filter=data.get("market_filter", "非熊市"),
                exclude_st=data.get("exclude_st", True),
                exclude_new=data.get("exclude_new", True),
                min_list_days=int(data.get("min_list_days", 60)),
            )

            logger.info(f"[策略解析] GLM-5解析成功: {params.name}")
            return params

        logger.warning("[策略解析] GLM-5返回内容无JSON，使用默认参数")
        return StrategyParams()

    except json.JSONDecodeError as e:
        logger.error(f"[策略解析] JSON解析失败: {e}")
        return StrategyParams()

    except Exception as e:
        logger.error(f"[策略解析] GLM-5调用失败: {e}")
        return StrategyParams()


def validate_params(params: StrategyParams) -> bool:
    """验证策略参数

    Args:
        params: 策略参数

    Returns:
        是否有效
    """
    # 验证数值范围
    if params.buy_threshold < 0 or params.buy_threshold > 30:
        logger.warning(f"[策略验证] buy_threshold={params.buy_threshold} 不合理")
        return False

    if params.profit_target < 0 or params.profit_target > 100:
        logger.warning(f"[策略验证] profit_target={params.profit_target} 不合理")
        return False

    if params.stop_loss > 0 or params.stop_loss < -50:
        logger.warning(f"[策略验证] stop_loss={params.stop_loss} 不合理")
        return False

    if params.buy_ratio <= 0 or params.buy_ratio > 1:
        logger.warning(f"[策略验证] buy_ratio={params.buy_ratio} 不合理")
        return False

    if params.max_positions <= 0 or params.max_positions > 50:
        logger.warning(f"[策略验证] max_positions={params.max_positions} 不合理")
        return False

    return True