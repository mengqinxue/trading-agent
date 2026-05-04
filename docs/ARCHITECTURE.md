# Trading Agent - 系统架构设计

> Version: 3.0
> Date: 2026-05-04
> Status: Complete

---

## 1. 系统架构概览

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              用户入口层                                       │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                   │
│  │   CLI        │    │  Web Dashboard│    │  Scheduler   │                   │
│  │  (main.py)   │    │  (FastAPI)    │    │  (定时任务)   │                   │
│  └──────────────┘    └──────────────┘    └──────────────┘                   │
└─────────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           LangGraph Workflow 层                              │
│                                                                              │
│  ┌──────────────────┐  ┌────────────────────┐  ┌────────────────────┐      │
│  │  Market Analysis │  │  Stock Analysis    │  │    Backtest        │      │
│  │    Workflow      │  │     Workflow       │  │     Workflow       │      │
│  │    (4 节点)       │  │    (9 节点)        │  │    (4 节点)        │      │
│  └──────────────────┘  └────────────────────┘  └────────────────────┘      │
│                                                                              │
│  状态管理: MarketAnalysisState, StockAnalysisState, BacktestState           │
└─────────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Agent 层                                        │
│                                                                              │
│  市场分析 Agents (src/agents/market/):                                       │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ MacroAnalyzer    SectorAnalyzer    IndustryAnalyzer    StockScreener   │ │
│  │ (宏观分析)        (板块分析)         (行业分析)          (个股筛选)     │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  股票分析 Agents (src/agents/stock/):                                        │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ InitAgent       FundamentalsAnalyzer  TechnicalAnalyzer                │ │
│  │ (初始化)         (基本面分析)           (技术面分析)                    │ │
│  │                                                                        │ │
│  │ DataAggregator  BullAdvocate          BearAdvocate                     │ │
│  │ (数据汇总)       (正方辩论)             (反方辩论)                      │ │
│  │                                                                        │ │
│  │ Judge           PositionAdvisor        FeishuPush                      │ │
│  │ (决策+归因)      (持仓建议)             (飞书推送)                      │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  回测 Agents (src/backtest/):                                                │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ StrategyParser  StrategyGenerator   BacktestRunner                     │ │
│  │ (策略解析)       (策略生成)           (回测执行)                       │ │
│  │                                                                        │ │
│  │ ReflectionAgent MonthlySettlement   LogGenerator                      │ │
│  │ (策略反思)       (月度结算)           (日志生成)                       │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           核心服务层                                         │
│                                                                              │
│  ┌─────────────────┐  ┌─────────────────────┐  ┌───────────────────────┐   │
│  │    LLM 服务      │  │    数据源管理        │  │    存储服务           │   │
│  │ (src/core/llm)  │  │ (src/data_sources/) │  │ (Workspace 文件系统) │   │
│  │                 │  │                     │  │                       │   │
│  │ DashScope API   │  │ DataFetcherManager  │  │ workspace/            │   │
│  │ GLM-5 模型      │  │ 多数据源自动切换     │  │ ├── ma_xxx/           │   │
│  │                 │  │ 熔断保护机制         │  │ ├── stock_xxx/        │   │
│  │                 │  │                     │  │ └── backtest_xxx/     │   │
│  └─────────────────┘  └─────────────────────┘  └───────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           数据源层                                           │
│                                                                              │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌──────────┐ │
│  │ Efinance   │ │ Akshare    │ │ Tushare    │ │ Pytdx      │ │ Baostock │ │
│  │ P=0        │ │ P=1        │ │ P=2        │ │ P=2        │ │ P=3      │ │
│  │ 最优先      │ │ 次优先     │ │ 专业数据   │ │ 通达信     │ │ 兜底     │ │
│  └────────────┘ └────────────┘ └────────────┘ └────────────┘ └──────────┘ │
│                                                                              │
│  优先级数字越小越优先，失败后自动切换到下一个数据源                          │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Workflow 详细设计

### 2.1 Market Analysis Workflow（市场分析）

**文件**: `src/workflows/market_analysis.py`

**流程图**:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     Market Analysis Workflow                              │
│                           (4 节点线性流程)                                │
└─────────────────────────────────────────────────────────────────────────┘

    ┌──────────────────┐
    │    macro_node    │
    │    (宏观分析)     │
    │                  │
    │ 功能:            │
    │ - 加载上证指数    │
    │ - 使用策略模块    │
    │ - 判断牛熊市      │
    │ - 检测历史周期    │
    │                  │
    │ 输出:            │
    │ - market_sentiment│
    │ - confidence     │
    │ - trend_detail   │
    │ - cycles         │
    └─────────┬────────┘
              │
              ▼
    ┌──────────────────┐
    │   sector_node    │
    │   (板块分析)      │
    │                  │
    │ 功能:            │
    │ - 获取热点板块    │
    │ - LLM 分析       │
    │ - 识别热点方向    │
    │                  │
    │ 输出:            │
    │ - hot_sectors    │
    │ - sector_scores  │
    └─────────┬────────┘
              │
              ▼
    ┌──────────────────┐
    │  industry_node   │
    │  (行业分析)       │
    │                  │
    │ 功能:            │
    │ - 分析行业潜力    │
    │ - 结合热点板块    │
    │                  │
    │ 输出:            │
    │ - industries     │
    │ - growth_scores  │
    └─────────┬────────┘
              │
              ▼
    ┌──────────────────┐
    │  screener_node   │
    │  (个股筛选)       │
    │                  │
    │ 功能:            │
    │ - 筛选潜力个股    │
    │ - 结合行业分析    │
    │                  │
    │ 输出:            │
    │ - recommended_   │
    │   stocks         │
    └─────────┬────────┘
              │
              ▼
           [END]
```

**状态定义** (`MarketAnalysisState`):

| 字段 | 类型 | 说明 |
|------|------|------|
| `messages` | `Annotated[list, add_messages]` | LangGraph 消息累积 |
| `market_sentiment` | `str` | 市场状态: 牛市/熊市/震荡市 |
| `sentiment_confidence` | `float` | 置信度 (0-1) |
| `market_trend_detail` | `dict` | 趋势分析详情 |
| `bull_bear_cycles` | `list[dict]` | 历史牛熊周期 |
| `hot_sectors` | `list[dict]` | 热点板块列表 |
| `industries` | `list[dict]` | 行业分析列表 |
| `recommended_stocks` | `list[dict]` | 推荐个股列表 |
| `current_step` | `str` | 当前执行步骤 |
| `logs` | `list[str]` | 执行日志 |

**关键函数**:

| 函数 | 文件 | 说明 |
|------|------|------|
| `create_market_analysis_workflow()` | market_analysis.py:21 | 创建 LangGraph workflow |
| `run_market_analysis_with_logging()` | market_analysis.py:209 | 带日志运行 |
| `run_market_analysis()` | market_analysis.py:232 | 无日志运行（兼容） |
| `macro_node()` | market_analysis.py:34 | 宏观分析节点 |
| `sector_node()` | market_analysis.py:102 | 板块分析节点 |
| `industry_node()` | market_analysis.py:140 | 行业分析节点 |
| `screener_node()` | market_analysis.py:165 | 个股筛选节点 |

---

### 2.2 Stock Analysis Workflow（股票分析）

**文件**: `src/workflows/stock_analysis.py`

**流程图**:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     Stock Analysis Workflow                               │
│                          (9 节点含辩论循环)                               │
└─────────────────────────────────────────────────────────────────────────┘

    ┌──────────────────┐
    │    init_node     │
    │    (初始化)       │
    │                  │
    │ 功能:            │
    │ - 系统检测        │
    │ - 加载持仓        │
    │ - 获取股票名称    │
    │                  │
    │ 输出:            │
    │ - stock_name     │
    │ - system_status  │
    │ - portfolio      │
    └─────────┬────────┘
              │
              ▼
    ┌──────────────────┐
    │ fundamentals_node│
    │   (基本面分析)    │
    │                  │
    │ 功能:            │
    │ - 获取股票信息    │
    │ - 获取财务数据    │
    │ - LLM 分析评分    │
    │                  │
    │ 输出:            │
    │ - fundamentals   │
    │ - strengths      │
    │ - weaknesses     │
    └─────────┬────────┘
              │
              ▼
    ┌──────────────────┐
    │ technical_node   │
    │   (技术面分析)    │
    │                  │
    │ 功能:            │
    │ - 获取实时行情    │
    │ - 获取 K 线数据   │
    │ - 技术指标分析    │
    │                  │
    │ 输出:            │
    │ - technical      │
    │ - buy_signal     │
    │ - sell_signal    │
    └─────────┬────────┘
              │
              ▼
    ┌──────────────────┐
    │ aggregator_node  │
    │    (数据汇总)     │
    │                  │
    │ 功能:            │
    │ - 合并技术+基本面 │
    │ - 提取关键论据    │
    │ - 计算综合评分    │
    │                  │
    │ 输出:            │
    │ - analysis_      │
    │   summary        │
    │ - buy_arguments  │
    │ - sell_arguments │
    └─────────┬────────┘
              │
              ▼
    ┌──────────────────────────────────────────────┐
    │              Debate Loop (辩论循环)           │
    │                                              │
    │   ┌─────────────┐      ┌─────────────┐      │
    │   │  bull_node  │ ──→ │  bear_node  │      │
    │   │  (正方辩论) │      │  (反方辩论) │      │
    │   └─────────────┘      └─────────────┘      │
    │         ↑                    │              │
    │         │                    │              │
    │         └────────────────────┘              │
    │              (继续辩论?)                    │
    │                                              │
    │   条件:                                      │
    │   - debate_rounds < 10                       │
    │   - continue → bull                         │
    │   - end → judge                             │
    └───────────────────────────┬──────────────────┘
                                │
                                ▼
    ┌──────────────────┐
    │   judge_node     │
    │     (决策)        │
    │                  │
    │ 功能:            │
    │ - 综合辩论结果    │
    │ - 生成决策        │
    │ - 归因分析        │
    │ - 反事实推断      │
    │                  │
    │ 输出:            │
    │ - final_decision │
    │ - causal_chain   │
    │ - counterfactual │
    └─────────┬────────┘
              │
              ▼
    ┌──────────────────┐
    │ position_node    │
    │   (持仓建议)      │
    │                  │
    │ 功能:            │
    │ - 判断是否持有    │
    │ - 计算建议仓位    │
    │ - 设置止损止盈    │
    │                  │
    │ 输出:            │
    │ - suggested_     │
    │   action         │
    │ - amount         │
    │ - stop_loss      │
    │ - take_profit    │
    └─────────┬────────┘
              │
              ▼
    ┌──────────────────┐
    │ feishu_push_node │
    │   (飞书推送)      │
    │                  │
    │ 功能:            │
    │ - 格式化报告      │
    │ - 推送飞书        │
    │ - 保存日志        │
    │                  │
    │ 输出:            │
    │ - push_result    │
    └─────────┬────────┘
              │
              ▼
           [END]
```

**状态定义** (`StockAnalysisState`):

| 字段 | 类型 | 说明 |
|------|------|------|
| `messages` | `Annotated[list, add_messages]` | LangGraph 消息累积 |
| `stock_code` | `str` | 股票代码 |
| `stock_name` | `str` | 股票名称 |
| `current_position` | `float` | 当前持仓金额 |
| `fundamentals` | `dict` | 基本面分析结果 |
| `technical` | `dict` | 技术面分析结果 |
| `analysis_summary` | `dict` | 综合分析摘要 |
| `bull_arguments` | `list[str]` | 正方论点列表 |
| `bear_arguments` | `list[str]` | 反方论点列表 |
| `debate_rounds` | `int` | 辩论轮数 |
| `debate_history` | `list[str]` | 辩论历史 |
| `final_decision` | `dict` | 最终决策 |
| `causal_chain` | `list[dict]` | 归因链 |
| `counterfactual` | `dict` | 反事实分析 |
| `suggested_action` | `str` | 建议操作 |
| `suggested_amount` | `float` | 建议金额 |
| `position_advice` | `dict` | 持仓建议详情 |
| `risk_warnings` | `list[str]` | 风险提示 |
| `push_result` | `dict` | 推送结果 |
| `logs` | `list[str]` | 执行日志 |
| `error` | `Optional[str]` | 错误信息 |

**关键函数**:

| 函数 | 文件 | 行号 | 说明 |
|------|------|------|------|
| `create_stock_analysis_workflow()` | stock_analysis.py | 26 | 创建 LangGraph workflow |
| `run_stock_analysis_with_logging()` | stock_analysis.py | 301 | 带日志运行 |
| `run_stock_analysis()` | stock_analysis.py | 344 | 无日志运行 |
| `init_node_wrapper()` | stock_analysis.py | 43 | 初始化节点包装 |
| `fundamentals_node()` | stock_analysis.py | 47 | 基本面分析节点 |
| `technical_node()` | stock_analysis.py | 84 | 技术面分析节点 |
| `aggregator_node_wrapper()` | stock_analysis.py | 121 | 汇总节点包装 |
| `bull_node()` | stock_analysis.py | 125 | 正方辩论节点 |
| `bear_node()` | stock_analysis.py | 161 | 反方辩论节点 |
| `should_continue_debate()` | stock_analysis.py | 198 | 辩论条件判断 |
| `judge_node_wrapper()` | stock_analysis.py | 215 | 决策节点包装 |
| `position_node()` | stock_analysis.py | 219 | 持仓建议节点 |
| `feishu_push_node_wrapper()` | stock_analysis.py | 259 | 推送节点包装 |

---

### 2.3 Backtest Workflow（回测）

**文件**: `src/workflows/backtest.py`

**流程图**:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      Backtest Workflow                                    │
│                          (4 节点线性流程)                                 │
└─────────────────────────────────────────────────────────────────────────┘

    ┌──────────────────┐
    │    init_node     │
    │    (策略解析)     │
    │                  │
    │ 功能:            │
    │ - 解析用户描述    │
    │ - 生成策略参数    │
    │                  │
    │ 输出:            │
    │ - strategy_params│
    └─────────┬────────┘
              │
              ▼
    ┌──────────────────┐
    │  backtest_node   │
    │    (执行回测)     │
    │                  │
    │ 功能:            │
    │ - 生成策略代码    │
    │ - 运行回测        │
    │ - 计算收益        │
    │                  │
    │ 输出:            │
    │ - trades         │
    │ - equity_curve   │
    │ - summary        │
    └─────────┬────────┘
              │
              ▼
    ┌──────────────────┐
    │ reflection_node  │
    │   (策略反思)      │
    │                  │
    │ 功能:            │
    │ - AI 评估策略    │
    │ - 提取优势劣势    │
    │ - 改进建议        │
    │                  │
    │ 输出:            │
    │ - reflection     │
    │ - improvements   │
    └─────────┬────────┘
              │
              ▼
    ┌──────────────────┐
    │   report_node    │
    │    (生成报告)     │
    │                  │
    │ 功能:            │
    │ - 月度结算        │
    │ - 生成日志        │
    │ - 保存文件        │
    │                  │
    │ 输出:            │
    │ - monthly_       │
    │   settlements    │
    │ - strategy_log   │
    └─────────┬────────┘
              │
              ▼
           [END]
```

**状态定义** (`BacktestState`):

| 字段 | 类型 | 说明 |
|------|------|------|
| `messages` | `Annotated[list, add_messages]` | LangGraph 消息累积 |
| `task_id` | `str` | 任务ID |
| `description` | `str` | 用户策略描述 |
| `params` | `dict` | 回测参数 |
| `strategy_params` | `dict` | 解析后的策略参数 |
| `strategy_code` | `str` | 生成的策略代码 |
| `trades` | `list[dict]` | 交易记录 |
| `equity_curve` | `list[dict]` | 净值曲线 |
| `summary` | `dict` | 回测摘要 |
| `reflection` | `dict` | AI反思结果 |
| `strengths` | `list[str]` | 策略优势 |
| `weaknesses` | `list[str]` | 策略劣势 |
| `improvements` | `list[str]` | 改进建议 |
| `risk_warnings` | `list[str]` | 风险提示 |
| `monthly_settlements` | `list[dict]` | 月度结算 |
| `strategy_log` | `str` | markdown日志内容 |
| `strategy_log_path` | `str` | 日志文件路径 |
| `current_step` | `str` | 当前步骤 |
| `logs` | `list[str]` | 执行日志 |
| `error` | `Optional[str]` | 错误信息 |

**关键函数**:

| 函数 | 文件 | 行号 | 说明 |
|------|------|------|------|
| `create_backtest_workflow()` | backtest.py | 23 | 创建 LangGraph workflow |
| `run_backtest_with_logging()` | backtest.py | 291 | 带日志运行 |
| `init_node()` | backtest.py | 33 | 策略解析节点 |
| `backtest_node()` | backtest.py | 72 | 执行回测节点 |
| `reflection_node()` | backtest.py | 155 | 策略反思节点 |
| `report_node()` | backtest.py | 208 | 报告生成节点 |

---

## 3. Agent 详细设计

### 3.1 Agent 基类

**文件**: `src/agents/base.py`

```python
class BaseAgent:
    """Agent 基类"""

    def __init__(self, llm):
        self.llm = llm

    def get_system_prompt(self) -> str:
        """返回系统提示词"""
        raise NotImplementedError

    def get_user_prompt(self, context: dict) -> str:
        """返回用户提示词"""
        raise NotImplementedError

    def run(self, context: dict) -> dict:
        """执行 Agent"""
        raise NotImplementedError
```

### 3.2 市场分析 Agents

| Agent | 文件 | 关键方法 |
|-------|------|----------|
| `MacroAnalyzer` | market/macro_analyzer.py | `run()` - 宏观分析 |
| `SectorAnalyzer` | market/sector_analyzer.py | `run()` - 板块分析 |
| `IndustryAnalyzer` | market/industry_analyzer.py | `run()` - 行业分析 |
| `StockScreener` | market/stock_screener.py | `run()` - 个股筛选 |

### 3.3 股票分析 Agents

| Agent | 文件 | 关键方法 |
|-------|------|----------|
| `InitAgent` | stock/init.py | `run()`, `_load_portfolio()`, `_get_stock_name()` |
| `FundamentalsAnalyzer` | stock/fundamentals.py | `run()` - 基本面评分 |
| `TechnicalAnalyzer` | stock/technical.py | `run()` - 技术面评分 |
| `DataAggregator` | stock/aggregator.py | `run()`, `aggregator_node()` |
| `BullAdvocate` | stock/bull_advocate.py | `run()` - 生成买入论点 |
| `BearAdvocate` | stock/bear_advocate.py | `run()` - 生成卖出论点 |
| `Judge` | stock/judge.py | `run()`, `_build_causal_chain()`, `_build_counterfactual()`, `judge_node()` |
| `PositionAdvisor` | stock/position_advisor.py | `run()` - 持仓建议 |
| `FeishuPush` | stock/feishu_push.py | `run()`, `_format_message()`, `_send_to_feishu()`, `feishu_push_node()` |

### 3.4 Judge Agent 详细设计

**归因分析 (Causal Chain)**:

```
因果链格式: A → B → C → D → E

A: 热点识别 (TrendRadar 热度数据 / 板块涨幅)
B: 关注度提升 (龙虎榜/资金流数据)
C: 技术面信号 (K线数据 / 技术指标)
D: 基本面支撑 (财务数据)
E: 最终决策 (综合评分 + 辩论结果)
```

**反事实推断 (Counterfactual)**:

| 场景 | 价格变化 | 影响 | 建议 |
|------|----------|------|------|
| 下跌5% | -5% | 短期波动 | 观望等待 |
| 下跌10% | -10% | 触发止损线 | 减仓50% |
| 下跌20% | -20% | 严重亏损 | 清仓止损 |

---

## 4. 数据源管理系统

### 4.1 核心架构

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        DataFetcherManager                                │
│                    (src/data_sources/providers/base.py)                  │
│                                                                         │
│  功能:                                                                   │
│  1. 多数据源自动切换 (策略模式)                                           │
│  2. 熔断保护 (Circuit Breaker)                                          │
│  3. 缓存管理 (实时行情缓存 + 股票名称缓存)                                 │
│  4. 防封禁策略 (随机休眠 + UA轮换 + 指数退避)                             │
│                                                                         │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                      数据获取方法                                   │ │
│  │                                                                    │ │
│  │  get_daily_data(code, days)        日线数据                        │ │
│  │  get_realtime_quote(code)          实时行情                        │ │
│  │  get_chip_distribution(code)       筹码分布                        │ │
│  │  get_stock_name(code)              股票名称                        │ │
│  │  get_belong_boards(code)           所属板块                        │ │
│  │  get_main_indices(region)          主要指数                        │ │
│  │  get_market_stats()                市场统计                        │ │
│  │  get_sector_rankings(n)            板块排名                        │ │
│  │  get_fundamental_context(code)     基本面全景                      │ │
│  │  batch_get_stock_names(codes)      批量获取名称                    │ │
│  └────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         数据源优先级                                      │
│                                                                         │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐   │
│  │  Efinance    │ │  Akshare     │ │  Tushare     │ │  Pytdx       │   │
│  │  P=0         │ │  P=1         │ │  P=2         │ │  P=2         │   │
│  │  最优先      │ │  次优先      │ │  专业数据    │ │  通达信      │   │
│  │              │ │              │ │  需Token     │ │  直连        │   │
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘   │
│                                                                         │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐                    │
│  │  Baostock    │ │  Yfinance    │ │  Longbridge  │                    │
│  │  P=3         │ │  P=4         │ │  P=5         │                    │
│  │  免费        │ │  美股兜底    │ │  长桥API     │                    │
│  │  数据稳定    │ │              │ │  需Keys      │                    │
│  └──────────────┘ └──────────────┘ └──────────────┘                    │
└─────────────────────────────────────────────────────────────────────────┘
```

### 4.2 DataAdapter（统一接口层）

**文件**: `src/data_sources/data_adapter.py`

DataAdapter 封装 DataFetcherManager，提供简洁的对外接口:

| 方法 | 说明 | 返回类型 |
|------|------|----------|
| `get_market_overview()` | 市场概览 | `Dict[str, Any]` |
| `get_hot_sectors(top_n)` | 热点板块 | `List[Dict]` |
| `get_market_stats()` | 市场统计 | `Dict[str, Any]` |
| `get_stock_info(code)` | 股票信息 | `Dict[str, Any]` |
| `get_stock_realtime(code)` | 实时行情 | `Dict[str, Any]` |
| `get_stock_kline(code, days)` | K线数据 | `Dict[str, Any]` |
| `get_stock_financial(code)` | 财务数据 | `Dict[str, Any]` |
| `get_chip_distribution(code)` | 筹码分布 | `Dict[str, Any]` |
| `get_chip_status(code)` | 筹码状态 | `str` |
| `get_fundamental_context(code)` | 基本面全景 | `Dict[str, Any]` |
| `batch_get_stock_names(codes)` | 批量名称 | `Dict[str, str]` |
| `clear_cache()` | 清除缓存 | `None` |

### 4.3 熔断机制

```
状态机:
CLOSED（正常） ─失败N次→ OPEN（熔断） ─冷却时间→ HALF_OPEN（半开）
HALF_OPEN ─成功→ CLOSED
HALF_OPEN ─失败→ OPEN

参数:
- failure_threshold = 3    # 连续失败 3 次熔断
- cooldown_seconds = 300   # 冷却 5 分钟
- half_open_max_calls = 1  # 半开状态试探 1 次
```

### 4.4 缓存管理

| 缓存类型 | TTL | 说明 |
|----------|-----|------|
| 实时行情缓存 | 10-20 分钟 | 全市场数据 DataFrame |
| 股票名称缓存 | 永久（内存） | `{code: name}` 字典 |
| 基本面缓存 | 1 小时 | `{cache_key: context}` |

---

## 5. 目录结构

```
trading-agent/
├── docs/
│   ├── PRD.md                      # 产品需求文档
│   ├── ARCHITECTURE.md             # 架构设计（本文档）
│   └── TESTING.md                  # 测试文档
│
├── src/
│   ├── cli.py                      # CLI 命令入口
│   │
│   ├── core/                       # 核心模块
│   │   ├── llm.py                  # LLM 集成 (DashScope)
│   │   ├── config.py               # 配置管理
│   │   └── logger.py               # 日志模块
│   │
│   ├── data_sources/               # 数据源管理
│   │   ├── data_adapter.py         # 统一数据接口 ⭐
│   │   ├── fetcher.py              # DataFetcher 类
│   │   │
│   │   ├── providers/              # 多数据源实现
│   │   │   ├── base.py             # BaseFetcher + DataFetcherManager
│   │   │   ├── realtime_types.py   # 统一数据类型 + 熔断器
│   │   │   ├── akshare_fetcher.py  # Akshare 数据源
│   │   │   ├── efinance_fetcher.py  # Efinance 数据源
│   │   │   ├── tushare_fetcher.py   # Tushare 数据源
│   │   │   ├── pytdx_fetcher.py     # 通达信数据源
│   │   │   ├── baostock_fetcher.py  # Baostock 数据源
│   │   │   ├── yfinance_fetcher.py  # Yfinance 数据源
│   │   │   └── longbridge_fetcher.py # 长桥数据源
│   │   │
│   │   ├── trade_daily.py          # 日线数据
│   │   ├── trade_realtime.py       # 实时行情
│   │   ├── trade_chip.py           # 筹码分布
│   │   ├── market_index.py         # 市场指数
│   │   ├── market_sector.py        # 板块数据
│   │   └── fundamental_financial.py # 财务数据
│   │
│   ├── agents/                     # Agent 实现
│   │   ├── base.py                 # Agent 基类
│   │   │
│   │   ├── market/                 # 市场分析 agents
│   │   │   ├── macro_analyzer.py
│   │   │   ├── sector_analyzer.py
│   │   │   ├── industry_analyzer.py
│   │   │   └── stock_screener.py
│   │   │
│   │   └── stock/                  # 股票分析 agents
│   │   │   ├── init.py
│   │   │   ├── fundamentals.py
│   │   │   ├── technical.py
│   │   │   ├── aggregator.py
│   │   │   ├── bull_advocate.py
│   │   │   ├── bear_advocate.py
│   │   │   ├── judge.py            # 含归因+反事实
│   │   │   ├── position_advisor.py
│   │   │   └── feishu_push.py
│   │
│   ├── workflows/                  # LangGraph Workflows
│   │   ├── state.py                # 状态定义
│   │   ├── market_analysis.py      # 市场分析流程
│   │   ├── stock_analysis.py       # 股票分析流程
│   │   └── backtest.py             # 回测流程
│   │
│   ├── backtest/                   # 回测模块
│   │   ├── strategy_parser.py
│   │   ├── strategy_generator.py
│   │   ├── runner.py
│   │   ├── reflection_agent.py
│   │   ├── monthly_settlement.py
│   │   └ log_generator.py
│   │
│   ├── scheduler/                  # 任务调度
│   │   ├── task_queue.py
│   │   ├── executor.py
│   │   └ workspace_manager.py
│   │
│   ├── query/                      # AI 查询模块
│   │   ├── engine.py
│   │   ├── templates.py
│   │   └ ai_query.py
│   │
│   └── web/                        # Web 界面
│   │   ├── app.py
│   │   ├── routes/
│   │   │   ├── tasks.py
│   │   │   ├── chat.py
│   │   │   └ catalog.py
│   │   └ static/
│
├── data/CN_A/                      # 股票数据目录
│   ├── stock_list.csv
│   ├── stock_daily/
│   └── archive/
│
├── workspace/                      # 任务工作目录
│   ├── ma_YYYYMMDD_HHMMSS_id/
│   └── stock_YYYYMMDD_HHMMSS_id/
│
├── main.py                         # 主入口
├── pyproject.toml
└ README.md
``

---

## 6. 部署与运行

### 6.1 CLI 命令

```bash
# 市场分析
trading-agent market

# 股票分析
trading-agent stock 000001 --position 10000

# Web 服务
trading-agent web --port 8080

# AI 查询
trading-agent query "涨幅超过5%的银行股"

# 更新数据
trading-agent update --codes 000001
```

### 6.2 环境变量

| 变量 | 说明 | 必需 |
|------|------|------|
| `DASHSCOPE_API_KEY` | 阿里云 DashScope API Key | ✅ |
| `TUSHARE_TOKEN` | Tushare Pro Token | ❌ |
| `PYTDX_HOST` | 通达信服务器地址 | ❌ |
| `PYTDX_PORT` | 通达信端口 | ❌ |

---

## 7. 扩展设计

### 7.1 添加新 Agent

```python
class MyAgent(BaseAgent):
    def get_system_prompt(self) -> str:
        return "你是一个..."

    def get_user_prompt(self, context: dict) -> str:
        return f"分析 {context['stock_code']}..."

    def run(self, context: dict) -> dict:
        prompt = self.get_user_prompt(context)
        response = self.llm.invoke(prompt)
        return {"result": response}
```

### 7.2 添加新数据源

```python
class MyFetcher(BaseFetcher):
    name = "MyFetcher"

    def get_daily_data(self, code, days):
        # 实现数据获取逻辑
        return df
```

---

## 下一步行动

1. ✅ 完成 StubConfig 兼容性修复
2. ✅ 完成缓存清除机制
3. ✅ 完成 ARCHITECTURE.md 文档更新
4. 🔄 统一数据获取接口（简化冗余函数）
5. 🔄 更新 README.md