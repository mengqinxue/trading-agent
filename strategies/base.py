# -*- coding: utf-8 -*-
"""策略基类"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class StrategyBase(ABC):
    """策略基类

    所有策略必须继承此类，实现 run 方法。

    Attributes:
        name: 策略名称
        params: 策略参数（可配置）
    """

    name: str = "base_strategy"
    default_params: Dict[str, Any] = {}

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        """初始化策略

        Args:
            params: 策略参数，覆盖默认参数
        """
        self.params = {**self.default_params, **(params or {})}
        self.validate_params()

    def validate_params(self) -> bool:
        """验证参数有效性

        Returns:
            参数是否有效

        Raises:
            ValueError: 参数无效时抛出
        """
        # 基类不做验证，子类可覆盖
        return True

    @abstractmethod
    def run(self, data: Any) -> Any:
        """执行策略

        Args:
            data: 输入数据

        Returns:
            策略结果
        """
        pass

    def get_param(self, key: str, default: Any = None) -> Any:
        """获取参数值

        Args:
            key: 参数名
            default: 默认值

        Returns:
            参数值
        """
        return self.params.get(key, default)

    def set_param(self, key: str, value: Any) -> None:
        """设置参数值

        Args:
            key: 参数名
            value: 参数值
        """
        self.params[key] = value
        self.validate_params()

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name}, params={self.params})"