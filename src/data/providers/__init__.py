# -*- coding: utf-8 -*-
"""
===================================
数据源策略层 - 包初始化
===================================

本包实现策略模式管理多个数据源，实现：
1. 统一的数据获取接口
2. 自动故障切换
3. 防封禁流控策略

数据源优先级：
【配置了 TUSHARE_TOKEN 时】
1. TushareFetcher (Priority 0) - 最高优先级（2000积分可获取全量数据）
2. AkshareFetcher (Priority 1) - 免费、无限制
3. PytdxFetcher (Priority 2) - 通达信
4. BaostockFetcher (Priority 3) - 免费
5. YfinanceFetcher (Priority 4) - 美股/港股
6. LongbridgeFetcher (Priority 5) - 长桥 OpenAPI

【未配置 TUSHARE_TOKEN 时】
1. AkshareFetcher (Priority 1) - 最高优先级
2. PytdxFetcher (Priority 2) - 通达信
3. BaostockFetcher (Priority 3) - 免费
4. YfinanceFetcher (Priority 4) - 美股/港股
5. LongbridgeFetcher (Priority 5) - 长桥 OpenAPI

提示：优先级数字越小越优先
"""

from .base import BaseFetcher, DataFetcherManager
from .akshare_fetcher import AkshareFetcher, is_hk_stock_code
from .tushare_fetcher import TushareFetcher
from .pytdx_fetcher import PytdxFetcher
from .baostock_fetcher import BaostockFetcher
from .yfinance_fetcher import YfinanceFetcher
from .longbridge_fetcher import LongbridgeFetcher
from .us_index_mapping import is_us_index_code, is_us_stock_code, get_us_index_yf_symbol, US_INDEX_MAPPING

__all__ = [
    'BaseFetcher',
    'DataFetcherManager',
    'AkshareFetcher',
    'TushareFetcher',
    'PytdxFetcher',
    'BaostockFetcher',
    'YfinanceFetcher',
    'LongbridgeFetcher',
    'is_us_index_code',
    'is_us_stock_code',
    'is_hk_stock_code',
    'get_us_index_yf_symbol',
    'US_INDEX_MAPPING',
]