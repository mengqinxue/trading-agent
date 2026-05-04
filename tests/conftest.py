# -*- coding: utf-8 -*-
"""
Trading Agent 测试配置

pytest 配置和共享 fixtures。
"""

import pytest
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))


@pytest.fixture
def sample_stock_code():
    """示例股票代码"""
    return "000001"


@pytest.fixture
def sample_stock_codes():
    """示例股票代码列表"""
    return ["000001", "600036", "300750"]


@pytest.fixture
def mock_config():
    """模拟配置（避免加载真实 API Key）"""
    from src.core.config import LLMConfig, AppConfig

    return AppConfig(
        llm=LLMConfig(
            api_key="test-api-key",
            base_url="https://test.example.com/v1",
            model="test-model",
        ),
        log_level="DEBUG",
        log_dir=Path("logs"),
    )