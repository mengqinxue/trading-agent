# -*- coding: utf-8 -*-
"""动态加载生成的策略"""

import importlib.util
import sys
from pathlib import Path
from typing import Optional, Type

from strategies.base import StrategyBase

GENERATED_DIR = Path(__file__).parent


def load_strategy(name: str) -> Optional[Type[StrategyBase]]:
    """动态加载生成的策略类

    Args:
        name: 策略名称

    Returns:
        策略类（不是实例）
    """
    strategy_file = GENERATED_DIR / f"{name}.py"

    if not strategy_file.exists():
        return None

    # 动态导入
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


def list_generated_strategies() -> list:
    """列出所有已生成的策略

    Returns:
        策略名称列表
    """
    strategies = []
    for file in GENERATED_DIR.glob("*.py"):
        if file.name != "__init__.py":
            strategies.append(file.stem)
    return strategies