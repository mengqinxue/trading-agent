# -*- coding: utf-8 -*-
"""
查询模块

提供智能查询功能：
- 模板查询：涨停股、高换手率、大涨股等
- 板块查询：板块成分股、板块涨跌榜
- 市场统计：涨跌家数、涨停跌停数
"""

from .engine import QueryEngine, get_engine, reset_engine
from .templates import QUERY_TEMPLATES, get_template, get_template_list

__all__ = [
    "QueryEngine",
    "get_engine",
    "reset_engine",
    "QUERY_TEMPLATES",
    "get_template",
    "get_template_list",
]