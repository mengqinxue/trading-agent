# -*- coding: utf-8 -*-
"""
数据类型定义

统一各数据源返回的数据结构，确保对外接口一致。
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from enum import Enum
import math


# ============================================
# 类型转换工具函数
# ============================================

def safe_float(val: Any, default: Optional[float] = None) -> Optional[float]:
    """安全转换为浮点数"""
    try:
        if val is None:
            return default
        if isinstance(val, str):
            val = val.strip()
            if val == "" or val == "-" or val == "--":
                return default
        try:
            if math.isnan(float(val)):
                return default
        except (ValueError, TypeError):
            pass
        return float(val)
    except (ValueError, TypeError):
        return default


def safe_int(val: Any, default: Optional[int] = None) -> Optional[int]:
    """安全转换为整数"""
    f_val = safe_float(val, default=None)
    if f_val is not None:
        return int(f_val)
    return default


# ============================================
# 数据源枚举
# ============================================

class DataSource(Enum):
    """数据源类型"""
    EFINANCE = "efinance"
    AKSHARE = "akshare"
    TUSHARE = "tushare"
    PYTDX = "pytdx"
    BAOSTOCK = "baostock"
    YFINANCE = "yfinance"
    LONGBRIDGE = "longbridge"
    FALLBACK = "fallback"


# ============================================
# 实时行情数据结构
# ============================================

@dataclass
class RealtimeQuote:
    """实时行情数据"""
    code: str
    name: str = ""
    source: DataSource = DataSource.FALLBACK

    # 核心价格
    price: Optional[float] = None
    change_pct: Optional[float] = None
    change_amount: Optional[float] = None

    # 量价指标
    volume: Optional[int] = None
    amount: Optional[float] = None
    volume_ratio: Optional[float] = None
    turnover_rate: Optional[float] = None
    amplitude: Optional[float] = None

    # 价格区间
    open_price: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    pre_close: Optional[float] = None

    # 估值指标
    pe_ratio: Optional[float] = None
    pb_ratio: Optional[float] = None
    total_mv: Optional[float] = None
    circ_mv: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = {'code': self.code, 'name': self.name, 'source': self.source.value}
        for f in ['price', 'change_pct', 'change_amount', 'volume', 'amount',
                  'volume_ratio', 'turnover_rate', 'amplitude',
                  'open_price', 'high', 'low', 'pre_close',
                  'pe_ratio', 'pb_ratio', 'total_mv', 'circ_mv']:
            val = getattr(self, f, None)
            if val is not None:
                result[f] = val
        return result

    def has_basic_data(self) -> bool:
        """检查是否有基本价格数据"""
        return self.price is not None and self.price > 0


# ============================================
# 筹码分布数据结构
# ============================================

@dataclass
class ChipDistribution:
    """筹码分布数据"""
    code: str
    date: str = ""
    source: str = ""

    profit_ratio: float = 0.0     # 获利比例(0-1)
    avg_cost: float = 0.0         # 平均成本

    cost_90_low: float = 0.0      # 90%筹码成本下限
    cost_90_high: float = 0.0     # 90%筹码成本上限
    concentration_90: float = 0.0  # 90%筹码集中度

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'code': self.code,
            'date': self.date,
            'source': self.source,
            'profit_ratio': self.profit_ratio,
            'avg_cost': self.avg_cost,
            'cost_90_low': self.cost_90_low,
            'cost_90_high': self.cost_90_high,
            'concentration_90': self.concentration_90,
        }

    def get_chip_status(self, current_price: float) -> str:
        """获取筹码状态描述"""
        parts = []

        # 获利比例
        if self.profit_ratio >= 0.9:
            parts.append("获利盘极高(>90%)")
        elif self.profit_ratio >= 0.7:
            parts.append("获利盘较高(70-90%)")
        elif self.profit_ratio >= 0.5:
            parts.append("获利盘中等(50-70%)")
        elif self.profit_ratio >= 0.3:
            parts.append("套牢盘中等(30-50%)")
        else:
            parts.append("套牢盘较高(<30%)")

        # 集中度
        if self.concentration_90 < 0.08:
            parts.append("筹码高度集中")
        elif self.concentration_90 < 0.15:
            parts.append("筹码较集中")
        else:
            parts.append("筹码较分散")

        # 成本关系
        if current_price > 0 and self.avg_cost > 0:
            diff = (current_price - self.avg_cost) / self.avg_cost * 100
            if abs(diff) < 5:
                parts.append("现价接近成本")
            elif diff > 0:
                parts.append(f"现价高于成本{diff:.1f}%")
            else:
                parts.append(f"现价低于成本{abs(diff):.1f}%")

        return "，".join(parts)


# ============================================
# 日线数据结构
# ============================================

@dataclass
class DailyBar:
    """日线数据"""
    date: str
    open: float
    close: float
    high: float
    low: float
    volume: float
    amount: float
    pct_chg: float = 0.0

    # 技术指标
    ma5: float = 0.0
    ma10: float = 0.0
    ma20: float = 0.0
    volume_ratio: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'date': self.date,
            'open': self.open,
            'close': self.close,
            'high': self.high,
            'low': self.low,
            'volume': self.volume,
            'amount': self.amount,
            'pct_chg': self.pct_chg,
            'ma5': self.ma5,
            'ma10': self.ma10,
            'ma20': self.ma20,
            'volume_ratio': self.volume_ratio,
        }


# ============================================
# 龙虎榜数据结构
# ============================================

@dataclass
class DragonTigerRecord:
    """龙虎榜记录"""
    code: str
    name: str = ""
    date: str = ""

    # 买入信息
    buy_amount: float = 0.0        # 买入总额
    buy_top_list: list = field(default_factory=list)  # 买入席位列表

    # 卖出信息
    sell_amount: float = 0.0       # 卖出总额
    sell_top_list: list = field(default_factory=list)  # 卖出席位列表

    # 净买入
    net_buy: float = 0.0           # 净买入额

    def to_dict(self) -> Dict[str, Any]:
        return {
            'code': self.code,
            'name': self.name,
            'date': self.date,
            'buy_amount': self.buy_amount,
            'buy_top_list': self.buy_top_list,
            'sell_amount': self.sell_amount,
            'sell_top_list': self.sell_top_list,
            'net_buy': self.net_buy,
        }


# ============================================
# 研报评级数据结构
# ============================================

@dataclass
class ResearchReport:
    """研报评级"""
    code: str
    name: str = ""
    date: str = ""

    rating: str = ""               # 评级（买入/增持/中性/减持）
    target_price: float = 0.0      # 目标价
    institution: str = ""          # 机构名称
    analyst: str = ""              # 分析师

    def to_dict(self) -> Dict[str, Any]:
        return {
            'code': self.code,
            'name': self.name,
            'date': self.date,
            'rating': self.rating,
            'target_price': self.target_price,
            'institution': self.institution,
            'analyst': self.analyst,
        }