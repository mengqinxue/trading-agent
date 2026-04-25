# 投资助手 - 架构设计文档

> Generated on 2026-04-25
> Status: DRAFT

---

## 系统架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                        投资助手系统                              │
│                    (LangGraph Workflow Engine)                   │
└─────────────────────────────────────────────────────────────────┘

        ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
        │   数据层     │     │   Agent层    │     │   输出层     │
        └──────────────┘     └──────────────┘     └──────────────┘

┌──────────────────────────────────────────────────────────────────┐
│                         数据层 (Data Layer)                       │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │ TrendRadar  │  │   akshare   │  │  stock_db   │              │
│  │ MCP Server  │  │  行情数据    │  │  股票数据库  │              │
│  │ (新闻热点)   │  │  (K线/指标)  │  │  (5500+只)  │              │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘              │
│         │                │                │                      │
│         └────────────────┴────────────────┘                      │
│                          ↓                                       │
│              ┌─────────────────────┐                            │
│              │    Data Aggregator  │                            │
│              │    (数据聚合层)      │                            │
│              └─────────────────────┘                            │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│                       Agent层 (Agent Layer)                       │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                  LangGraph Workflow                         ││
│  ├─────────────────────────────────────────────────────────────┤│
│  │                                                             ││
│  │  [screener] → [data_analyst] ──┬──→ [debater] → [judge]    ││
│  │                   ↑            │                             ││
│  │            [due_diligence] ────┘                             ││
│  │                                                             ││
│  │  State: InvestmentState                                     ││
│  │  - candidate_stocks: list                                   ││
│  │  - hot_sectors: list                                        ││
│  │  - data_analysis: AnalysisResult                            ││
│  │  - due_diligence: AnalysisResult                            ││
│  │  - debate_rounds: list                                      ││
│  │  - judge_decision: Decision                                 ││
│  │                                                             ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │  Screener   │  │ DataAnalyst │  │ DueDiligence│              │
│  │  Agent      │  │  Agent      │  │   Agent     │              │
│  │  (粗筛)     │  │  (技术面)    │  │  (基本面)   │              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
│                                                                   │
│  ┌─────────────┐  ┌─────────────┐                                │
│  │  Debater    │  │   Judge     │                                │
│  │  Agent      │  │   Agent     │                                │
│  │  (博弈辩论)  │  │  (评委决策)  │                                │
│  └─────────────┘  └─────────────┘                                │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│                       输出层 (Output Layer)                       │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │   Dashboard │  │  Feishu     │  │   Email     │              │
│  │   (Web UI)  │  │  Push       │  │   Push      │              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
│                                                                   │
│  ┌─────────────┐  ┌─────────────┐                                │
│  │  Decision   │  │   History   │                                │
│  │   Log       │  │   Records   │                                │
│  └─────────────┘  └─────────────┘                                │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘
```

---

## 核心组件设计

### 1. LangGraph Workflow

```python
from langgraph.graph import StateGraph, END
from typing import TypedDict, List

# 状态定义
class InvestmentState(TypedDict):
    candidate_stocks: List[Stock]      # 原始候选池
    portfolio: Portfolio               # 当前持仓
    hot_sectors: List[Sector]          # 热点板块
    filtered_stocks: List[Stock]       # 过滤后股票
    data_analysis: AnalysisResult      # 技术面分析
    due_diligence: AnalysisResult      # 尽调分析
    debate_rounds: List[DebateRound]   # 辩论记录
    debate_summary: str                # 辩论摘要
    judge_decision: Decision           # 最终决策

# 构建工作流
workflow = StateGraph(InvestmentState)

# 添加节点
workflow.add_node("screener", screener_node)
workflow.add_node("data_analyst", data_analyst_node)
workflow.add_node("due_diligence", due_diligence_node)
workflow.add_node("debater", debater_node)
workflow.add_node("judge", judge_node)

# 添加边
workflow.add_edge("screener", "data_analyst")
workflow.add_edge("screener", "due_diligence")
workflow.add_edge("data_analyst", "debater")
workflow.add_edge("due_diligence", "debater")
workflow.add_edge("debater", "judge")
workflow.add_edge("judge", END)

# 编译
app = workflow.compile()
```

### 2. Agent 设计

#### Screener Agent (粗筛)

```python
class ScreenerAgent:
    """热点发现 & 粗筛"""
    
    def __init__(self, trendradar_mcp, stock_db):
        self.trendradar = trendradar_mcp
        self.stock_db = stock_db
    
    def run(self, state: InvestmentState) -> InvestmentState:
        # 1. 获取热点新闻
        news = self.trendradar.get_hot_news()
        
        # 2. AI 分析热点板块
        sectors = self.analyze_hot_sectors(news)
        
        # 3. 识别炒作龙头
        leaders = self.identify_hype_leaders(sectors)
        
        # 4. 结合持仓关键词过滤
        filtered = self.filter_by_keywords(leaders, state["portfolio"])
        
        state["hot_sectors"] = sectors
        state["filtered_stocks"] = filtered
        return state
```

#### Data Analyst Agent (技术面)

```python
class DataAnalystAgent:
    """技术面分析"""
    
    def __init__(self, akshare_client):
        self.akshare = akshare_client
    
    def run(self, state: InvestmentState) -> InvestmentState:
        stocks = state["filtered_stocks"]
        results = []
        
        for stock in stocks:
            # 获取行情数据
            quote = self.akshare.get_quote(stock.code)
            kline = self.akshare.get_kline(stock.code, period="day")
            
            # 分析
            analysis = {
                "stock": stock,
                "trend": self.analyze_trend(kline),
                "volume": self.analyze_volume(kline),
                "indicators": self.calculate_indicators(kline),
                "support_resistance": self.find_levels(kline),
                "recommendation": self.make_recommendation(quote, kline),
                "confidence": self.calculate_confidence(quote, kline),
                "arguments": self.build_arguments(quote, kline)
            }
            results.append(analysis)
        
        state["data_analysis"] = results
        return state
```

#### Debater Agent (博弈辩论)

```python
class DebaterAgent:
    """博弈辩论引擎"""
    
    def __init__(self, llm_buyer, llm_seller, rounds=100):
        self.buyer = llm_buyer   # 买入方 agent
        self.seller = llm_seller # 卖出方 agent
        self.rounds = rounds
    
    def run(self, state: InvestmentState) -> InvestmentState:
        data_analysis = state["data_analysis"]
        due_diligence = state["due_diligence"]
        
        debate_rounds = []
        
        for round in range(self.rounds):
            # 买入方发言
            buyer_msg = self.buyer.argue(
                data_analysis, due_diligence, 
                previous_rounds=debate_rounds,
                side="buy"
            )
            
            # 卖出方反驳
            seller_msg = self.seller.argue(
                data_analysis, due_diligence,
                previous_rounds=debate_rounds,
                side="sell"
            )
            
            debate_rounds.append({
                "round": round + 1,
                "buyer": buyer_msg,
                "seller": seller_msg
            })
            
            # 检查是否收敛到共识
            if self.check_consensus(buyer_msg, seller_msg):
                break
        
        state["debate_rounds"] = debate_rounds
        state["debate_summary"] = self.summarize(debate_rounds)
        return state
```

---

## 数据流

```
TrendRadar MCP                akshare API
      │                            │
      ↓                            ↓
  热点新闻                      行情数据
      │                            │
      └──────────┬─────────────────┘
                 ↓
           Data Aggregator
                 ↓
           Screener Agent
                 ↓
         candidate_stocks
                 ↓
     ┌───────────┴───────────┐
     ↓                       ↓
DataAnalyst            DueDiligence
     ↓                       ↓
     └───────────┬───────────┘
                 ↓
            Debater Agent
                 ↓
          debate_summary
                 ↓
            Judge Agent
                 ↓
          final_decision
                 ↓
     ┌───────────┴───────────┐
     ↓                       ↓
  Dashboard              Feishu Push
```

---

## 技术选型

| 组件 | 技术方案 | 说明 |
|------|---------|------|
| Workflow Engine | LangGraph | deer-flow 已有成熟实现 |
| 数据源 - 新闻 | TrendRadar MCP | 已有，直接复用 |
| 数据源 - 行情 | akshare | 已有，直接复用 |
| 数据源 - 股票库 | stock_db | 已有，直接复用 |
| LLM | 火山引擎方舟 / GLM-5 | 用户想尝试 Doubao |
| Dashboard | FastAPI + React | 复用现有 stock/dashboard |
| Push | 飞书机器人 | 已有 TrendRadar 推送能力 |

---

## 项目融合方案

| 现有组件 | 复用方式 |
|---------|---------|
| stock/stock_db/ | 直接复用 |
| stock/portfolio/ | 直接复用 |
| stock/data_sources/ | 直接复用 |
| stock/dashboard/ | 扩展为决策 Dashboard |
| TrendRadar MCP | 作为 Screener 数据源 |
| deer-flow LangGraph | 参考架构（但删除 deer-flow 项目） |

---

## 部署架构

```
┌─────────────────────────────────────────┐
│              本地运行环境                │
├─────────────────────────────────────────┤
│                                         │
│  ┌─────────────┐    ┌─────────────┐    │
│  │ LangGraph   │    │  Dashboard  │    │
│  │ Server      │    │  Server     │    │
│  │ (localhost) │    │ (localhost) │    │
│  └─────────────┘    └─────────────┘    │
│                                         │
│  ┌─────────────────────────────────┐   │
│  │         Cron Scheduler          │   │
│  │   (盘前9:00 / 盘后15:30)        │   │
│  └─────────────────────────────────┘   │
│                                         │
└─────────────────────────────────────────┘

外部依赖：
- TrendRadar MCP Server (localhost)
- 飞书机器人 Webhook
- 火山引擎方舟 API / GLM API
```

---

## 下一步

1. 确认删除 deer-flow 项目
2. 搭建项目骨架：`stock-investigator/`
3. 实现 LangGraph workflow 骨架
4. 实现 Screener Agent（TrendRadar 集成）