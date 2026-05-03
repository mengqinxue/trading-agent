# Trading Agent - 系统架构设计

> Version: 2.0
> Date: 2026-05-03
> Status: Complete

---

## 1. 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        Web Dashboard                             │
│  (FastAPI + HTML/CSS/JS)                                        │
│  - 任务列表 / 创建 / 详情                                         │
│  - 日志实时查看                                                   │
│  - Workflow 解释页面                                              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Task Scheduler                              │
│  - 任务队列管理                                                  │
│  - Workspace 日志记录                                            │
│  - 执行调度                                                      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   LangGraph Workflows                            │
│                                                                  │
│  ┌──────────────────┐      ┌──────────────────────┐            │
│  │ Market Analysis  │      │   Stock Analysis      │            │
│  │   Workflow       │      │     Workflow          │            │
│  │                  │      │                       │            │
│  │ 4节点线性流程     │      │ 9节点含辩论循环        │            │
│  └──────────────────┘      └──────────────────────┘            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Agents                                    │
│                                                                  │
│  市场分析：                                                       │
│  - MarketMacroAnalyzer                                          │
│  - SectorAnalyzer                                               │
│  - IndustryAnalyzer                                             │
│  - StockScreener                                                │
│                                                                  │
│  股票分析：                                                       │
│  - InitAgent (系统检测/持仓加载)                                  │
│  - FundamentalsAnalyzer                                         │
│  - TechnicalAnalyzer                                            │
│  - DataAggregator (技术+基本面汇总)                               │
│  - BullAdvocate (买方辩论)                                       │
│  - BearAdvocate (卖方辩论)                                       │
│  - Judge (决策+归因+反事实)                                       │
│  - PositionAdvisor                                              │
│  - FeishuPush (飞书推送)                                         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Core Services                               │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   LLM API    │  │ Data Source  │  │   Storage    │          │
│  │ (DashScope   │  │  (Akshare)   │  │  (SQLite +   │          │
│  │  + GLM-5)    │  │              │  │   Workspace) │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐                             │
│  │ TrendRadar   │  │   Feishu     │                             │
│  │ MCP (热点)    │  │  Webhook     │                             │
│  └──────────────┘  └──────────────┘                             │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. 股票分析 Workflow（完整 9 节点）

```
┌──────────────┐
│  初始化节点   │
│  (init)      │
│              │
│ - 系统检测    │
│ - 参数加载    │
│ - 状态初始化  │
│ - 持仓加载    │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  基本面分析   │
│(fundamentals)│
│              │
│ - 财务数据    │
│ - 行业地位    │
│ - 风险评估    │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  技术面分析   │
│ (technical)  │
│              │
│ - K线形态    │
│ - 技术指标    │
│ - 成交量     │
│ - 资金流     │
└──────┬───────┘
       │
       ▼
┌─────────────────────────────────────────────┐
│              汇总节点 (aggregator)            │
│                                             │
│ - 合并技术面 + 基本面分析结果                  │
│ - 计算综合评分                                │
│ - 提取关键论据                                │
│ - 生成分析报告                                │
└──────────────────────┬──────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────┐
│              辩论节点 (debater)               │
│                                             │
│  ┌─────────────┐    ┌─────────────┐         │
│  │  买入方     │ VS │  卖出方     │          │
│  │  (bull)     │    │  (bear)     │          │
│  └─────────────┘    └─────────────┘         │
│                                             │
│  辩论机制:                                   │
│  - Round 1-N: 双方陈述观点、反驳              │
│  - 提前终止: 5轮无新论据                      │
│  - 最大轮数: 10轮                             │
│  - 辩论评分: 论据质量评分                     │
│                                             │
│  输出:                                       │
│  - debate_log: 辩论记录                      │
│  - bull_score: 买入方得分                   │
│  - bear_score: 卖出方得分                  │
│  - consensus: 是否达成共识                   │
└──────────────────────┬──────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────┐
│              决策节点 (judge)                 │
│                                             │
│ - 综合分析结果                                │
│ - 结合辩论得分                                │
│ - 评估风险收益比                              │
│                                             │
│ 归因分析 (Causal Chain):                     │
│ - 解释买入/卖出的因果链                       │
│ - A→B→C→D→E 形式                             │
│                                             │
│ 反事实推断 (Counterfactual):                  │
│ - 假设下跌场景分析                            │
│ - 最坏情况评估                                │
│ - 退出策略                                    │
│                                             │
│ 输出:                                        │
│ - action: buy/sell/hold                     │
│ - confidence: 决策置信度                     │
│ - reasoning: 决策理由                        │
│ - causal_chain: 归因链                       │
│ - counterfactual: 反事实分析                 │
│ - should_enter: 是否建议入场                 │
└──────────────────────┬──────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────┐
│              持仓建议节点 (position_advisor)  │
│                                             │
│ 输入:                                        │
│ - 决策结果                                    │
│ - 当前持仓状态                                │
│                                             │
│ 判断逻辑:                                     │
│ ┌─────────────────────────────────────────┐ │
│ │ 已持有该股票?                            │ │
│ │   YES → 加仓/减仓/清仓建议               │ │
│ │   NO  → 新买入建议                       │ │
│ └─────────────────────────────────────────┘ │
│                                             │
│ 输出:                                        │
│ - position_action: new_buy/add/reduce/clear │
│ - suggested_amount: 建议仓位                │
│ - stop_loss: 止损位                         │
│ - take_profit: 止盈位                       │
└──────────────────────┬──────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────┐
│              推送节点 (push)                  │
│                                             │
│ - 格式化决策报告                              │
│ - 推送飞书 Webhook                            │
│ - 记录决策日志                                │
│ - 保存到 Workspace                           │
└─────────────────────────────────────────────┘
```

---

## 3. 归因分析 (Causal Chain Attribution)

Judge Agent 输出包含完整的因果链，解释为什么做出这个决策。

### 3.1 归因链格式

```
A(热点板块炒作) → B(龙头股关注度提升) → C(技术面突破信号) → D(基本面支撑) → E(买入建议)

每一步都要有数据/论据支撑：
- A: TrendRadar 热度数据 / 板块涨幅
- B: 龙虎榜/资金流数据
- C: akshare K线数据 / 技术指标
- D: akshare 财务数据
- E: 综合评分 + 辩论结果
```

### 3.2 归因实现

```python
class CausalChain:
    """因果链归因"""
    
    def build_chain(self, analysis_summary, debate_log) -> list:
        """构建因果链"""
        chain = []
        
        # Step A: 热点识别
        if analysis_summary.get("hot_sector"):
            chain.append({
                "step": "A",
                "description": f"热点板块：{analysis_summary['hot_sector']}",
                "evidence": analysis_summary.get("sector_heat_score"),
                "source": "TrendRadar MCP"
            })
        
        # Step B: 关注度提升
        if analysis_summary.get("fund_flow_in"):
            chain.append({
                "step": "B",
                "description": "资金流入，关注度提升",
                "evidence": analysis_summary.get("fund_flow_amount"),
                "source": "akshare资金流"
            })
        
        # Step C: 技术面信号
        tech_signals = analysis_summary.get("tech_signals", [])
        if tech_signals:
            chain.append({
                "step": "C",
                "description": f"技术面信号：{tech_signals}",
                "evidence": analysis_summary.get("tech_score"),
                "source": "akshare K线"
            })
        
        # Step D: 基本面支撑
        if analysis_summary.get("fund_score") > 60:
            chain.append({
                "step": "D",
                "description": f"基本面评分：{analysis_summary['fund_score']}",
                "evidence": analysis_summary.get("fundamentals"),
                "source": "akshare财务"
            })
        
        # Step E: 最终决策
        chain.append({
            "step": "E",
            "description": f"决策：{analysis_summary['final_action']}",
            "evidence": {
                "bull_score": debate_log.get("bull_score"),
                "bear_score": debate_log.get("bear_score")
            },
            "source": "辩论+决策"
        })
        
        return chain
```

---

## 4. 反事实推断 (Counterfactual Analysis)

Judge Agent 输出包含反事实推断，分析假设下跌场景的影响。

### 4.1 反事实推断格式

```python
class CounterfactualAnalysis:
    """反事实推断"""
    
    def analyze(self, stock_code, current_price, position) -> dict:
        """分析下跌场景"""
        scenarios = []
        
        # 场景1：下跌5%
        scenarios.append({
            "scenario": "下跌5%",
            "price": current_price * 0.95,
            "impact": f"持仓市值减少 {position * 0.05} 元",
            "expectation": "短期波动，可能回调",
            "suggestion": "观望，等待企稳"
        })
        
        # 场景2：下跌10%
        scenarios.append({
            "scenario": "下跌10%",
            "price": current_price * 0.90,
            "impact": f"触发止损线",
            "expectation": "技术面可能破位",
            "suggestion": "减仓50%，保留观察仓位"
        })
        
        # 场景3：下跌20%
        scenarios.append({
            "scenario": "下跌20%",
            "price": current_price * 0.80,
            "impact": "严重亏损，基本面可能有问题",
            "expectation": "需要重新评估",
            "suggestion": "清仓止损，等待新信号"
        })
        
        return {
            "scenarios": scenarios,
            "worst_case": scenarios[-1],
            "probability_estimate": self._estimate_probability(),
            "exit_strategy": {
                "stop_loss": current_price * 0.90,
                "take_profit": current_price * 1.20,
                "risk_level": "medium"
            }
        }
```

---

## 5. 辩论评分机制

### 5.1 评分规则

```python
SCORING_RULES = {
    "data_evidence": 10,      # 有数据支撑的论据
    "logical_argument": 8,    # 逻辑清晰的论据
    "counter_rebuttal": 6,    # 有效反驳对方
    "new_insight": 5,         # 提出新观点
    "weak_argument": -3,      # 论据薄弱
    "contradiction": -5,      # 自相矛盾
}
```

### 5.2 提前终止条件

```python
TERMINATION_CONDITIONS = {
    "max_rounds": 10,           # 最大轮数
    "no_new_args_rounds": 5,    # 连续5轮无新论据
    "consensus_threshold": 0.8, # 双方得分差距 < 20%
}
```

---

## 6. TrendRadar MCP 集成

### 6.1 MCP Client

```python
class TrendRadarMCPClient:
    """TrendRadar MCP 客户端"""
    
    def __init__(self, mcp_server_path: str):
        self.mcp_server_path = Path(mcp_server_path)
    
    def get_hot_news(self, date: str = None) -> list:
        """获取热点新闻"""
        # 通过 MCP 协议调用
        # 或直接读取 TrendRadar 输出的 JSON 文件
        news_path = self.mcp_server_path.parent / "data" / "daily" / f"{date}.json"
        if news_path.exists():
            return json.loads(news_path.read_text())
        return []
    
    def get_hot_sectors(self, news: list) -> list:
        """从新闻中提取热点板块"""
        # 使用 LLM 分析新闻标题
        # 提取高频板块关键词
        # 计算热度评分
        pass
```

### 6.2 Screener Agent

```python
class ScreenerAgent(BaseAgent):
    """热点发现 & 粗筛"""
    
    def __init__(self, llm, trendradar_mcp, stock_db):
        self.llm = llm
        self.trendradar = trendradar_mcp
        self.stock_db = stock_db
    
    def run(self, context: dict) -> dict:
        # 1. 获取热点新闻
        news = self.trendradar.get_hot_news()
        
        # 2. AI 分析热点板块
        sectors = self.analyze_hot_sectors(news)
        
        # 3. 识别炒作龙头
        leaders = self.identify_hype_leaders(sectors)
        
        # 4. 结合持仓关键词过滤
        filtered = self.filter_by_keywords(leaders, context.get("portfolio"))
        
        return {
            "hot_sectors": sectors,
            "candidate_stocks": filtered
        }
```

---

## 7. 飞书推送集成

### 7.1 Feishu Webhook

```python
class FeishuPush:
    """飞书推送"""
    
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
    
    def send_decision_report(self, decision: dict, position: dict) -> bool:
        """推送决策报告"""
        message = self._format_message(decision, position)
        
        response = httpx.post(
            self.webhook_url,
            json={
                "msg_type": "interactive",
                "card": message
            }
        )
        
        return response.status_code == 200
    
    def _format_message(self, decision, position) -> dict:
        """格式化飞书卡片消息"""
        return {
            "header": {
                "title": {
                    "content": f"股票分析报告：{decision['stock_name']}",
                    "tag": "plain_text"
                }
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "content": f"**决策**: {decision['action']}\n**置信度**: {decision['confidence']}\n**建议仓位**: {position['suggested_amount']}",
                        "tag": "lark_md"
                    }
                },
                {
                    "tag": "div",
                    "text": {
                        "content": f"**决策理由**:\n{decision['reasoning']}",
                        "tag": "lark_md"
                    }
                },
                {
                    "tag": "div",
                    "text": {
                        "content": f"**止损位**: {position['stop_loss']}\n**止盈位**: {position['take_profit']}",
                        "tag": "lark_md"
                    }
                }
            ]
        }
```

---

## 8. 目录结构

```
trading-agent/
├── docs/
│   ├── PRD.md                      # 产品需求文档
│   ├── ARCHITECTURE.md             # 架构设计（本文档）
│   ├── WORKPLAN.md                 # 工作计划
│   └── akshare-guide.md            # Akshare API 指南
│
├── src/trading_agent/
│   ├── core/
│   │   ├── llm.py                  # LLM 接口
│   │   ├── config.py               # 配置管理
│   │   └── logger.py               # 日志
│   │
│   ├── data_sources/
│   │   ├── akshare_data.py         # A股数据
│   │   ├── trendradar.py           # TrendRadar MCP
│   │   └── stock_daily_updater.py  # CSV 数据更新
│   │
│   ├── agents/
│   │   ├── base.py                 # Agent 基类
│   │   │
│   │   ├── market/
│   │   │   ├── macro_analyzer.py
│   │   │   ├── sector_analyzer.py
│   │   │   ├── industry_analyzer.py
│   │   │   └── stock_screener.py
│   │   │
│   │   └── stock/
│   │   │   ├── init.py             # 初始化 Agent
│   │   │   ├── fundamentals.py
│   │   │   ├── technical.py
│   │   │   ├── aggregator.py       # 数据汇总 Agent
│   │   │   ├── bull_advocate.py
│   │   │   ├── bear_advocate.py
│   │   │   ├── judge.py            # 含归因+反事实
│   │   │   ├── position_advisor.py
│   │   │   └── feishu_push.py      # 飞书推送
│   │
│   ├── workflows/
│   │   ├── state.py
│   │   ├── market_analysis.py
│   │   └── stock_analysis.py
│   │
│   ├── scheduler/
│   │   ├── executor.py
│   │   ├── task_queue.py
│   │   └── workspace_manager.py
│   │
│   └── web/
│   │   ├── app.py
│   │   ├── routes/
│   │   └── static/
│
├── data/
│   └── CN_A/stock_daily/           # CSV 日线数据
│
├── workspace/                      # 任务日志
│   ├── ma_YYYYMMDD_HHMMSS_id/
│   └── stock_YYYYMMDD_HHMMSS_id/
│
├── main.py
├── pyproject.toml
└── README.md
```

---

## 9. 状态定义

```python
class StockAnalysisState(TypedDict):
    # 初始化
    run_id: str
    system_status: dict
    portfolio: dict
    
    # 基本面
    fundamentals: dict
    
    # 技术面
    technical: dict
    
    # 汇总
    analysis_summary: dict
    
    # 辩论
    bull_arguments: list[str]
    bear_arguments: list[str]
    debate_rounds: int
    debate_history: list[str]
    bull_score: float
    bear_score: float
    
    # 决策 (含归因+反事实)
    final_decision: dict
    causal_chain: list[dict]
    counterfactual: dict
    
    # 持仓建议
    suggested_action: str
    suggested_amount: float
    stop_loss: float
    take_profit: float
    
    # 推送
    push_result: dict
    
    # 元数据
    logs: list[str]
    error: Optional[str]
```

---

## 10. 部署方案

### 10.1 本地运行

```bash
# 安装依赖
uv sync

# 配置环境变量
cp .env.example .env

# 启动 Web 服务
trading-agent web

# 运行股票分析
trading-agent stock 600036 --position 10000

# 运行市场分析
trading-agent market

# 更新日线数据
trading-agent update 600036
```

### 10.2 环境变量

```bash
# .env
DASHSCOPE_API_KEY=xxx
FEISHU_WEBHOOK=https://open.feishu.cn/open-apis/bot/v2/hook/xxx
TRENDARAR_MCP_PATH=~/Documents/workspace/TrendRadar/mcp_server
```

---

## 11. 扩展设计

### 11.1 易于添加新 Agent
- 继承 BaseAgent
- 实现 run(context) 方法
- 在 workflow 中添加节点和边

### 11.2 易于添加新数据源
- 实现统一接口
- 在 config 中配置

### 11.3 易于切换 LLM
- config 中设置 provider
- 无需修改代码

---

## 下一步行动

1. 实现 aggregator.py 汇总节点
2. 增强 judge.py 添加归因和反事实
3. 实现 trendradar.py MCP 客户端
4. 实现 feishu_push.py 推送
5. 更新 stock_analysis.py workflow 连接新节点