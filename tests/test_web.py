# -*- coding: utf-8 -*-
"""
Web 模块测试

测试 FastAPI 路由、响应格式。
"""

import pytest
from fastapi.testclient import TestClient


class TestApp:
    """FastAPI 应用测试"""

    def test_app_creation(self):
        """测试应用创建"""
        from src.web.app import app

        assert app is not None
        assert app.title == "Trading Agent"

    def test_app_has_routes(self):
        """测试应用有路由"""
        from src.web.app import app

        routes = [r.path for r in app.routes if hasattr(r, "path")]
        assert len(routes) > 0

    def test_app_has_api_routes(self):
        """测试应用有 API 路由"""
        from src.web.app import app

        routes = [r.path for r in app.routes if hasattr(r, "path")]
        api_routes = [r for r in routes if "/api/" in r]

        assert len(api_routes) > 0


class TestChatRoutes:
    """Chat 路由测试"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        from src.web.app import app
        return TestClient(app)

    def test_templates_endpoint_exists(self, client):
        """测试模板端点存在"""
        resp = client.get("/api/chat/templates")
        assert resp.status_code == 200

    def test_templates_returns_list(self, client):
        """测试模板返回列表"""
        resp = client.get("/api/chat/templates")
        data = resp.json()

        assert "count" in data
        assert "templates" in data
        assert isinstance(data["templates"], list)

    def test_market_stats_endpoint_exists(self, client):
        """测试市场统计端点"""
        resp = client.get("/api/chat/market-stats")
        assert resp.status_code == 200

    def test_limit_up_endpoint_exists(self, client):
        """测试涨停股端点"""
        resp = client.get("/api/chat/limit-up")
        assert resp.status_code == 200


class TestCatalogRoutes:
    """Catalog 路由测试"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        from src.web.app import app
        return TestClient(app)

    def test_data_sources_endpoint(self, client):
        """测试数据源端点"""
        resp = client.get("/api/catalog/data-sources")
        assert resp.status_code == 200

        data = resp.json()
        assert "sources" in data

    def test_data_types_endpoint(self, client):
        """测试数据类型端点"""
        resp = client.get("/api/catalog/data-types")
        assert resp.status_code == 200

        data = resp.json()
        assert "types" in data

    def test_fields_endpoint(self, client):
        """测试字段说明端点"""
        resp = client.get("/api/catalog/fields/实时行情")
        assert resp.status_code == 200

        data = resp.json()
        assert "fields" in data


class TestTaskRoutes:
    """Task 路由测试"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        from src.web.app import app
        return TestClient(app)

    def test_tasks_list_endpoint(self, client):
        """测试任务列表端点"""
        resp = client.get("/api/tasks")
        assert resp.status_code == 200

        data = resp.json()
        assert isinstance(data, list)


class TestStaticFiles:
    """静态文件测试"""

    def test_static_directory_exists(self):
        """测试静态文件目录存在"""
        from pathlib import Path

        static_dir = Path("src/web/static")
        assert static_dir.exists()

    def test_index_html_exists(self):
        """测试 index.html 存在"""
        from pathlib import Path

        index_file = Path("src/web/static/index.html")
        assert index_file.exists()

    def test_chat_html_exists(self):
        """测试 chat.html 存在"""
        from pathlib import Path

        chat_file = Path("src/web/static/chat.html")
        assert chat_file.exists()

    def test_catalog_html_exists(self):
        """测试 catalog.html 存在"""
        from pathlib import Path

        catalog_file = Path("src/web/static/catalog.html")
        assert catalog_file.exists()