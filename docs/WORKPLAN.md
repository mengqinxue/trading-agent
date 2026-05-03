# Trading Agent - 工作计划 (WORKPLAN)

## 当前状态
- [x] 项目初始化
- [x] Phase 1：基础框架搭建 ✅
- [x] Phase 2：核心功能实现 ✅
- [x] Phase 3：完善优化 ✅
- [x] Phase 4：文档合并和功能增强 ✅
- [x] Phase 5：股票数据管理 ✅

---

## Phase 1：基础框架搭建 ✅ 已完成

### 1.1 项目结构 ✅
- [x] 创建 docs 目录
- [x] 编写 PRD 文档
- [x] 编写 WORKPLAN 文档
- [x] 编写架构文档
- [x] 创建 src/trading_agent 目录结构

### 1.2 环境配置 ✅
- [x] 配置 pyproject.toml 依赖
- [x] 创建配置文件 config.py
- [x] 创建日志模块 logger.py
- [x] 验证 .env 配置

### 1.3 LLM 集成 ✅
- [x] 实现阿里云 DashScope + GLM-5 支持
- [x] 创建统一的 LLM 接口
- [x] 测试 LLM 调用（已验证）

### 1.4 数据源集成 ✅
- [x] 集成 akshare 获取 A股数据
- [x] 实现市场数据获取接口
- [x] 实现个股数据获取接口
- [x] 测试数据获取（已验证）

### 1.5 Web Skeleton ✅
- [x] 创建 FastAPI 应用骨架
- [x] 设计 API 路由结构
- [x] 创建基础 HTML 页面
- [x] 测试 Web 服务启动（已验证）

---

## Phase 2：核心功能实现 ✅ 已完成

### 2.1 基础 Workflow 框架 ✅
- [x] 实现 WorkflowState 数据结构
- [x] 创建基础 Workflow 类
- [x] 实现 Workflow 执行器
- [x] 测试基础 workflow

### 2.2 市场分析 Workflow ✅

**Agent 实现**：
- [x] MarketMacroAnalyzer：市场宏观分析
- [x] SectorAnalyzer：板块分析
- [x] IndustryAnalyzer：行业分析  
- [x] StockScreener：个股筛选

**Workflow 编排**：
- [x] 设计市场分析 workflow 图
- [x] 实现 workflow 节点连接
- [x] 测试完整流程

### 2.3 股票分析 Workflow ✅

**Agent 实现**：
- [x] FundamentalsAnalyzer：基本面分析
- [x] TechnicalAnalyzer：技术面分析
- [x] BullAdvocate：正方辩论 agent
- [x] BearAdvocate：反方辩论 agent
- [x] Judge：决策 agent
- [x] PositionAdvisor：持仓建议 agent

**Workflow 编排**：
- [x] 设计股票分析 workflow 图
- [x] 实现辩论环节（最多 10 轮交互）
- [x] 实现决策环节
- [x] 测试完整流程

### 2.4 任务调度 ✅
- [x] 实现任务队列
- [x] 实现任务执行器
- [x] 实现日志记录
- [x] 支持批处理任务
- [x] SQLite 存储

---

## Phase 3：完善优化 ✅ 已完成

### 3.1 CLI 工具 ✅
- [x] trading-agent market 命令
- [x] trading-agent stock 命令
- [x] trading-agent web 命令
- [x] trading-agent tasks 命令
- [x] trading-agent task 命令
- [x] trading-agent update 命令

### 3.2 Web Dashboard ✅
- [x] 任务列表页面
- [x] 任务创建页面（市场分析/股票分析）
- [x] 任务详情页面
- [x] 日志实时展示
- [x] Workflow 说明页面（双 Tab）

---

## Phase 4：文档合并和功能增强 ✅ 已完成

### 4.1 文档合并 ✅
- [x] 合并 business-flow-v2.md 到 ARCHITECTURE.md
- [x] 合并 invest-assistant-*.md 到 PRD.md
- [x] 删除重复文档（5 个）
- [x] 最终文档：PRD.md, ARCHITECTURE.md, WORKPLAN.md, akshare-guide.md

### 4.2 新增 Agents ✅
- [x] InitAgent：系统检测、持仓加载
- [x] DataAggregator：技术面+基本面汇总
- [x] FeishuPush：飞书 Webhook 推送

### 4.3 增强 Judge Agent ✅
- [x] 归因分析（因果链）
- [x] 反事实推断（下跌场景分析）

### 4.4 Workflow 更新 ✅
- [x] 股票分析 Workflow 扩展为 9 节点
- [x] State 增加 22 个字段

---

## Phase 5：股票数据管理 ✅ 已完成

### 5.1 股票列表下载 ✅
- [x] 从 akshare 获取全市场股票列表（5800+ 只）
- [x] 保存为 data/CN_A/stock_list.csv
- [x] 包含代码、名称、市场、ST 标记、退市标记

### 5.2 数据归档 ✅
- [x] 创建 data/CN_A/archive/ 目录
- [x] 归档 139 个退市股票数据文件
- [x] 自动识别退市股票（名称包含"退")

### 5.3 批量更新功能 ✅
- [x] 创建 scripts/update_all_stocks.py
- [x] 支持批量更新所有股票日线数据
- [x] 测试更新功能

---

## Phase 6：Web 界面增强 ✅ 已完成

### 6.1 批量持仓输入 ✅
- [x] 修改 HTML：支持动态添加股票行
- [x] 修改 JavaScript：管理股票列表、持仓输入
- [x] 修改 CSS：新增股票输入样式
- [x] 后端 API：支持 stocks 新格式

### 6.2 API 增强 ✅
- [x] CreateTaskRequest 支持 stocks 列表
- [x] 每只股票独立持仓
- [x] 股票名称查询 API：GET /api/stocks/{code}/name
- [x] 后端兼容旧格式

---

## 任务优先级

**高优先级（Phase 1 必须完成）**：
1. 项目结构和配置
2. LLM 集成
3. 数据源集成
4. Web skeleton

**中优先级（Phase 2 核心功能）**：
1. 基础 workflow 框架
2. 市场分析 workflow
3. 股票分析 workflow

**低优先级（Phase 3 完善）**：
1. Web dashboard 完善
2. 测试覆盖
3. 文档完善

---

## 更新记录

| 日期 | 更新内容 | 状态 |
|------|---------|------|
| 2026-05-03 | 项目初始化，创建 PRD 和 WORKPLAN | 完成 |
| 2026-05-03 | Phase 1：基础框架搭建完成 | ✅ |
| 2026-05-03 | Phase 2：核心功能实现完成 | ✅ |
| 2026-05-03 | Phase 3：CLI 和 README 完善 | ✅ |
| 2026-05-03 | Phase 4：文档合并和功能增强 | ✅ |
| 2026-05-03 | Phase 5：股票数据管理 | ✅ |
| 2026-05-03 | Phase 6：Web 界面增强 | ✅ |
| 2026-05-03 | 项目完成，共 38 个 Python 文件 | ✅ |

---

## 文件清单

**核心模块**：
- core/llm.py - LLM 集成
- core/config.py - 配置管理
- core/logger.py - 日志

**数据源**：
- data_sources/akshare_data.py - A股数据
- data_sources/trendradar.py - TrendRadar MCP
- data_sources/update_stock_daily.py - 日线更新
- data_sources/stock_data_manager.py - 批量管理

**Agents (market)**：
- agents/market/macro_analyzer.py
- agents/market/sector_analyzer.py
- agents/market/industry_analyzer.py
- agents/market/stock_screener.py

**Agents (stock)**：
- agents/stock/init.py
- agents/stock/fundamentals.py
- agents/stock/technical.py
- agents/stock/aggregator.py
- agents/stock/bull_advocate.py
- agents/stock/bear_advocate.py
- agents/stock/judge.py
- agents/stock/position_advisor.py
- agents/stock/feishu_push.py

**Workflows**：
- workflows/state.py
- workflows/market_analysis.py
- workflows/stock_analysis.py

**Scheduler**：
- scheduler/task_queue.py
- scheduler/executor.py
- scheduler/storage.py
- scheduler/workspace_manager.py

**Web**：
- web/app.py
- web/routes/tasks.py
- web/static/index.html
- web/static/style.css
- web/static/app.js

**CLI**：
- cli.py

**Scripts**：
- scripts/update_all_stocks.py

**数据目录**：
- data/CN_A/stock_list.csv - 5800+ 股票列表
- data/CN_A/stock_daily/ - 5356 个日线 CSV
- data/CN_A/archive/ - 139 个归档文件
- workspace/ - 任务日志目录