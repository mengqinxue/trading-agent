# -*- coding: utf-8 -*-
"""行情数据类型定义"""

from typing import TypedDict, Optional


class DailyBar(TypedDict):
    """日线数据"""
    code: str
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    amount: float
    pct_chg: float
    turnover: Optional[float]


class IndexBar(TypedDict):
    """指数日线数据"""
    code: str
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    amount: float
    pct_chg: float


class SectorBar(TypedDict):
    """板块日线数据"""
    code: str
    date: str
    name: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    amount: float
    pct_chg: float
    lead_stock: Optional[str]


class RealtimeQuote(TypedDict):
    """实时行情"""
    code: str
    price: float
    open: float
    high: float
    low: float
    volume: float
    amount: float
    bid1: float
    ask1: float
    last_close: float


class MinuteData(TypedDict):
    """分时数据"""
    code: str
    time: str
    price: float
    volume: float
    amount: float


class AuctionData(TypedDict):
    """竞价数据"""
    code: str
    call_price: float
    call_volume: float
    bid1: float
    bid1_vol: float
    ask1: float
    ask1_vol: float