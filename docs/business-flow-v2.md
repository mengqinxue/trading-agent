# Trading Agent - 业务流程 V2

> Version: 2.0
> Date: 2026-04-25
> Based on user requirements discussion

---

## 整体流程图

```
┌─────────────────────────────────────────────────────────────────┐
│                    Trading Agent Workflow                        │
└─────────────────────────────────────────────────────────────────┘

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
│  粗筛节点     │
│  (screener)  │
│              │
│ - 热点新闻    │
│ - 板块识别    │
│ - 龙头筛选    │
│ - 候选池生成  │
└──────┬───────┘
       │
       ├──────────────────────────┐
       │                          │
       ▼                          ▼
┌──────────────┐          ┌──────────────┐
│ 技术面分析    │          │ 基本面分析    │
│ (tech_analyst)│          │ (fund_analyst)│
│              │          │              │
│ - K线形态    │          │ - 财务数据    │
│ - 技术指标    │          │ - 行业地位    │
│ - 成交量     │          │ - 新闻/政策   │
│ - 资金流     │          │ - 风险评估    │
│              │          │              │
│ 输出:        │          │ 输出:        │
│ recommendation│          │ recommendation│
│ confidence   │          │ confidence   │
│ arguments    │          │ arguments    │
└──────┬───────┘          └──────┬───────┘
       │                          │
       └──────────┬───────────────┘
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
│  │  (buyer)    │    │  (seller)   │          │
│  └─────────────┘    └─────────────┘         │
│                                             │
│  辩论机制:                                   │
│  - Round 1: 双方陈述核心观点                  │
│  - Round 2-N: 反驳对方论点                    │
│  - 提前终止条件: 5轮无新论据                   │
│  - 最大轮数: 20轮                             │
│                                             │
│  输出:                                       │
│  - debate_log: 辩论记录                      │
│  - buyer_score: 买入方得分                   │
│  - seller_score: 卖出方得分                  │
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
│ 输出:                                        │
│ - action: buy/sell/hold                     │
│ - confidence: 决策置信度                     │
│ - reasoning: 决策理由                        │
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
│ - 格式化报告                                  │
│ - 推送飞书                                    │
│ - 记录决策日志                                │
└─────────────────────────────────────────────┘
```

---

## 节点详细说明

### 1. 初始化节点 (init)

**职责**：
- 系统检测：检查 API 连接、数据源状态
- 参数加载：加载配置文件、持仓信息
- 状态初始化：创建 workflow state
- 持仓加载：读取当前持仓配置

**输入**：
- config/config.yaml
- config/portfolio.yaml
- .env (API keys)

**输出**：
- workflow_state: 初始化状态
- system_status: 系统检测结果
- portfolio: 当前持仓

**日志示例**：
```
[09:00:01] [INIT] Workflow initialized
[09:00:02] [INIT] System check: akshare=OK, TrendRadar=OK, Feishu=OK
[09:00:03] [INIT] Portfolio loaded: 5 positions
[09:00:04] [INIT] Candidates pool: empty (to be filled by screener)
```

---

### 2. 粗筛节点 (screener)

**职责**：
- 从 TrendRadar 获取热点新闻
- AI 分析热点板块
- 识别炒作龙头（非基本面龙头）
- 生成候选股票池

**输入**：
- TrendRadar MCP 新闻数据
- keywords.yaml 关键词配置
- portfolio.yaml 持仓关键词

**输出**：
- hot_sectors: 热点板块列表
- candidate_stocks: 候选股票池 (20-50只)

---

### 3. 技术面分析节点 (tech_analyst)

**职责**：
- K线形态识别
- 技术指标计算（MACD、RSI、均线）
- 成交量分析
- 资金流向分析

**输入**：
- candidate_stocks
- akshare 行情数据

**输出**：
- tech_results: 技术面分析结果列表
  - stock_code
  - trend_direction (up/down/neutral)
  - signals: ["突破均线", "放量", "MACD金叉"]
  - recommendation (buy/sell/hold)
  - confidence (0-1)
  - arguments: 论据列表

---

### 4. 基本面分析节点 (fund_analyst)

**职责**：
- 财务数据分析
- 行业地位评估
- 新闻/政策影响分析
- 风险提示

**输入**：
- candidate_stocks
- 财务数据（akshare）
- 相关新闻

**输出**：
- fund_results: 基本面分析结果列表
  - stock_code
  - fundamentals_score (0-100)
  - risks: 风险列表
  - positives: 亮点列表
  - recommendation
  - confidence
  - arguments

---

### 5. 汇总节点 (aggregator)

**职责**：
- 合并技术面 + 基本面分析结果
- 计算综合评分
- 提取关键论据（供辩论使用）
- 生成分析报告

**输入**：
- tech_results
- fund_results

**输出**：
- analysis_summary: 汇总结果
  - stock_code
  - tech_score
  - fund_score
  - combined_score
  - buy_arguments: 支持买入的论据
  - sell_arguments: 支持卖出的论据

---

### 6. 辩论节点 (debater)

**职责**：
- 买入方 agent 和卖出方 agent 对抗
- 每轮交换观点
- 提前终止条件：5轮无新论据
- 最大轮数：20轮

**辩论机制**：

```
Round 1:
  Buyer: "技术面显示突破均线，MACD金叉，建议买入"
  Seller: "基本面显示公司亏损，行业竞争加剧，建议观望"

Round 2:
  Buyer: "虽然亏损，但成交量放大，资金流入明显"
  Seller: "资金流入可能是短期炒作，龙虎榜显示游资进出"

Round 3-20:
  继续辩论...
  
提前终止条件:
  - 连续5轮双方无新论据
  - 达成共识（双方观点趋同）
```

**输入**：
- analysis_summary
- portfolio (持仓状态)

**输出**：
- debate_log: 辩论记录
- buyer_score: 买入方得分 (0-100)
- seller_score: 卖出方得分 (0-100)
- consensus: 是否达成共识
- final_position: buy/sell/hold

---

### 7. 决策节点 (judge)

**职责**：
- 综合分析结果 + 辩论结果
- 评估风险收益比
- **归因分析**：解释买入理由的因果链
- **反事实推断**：假设下跌场景的影响分析
- 给出最终决策

**输入**：
- analysis_summary
- debate_log
- portfolio

**归因分析机制**：
```
因果链推导示例：

热点板块：半导体 → 炒作龙头：XXX股票
→ 技术面：突破均线 + 放量
→ 基本面：业绩改善 + 订单增加
→ 结论：买入建议

归因输出格式：
A(热点板块炒作) → B(龙头股关注度提升) → C(技术面突破信号) → D(基本面支撑) → E(买入建议)

每一步都要有数据/论据支撑：
- A: TrendRadar 热度数据
- B: 龙虎榜/资金流数据
- C: akshare K线数据
- D: akshare 财务数据
- E: 综合评分
```

**反事实推断机制**：
```
假设下跌场景分析：

场景1：下跌5%
- 影响：持仓市值减少 X 元
- 预期：短期波动，可能回调
- 建议：观望，等待企稳

场景2：下跌10%
- 影响：触发止损线
- 预期：可能技术面破位
- 建议：减仓50%，保留观察仓位

场景3：下跌20%
- 影响：严重亏损，基本面可能有问题
- 预期：需要重新评估
- 建议：清仓止损，等待新信号

反事实输出：
- worst_case: 最坏情况
- probability: 发生概率估计
- mitigation: 风险缓解措施
- exit_strategy: 退出策略
```

**输出**：
- decision:
  - stock_code
  - action: buy/sell/hold
  - confidence: 决策置信度
  - reasoning: 决策理由
  - **causal_chain**: 归因分析因果链
  - **counterfactual**: 反事实推断结果
  - should_enter: 是否建议入场
  - risk_level: high/medium/low

---

### 8. 持仓建议节点 (position_advisor)

**职责**：
- 结合已有持仓
- 判断是新买入还是加仓/减仓

**逻辑**：

```
if 已持有该股票:
  if action == buy:
    position_action = "add" (加仓)
  elif action == sell:
    检查持仓盈亏:
      if 盈利 > 20%:
        position_action = "reduce" (减仓，部分止盈)
      elif 亏损 > 10%:
        position_action = "clear" (清仓止损)
      else:
        position_action = "hold" (持有观望)
else:
  if action == buy:
    position_action = "new_buy" (新建仓位)
  else:
    position_action = "skip" (不操作)
```

**输入**：
- decision
- portfolio

**输出**：
- position_advice:
  - stock_code
  - position_action: new_buy/add/reduce/clear/hold/skip
  - suggested_amount: 建议仓位比例
  - stop_loss: 止损位
  - take_profit: 止盈位
  - current_position: 当前持仓状态

---

### 9. 推送节点 (push)

**职责**：
- 格式化决策报告
- 推送飞书
- 记录决策日志

**输入**：
- decision
- position_advice
- debate_log (摘要)

**输出**：
- feishu_message: 飞书消息
- decision_log: 决策日志文件

---

## 数据流图

```
Config Files          External APIs
    │                     │
    ├── config.yaml       ├── TrendRadar MCP
    ├── portfolio.yaml    ├── akshare
    ├── keywords.yaml     └── Feishu Webhook
    └─────────┬───────────┴─────────────┘
              │
              ▼
        ┌───────────┐
        │   INIT    │
        └───────────┘
              │
              ▼
        ┌───────────┐
        │ SCREENER  │──────► candidate_stocks
        └───────────┘
              │
     ┌────────┴────────┐
     ▼                 ▼
┌──────────┐     ┌──────────┐
│TECH_ANAL │     │FUND_ANAL │
└──────────┘     └──────────┘
     │                 │
     └─────────┬───────┘
               ▼
        ┌───────────┐
        │AGGREGATOR │──────► analysis_summary
        └───────────┘
               │
               ▼
        ┌───────────┐
        │  DEBATER  │──────► debate_log
        └───────────┘
               │
               ▼
        ┌───────────┐
        │   JUDGE   │──────► decision
        └───────────┘
               │
               ▼
        ┌───────────────┐
        │POSITION_ADVISOR│────► position_advice
        └───────────────┘
               │
               ▼
        ┌───────────┐
        │   PUSH    │──────► Feishu + Log
        └───────────┘
```

---

## 状态定义

```python
class WorkflowState(TypedDict):
    # 初始化
    run_id: str
    run_type: str  # pre_market / post_market
    system_status: dict
    portfolio: dict

    # Step 1: Screener
    screener_status: str
    hot_sectors: list
    candidate_stocks: list

    # Step 2: Analysis (并行)
    tech_analyst_status: str
    fund_analyst_status: str
    tech_results: list
    fund_results: list

    # Step 3: Aggregator
    aggregator_status: str
    analysis_summary: list

    # Step 4: Debater
    debater_status: str
    debate_log: list
    buyer_score: float
    seller_score: float

    # Step 5: Judge
    judge_status: str
    decision: dict

    # Step 6: Position Advisor
    position_status: str
    position_advice: dict

    # Step 7: Push
    push_status: str
    push_result: dict

    # 元数据
    start_time: str
    end_time: str
    error: Optional[str]
```

---

## 辩论评分机制

```python
# 评分规则
SCORING_RULES = {
    "data_evidence": 10,      # 有数据支撑的论据
    "logical_argument": 8,    # 逻辑清晰的论据
    "counter_rebuttal": 6,    # 有效反驳对方
    "new_insight": 5,         # 提出新观点
    "weak_argument": -3,      # 论据薄弱
    "contradiction": -5,      # 自相矛盾
}

# 提前终止条件
TERMINATION_CONDITIONS = {
    "max_rounds": 20,
    "no_new_args_rounds": 5,  # 连续5轮无新论据
    "consensus_threshold": 0.8,  # 双方得分差距 < 20%
}
```

---

## 下一步

1. 更新 LangGraph workflow 结构
2. 实现 init + aggregator + position_advisor 新节点
3. 更新 debater 为 20 轮 + 提前终止逻辑