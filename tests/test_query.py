# -*- coding: utf-8 -*-
"""
查询模块测试

测试 QueryEngine、查询模板、AI 查询功能。
"""

import pytest
from unittest.mock import Mock, patch


class TestQueryEngine:
    """QueryEngine 测试"""

    def test_engine_initialization(self):
        """测试引擎初始化"""
        from src.query import get_engine, reset_engine

        reset_engine()
        engine = get_engine()

        assert engine is not None
        assert engine._cache_ttl == 600  # 10分钟缓存

    def test_engine_is_singleton(self):
        """测试引擎单例模式"""
        from src.query import get_engine, reset_engine

        reset_engine()
        engine1 = get_engine()
        engine2 = get_engine()

        assert engine1 is engine2

    def test_engine_clear_cache(self):
        """测试缓存清除"""
        from src.query import get_engine

        engine = get_engine()
        engine.clear_cache()

        assert engine._market_data_cache is None
        assert engine._cache_time == 0


class TestTemplates:
    """查询模板测试"""

    def test_template_list_not_empty(self):
        """测试模板列表不为空"""
        from src.query import get_template_list

        templates = get_template_list()
        assert len(templates) > 0

    def test_template_has_required_fields(self):
        """测试模板包含必需字段"""
        from src.query import get_template_list

        templates = get_template_list()

        for t in templates:
            assert "id" in t
            assert "name" in t
            assert "description" in t

    def test_template_get_by_id(self):
        """测试获取单个模板"""
        from src.query.templates import get_template

        template = get_template("limit_up")
        assert template is not None
        assert template["name"] == "涨停股"

    def test_template_get_invalid_returns_none(self):
        """测试获取无效模板返回 None"""
        from src.query.templates import get_template

        template = get_template("invalid_template")
        assert template is None

    def test_limit_up_template_exists(self):
        """测试涨停股模板存在"""
        from src.query.templates import QUERY_TEMPLATES

        assert "limit_up" in QUERY_TEMPLATES
        assert "limit_down" in QUERY_TEMPLATES
        assert "high_turnover" in QUERY_TEMPLATES

    def test_template_count(self):
        """测试模板数量"""
        from src.query.templates import QUERY_TEMPLATES

        # 应至少有 10 个模板
        assert len(QUERY_TEMPLATES) >= 10


class TestAIQuery:
    """AI 查询测试"""

    @pytest.mark.skip(reason="需要真实 API Key")
    def test_ai_query_service_initialization(self):
        """测试 AI 查询服务初始化"""
        from src.query.ai_query import get_service

        service = get_service()
        assert service is not None
        assert service._stock_list is not None

    @pytest.mark.skip(reason="需要真实 API Key")
    def test_ai_query_understands_intent(self):
        """测试 AI 理解意图"""
        from src.query.ai_query import get_service

        service = get_service()
        intent = service._understand_intent("涨幅超过5%的银行股")

        assert "query_type" in intent
        assert "conditions" in intent

    def test_ai_query_service_singleton(self):
        """测试 AI 查询服务单例"""
        from src.query.ai_query import get_service, _service

        # 重置
        import src.query.ai_query as ai_module
        ai_module._service = None

        service1 = get_service()
        service2 = get_service()

        assert service1 is service2


class TestMarketStats:
    """市场统计测试"""

    @pytest.mark.skip(reason="需要网络数据")
    def test_get_market_stats(self):
        """测试获取市场统计"""
        from src.query import get_engine

        engine = get_engine()
        stats = engine.get_market_stats()

        assert "total" in stats
        assert "up_count" in stats
        assert "down_count" in stats
        assert stats["total"] > 0


class TestQueryResults:
    """查询结果格式测试"""

    def test_result_format_has_required_fields(self):
        """测试结果包含必需字段"""
        from src.query.templates import QUERY_TEMPLATES

        for template_id, template in QUERY_TEMPLATES.items():
            # 每个模板应该有 name 和 fields
            assert "name" in template
            assert "fields" in template
            assert isinstance(template["fields"], list)