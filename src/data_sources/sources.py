# -*- coding: utf-8 -*-
"""
数据源配置与熔断机制

管理多数据源的优先级、熔断状态、防封禁策略。
"""

import logging
import time
import random
from threading import RLock
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


# ============================================
# 熔断器
# ============================================

class CircuitBreaker:
    """熔断器 - 管理数据源的熔断/冷却状态"""

    CLOSED = "closed"       # 正常
    OPEN = "open"           # 熔断
    HALF_OPEN = "half_open"  # 半开

    def __init__(
        self,
        failure_threshold: int = 3,
        cooldown_seconds: float = 300.0,
        half_open_max_calls: int = 1
    ):
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self.half_open_max_calls = half_open_max_calls
        self._states: Dict[str, Dict[str, Any]] = {}
        self._lock = RLock()

    def _get_state_locked(self, source: str) -> Dict[str, Any]:
        if source not in self._states:
            self._states[source] = {
                'state': self.CLOSED,
                'failures': 0,
                'last_failure_time': 0.0,
                'half_open_calls': 0
            }
        return self._states[source]

    def is_available(self, source: str) -> bool:
        """检查数据源是否可用"""
        with self._lock:
            state = self._get_state_locked(source)
            current_time = time.time()

            if state['state'] == self.CLOSED:
                return True

            if state['state'] == self.OPEN:
                elapsed = current_time - state['last_failure_time']
                if elapsed >= self.cooldown_seconds:
                    state['state'] = self.HALF_OPEN
                    state['half_open_calls'] = 0
                    logger.info(f"[熔断器] {source} 冷却完成，进入半开状态")
                else:
                    return False

            if state['state'] == self.HALF_OPEN:
                if state['half_open_calls'] < self.half_open_max_calls:
                    state['half_open_calls'] += 1
                    return True
                elapsed = current_time - state['last_failure_time']
                if elapsed >= self.cooldown_seconds:
                    state['half_open_calls'] = 1
                    return True
                return False

            return True

    def record_success(self, source: str) -> None:
        """记录成功"""
        with self._lock:
            state = self._get_state_locked(source)
            if state['state'] == self.HALF_OPEN:
                logger.info(f"[熔断器] {source} 半开恢复，状态正常")
            state['state'] = self.CLOSED
            state['failures'] = 0
            state['half_open_calls'] = 0

    def record_inconclusive(self, source: str) -> None:
        """记录不确定结果（返回空数据）"""
        with self._lock:
            state = self._get_state_locked(source)
            if state['state'] == self.HALF_OPEN:
                state['state'] = self.OPEN
                state['half_open_calls'] = 0
                state['last_failure_time'] = time.time()
                logger.info(f"[熔断器] {source} 半开结果不确定，重新冷却")

    def record_failure(self, source: str, error: Optional[str] = None) -> None:
        """记录失败"""
        with self._lock:
            state = self._get_state_locked(source)
            state['failures'] += 1
            state['last_failure_time'] = time.time()

            if state['state'] == self.HALF_OPEN:
                state['state'] = self.OPEN
                state['half_open_calls'] = 0
                logger.warning(f"[熔断器] {source} 半开失败，继续熔断")
            elif state['failures'] >= self.failure_threshold:
                state['state'] = self.OPEN
                logger.warning(f"[熔断器] {source} 连续失败 {state['failures']} 次，熔断 {self.cooldown_seconds}s")

    def get_status(self) -> Dict[str, str]:
        """获取所有状态"""
        with self._lock:
            return {s: i['state'] for s, i in self._states.items()}

    def reset(self, source: Optional[str] = None) -> None:
        """重置状态"""
        with self._lock:
            if source:
                self._states.pop(source, None)
            else:
                self._states.clear()


# ============================================
# 数据源优先级配置
# ============================================

# 日线数据源优先级（数字越小越优先）
DAILY_SOURCE_PRIORITY = [
    ("efinance", 0),    # 东财爬虫
    ("akshare", 1),     # Akshare
    ("baostock", 2),    # Baostock（免费稳定）
    ("tushare", 3),     # Tushare（需token）
    ("pytdx", 4),       # 通达信直连
]

# 实时行情数据源优先级
REALTIME_SOURCE_PRIORITY = [
    ("efinance", 0),
    ("akshare", 1),
]

# 筹码分布数据源优先级
CHIP_SOURCE_PRIORITY = [
    ("efinance", 0),
    ("akshare", 1),
]


# ============================================
# 防封禁策略
# ============================================

def random_sleep(min_sec: float = 1.5, max_sec: float = 3.0) -> None:
    """随机休眠，避免请求过于规律"""
    delay = random.uniform(min_sec, max_sec)
    time.sleep(delay)


# ============================================
# 全局熔断器实例
# ============================================

# 实时行情熔断器
_realtime_breaker = CircuitBreaker(failure_threshold=3, cooldown_seconds=300.0)

# 日线数据熔断器
_daily_breaker = CircuitBreaker(failure_threshold=3, cooldown_seconds=300.0)

# 筹码分布熔断器（更保守）
_chip_breaker = CircuitBreaker(failure_threshold=2, cooldown_seconds=600.0)


def get_realtime_breaker() -> CircuitBreaker:
    return _realtime_breaker

def get_daily_breaker() -> CircuitBreaker:
    return _daily_breaker

def get_chip_breaker() -> CircuitBreaker:
    return _chip_breaker


# ============================================
# 数据源可用性检查
# ============================================

def get_available_sources(source_type: str = "daily") -> List[str]:
    """获取当前可用的数据源列表（按优先级）"""
    if source_type == "daily":
        priority = DAILY_SOURCE_PRIORITY
        breaker = get_daily_breaker()
    elif source_type == "realtime":
        priority = REALTIME_SOURCE_PRIORITY
        breaker = get_realtime_breaker()
    elif source_type == "chip":
        priority = CHIP_SOURCE_PRIORITY
        breaker = get_chip_breaker()
    else:
        priority = DAILY_SOURCE_PRIORITY
        breaker = get_daily_breaker()

    available = []
    for source, _ in priority:
        if breaker.is_available(source):
            available.append(source)
    return available