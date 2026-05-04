# -*- coding: utf-8 -*-
"""
智能查询 API 路由

提供 AI 自然语言查询、模板查询、市场统计、板块查询接口。
"""

from fastapi import APIRouter, Query, Path, HTTPException
from typing import Optional, Dict, Any

from src.query import get_engine, get_template_list
from src.query.ai_query import get_service

router = APIRouter()


# ============================================
# AI 自然语言查询（新增）
# ============================================

@router.post("/ai-query")
async def ai_natural_query(request: Dict[str, Any]):
    """AI 自然语言查询

    用户输入自然语言问题，AI 理解语义并查询本地数据库。

    Request body:
    - query: 自然语言问题，如 "最近涨幅超过10%的银行股有哪些？"
    """
    user_query = request.get("query", "")
    if not user_query:
        raise HTTPException(status_code=400, detail="query 参数必填")

    service = get_service()
    result = service.query(user_query)
    return result


# ============================================
# 模板列表
# ============================================

@router.get("/templates")
async def list_templates():
    """获取查询模板列表"""
    templates = get_template_list()
    return {"count": len(templates), "templates": templates}


# ============================================
# 模板查询
# ============================================

@router.get("/query/{template_id}")
async def query_by_template(
    template_id: str = Path(..., description="模板ID"),
    threshold: Optional[float] = Query(None, description="阈值参数"),
    n: Optional[int] = Query(None, description="返回数量"),
):
    """按模板查询股票"""
    engine = get_engine()

    # 构建参数
    params = {}
    if threshold is not None:
        params['threshold'] = threshold
    if n is not None:
        params['n'] = n

    result = engine.query(template_id, **params)
    return result


# ============================================
# 快捷查询
# ============================================

@router.get("/limit-up")
async def query_limit_up():
    """查询涨停股"""
    engine = get_engine()
    return engine.query('limit_up')


@router.get("/limit-down")
async def query_limit_down():
    """查询跌停股"""
    engine = get_engine()
    return engine.query('limit_down')


@router.get("/high-turnover")
async def query_high_turnover(threshold: float = Query(10, ge=0, le=100)):
    """查询高换手率股票"""
    engine = get_engine()
    return engine.query('high_turnover', threshold=threshold)


@router.get("/big-rise")
async def query_big_rise(threshold: float = Query(5, ge=0, le=20)):
    """查询大涨股"""
    engine = get_engine()
    return engine.query('big_rise', threshold=threshold)


@router.get("/big-fall")
async def query_big_fall(threshold: float = Query(-5, ge=-20, le=0)):
    """查询大跌股"""
    engine = get_engine()
    return engine.query('big_fall', threshold=threshold)


@router.get("/top-gainers")
async def query_top_gainers(n: int = Query(20, ge=1, le=100)):
    """涨幅榜"""
    engine = get_engine()
    return engine.query('top_gainers', n=n)


@router.get("/top-fallers")
async def query_top_fallers(n: int = Query(20, ge=1, le=100)):
    """跌幅榜"""
    engine = get_engine()
    return engine.query('top_fallers', n=n)


@router.get("/top-turnover")
async def query_top_turnover(n: int = Query(20, ge=1, le=100)):
    """换手率榜"""
    engine = get_engine()
    return engine.query('top_turnover', n=n)


@router.get("/top-volume")
async def query_top_volume(n: int = Query(20, ge=1, le=100)):
    """成交额榜"""
    engine = get_engine()
    return engine.query('top_volume', n=n)


# ============================================
# 市场统计
# ============================================

@router.get("/market-stats")
async def get_market_stats():
    """获取市场涨跌统计"""
    engine = get_engine()
    return engine.get_market_stats()


# ============================================
# 板块查询
# ============================================

@router.get("/sector/{sector_name}")
async def query_sector(
    sector_name: str = Path(..., description="板块名称"),
    sort_by: str = Query('涨跌幅', description="排序字段"),
    n: int = Query(50, ge=1, le=200, description="返回数量"),
):
    """查询板块成分股"""
    engine = get_engine()
    return engine.query_sector(sector_name, sort_by=sort_by, n=n)


@router.get("/sector-rankings")
async def get_sector_rankings(n: int = Query(10, ge=1, le=50)):
    """获取板块涨跌榜"""
    engine = get_engine()
    return engine.get_sector_rankings(n=n)


# ============================================
# 缓存管理
# ============================================

@router.post("/clear-cache")
async def clear_cache():
    """清除缓存"""
    engine = get_engine()
    engine.clear_cache()
    return {"message": "缓存已清除"}