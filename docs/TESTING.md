# 测试文档

## 测试概述

Trading Agent 项目使用 pytest 进行自动化测试。

### 测试统计

| 指标 | 数值 |
|------|------|
| 测试用例总数 | 68 |
| 通过 | 62 |
| 失败 | 3 |
| 跳过 | 3 |
| 覆盖率 | 18% |

### 运行测试

```bash
# 运行全部测试
uv run pytest tests/ -v

# 运行带覆盖率报告
uv run pytest tests/ -v --cov=src --cov-report=term-missing

# 运行单个测试文件
uv run pytest tests/test_query.py -v
```

---

## 测试模块

### 1. Core 模块测试 (`test_core.py`)

测试核心配置和日志功能。

| 测试用例 | 结果 | 说明 |
|----------|------|------|
| `test_config_loads_successfully` | ✅ PASS | 配置模块正常加载 |
| `test_llm_config_has_required_fields` | ✅ PASS | LLM 配置包含必需字段 |
| `test_logger_initialization` | ✅ PASS | 日志初始化成功 |
| `test_logger_has_handlers` | ✅ PASS | 日志处理器配置正确 |
| `test_log_dir_exists` | ✅ PASS | 日志目录存在 |
| `test_import_core_modules` | ✅ PASS | 核心模块导入成功 |
| `test_import_query_modules` | ✅ PASS | 查询模块导入成功 |
| `test_import_data_sources` | ✅ PASS | 数据源模块导入成功 |

### 2. Query 模块测试 (`test_query.py`)

测试查询引擎和查询模板。

| 测试用例 | 结果 | 说明 |
|----------|------|------|
| `test_engine_initialization` | ✅ PASS | QueryEngine 初始化成功 |
| `test_engine_is_singleton` | ✅ PASS | 引擎单例模式正确 |
| `test_engine_clear_cache` | ✅ PASS | 缓存清除功能正常 |
| `test_template_list_not_empty` | ✅ PASS | 模板列表不为空 |
| `test_template_has_required_fields` | ✅ PASS | 模板包含必需字段 |
| `test_template_get_by_id` | ✅ PASS | 获取单个模板成功 |
| `test_template_get_invalid_returns_none` | ✅ PASS | 无效模板返回 None |
| `test_limit_up_template_exists` | ✅ PASS | 涨停股模板存在 |
| `test_template_count` | ✅ PASS | 模板数量 >= 10 |
| `test_ai_query_service_initialization` | ⏭️ SKIP | 需要 API Key |
| `test_ai_query_understands_intent` | ⏭️ SKIP | 需要 API Key |
| `test_ai_query_service_singleton` | ✅ PASS | AI 服务单例正确 |
| `test_get_market_stats` | ⏭️ SKIP | 需要网络数据 |
| `test_result_format_has_required_fields` | ✅ PASS | 结果格式正确 |

### 3. Data Sources 模块测试 (`test_data_sources.py`)

测试数据获取功能。

| 测试用例 | 结果 | 说明 |
|----------|------|------|
| `test_fetcher_initialization` | ✅ PASS | DataFetcher 初始化成功 |
| `test_fetcher_is_singleton` | ✅ PASS | Fetcher 单例模式正确 |
| `test_daily_data_module_exists` | ✅ PASS | 日线数据模块存在 |
| `test_daily_data_columns` | ❌ FAIL | STANDARD_COLUMNS 导入失败 |
| `test_sources_priority_defined` | ✅ PASS | 数据源优先级定义正确 |
| `test_sources_order` | ✅ PASS | Akshare 在优先级前列 |
| `test_data_source_enum` | ❌ FAIL | 枚举比较方式需调整 |
| `test_daily_bar_class` | ✅ PASS | DailyBar 类正常 |
| `test_stock_list_file_exists` | ✅ PASS | 股票列表文件存在 |
| `test_stock_list_has_required_columns` | ✅ PASS | 股票列表列名正确 |
| `test_circuit_breaker_exists` | ✅ PASS | 熔断器类存在 |
| `test_circuit_breaker_initial_state` | ❌ FAIL | 参数名需调整 |
| `test_local_data_directory_exists` | ✅ PASS | 本地数据目录存在 |
| `test_stock_daily_directory_exists` | ✅ PASS | 日线数据目录存在 |
| `test_stock_daily_has_files` | ✅ PASS | 日线数据文件存在 |

### 4. Web 模块测试 (`test_web.py`)

测试 FastAPI 路由和静态文件。

| 测试用例 | 结果 | 说明 |
|----------|------|------|
| `test_app_creation` | ✅ PASS | FastAPI 应用创建成功 |
| `test_app_has_routes` | ✅ PASS | 应用有路由配置 |
| `test_app_has_api_routes` | ✅ PASS | API 路由存在 |
| `test_templates_endpoint_exists` | ✅ PASS | 模板端点响应正常 |
| `test_templates_returns_list` | ✅ PASS | 模板返回列表格式 |
| `test_market_stats_endpoint_exists` | ✅ PASS | 市场统计端点正常 |
| `test_limit_up_endpoint_exists` | ✅ PASS | 涨停股端点正常 |
| `test_data_sources_endpoint` | ✅ PASS | 数据源端点正常 |
| `test_data_types_endpoint` | ✅ PASS | 数据类型端点正常 |
| `test_fields_endpoint` | ✅ PASS | 字段说明端点正常 |
| `test_tasks_list_endpoint` | ✅ PASS | 任务列表端点正常 |
| `test_static_directory_exists` | ✅ PASS | 静态文件目录存在 |
| `test_index_html_exists` | ✅ PASS | index.html 存在 |
| `test_chat_html_exists` | ✅ PASS | chat.html 存在 |
| `test_catalog_html_exists` | ✅ PASS | catalog.html 存在 |

### 5. CLI 模块测试 (`test_cli.py`)

测试命令行界面功能。

| 测试用例 | 结果 | 说明 |
|----------|------|------|
| `test_cli_module_exists` | ✅ PASS | CLI 模块存在 |
| `test_cli_main_function_exists` | ✅ PASS | main 函数存在 |
| `test_cli_has_query_command` | ✅ PASS | query 命令存在 |
| `test_cli_has_template_query_command` | ✅ PASS | tpl 命令存在 |
| `test_cli_has_stats_command` | ✅ PASS | stats 命令存在 |
| `test_cli_has_templates_command` | ✅ PASS | templates 命令存在 |
| `test_cli_has_market_command` | ✅ PASS | market 命令存在 |
| `test_cli_has_stock_command` | ✅ PASS | stock 命令存在 |
| `test_cli_has_web_command` | ✅ PASS | web 命令存在 |
| `test_cli_has_tasks_command` | ✅ PASS | tasks 命令存在 |
| `test_cli_has_update_command` | ✅ PASS | update 命令存在 |
| `test_print_stock_result_function_exists` | ✅ PASS | 打印函数存在 |
| `test_print_market_result_function_exists` | ✅ PASS | 打印函数存在 |
| `test_cli_help_runs` | ✅ PASS | CLI help 运行正常 |
| `test_cli_templates_help_runs` | ✅ PASS | templates help 正常 |
| `test_templates_command_runs` | ✅ PASS | templates 命令执行成功 |

---

## 失败测试分析

### 1. `test_daily_data_columns`

**错误**: `ImportError: cannot import name 'STANDARD_COLUMNS'`

**原因**: `STANDARD_COLUMNS` 定义在 `base.py` 而非 `trade_daily.py`

**修复方案**: 从正确模块导入或跳过此测试

### 2. `test_data_source_enum`

**错误**: 枚举值比较方式不正确

**原因**: `DataSource.AKSHARE` 是枚举对象，需要用 `.value` 比较

**修复方案**: 使用 `DataSource.AKSHARE.value == "akshare"`

### 3. `test_circuit_breaker_initial_state`

**错误**: `TypeError: CircuitBreaker.__init__() got an unexpected keyword argument 'threshold'`

**原因**: CircuitBreaker 参数名不同

**修复方案**: 调整测试参数名

---

## 测试覆盖范围

### 高覆盖率模块 (>50%)

| 模块 | 覆盖率 |
|------|--------|
| `src/core/config.py` | 95% |
| `src/core/logger.py` | 95% |
| `src/core/llm.py` | 100% |
| `src/query/templates.py` | 100% |
| `src/query/engine.py` | 68% |
| `src/data_sources/__init__.py` | 100% |
| `src/web/app.py` | 57% |
| `src/web/routes/tasks.py` | 59% |

### 需增加测试的模块 (<20%)

| 模块 | 覆盖率 | 建议 |
|------|--------|------|
| `src/cli.py` | 7% | 添加集成测试 |
| `src/workflows/stock_analysis.py` | 13% | 需要 Mock LLM |
| `src/data_sources/providers/base.py` | 10% | 添加单元测试 |

---

## 持续集成建议

```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install uv
      - run: uv sync
      - run: uv run pytest tests/ -v --cov=src
```