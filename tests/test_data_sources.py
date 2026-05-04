# -*- coding: utf-8 -*-
"""
数据源模块测试

测试 DataFetcher、数据获取功能。
"""

import pytest
from unittest.mock import Mock, patch
import pandas as pd


class TestDataFetcher:
    """DataFetcher 测试"""

    def test_fetcher_initialization(self):
        """测试 Fetcher 初始化"""
        from src.data_sources import get_fetcher

        fetcher = get_fetcher()
        assert fetcher is not None

    def test_fetcher_is_singleton(self):
        """测试 Fetcher 单例"""
        from src.data_sources import get_fetcher, reset_fetcher

        reset_fetcher()
        f1 = get_fetcher()
        f2 = get_fetcher()

        assert f1 is f2


class TestDailyData:
    """日线数据测试"""

    def test_daily_data_module_exists(self):
        """测试日线数据模块存在"""
        from src.data_sources import trade_daily

        assert trade_daily is not None

    def test_daily_data_columns(self):
        """测试日线数据列名"""
        from src.data_sources.trade_daily import STANDARD_COLUMNS

        expected = ["date", "open", "close", "high", "low", "volume", "amount"]
        for col in expected:
            assert col in STANDARD_COLUMNS


class TestSourcesPriority:
    """数据源优先级测试"""

    def test_sources_priority_defined(self):
        """测试数据源优先级定义"""
        from src.data_sources.sources import DAILY_SOURCE_PRIORITY

        assert len(DAILY_SOURCE_PRIORITY) > 0

    def test_sources_order(self):
        """测试数据源顺序"""
        from src.data_sources.sources import DAILY_SOURCE_PRIORITY

        # Akshare 应在前两位
        sources = [s[0] for s in DAILY_SOURCE_PRIORITY]
        assert "akshare" in sources


class TestTypes:
    """数据类型测试"""

    def test_data_source_enum(self):
        """测试数据源枚举"""
        from src.data_sources.types import DataSource

        assert DataSource.AKSHARE == "akshare"
        assert DataSource.EFINANCE == "efinance"

    def test_daily_bar_class(self):
        """测试 DailyBar 类"""
        from src.data_sources.types import DailyBar

        bar = DailyBar(
            date="2024-01-01",
            open=10.0,
            high=11.0,
            low=9.5,
            close=10.5,
            volume=1000000,
            amount=10500000,
            pct_chg=0.5,
        )

        assert bar.date == "2024-01-01"
        assert bar.close == 10.5


class TestStockList:
    """股票列表测试"""

    def test_stock_list_file_exists(self):
        """测试股票列表文件存在"""
        from pathlib import Path

        stock_list_file = Path("data/CN_A/stock_list.csv")
        assert stock_list_file.exists()

    def test_stock_list_has_required_columns(self):
        """测试股票列表列名"""
        import pandas as pd

        df = pd.read_csv("data/CN_A/stock_list.csv")
        assert "code" in df.columns
        assert "name" in df.columns


class TestCircuitBreaker:
    """熔断器测试"""

    def test_circuit_breaker_exists(self):
        """测试熔断器类存在"""
        from src.data_sources.sources import CircuitBreaker

        assert CircuitBreaker is not None

    def test_circuit_breaker_initial_state(self):
        """测试熔断器初始状态"""
        from src.data_sources.sources import CircuitBreaker

        breaker = CircuitBreaker("test_source", threshold=3, cooldown=60)
        assert breaker.failures == 0
        assert not breaker.is_open()


class TestLocalData:
    """本地数据测试"""

    def test_local_data_directory_exists(self):
        """测试本地数据目录存在"""
        from pathlib import Path

        data_dir = Path("data/CN_A")
        assert data_dir.exists()

    def test_stock_daily_directory_exists(self):
        """测试日线数据目录存在"""
        from pathlib import Path

        daily_dir = Path("data/CN_A/stock_daily")
        assert daily_dir.exists()

    def test_stock_daily_has_files(self):
        """测试日线数据目录有文件"""
        from pathlib import Path

        daily_dir = Path("data/CN_A/stock_daily")
        files = list(daily_dir.glob("*.csv"))
        assert len(files) > 0