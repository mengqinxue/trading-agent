# Trading Agent

A股交易辅助系统 - 基于 LangGraph 多 agent 协作的市场和个股分析工具。

## 功能特性

### 1. 市场分析
- 判断当前市场形势（牛市/熊市/震荡市）
- 识别热点板块
- 分析行业增长潜力
- 筛选潜力个股

### 2. 股票分析
- 基本面分析（财务指标、行业地位）
- 技术面分析（K线形态、技术指标）
- 多 agent 辩论（正方 vs 反方，最多 10 轮）
- 综合决策（买入/卖出/持有）
- 持仓建议（仓位、止损止盈）

### 3. AI 智能查询（新增）
- 自然语言查询本地股票数据
- AI（GLM-5）理解语义并返回结果
- 示例："涨幅超过5%的银行股"、"最近涨停的股票"
- 基于本地数据（data/CN_A），无需网络请求

### 4. 数据词典（新增）
- 查看可用数据源（Akshare/Efinance/Tushare）
- 数据类型说明（实时行情、日线、筹码分布）
- 字段定义和数据样例

### 5. Web Dashboard
- 任务列表管理（基于 Workspace 文件系统）
- **批量股票分析（支持每只股票独立持仓）**
- 实时日志查看
- Workflow 流程图可视化
- 任务详情页面（含执行步骤时间线）
- **智能查询页面（自然语言输入）**
- **数据词典页面**

### 6. 股票数据管理
- 下载全市场股票列表（5800+ 只）
- 批量更新日线数据
- 归档退市股票数据

### 7. 数据源管理
- 多数据源自动切换（防单点故障）
- 熔断机制保护（防 API 封禁）
- 实时行情增强（量比、换手率、PE/PB、市值）
- 筹码分布分析（获利比例、平均成本、集中度）

---

## 数据源管理系统

`tmp/data_provider/` 是一个完善的多数据源策略管理系统，采用策略模式实现数据获取的自动故障切换和防封禁保护。

### 核心架构

```
┌─────────────────────────────────────────────────────────────┐
│                   DataFetcherManager                         │
│  ┌─────────────────────────────────────────────────────────┐│
│  │  策略管理器 - 自动故障切换 + 熔断保护                     ││
│  └─────────────────────────────────────────────────────────┘│
│                                                              │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐        │
│  │ Efinance │ │ Akshare  │ │ Tushare  │ │  Pytdx   │ ...    │
│  │ P=0      │ │ P=1      │ │ P=2      │ │ P=2      │        │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘        │
│                                                              │
│  优先级数字越小越优先，失败后自动切换到下一个                │
└─────────────────────────────────────────────────────────────┘
```

### 支持的数据源

| 数据源 | 优先级 | 特点 | 配置要求 |
|--------|--------|------|----------|
| EfinanceFetcher | 0 | 东财爬虫，API简洁，数据全面 | 无 |
| AkshareFetcher | 1 | 多源支持（东财/新浪/腾讯） | 无 |
| TushareFetcher | 2 | 专业数据，积分制 | TUSHARE_TOKEN |
| PytdxFetcher | 2 | 通达信直连，稳定 | PYTDX_HOST/PORT |
| BaostockFetcher | 3 | 免费，数据稳定 | 无 |
| YfinanceFetcher | 4 | 美股/港股兜底 | 无 |
| LongbridgeFetcher | 5 | 长桥 OpenAPI | LONGBRIDGE Keys |

### 主要功能

#### 1. 日线数据获取

```python
from src.data_sources.providers import DataFetcherManager

manager = DataFetcherManager()

# 自动故障切换获取日线数据
df, source = manager.get_daily_data("000001", days=60)

# df 包含标准化列：date, open, high, low, close, volume, amount, pct_chg
# df 包含计算指标：ma5, ma10, ma20, volume_ratio
```

#### 2. 实时行情获取

```python
# 获取实时行情（自动多源切换）
quote = manager.get_realtime_quote("000001")

# UnifiedRealtimeQuote 包含丰富字段：
quote.code           # 代码
quote.name           # 名称
quote.price          # 最新价
quote.change_pct     # 涨跌幅(%)
quote.volume         # 成交量
quote.amount         # 成交额
quote.volume_ratio   # 量比 ⭐ 新增
quote.turnover_rate  # 换手率(%) ⭐ 新增
quote.amplitude      # 振幅(%) ⭐ 新增
quote.pe_ratio       # 市盈率(动态) ⭐ 新增
quote.pb_ratio       # 市净率 ⭐ 新增
quote.total_mv       # 总市值(元) ⭐ 新增
quote.circ_mv        # 流通市值(元) ⭐ 新增
```

#### 3. 筹码分布分析

```python
# 获取筹码分布（带熔断保护）
chip = manager.get_chip_distribution("000001")

# ChipDistribution 包含：
chip.profit_ratio       # 获利比例 (0-1)
chip.avg_cost           # 平均成本
chip.cost_90_low        # 90%筹码成本下限
chip.cost_90_high       # 90%筹码成本上限
chip.concentration_90   # 90%筹码集中度

# 获取筹码状态描述
status = chip.get_chip_status(current_price=50.0)
# 返回："获利盘较高(获利盘70-90%)，筹码较集中，现价略高于成本5.2%"
```

#### 4. 基本面数据聚合

```python
# 获取基本面全景数据（估值、成长、盈利、机构、资金流、龙虎榜、板块）
context = manager.get_fundamental_context("000001", budget_seconds=30)

context['valuation']     # 估值：PE、PB、市值
context['growth']        # 成长：营收/利润增速
context['earnings']      # 盈利：ROE、净利率、分红
context['institution']   # 机构：持股比例
context['capital_flow']  # 资金流：主力/散户资金
context['dragon_tiger']  # 龙虎榜：上榜次数
context['boards']        # 板块：所属板块、板块排行
```

#### 5. 市场数据

```python
# 获取主要指数行情
indices = manager.get_main_indices(region="cn")
# [{"code": "000001", "name": "上证指数", "current": 3100, "change_pct": 1.2}, ...]

# 获取市场涨跌统计
stats = manager.get_market_stats()
# {"up_count": 2000, "down_count": 3000, "limit_up_count": 50, ...}

# 获取板块涨跌榜
top, bottom = manager.get_sector_rankings(n=5)
# top = [{"name": "人工智能", "change": 3.5}, ...]
```

#### 6. 股票信息查询

```python
# 获取股票名称
name = manager.get_stock_name("000001")  # "平安银行"

# 获取所属板块
boards = manager.get_belong_boards("000001")
# [{"name": "银行", "type": "行业"}, {"name": "深圳本地", "type": "地域"}]

# 批量获取股票名称
names = manager.batch_get_stock_names(["000001", "600000"])
# {"000001": "平安银行", "600000": "浦发银行"}
```

### 熔断机制

熔断器防止反复请求失败的数据源，策略如下：

```
状态机：
CLOSED（正常） ─失败N次→ OPEN（熔断） ─冷却时间→ HALF_OPEN（半开）
HALF_OPEN ─成功→ CLOSED
HALF_OPEN ─失败→ OPEN

参数：
- failure_threshold = 3    # 连续失败 3 次熔断
- cooldown_seconds = 300   # 冷却 5 分钟
- half_open_max_calls = 1  # 半开状态试探 1 次
```

### 防封禁策略

| 策略 | 实现方式 |
|------|----------|
| 随机休眠 | 每次请求前随机等待 1.5-3.0 秒 |
| UA 轮换 | 随机选择 User-Agent 避免指纹 |
| 指数退避 | 失败后等待时间逐步增加（tenacity） |
| 缓存复用 | 实时行情缓存 10-20 分钟 |

### 数据缓存

```python
# 实时行情缓存（10-20 分钟 TTL）
_realtime_cache = {
    'data': DataFrame,    # 全市场数据
    'timestamp': float,   # 缓存时间
    'ttl': 1200           # 20分钟有效期
}

# 批量分析场景：
# - 30 只股票在 5 分钟内分析完
# - 20 分钟缓存足够覆盖整个分析周期
# - 减少 API 调用，避免封禁
```

---

## 本地数据存储

系统支持将 A 股历史数据下载到本地，用于离线分析或回测。

### 数据目录结构

```
data/CN_A/
├── stock_list.csv           # 全市场股票列表（5702 只）
├── stock_daily/             # 日线数据目录（5702 个 CSV）
│   ├── 000001_平安银行_Daily_To2026.csv
│   ├── 000002_万科A_Daily_To2026.csv
│   └── ...
├── etf_daily/               # ETF 日线数据
└── archive/                 # 退市股票归档（141 个文件）
```

### 数据源与更新频率

| 数据类型 | 数据源 | 更新频率 | 字段说明 |
|----------|--------|----------|----------|
| 股票列表 | Akshare (东财实时行情) | 手动更新 | code, name, market, industry, is_st, is_delisted |
| 日线数据 | 多源自动切换 | 手动/定时 | date, open, close, high, low, volume, amount, pct_chg, ma5, ma10, ma20, volume_ratio |
| 退市归档 | 文件迁移 | 手动处理 | 保持原有格式 |

### 日线数据字段说明

每个 CSV 文件包含以下标准化字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| date | str | 交易日期 (YYYY-MM-DD) |
| open | float | 开盘价 |
| close | float | 收盘价 |
| high | float | 最高价 |
| low | float | 最低价 |
| volume | float | 成交量（股） |
| amount | float | 成交额（元） |
| pct_chg | float | 涨跌幅 (%) |
| turnover | float | 换手率 (%) |
| ma5 | float | 5 日均线 |
| ma10 | float | 10 日均线 |
| ma20 | float | 20 日均线 |
| volume_ratio | float | 量比（相对 5 日均量） |

### 数据样例

#### stock_list.csv（前 5 行）

```csv
code,name,market,industry,list_date,is_st,is_delisted
301599,N理奇,SZ,,,False,False
920125,鸿仕达,UNKNOWN,,,False,False
000001,平安银行,SZ,银行,,False,False
600036,招商银行,SH,银行,,False,False
```

#### 日线数据样例（000001_平安银行_Daily_To2026.csv）

```csv
date,open,close,high,low,volume,amount,pct_chg,turnover,ma5,ma10,ma20,volume_ratio
2026-04-28,11.50,11.49,11.55,11.45,123456789,1.42e9,-0.26,0.85,11.48,11.52,11.60,0.74
2026-04-27,11.52,11.52,11.58,11.48,98765432,1.13e9,0.00,0.68,11.50,11.53,11.61,0.58
...
```

### 更新命令

```bash
# 更新单只股票
trading-agent update --codes 000001

# 更新多只股票
trading-agent update --codes 000001 600036 300750

# 更新所有股票（耗时约 30 分钟）
trading-agent update --all --batch-size 100 --delay 1.0

# 测试模式（仅更新前 10 只）
trading-agent update --all --limit 10
```

### 数据管理脚本

```python
from trading_agent.data_sources.stock_data_manager import (
    download_stock_list,
    update_stock_daily,
    batch_update_all_stocks,
    archive_stocks,
)

# 1. 下载股票列表
stock_list = download_stock_list()
# 返回 DataFrame: 5702 只股票

# 2. 更新单只股票日线数据
success = update_stock_daily("000001", "平安银行")
# 使用多数据源自动切换（Efinance -> Akshare -> Baostock）

# 3. 批量更新所有股票
batch_update_all_stocks(limit=10)  # 测试模式
batch_update_all_stocks()          # 全量更新

# 4. 归档退市股票
archive_stocks(["000003", "000004"])
# 移动到 data/CN_A/archive/
```

---

## 技术栈

| 组件 | 技术 |
|------|------|
| Workflow 编排 | LangGraph |
| LLM 集成 | LangChain |
| 大语言模型 | 阿里云 DashScope + GLM-5 |
| Web 后端 | FastAPI |
| 任务存储 | Workspace 文件系统（无数据库） |
| A股数据源 | 多源管理（Efinance/Akshare/Tushare/Pytdx/...） |
| CLI | argparse |

---

## 快速开始

### 1. 安装依赖

```bash
# 使用 uv（推荐）
uv sync

# 或使用 pip
pip install -e .
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env，填入 DashScope API Key
```

必需配置：
```bash
DASHSCOPE_API_KEY=your_api_key_here
```

可选配置（增强数据源）：
```bash
TUSHARE_TOKEN=your_token       # Tushare Pro（专业数据）
PYTDX_HOST=119.147.212.81      # 通达信服务器
PYTDX_PORT=7709                # 通达信端口
```

### 3. 使用方式

#### CLI 命令行

```bash
# 查看帮助
trading-agent --help

# 市场分析
trading-agent market

# 分析单个股票
trading-agent stock 000001

# 分析多个股票（持仓1万元）
trading-agent stock 000001,600000,000002 --position 10000

# 保存结果到文件
trading-agent stock 000001 -o result.json

# 启动 Web 服务
trading-agent web --port 8080

# 查看任务列表
trading-agent tasks

# 查看任务详情
trading-agent task <task_id>
```

#### Web Dashboard

```bash
# 启动服务
trading-agent web

# 访问
http://localhost:8000
```

Web 功能：
- 点击"市场分析"创建市场分析任务
- 点击"股票分析"输入股票代码和持仓金额
- 点击"查看任务"查看任务列表和执行日志
- 支持批量分析（逗号分隔多个股票代码）
- 任务详情页：Workflow 流程图、执行时间线、分析摘要

---

## 项目结构

```
trading-agent/
├── docs/                       # 文档
│   ├── PRD.md                  # 产品需求文档
│   ├── WORKPLAN.md             # 工作计划
│   └── ARCHITECTURE.md         # 系统架构
│
├── workspace/                  # 任务工作目录
│   ├── ma_20260503_abc12345/   # 市场分析任务文件夹
│   │   ├── status.json         # 任务状态
│   │   ├── logs.txt            # 执行日志
│   │   └── result.json         # 分析结果
│   └── stock_20260503_def67890/ # 股票分析任务文件夹
│
├── data/CN_A/                  # 股票数据目录
│   ├── stock_list.csv          # 5800+ 股票列表
│   ├── stock_daily/            # 5400+ 日线 CSV
│   └── archive/                # 退市股票归档
│
├── src/                        # 源代码 ⭐
│   ├── cli.py                  # 命令行入口
│   │
│   ├── core/                   # 核心模块
│   │   ├── llm.py              # LLM 集成（GLM-5）
│   │   ├── config.py           # 配置管理
│   │   └── logger.py           # 日志模块
│   │
│   ├── data_sources/           # 数据源
│   │   ├── data_adapter.py     # 统一数据接口 ⭐
│   │   ├── providers/          # 多数据源管理 ⭐
│   │   │   ├── base.py         # 基类 + 管理器
│   │   │   ├── realtime_types.py # 统一数据类型 + 熔断器
│   │   │   ├── akshare_fetcher.py  # Akshare 数据源
│   │   │   ├── efinance_fetcher.py  # Efinance 数据源
│   │   │   ├── tushare_fetcher.py   # Tushare 数据源
│   │   │   ├── pytdx_fetcher.py     # 通达信数据源
│   │   │   ├── baostock_fetcher.py  # Baostock 数据源
│   │   │   ├── yfinance_fetcher.py  # Yfinance 数据源
│   │   │   └── longbridge_fetcher.py # 长桥数据源
│   │   └ akshare_data.py       # A股数据获取（备用）
│   │   └ stock_data_manager.py # 股票数据批量更新
│   │
│   ├── agents/                 # Agent 实现
│   │   ├── base.py             # Agent 基类
│   │   │
│   │   ├── market/             # 市场分析 agents
│   │   │   ├── macro_analyzer.py     # 宏观分析
│   │   │   ├── sector_analyzer.py    # 板块分析
│   │   │   ├── industry_analyzer.py  # 行业分析
│   │   │   └ stock_screener.py       # 个股筛选
│   │   │
│   │   └── stock/              # 股票分析 agents
│   │   │   ├── init.py               # 初始化
│   │   │   ├── fundamentals.py       # 基本面
│   │   │   ├── technical.py          # 技术面
│   │   │   ├── aggregator.py         # 数据汇总
│   │   │   ├── bull_advocate.py      # 正方辩论
│   │   │   ├── bear_advocate.py      # 反方辩论
│   │   │   ├── judge.py              # 决策
│   │   │   ├── position_advisor.py   # 持仓建议
│   │   │   └ feishu_push.py          # 飞书推送
│   │
│   ├── workflows/              # LangGraph Workflows
│   │   ├── state.py            # 状态定义
│   │   ├── market_analysis.py  # 市场分析流程
│   │   └ stock_analysis.py     # 股票分析流程
│   │
│   ├── scheduler/              # 任务调度
│   │   ├── task_queue.py       # 任务队列
│   │   ├── executor.py         # 任务执行器
│   │   └ workspace_manager.py  # Workspace 管理 ⭐
│   │
│   └── web/                    # Web 界面
│   │   ├── app.py              # FastAPI 应用
│   │   ├── routes/
│   │   │   └ tasks.py          # 任务 API
│   │   └ static/
│   │   │   ├── index.html      # 主页
│   │   │   ├── style.css       # 样式（科技商务风格）
│   │   │   └ app.js            # 前端逻辑
│
├── scripts/
│   └ update_all_stocks.py      # 股票数据批量更新脚本
│
├── main.py                     # 主入口
├── pyproject.toml              # 项目配置
├── .env                        # 环境变量
└── README.md                   # 项目说明
```

---

## CLI 命令详解

### query - AI 自然语言查询（新增）

```bash
# AI 自然语言查询本地股票数据
trading-agent query "涨幅超过5%的银行股有哪些"
trading-agent query "最近一周上涨的科技股" -o result.json
trading-agent query "换手率超过20%的小盘股"
```

AI 会理解语义，查询本地数据库（data/CN_A/），返回符合条件的股票列表。

### tpl - 模板快速查询（新增）

```bash
# 查询涨停股
trading-agent tpl limit_up

# 查询高换手率股票（阈值15%）
trading-agent tpl high_turnover --threshold 15

# 查询涨幅榜前30名
trading-agent tpl top_gainers --n 30

# 查询大跌股（阈值-3%）
trading-agent tpl big_fall --threshold -3
```

可用模板：`limit_up`, `limit_down`, `high_turnover`, `big_rise`, `big_fall`, `top_gainers`, `top_fallers`, `top_turnover`, `top_volume`

### stats - 市场统计（新增）

```bash
trading-agent stats
```

输出：
- 总股票数
- 上涨家数/下跌家数/平盘家数
- 涨停家数/跌停家数
- 上涨占比

### templates - 查询模板列表（新增）

```bash
trading-agent templates
```

显示所有可用查询模板和参数说明。

### market - 市场分析

```bash
trading-agent market [-o output.json]
```

输出：
- 市场形势判断（牛市/熊市/震荡市）
- 热点板块 Top 5
- 推荐个股 Top 10

### stock - 股票分析

```bash
trading-agent stock <codes> [-p position] [-o output.json]
```

参数：
- `codes`: 股票代码，多个用逗号分隔（如 `000001,600000`）
- `-p/--position`: 当前持仓金额（人民币）
- `-o/--output`: 保存结果到 JSON 文件

输出：
- 基本面评分和分析
- 技术面评分和信号
- 辩论过程（正方 vs 反方）
- 最终决策（buy/sell/hold）
- 持仓建议（操作、金额、风险提示）

### web - Web 服务

```bash
trading-agent web [--host host] [--port port]
```

默认：`http://127.0.0.1:8000`

### tasks - 任务列表

```bash
trading-agent tasks
```

从 workspace 目录读取任务列表，显示最近 20 个任务。

### task - 任务详情

```bash
trading-agent task <task_id>
```

显示任务完整信息、Workflow 步骤、分析结果和执行日志。

### update - 更新股票数据

```bash
# 更新单个或多个股票
trading-agent update --codes 600036 000001 000002

# 更新所有股票（慎用，耗时约 30 分钟）
trading-agent update --all --batch-size 100 --delay 1.0

# 指定截止日期
trading-agent update --codes 600036 --end-date 20260503
```

参数：
- `--all`: 更新所有 5495 个股票
- `--codes`: 指定股票代码列表
- `--end-date`: 截止日期（默认今天）
- `--batch-size`: 每批次数量（控制请求速度）
- `--delay`: 批次间隔秒数（避免请求过快）

---

## API 接口

### AI 自然语言查询（新增）

```bash
POST /api/chat/ai-query
Content-Type: application/json

{
  "query": "涨幅超过5%的银行股有哪些"
}
```

返回：
```json
{
  "success": true,
  "query": "涨幅超过5%的银行股有哪些",
  "intent": {
    "explanation": "用户想查询涨幅超过5%的银行股",
    "conditions": [...]
  },
  "data": {
    "stocks": [...],
    "count": 10
  },
  "response": "找到10只符合条件的银行股..."
}
```

### 模板查询

```bash
GET /api/chat/templates          # 模板列表
GET /api/chat/limit-up           # 涨停股
GET /api/chat/high-turnover?threshold=10  # 高换手率
GET /api/chat/market-stats       # 市场统计
GET /api/chat/sector-rankings    # 板块榜
```

### 数据词典（新增）

```bash
GET /api/catalog/data-sources    # 数据源列表
GET /api/catalog/data-types      # 数据类型列表
GET /api/catalog/fields/实时行情  # 字段说明
GET /api/catalog/sample/实时行情  # 数据样例
```

### 创建市场分析任务

```bash
POST /api/tasks
Content-Type: application/json

{
  "task_type": "market_analysis"
}
```

### 创建股票分析任务

**新格式（每只股票独立持仓）**：
```bash
POST /api/tasks
Content-Type: application/json

{
  "task_type": "stock_analysis",
  "stocks": [
    {"code": "000001", "position": 5000},
    {"code": "600036", "position": 10000},
    {"code": "300750", "position": 0}
  ]
}
```

### 获取股票名称

```bash
GET /api/stocks/{code}/name
```

返回：
```json
{"code": "600036", "name": "招商银行"}
```

### 查看任务列表

```bash
GET /api/tasks
```

从 workspace 目录读取，返回所有任务。

### 查看任务详情

```bash
GET /api/tasks/{task_id}
```

返回：
```json
{
  "task_id": "abc12345",
  "task_type": "market_analysis",
  "status": "completed",
  "workflow_steps": [
    {"name": "macro_analyzer", "started_at": "...", "completed_at": "..."}
  ],
  "summary": {...},
  "logs": ["[2026-05-03 18:10:41] 任务开始...", ...]
}
```

### 删除任务

```bash
DELETE /api/tasks/{task_id}
```

---

## Workflow 流程

### 市场分析流程

```
┌─────────────────┐
│ 宏观分析        │ → 判断牛市/熊市/震荡市
└────────┬────────┘
         ↓
┌─────────────────┐
│ 板块分析        │ → 识别热点板块 Top 5
└────────┬────────┘
         ↓
┌─────────────────┐
│ 行业分析        │ → 分析行业增长潜力
└────────┬────────┘
         ↓
┌─────────────────┐
│ 个股筛选        │ → 筛选潜力个股 Top 10
└─────────────────┘
```

### 股票分析流程（9 个节点）

```
┌─────────────────┐     ┌─────────────────┐
│ 初始化检测      │     │ 数据汇总        │
│ (InitAgent)     │     │ (Aggregator)    │
└────────┬────────┘     └────────┬────────┘
         │                       │
         ↓                       ↓
┌─────────────────┐     ┌─────────────────┐
│ 基本面分析      │     │ 技术面分析      │
└────────┬────────┘     └────────┬────────┘
         │                       │
         └───────────┬───────────┘
                     ↓
              ┌─────────────┐
              │  正方辩论   │ ← 买入理由
              └──────┬──────┘
                     ↓
              ┌─────────────┐
              │  反方辩论   │ ← 卖出理由
              └──────┬──────┘
                     │
         ┌───────────┴───────────┐
         │   继续辩论？          │
         │   (最多 10 轮)        │
         └───────────┬───────────┘
                     ↓
              ┌─────────────┐
              │   Judge     │ → 综合决策 + 归因分析
              └──────┬──────┘
                     ↓
              ┌─────────────┐
              │ 持仓建议    │ → 操作建议
              └──────┬──────┘
                     ↓
              ┌─────────────┐
              │ 飞书推送    │ → 发送分析结果
              └─────────────┘
```

---

## 注意事项

### 1. 投资风险提示

⚠️ **重要**: 本系统仅供参考，不构成投资建议。投资决策需自行判断，风险自负。

### 2. API 成本

- 股票分析辩论最多 10 轮，会产生较多 LLM API 调用成本
- 建议先测试单个股票，确认成本后再批量分析

### 3. 数据准确性

- 数据源多源切换，可靠性较高
- 但仍可能存在延迟或错误，请以实际行情为准

### 4. 执行时间

- 市场分析：约 1-2 分钟
- 单个股票分析：约 2-3 分钟（10 轮辩论）
- 批量分析：取决于股票数量

---

## 环境变量

| 变量 | 说明 | 必需 |
|------|------|------|
| `DASHSCOPE_API_KEY` | 阿里云 DashScope API Key | ✅ |
| `DASHSCOPE_BASE_URL` | API 地址 | ❌ (有默认值) |
| `DASHSCOPE_MODEL` | 模型名称 | ❌ (默认 glm-5) |
| `LOG_LEVEL` | 日志级别 | ❌ (默认 INFO) |
| `LOG_DIR` | 日志目录 | ❌ (默认 logs) |
| `TUSHARE_TOKEN` | Tushare Pro Token | ❌ |
| `PYTDX_HOST` | 通达信服务器地址 | ❌ |
| `PYTDX_PORT` | 通达信端口 | ❌ |

---

## 开发

### 运行测试

```bash
# 运行全部测试
uv run pytest tests/ -v

# 运行带覆盖率报告
uv run pytest tests/ -v --cov=src --cov-report=term-missing

# 运行单个测试文件
uv run pytest tests/test_query.py -v

# 测试统计：68 用例，62 通过，3 失败，3 跳过
```

详见 [测试文档](docs/TESTING.md)

### 类型检查

```bash
mypy src/
```

### 代码格式化

```bash
black src/
ruff check src/
```

### 项目结构

```
src/
├── cli.py              # CLI 命令入口
├── core/               # 核心模块（config, logger, llm）
├── data_sources/       # 数据源管理
│   ├── fetcher.py      # 统一数据获取入口
│   ├── providers/      # 多数据源实现
│   └── trade_daily.py  # 日线数据
├── query/              # 查询模块（新增）
│   ├── engine.py       # QueryEngine
│   ├── templates.py    # 查询模板
│   └── ai_query.py     # AI 自然语言查询
├── agents/             # LangGraph Agents
├── workflows/          # Workflows
├── web/                # Web 界面
│   ├── routes/
│   │   ├── chat.py     # 智能查询 API
│   │   └── catalog.py  # 数据词典 API
│   └── static/
│       ├── chat.html   # 智能查询页面
│       └── catalog.html # 数据词典页面
└── scheduler/          # 任务调度

tests/
├── conftest.py         # pytest 配置
├── test_core.py        # 核心模块测试
├── test_query.py       # 查询模块测试
├── test_data_sources.py # 数据源测试
├── test_web.py         # Web 路由测试
└── test_cli.py         # CLI 测试
```

---

## 许可证

MIT License

---

## 贡献

欢迎提交 Issue 和 Pull Request。

---

## 更新日志

### v0.3.0 (2026-05-04)

- **新增 AI 智能查询**：自然语言查询本地股票数据
- **新增数据词典**：数据源、数据类型、字段说明展示
- **新增 CLI 命令**：`query`, `tpl`, `stats`, `templates`
- **新增测试套件**：68 测试用例，覆盖率 18%
- **修复返回按钮样式**：蓝紫渐变按钮
- **夜间数据补全脚本**：批量补全行业、基本面、标签数据

### v0.2.0 (2026-05-03)

- 重构任务管理：移除 SQLite，改用 Workspace 文件系统
- 任务详情页：Workflow 流程图可视化
- 新增 InitAgent、Aggregator、FeishuPush agents
- Judge 增强：归因分析、反事实推断
- 集成数据源管理系统

### v0.1.0 (2026-05-03)

- 实现市场分析 Workflow
- 实现股票分析 Workflow（含辩论机制）
- CLI 命令行工具
- Web Dashboard
- 阿里云 DashScope + GLM-5 集成