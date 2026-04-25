# 投资助手 - 技术设计文档

> Generated on 2026-04-25
> Status: DRAFT

---

## 项目结构

```
stock-investigator/          (新项目根目录)
├── pyproject.toml           # 项目配置 (uv)
├── README.md                # 项目说明
├── .env                     # 环境变量 (API keys)
│
├── config/
│   ├── settings.yaml        # 全局配置
│   ├── portfolio.yaml       # 持仓配置 (复用现有)
│   └── keywords.yaml        # 关注关键词
│
├── data/
│   ├── stock_db/            # 复用 stock/stock_db
│   │   ├── database.py
│   │   ├── updater.py
│   │   └── stocks.json
│   ├── news/                # TrendRadar 新闻缓存
│   │   └── daily/
│   └── decisions/           # 决策记录
│   │   ├── 2026-04-25.json
│   │   └── ...
│
├── agents/
│   ├── __init__.py
│   ├── screener.py          # 粗筛 Agent
│   ├── data_analyst.py      # 技术面分析 Agent
│   ├── due_diligence.py     # 尽调分析 Agent
│   ├── debater.py           # 博弈辩论 Agent
│   └── judge.py             # 评委 Agent
│   ├── base.py              # Agent 基类
│   └── prompts/             # Agent prompt 模板
│       ├── screener.txt
│       ├── data_analyst.txt
│       ├── due_diligence.txt
│       ├── debater_buy.txt
│       ├── debater_sell.txt
│       └── judge.txt
│
├── graph/
│   ├── __init__.py
│   ├── workflow.py          # LangGraph 主工作流
│   ├── state.py             # 状态定义
│   ├── nodes.py             # 各节点逻辑
│   └── edges.py             # 边定义
│
├── integrations/
│   ├── __init__.py
│   ├── trendradar.py        # TrendRadar MCP 集成
│   ├── akshare.py           # akshare 行情数据
│   ├── feishu.py            # 飞书推送
│   └── volcengine.py        # 火山引擎方舟 API
│
├── dashboard/
│   ├── __init__.py
│   ├── server.py            # FastAPI 服务
│   ├── routes/
│   │   ├── portfolio.py
│   │   ├── decisions.py
│   │   └── stocks.py
│   ├── static/              # 前端静态文件
│   └── templates/           # HTML 模板
│
├── scheduler/
│   ├── __init__.py
│   ├── jobs.py              # 定时任务
│   └── runner.py            # 任务执行器
│
├── utils/
│   ├── __init__.py
│   ├── logger.py            # 日志
│   ├── cache.py             # 缓存
│   └── config.py            # 配置加载
│
└── main.py                  # 入口
```

---

## 核心代码实现

### 1. pyproject.toml

```toml
[project]
name = "stock-investigator"
version = "0.1.0"
description = "AI-powered stock investment decision system"
requires-python = ">=3.12"
dependencies = [
    "langgraph>=0.2.0",
    "langchain>=0.3.0",
    "langchain-openai>=0.2.0",
    "akshare>=1.12.0",
    "fastapi>=0.115.0",
    "uvicorn>=0.30.0",
    "pyyaml>=6.0",
    "pydantic>=2.0",
    "httpx>=0.27.0",
    "rich>=13.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "ruff>=0.6.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.ruff]
line-length = 100

[tool.pytest.ini_options]
testpaths = ["tests"]
```

### 2. config/settings.yaml

```yaml
# 投资助手配置

# LLM 配置
llm:
  provider: "volcengine"  # 或 "zhipu" / "openai"
  model: "doubao-pro-32k"
  api_key: "${VOLCENGINE_API_KEY}"
  base_url: "https://ark.cn-beijing.volces.com/api/v3"
  temperature: 0.7
  max_tokens: 4000

# 备用模型
fallback_models:
  - "glm-5"
  - "qwen3.5-plus"

# TrendRadar MCP
trendradar:
  mcp_server_path: "~/Documents/workspace/TrendRadar/mcp_server"
  transport: "stdio"

# 数据源
data_sources:
  akshare:
    enabled: true
    proxy: ""  # 可选代理

  stock_db:
    path: "data/stock_db/stocks.json"
    update_interval: "weekly"

# 博弈配置
debate:
  rounds: 100
  convergence_threshold: 0.8  # 达到 80% 共识时停止

# 推送配置
push:
  feishu:
    webhook: "${FEISHU_WEBHOOK}"
    enabled: true

# 定时任务
schedule:
  pre_market:
    time: "09:00"
    enabled: true

  post_market:
    time: "15:30"
    enabled: true

# Dashboard
dashboard:
  host: "localhost"
  port: 8080
```

### 3. graph/state.py

```python
from typing import TypedDict, List, Optional
from enum import Enum
from pydantic import BaseModel

class Recommendation(Enum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"

class Stock(BaseModel):
    code: str
    name: str
    market: str
    sector: Optional[str] = None

class Sector(BaseModel):
    name: str
    heat_score: float  # 热度评分
    leaders: List[str]  # 龙头股票代码
    news_count: int

class AnalysisResult(BaseModel):
    stock: Stock
    recommendation: Recommendation
    confidence: float  # 0-1
    arguments: List[str]  # 论据列表
    signals: List[str]  # 技术信号/基本面信号

class DebateRound(BaseModel):
    round: int
    buyer_argument: str
    seller_argument: str
    buyer_score: float  # 评委评分 (模拟)
    seller_score: float

class Decision(BaseModel):
    stock: Stock
    recommendation: Recommendation
    confidence: float
    position_advice: str  # 仓位建议
    reasoning: str
    debate_summary: str
    timestamp: str

class Portfolio(BaseModel):
    positions: List[dict]
    keywords: List[str]

class InvestmentState(TypedDict):
    # 输入
    candidate_stocks: List[Stock]
    portfolio: Portfolio
    
    # Step 1 输出
    hot_sectors: List[Sector]
    filtered_stocks: List[Stock]
    
    # Step 2 输出
    data_analysis: List[AnalysisResult]
    due_diligence: List[AnalysisResult]
    
    # Step 3 输出
    debate_rounds: List[DebateRound]
    debate_summary: str
    
    # Step 4 输出
    decisions: List[Decision]
    
    # 元数据
    run_id: str
    timestamp: str
```

### 4. graph/workflow.py

```python
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from .state import InvestmentState
from .nodes import (
    screener_node,
    data_analyst_node,
    due_diligence_node,
    debater_node,
    judge_node,
)

def build_workflow():
    """构建投资决策工作流"""
    
    workflow = StateGraph(InvestmentState)
    
    # 添加节点
    workflow.add_node("screener", screener_node)
    workflow.add_node("data_analyst", data_analyst_node)
    workflow.add_node("due_diligence", due_diligence_node)
    workflow.add_node("debater", debater_node)
    workflow.add_node("judge", judge_node)
    
    # 定义入口
    workflow.set_entry_point("screener")
    
    # 添加边 - 并行分支
    workflow.add_edge("screener", "data_analyst")
    workflow.add_edge("screener", "due_diligence")
    
    # 合并到辩论
    workflow.add_edge("data_analyst", "debater")
    workflow.add_edge("due_diligence", "debater")
    
    # 辩论到评委
    workflow.add_edge("debater", "judge")
    
    # 结束
    workflow.add_edge("judge", END)
    
    # 编译 (带内存检查点)
    checkpointer = MemorySaver()
    app = workflow.compile(checkpointer=checkpointer)
    
    return app

# 全局工作流实例
workflow_app = build_workflow()
```

### 5. agents/base.py

```python
from abc import ABC, abstractmethod
from langchain_core.language_models import BaseLanguageModel
from pathlib import Path

class BaseAgent(ABC):
    """Agent 基类"""
    
    def __init__(self, llm: BaseLanguageModel, prompt_file: str = None):
        self.llm = llm
        self.prompt_template = None
        
        if prompt_file:
            prompt_path = Path(__file__).parent / "prompts" / prompt_file
            if prompt_path.exists():
                self.prompt_template = prompt_path.read_text()
    
    @abstractmethod
    def run(self, state: dict) -> dict:
        """执行 agent 逻辑"""
        pass
    
    def _invoke_llm(self, prompt: str) -> str:
        """调用 LLM"""
        response = self.llm.invoke(prompt)
        return response.content
```

### 6. integrations/trendradar.py

```python
import subprocess
import json
from pathlib import Path

class TrendRadarMCP:
    """TrendRadar MCP 集成"""
    
    def __init__(self, mcp_server_path: str):
        self.mcp_server_path = Path(mcp_server_path)
    
    def get_hot_news(self, date: str = None, keywords: list = None) -> list:
        """获取热点新闻"""
        # 通过 MCP 调用 TrendRadar
        # 实际实现需要 MCP client library
        
        # 简化版：直接读取 TrendRadar 输出
        news_path = self.mcp_server_path.parent / "data" / "daily" / f"{date}.json"
        if news_path.exists():
            news = json.loads(news_path.read_text())
            if keywords:
                news = [n for n in news if any(k in n.get("title", "") for k in keywords)]
            return news
        return []
    
    def get_hot_sectors(self, news: list) -> list:
        """从新闻中提取热点板块"""
        # 使用 LLM 分析
        pass
```

---

## API 设计

### Dashboard API

```
GET  /api/portfolio/status       # 获取持仓状态
GET  /api/portfolio/config       # 获取持仓配置
POST /api/portfolio/position     # 新增持仓
PUT  /api/portfolio/position/:id # 更新持仓

GET  /api/decisions              # 获取决策历史
GET  /api/decisions/:date        # 获取指定日期决策
GET  /api/decisions/:id/debate   # 获取辩论详情

GET  /api/stocks/search?q=xxx    # 搜索股票
GET  /api/stocks/:code/quote     # 获取行情
GET  /api/stocks/:code/kline     # 获取 K 线

POST /api/run                    # 手动触发运行
GET  /api/run/:id/status         # 获取运行状态
```

---

## 定时任务设计

```python
# scheduler/jobs.py

from croniter import croniter
from datetime import datetime
import asyncio

class Scheduler:
    def __init__(self, workflow_app):
        self.app = workflow_app
        self.jobs = []
    
    def add_job(self, cron_expr: str, job_func):
        """添加定时任务"""
        self.jobs.append({
            "cron": cron_expr,
            "func": job_func,
        })
    
    async def run(self):
        """运行调度器"""
        while True:
            now = datetime.now()
            for job in self.jobs:
                cron = croniter(job["cron"], now)
                next_run = cron.get_next(datetime)
                
                if now >= next_run:
                    await job["func"]()
            
            await asyncio.sleep(60)  # 每分钟检查

# 配置定时任务
scheduler = Scheduler(workflow_app)

# 盘前 (每天 9:00)
scheduler.add_job("0 9 * * 1-5", pre_market_analysis)

# 盘后 (每天 15:30)
scheduler.add_job("30 15 * * 1-5", post_market_decision)
```

---

## 测试策略

```
tests/
├── agents/
│   ├── test_screener.py
│   ├── test_data_analyst.py
│   └── test_debater.py
│
├── graph/
│   ├── test_workflow.py
│   └── test_state.py
│
├── integrations/
│   ├── test_trendradar.py
│   └── test_akshare.py
│
└── fixtures/
    ├── mock_news.json
    ├── mock_quotes.json
    └── mock_portfolio.json
```

---

## 依赖关系

```
                    LangGraph
                        │
          ┌─────────────┼─────────────┐
          │             │             │
    agents/         integrations/   graph/
          │             │             │
          └─────────────┼─────────────┘
                        │
                    config/
                        │
          ┌─────────────┼─────────────┐
          │             │             │
    TrendRadar      akshare      stock_db
       MCP           API         (复用)
```

---

## 下一步行动

1. 创建项目目录结构
2. 复用 stock/stock_db 和 stock/portfolio
3. 实现 LangGraph workflow 骨架
4. 实现 Screener Agent
5. 集成 TrendRadar MCP
6. 实现 Dashboard API