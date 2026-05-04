# -*- coding: utf-8 -*-
"""
查询模板定义

预设常用查询模板，快速返回结果。
"""

from typing import Dict, Any, List, Callable, Optional
import pandas as pd


# ============================================
# 查询模板定义
# ============================================

QUERY_TEMPLATES: Dict[str, Dict[str, Any]] = {
    # === 涨跌停 ===
    "limit_up": {
        "name": "涨停股",
        "description": "涨停股票列表（涨跌幅 >= 9.9%）",
        "condition": lambda df: df[df['涨跌幅'] >= 9.9],
        "fields": ['代码', '名称', '涨跌幅', '换手率', '流通市值'],
        "extra_fields": ['所属板块'],  # 需要额外获取
    },
    "limit_down": {
        "name": "跌停股",
        "description": "跌停股票列表（涨跌幅 <= -9.9%）",
        "condition": lambda df: df[df['涨跌幅'] <= -9.9],
        "fields": ['代码', '名称', '涨跌幅', '换手率', '流通市值'],
        "extra_fields": ['所属板块'],
    },

    # === 涨跌幅范围 ===
    "big_rise": {
        "name": "大涨股",
        "description": "涨幅超过指定百分比的股票",
        "condition": lambda df, threshold=5: df[df['涨跌幅'] >= threshold],
        "fields": ['代码', '名称', '涨跌幅', '换手率'],
        "params": {"threshold": {"default": 5, "type": "float", "desc": "涨幅阈值(%)"}},
    },
    "big_fall": {
        "name": "大跌股",
        "description": "跌幅超过指定百分比的股票",
        "condition": lambda df, threshold=-5: df[df['涨跌幅'] <= threshold],
        "fields": ['代码', '名称', '涨跌幅', '换手率'],
        "params": {"threshold": {"default": -5, "type": "float", "desc": "跌幅阈值(%)"}},
    },

    # === 换手率 ===
    "high_turnover": {
        "name": "高换手率",
        "description": "换手率超过指定百分比的股票",
        "condition": lambda df, threshold=10: df[df['换手率'] >= threshold].sort_values('换手率', ascending=False),
        "fields": ['代码', '名称', '换手率', '涨跌幅', '流通市值'],
        "params": {"threshold": {"default": 10, "type": "float", "desc": "换手率阈值(%)"}},
    },

    # === 成交额占比 ===
    "high_volume_ratio": {
        "name": "高成交占比",
        "description": "成交额/流通市值占比超过指定比例的股票",
        "condition": lambda df, threshold=0.05: df[(df['成交额'] / df['流通市值'].replace(0, 1)) >= threshold].sort_values(
            lambda x: x['成交额'] / x['流通市值'].replace(0, 1), ascending=False
        ),
        "fields": ['代码', '名称', '成交额', '流通市值', '换手率'],
        "params": {"threshold": {"default": 0.05, "type": "float", "desc": "成交额/市值占比阈值"}},
    },

    # === 市值范围 ===
    "small_cap": {
        "name": "小市值",
        "description": "流通市值小于指定金额的股票",
        "condition": lambda df, threshold=50e9: df[df['流通市值'] < threshold].sort_values('流通市值'),
        "fields": ['代码', '名称', '流通市值', '涨跌幅'],
        "params": {"threshold": {"default": 50e9, "type": "float", "desc": "市值阈值(元)"}},
    },
    "large_cap": {
        "name": "大市值",
        "description": "流通市值大于指定金额的股票",
        "condition": lambda df, threshold=100e9: df[df['流通市值'] > threshold].sort_values('流通市值', ascending=False),
        "fields": ['代码', '名称', '流通市值', '涨跌幅'],
        "params": {"threshold": {"default": 100e9, "type": "float", "desc": "市值阈值(元)"}},
    },

    # === PE PB ===
    "low_pe": {
        "name": "低PE",
        "description": "市盈率低于指定值的股票（PE > 0）",
        "condition": lambda df, threshold=15: df[(df['市盈率-动态'] > 0) & (df['市盈率-动态'] < threshold)].sort_values('市盈率-动态'),
        "fields": ['代码', '名称', '市盈率-动态', '涨跌幅'],
        "params": {"threshold": {"default": 15, "type": "float", "desc": "PE阈值"}},
    },
    "low_pb": {
        "name": "低PB（破净）",
        "description": "市净率低于1的股票",
        "condition": lambda df: df[(df['市净率'] > 0) & (df['市净率'] < 1)].sort_values('市净率'),
        "fields": ['代码', '名称', '市净率', '涨跌幅'],
    },

    # === 排序榜 ===
    "top_gainers": {
        "name": "涨幅榜",
        "description": "涨幅 TOP N",
        "condition": lambda df, n=20: df.sort_values('涨跌幅', ascending=False).head(n),
        "fields": ['代码', '名称', '涨跌幅', '换手率'],
        "params": {"n": {"default": 20, "type": "int", "desc": "返回数量"}},
    },
    "top_fallers": {
        "name": "跌幅榜",
        "description": "跌幅 TOP N",
        "condition": lambda df, n=20: df.sort_values('涨跌幅', ascending=True).head(n),
        "fields": ['代码', '名称', '涨跌幅', '换手率'],
        "params": {"n": {"default": 20, "type": "int", "desc": "返回数量"}},
    },
    "top_turnover": {
        "name": "换手率榜",
        "description": "换手率 TOP N",
        "condition": lambda df, n=20: df.sort_values('换手率', ascending=False).head(n),
        "fields": ['代码', '名称', '换手率', '涨跌幅', '流通市值'],
        "params": {"n": {"default": 20, "type": "int", "desc": "返回数量"}},
    },
    "top_volume": {
        "name": "成交额榜",
        "description": "成交额 TOP N",
        "condition": lambda df, n=20: df.sort_values('成交额', ascending=False).head(n),
        "fields": ['代码', '名称', '成交额', '涨跌幅'],
        "params": {"n": {"default": 20, "type": "int", "desc": "返回数量"}},
    },
}


# ============================================
# 模板列表获取
# ============================================

def get_template_list() -> List[Dict[str, Any]]:
    """获取所有模板列表"""
    result = []
    for key, template in QUERY_TEMPLATES.items():
        item = {
            "id": key,
            "name": template["name"],
            "description": template["description"],
            "params": template.get("params", {}),
        }
        result.append(item)
    return result


def get_template(template_id: str) -> Optional[Dict[str, Any]]:
    """获取单个模板"""
    return QUERY_TEMPLATES.get(template_id)