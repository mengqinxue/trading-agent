# -*- coding: utf-8 -*-
"""
CLI 模块测试

测试命令行界面功能。
"""

import pytest
from unittest.mock import patch, Mock
import sys


class TestCLI:
    """CLI 测试"""

    def test_cli_module_exists(self):
        """测试 CLI 模块存在"""
        from src import cli
        assert cli is not None

    def test_cli_main_function_exists(self):
        """测试 main 函数存在"""
        from src.cli import main
        assert main is not None

    def test_cli_has_query_command(self):
        """测试 CLI 有 query 命令"""
        from src.cli import cli_query
        assert cli_query is not None

    def test_cli_has_template_query_command(self):
        """测试 CLI 有 tpl 命令"""
        from src.cli import cli_template_query
        assert cli_template_query is not None

    def test_cli_has_stats_command(self):
        """测试 CLI 有 stats 命令"""
        from src.cli import cli_market_stats
        assert cli_market_stats is not None

    def test_cli_has_templates_command(self):
        """测试 CLI 有 templates 命令"""
        from src.cli import cli_list_templates
        assert cli_list_templates is not None

    def test_cli_has_market_command(self):
        """测试 CLI 有 market 命令"""
        from src.cli import cli_market_analysis
        assert cli_market_analysis is not None

    def test_cli_has_stock_command(self):
        """测试 CLI 有 stock 命令"""
        from src.cli import cli_stock_analysis
        assert cli_stock_analysis is not None

    def test_cli_has_web_command(self):
        """测试 CLI 有 web 命令"""
        from src.cli import cli_web
        assert cli_web is not None

    def test_cli_has_tasks_command(self):
        """测试 CLI 有 tasks 命令"""
        from src.cli import cli_list_tasks
        assert cli_list_tasks is not None

    def test_cli_has_update_command(self):
        """测试 CLI 有 update 命令"""
        from src.cli import cli_update_data
        assert cli_update_data is not None


class TestCLIQueryFunctions:
    """CLI 查询功能测试"""

    def test_print_stock_result_function_exists(self):
        """测试打印股票结果函数存在"""
        from src.cli import print_stock_result
        assert print_stock_result is not None

    def test_print_market_result_function_exists(self):
        """测试打印市场结果函数存在"""
        from src.cli import print_market_result
        assert print_market_result is not None


class TestCLIHelp:
    """CLI 帮助测试"""

    def test_cli_help_runs(self):
        """测试 CLI 帮助命令运行"""
        import subprocess

        result = subprocess.run(
            ["uv", "run", "python", "main.py", "--help"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert "Trading Agent" in result.stdout

    def test_cli_templates_help_runs(self):
        """测试 templates 帮助"""
        import subprocess

        result = subprocess.run(
            ["uv", "run", "python", "main.py", "templates", "--help"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0


class TestCLIExecution:
    """CLI 执行测试"""

    def test_templates_command_runs(self):
        """测试 templates 命令执行"""
        import subprocess

        result = subprocess.run(
            ["uv", "run", "python", "main.py", "templates"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert "模板" in result.stdout or "template" in result.stdout.lower()