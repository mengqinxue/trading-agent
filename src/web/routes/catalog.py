# -*- coding: utf-8 -*-
"""
数据词典 API 路由

提供数据源、数据类型、字段说明接口。
"""

from fastapi import APIRouter, Path
from typing import Dict, Any, List

router = APIRouter()


# ============================================
# 数据源列表
# ============================================

DATA_SOURCES: List[Dict[str, Any]] = [
    {
        "name": "Akshare",
        "status": "active",
        "description": "主要数据源 - 免费 Python 库，多源聚合",
        "config": "无需配置",
        "priority": 1,
    },
    {
        "name": "Efinance",
        "status": "available",
        "description": "东财爬虫 - 接口简洁，实时性好",
        "config": "pip install efinance",
        "priority": 2,
    },
    {
        "name": "Tushare",
        "status": "config_required",
        "description": "专业数据 - 积分制，需注册 Token",
        "config": "环境变量 TUSHARE_TOKEN",
        "priority": 3,
    },
    {
        "name": "Baostock",
        "status": "active",
        "description": "兜底数据源 - 免费，历史数据稳定",
        "config": "无需配置",
        "priority": 4,
    },
]


@router.get("/data-sources")
async def get_data_sources():
    """获取数据源列表"""
    return {"count": len(DATA_SOURCES), "sources": DATA_SOURCES}


# ============================================
# 数据类型列表
# ============================================

DATA_TYPES: List[Dict[str, Any]] = [
    {
        "name": "实时行情",
        "category": "trade",
        "status": "implemented",
        "update_freq": "实时",
        "description": "价格、涨跌幅、成交量、换手率、PE、PB、市值",
    },
    {
        "name": "日线数据",
        "category": "trade",
        "status": "implemented",
        "update_freq": "每日",
        "description": "开高低收、量、额、均线、量比",
    },
    {
        "name": "筹码分布",
        "category": "trade",
        "status": "implemented",
        "update_freq": "实时",
        "description": "获利比例、平均成本、集中度",
    },
    {
        "name": "龙虎榜",
        "category": "trade",
        "status": "partial",
        "update_freq": "每日",
        "description": "买入席位、卖出席位、净买入额",
    },
    {
        "name": "财务报表",
        "category": "fundamental",
        "status": "implemented",
        "update_freq": "季度",
        "description": "营收、净利润、毛利率、ROE、负债率",
    },
    {
        "name": "估值指标",
        "category": "fundamental",
        "status": "implemented",
        "update_freq": "实时",
        "description": "PE_TTM、PB、PS、市值(总/流通)",
    },
    {
        "name": "分红数据",
        "category": "fundamental",
        "status": "partial",
        "update_freq": "年度",
        "description": "股息率、分红历史、除权除息日",
    },
    {
        "name": "股东结构",
        "category": "fundamental",
        "status": "partial",
        "update_freq": "季度",
        "description": "机构持股比例、十大股东",
    },
    {
        "name": "研报评级",
        "category": "fundamental",
        "status": "partial",
        "update_freq": "不定期",
        "description": "评级、目标价、机构名称",
    },
    {
        "name": "指数行情",
        "category": "market",
        "status": "implemented",
        "update_freq": "实时",
        "description": "上证、深证、创业板、科创50",
    },
    {
        "name": "板块数据",
        "category": "market",
        "status": "implemented",
        "update_freq": "实时",
        "description": "板块涨跌榜、板块成分股、股票所属板块",
    },
    {
        "name": "市场统计",
        "category": "market",
        "status": "implemented",
        "update_freq": "实时",
        "description": "涨跌家数、涨停跌停数",
    },
]


@router.get("/data-types")
async def get_data_types():
    """获取数据类型列表"""
    return {"count": len(DATA_TYPES), "types": DATA_TYPES}


# ============================================
# 字段说明
# ============================================

DATA_FIELDS: Dict[str, List[Dict[str, Any]]] = {
    "实时行情": [
        {"name": "code", "type": "string", "desc": "股票代码（如 000001）"},
        {"name": "name", "type": "string", "desc": "股票名称"},
        {"name": "price", "type": "float", "desc": "最新价格（元）"},
        {"name": "change_pct", "type": "float", "desc": "涨跌幅（%）"},
        {"name": "change_amount", "type": "float", "desc": "涨跌额（元）"},
        {"name": "volume", "type": "int", "desc": "成交量（股）"},
        {"name": "amount", "type": "float", "desc": "成交额（元）"},
        {"name": "turnover_rate", "type": "float", "desc": "换手率（%）"},
        {"name": "volume_ratio", "type": "float", "desc": "量比"},
        {"name": "amplitude", "type": "float", "desc": "振幅（%）"},
        {"name": "pe_ratio", "type": "float", "desc": "市盈率（动态）"},
        {"name": "pb_ratio", "type": "float", "desc": "市净率"},
        {"name": "total_mv", "type": "float", "desc": "总市值（元）"},
        {"name": "circ_mv", "type": "float", "desc": "流通市值（元）"},
    ],
    "日线数据": [
        {"name": "date", "type": "string", "desc": "交易日期（YYYY-MM-DD）"},
        {"name": "open", "type": "float", "desc": "开盘价"},
        {"name": "close", "type": "float", "desc": "收盘价"},
        {"name": "high", "type": "float", "desc": "最高价"},
        {"name": "low", "type": "float", "desc": "最低价"},
        {"name": "volume", "type": "int", "desc": "成交量（股）"},
        {"name": "amount", "type": "float", "desc": "成交额（元）"},
        {"name": "pct_chg", "type": "float", "desc": "涨跌幅（%）"},
        {"name": "ma5", "type": "float", "desc": "5日均线"},
        {"name": "ma10", "type": "float", "desc": "10日均线"},
        {"name": "ma20", "type": "float", "desc": "20日均线"},
        {"name": "volume_ratio", "type": "float", "desc": "量比"},
    ],
    "筹码分布": [
        {"name": "profit_ratio", "type": "float", "desc": "获利比例（%）"},
        {"name": "avg_cost", "type": "float", "desc": "平均成本（元）"},
        {"name": "concentration_90", "type": "float", "desc": "90%筹码集中度"},
        {"name": "concentration_70", "type": "float", "desc": "70%筹码集中度"},
    ],
    "财务报表": [
        {"name": "revenue", "type": "float", "desc": "营业收入（元）"},
        {"name": "net_profit", "type": "float", "desc": "净利润（元）"},
        {"name": "gross_margin", "type": "float", "desc": "毛利率（%）"},
        {"name": "roe", "type": "float", "desc": "净资产收益率（%）"},
        {"name": "debt_ratio", "type": "float", "desc": "资产负债率（%）"},
        {"name": "revenue_growth", "type": "float", "desc": "营收增长率（%）"},
        {"name": "profit_growth", "type": "float", "desc": "净利润增长率（%）"},
    ],
    "估值指标": [
        {"name": "pe_ttm", "type": "float", "desc": "市盈率TTM"},
        {"name": "pb", "type": "float", "desc": "市净率"},
        {"name": "ps", "type": "float", "desc": "市销率"},
        {"name": "total_mv", "type": "float", "desc": "总市值（元）"},
        {"name": "circ_mv", "type": "float", "desc": "流通市值（元）"},
    ],
    "指数行情": [
        {"name": "code", "type": "string", "desc": "指数代码"},
        {"name": "name", "type": "string", "desc": "指数名称"},
        {"name": "price", "type": "float", "desc": "当前点位"},
        {"name": "change_pct", "type": "float", "desc": "涨跌幅（%）"},
        {"name": "volume", "type": "float", "desc": "成交额（元）"},
    ],
    "板块数据": [
        {"name": "name", "type": "string", "desc": "板块名称"},
        {"name": "change_pct", "type": "float", "desc": "板块涨跌幅（%）"},
        {"name": "up_count", "type": "int", "desc": "上涨家数"},
        {"name": "down_count", "type": "int", "desc": "下跌家数"},
        {"name": "leader_code", "type": "string", "desc": "领涨股代码"},
        {"name": "leader_name", "type": "string", "desc": "领涨股名称"},
        {"name": "leader_change", "type": "float", "desc": "领涨股涨幅"},
    ],
    "市场统计": [
        {"name": "total", "type": "int", "desc": "总股票数"},
        {"name": "up_count", "type": "int", "desc": "上涨家数"},
        {"name": "down_count", "type": "int", "desc": "下跌家数"},
        {"name": "flat_count", "type": "int", "desc": "平盘家数"},
        {"name": "limit_up_count", "type": "int", "desc": "涨停家数"},
        {"name": "limit_down_count", "type": "int", "desc": "跌停家数"},
        {"name": "up_ratio", "type": "float", "desc": "上涨占比（%）"},
    ],
}


@router.get("/fields/{data_type}")
async def get_data_fields(data_type: str = Path(..., description="数据类型名称")):
    """获取数据类型字段说明"""
    fields = DATA_FIELDS.get(data_type, [])
    if not fields:
        return {"error": f"未找到数据类型: {data_type}", "available_types": list(DATA_FIELDS.keys())}
    return {"data_type": data_type, "count": len(fields), "fields": fields}


# ============================================
# 数据样例
# ============================================

@router.get("/sample/{data_type}")
async def get_data_sample(data_type: str = Path(..., description="数据类型名称")):
    """获取数据样例"""
    sample: Dict[str, Any] = {}

    try:
        if data_type == "实时行情":
            from src.data import get_fetcher
            fetcher = get_fetcher()
            quote = fetcher.get_realtime("000001")
            if quote:
                sample = {
                    "code": quote.code,
                    "name": quote.name,
                    "price": quote.price,
                    "change_pct": quote.change_pct,
                    "volume": quote.volume,
                    "amount": quote.amount,
                    "turnover_rate": quote.turnover_rate,
                    "pe_ratio": quote.pe_ratio,
                    "pb_ratio": quote.pb_ratio,
                    "total_mv": quote.total_mv,
                    "circ_mv": quote.circ_mv,
                }
        elif data_type == "日线数据":
            from src.data import get_fetcher
            fetcher = get_fetcher()
            df, msg = fetcher.get_daily("000001", days=1)
            if df is not None and not df.empty:
                row = df.tail(1).iloc[0]
                sample = {
                    "date": row.get("date", ""),
                    "open": row.get("open", 0),
                    "close": row.get("close", 0),
                    "high": row.get("high", 0),
                    "low": row.get("low", 0),
                    "volume": row.get("volume", 0),
                    "amount": row.get("amount", 0),
                    "pct_chg": row.get("pct_chg", 0),
                }
        elif data_type == "筹码分布":
            from src.data import get_fetcher
            fetcher = get_fetcher()
            chip = fetcher.get_chip("000001")
            if chip:
                sample = {
                    "profit_ratio": chip.profit_ratio,
                    "avg_cost": chip.avg_cost,
                    "concentration_90": chip.concentration_90,
                    "concentration_70": chip.concentration_70,
                }
        elif data_type == "指数行情":
            from src.data import get_fetcher
            fetcher = get_fetcher()
            indices = fetcher.get_indices()
            if indices:
                sample = indices[0] if indices else {}
        elif data_type == "板块数据":
            from src.data import get_fetcher
            fetcher = get_fetcher()
            top, bottom = fetcher.get_sectors(n=1)
            sample = top[0] if top else {}
        elif data_type == "市场统计":
            from src.query import get_engine
            engine = get_engine()
            stats = engine.get_market_stats()
            sample = stats

    except Exception as e:
        sample = {"error": f"获取样例失败: {str(e)}"}

    return {"data_type": data_type, "sample": sample}