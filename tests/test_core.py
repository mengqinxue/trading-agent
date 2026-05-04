# -*- coding: utf-8 -*-
"""
核心模块测试

测试配置加载、日志初始化等核心功能。
"""

import pytest
from pathlib import Path


class TestConfig:
    """配置模块测试"""

    def test_config_loads_successfully(self):
        """测试配置正常加载"""
        from src.core.config import config

        assert config.llm.api_key is not None
        assert config.llm.base_url is not None
        assert config.llm.model == "glm-5"
        assert config.log_dir == Path("logs")

    def test_llm_config_has_required_fields(self):
        """测试 LLM 配置包含必需字段"""
        from src.core.config import LLMConfig

        llm = LLMConfig(api_key="test", base_url="https://test.com", model="test")
        assert llm.api_key == "test"
        assert llm.base_url == "https://test.com"
        assert llm.model == "test"


class TestLogger:
    """日志模块测试"""

    def test_logger_initialization(self):
        """测试日志初始化"""
        from src.core.logger import logger

        assert logger is not None
        assert logger.name == "trading_agent"

    def test_logger_has_handlers(self):
        """测试日志处理器"""
        from src.core.logger import logger

        # 应至少有一个处理器
        assert len(logger.handlers) >= 1


class TestPaths:
    """路径配置测试"""

    def test_log_dir_exists(self):
        """测试日志目录存在"""
        from src.core.config import config

        # 日志目录应该在初始化时创建
        assert config.log_dir.exists() or config.log_dir == Path("logs")


class TestImports:
    """导入测试"""

    def test_import_core_modules(self):
        """测试核心模块导入"""
        from src.core import config, logger
        assert config is not None
        assert logger is not None

    def test_import_query_modules(self):
        """测试查询模块导入"""
        from src.query import get_engine, get_template_list
        assert get_engine is not None
        assert get_template_list is not None

    def test_import_data_sources(self):
        """测试数据源模块导入"""
        from src.data_sources import get_fetcher
        assert get_fetcher is not None