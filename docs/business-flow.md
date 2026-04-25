# Trading Agent - 业务流程文档

> Version: 1.0.0
> Date: 2026-04-25

---

## 整体流程概览

```
每日运行流程（定时触发）:

盘前 09:00                    盘后 15:30
    │                             │
    ▼                             ▼
[热点发现]                    [决策评审]
    │                             │
    ▼                             ▼
[粗筛股票池]                  [推送报告]
    │                             │
    ▼                             ▼
[保存候选池]                  [记录日志]
    │
    │ (候选池供盘后使用)
    ▼
盘后 15:30
    │
    ▼
[加载候选池]
    │
    ├──────────┬──────────┐
    ▼          ▼          │
[技术面]   [基本面]       │
    │          │          │
    └──────────┴──────────┘
               │
               ▼
         [博弈辩论]
               │
               ▼
         [评委决策]
               │
               ▼
         [推送报告]
```

---

## 详细流程步骤

### Step 1: 热点发现（盘前 09:00）

**触发时机**：每日开盘前 09:00（周一至周五）

**输入**：
- TrendRadar MCP 新闻数据
- 用户持仓关键词配置

**处理逻辑**：
1. 从 TrendRadar MCP 获取昨日 + 今日热点新闻
2. AI 分析提取热点板块（如：AI、新能源、医药）
3. 识别每个板块的炒作龙头（不是基本面龙头）
4. 结合持仓关键词过滤相关性

**输出**：
- 热点板块列表（name, heat_score, leaders）
- 候选股票池（20-50只股票代码）
- 保存到 `data/candidates/YYYY-MM-DD.json`

**日志记录**：
```
[09:00:01] [SCREENER] 开始热点发现任务
[09:00:05] [SCREENER] 获取新闻 X 条
[09:00:10] [SCREENER] 识别热点板块 Y 个
[09:00:15] [SCREENER] 候选池生成完成，共 Z 只股票
[09:00:20] [SCREENER] 保存候选池到 data/candidates/...
[09:00:21] [SCREENER] 任务完成
```

---

### Step 2: 技术面分析（盘后 15:30）

**触发时机**：盘后 15:30，候选池已生成

**输入**：
- 候选股票池
- akshare 行情数据（K线、成交量、技术指标）

**处理逻辑**：
1. 加载当日候选池
2. 对每只股票获取当日行情数据
3. 分析 K线形态（趋势、形态）
4. 计算技术指标（MACD、RSI、均线）
5. 分析成交量/资金流
6. 给出每只股票的技术面评分

**输出**：
- 技术面分析结果列表
  - stock_code, stock_name
  - trend_direction (up/down/neutral)
  - signals: ["突破均线", "放量上涨", "MACD金叉"]
  - recommendation (buy/sell/hold)
  - confidence (0-1)
  - arguments: ["理由1", "理由2"]

**日志记录**：
```
[15:30:01] [DATA_ANALYST] 开始技术面分析
[15:30:05] [DATA_ANALYST] 加载候选池 X 只股票
[15:30:10] [DATA_ANALYST] 获取 XXX 行情数据
[15:30:15] [DATA_ANALYST] 分析 XXX 技术指标
[15:30:20] [DATA_ANALYST] XXX 评分完成: buy, confidence=0.75
[15:35:00] [DATA_ANALYST] 全部股票分析完成
[15:35:01] [DATA_ANALYST] 保存结果到 data/analysis/...
```

---

### Step 3: 基本面/尽调分析（盘后 15:30）

**触发时机**：与技术面分析并行执行

**输入**：
- 候选股票池
- 公司基本面数据（财务、业务）
- 相关新闻/公告

**处理逻辑**：
1. 加载当日候选池
2. 对每只股票获取基本面数据
3. 分析公司财务状况
4. 分析行业地位/竞争格局
5. 分析政策/消息影响
6. 检查龙虎榜/机构持仓
7. 给出基本面评分

**输出**：
- 基本面分析结果列表
  - stock_code, stock_name
  - fundamentals_score (0-100)
  - risks: ["风险1", "风险2"]
  - positives: ["亮点1", "亮点2"]
  - recommendation (buy/sell/hold)
  - confidence (0-1)
  - arguments: ["理由1", "理由2"]

**日志记录**：
```
[15:30:01] [DUE_DILIGENCE] 开始基本面分析
[15:30:05] [DUE_DILIGENCE] 加载候选池 X 只股票
[15:30:10] [DUE_DILIGENCE] 获取 XXX 基本面数据
[15:30:15] [DUE_DILIGENCE] 分析 XXX 行业地位
[15:30:20] [DUE_DILIGENCE] XXX 评分完成: hold, confidence=0.6
[15:35:00] [DUE_DILIGENCE] 全部股票分析完成
[15:35:01] [DUE_DILIGENCE] 保存结果到 data/diligence/...
```

---

### Step 4: 博弈辩论（盘后 15:35）

**触发时机**：技术面 + 基本面分析完成后

**输入**：
- 技术面分析结果
- 基本面分析结果
- 用户持仓状态

**处理逻辑**：
1. 对每只候选股票启动辩论
2. 买入方 agent 提出买入论据
3. 卖出方 agent 提出卖出论据
4. 每轮交换观点、反驳对方
5. 最多 100 轮，检测共识提前终止
6. 生成辩论摘要

**输出**：
- 辩论记录列表
  - stock_code
  - rounds: [{round, buyer_arg, seller_arg}]
  - consensus_reached (bool)
  - buyer_final_position
  - seller_final_position
  - debate_summary

**日志记录**：
```
[15:35:01] [DEBATER] 开始博弈辩论
[15:35:05] [DEBATER] XXX 辩论开始
[15:35:10] [DEBATER] XXX Round 1: buyer 提出 X, seller 提出 Y
[15:36:00] [DEBATER] XXX Round 50: ...
[15:40:00] [DEBATER] XXX 达成共识: hold
[15:45:00] [DEBATER] 全部辩论完成
[15:45:01] [DEBATER] 保存辩论记录到 data/debates/...
```

---

### Step 5: 评委决策（盘后 15:45）

**触发时机**：辩论完成后

**输入**：
- 技术面分析结果
- 基本面分析结果
- 辩论摘要
- 用户持仓状态

**处理逻辑**：
1. 综合三方信息（技术面 + 基本面 + 辩论）
2. 结合用户持仓（是否已持有、仓位比例）
3. 评估风险收益比
4. 给出最终决策：buy/sell/hold
5. 给出仓位建议
6. 生成结构化决策报告

**输出**：
- 决策报告
  - stock_code, stock_name
  - recommendation (buy/sell/hold)
  - position_advice ("建议买入 20% 仓位" 或 "建议卖出全部持仓")
  - confidence (0-1)
  - reasoning (决策理由)
  - debate_summary
  - risks (风险提示)

**日志记录**：
```
[15:45:01] [JUDGE] 开始评委决策
[15:45:05] [JUDGE] XXX 综合评估
[15:45:10] [JUDGE] XXX 决策: buy, 建议仓位 20%
[15:50:00] [JUDGE] 全部决策完成
[15:50:01] [JUDGE] 保存决策报告到 data/decisions/...
```

---

### Step 6: 推送报告（盘后 15:50）

**触发时机**：决策完成后

**输入**：
- 决策报告

**处理逻辑**：
1. 格式化决策报告
2. 推送到飞书机器人
3. 可选推送邮件

**输出**：
- 飞书消息推送成功
- 推送日志

**日志记录**：
```
[15:50:01] [PUSH] 开始推送报告
[15:50:05] [PUSH] 格式化报告
[15:50:10] [PUSH] 推送到飞书
[15:50:15] [PUSH] 飞书推送成功
[15:50:16] [PUSH] 推送完成
```

---

## 状态流转

```python
class WorkflowState:
    # 每日运行状态
    run_id: str              # YYYY-MM-DD-HHMMSS
    run_type: str            # "pre_market" | "post_market"
    status: str              # "pending" | "running" | "completed" | "failed"
    
    # 各步骤状态
    screener_status: str     # "pending" | "running" | "completed"
    data_analyst_status: str
    due_diligence_status: str
    debater_status: str
    judge_status: str
    push_status: str
    
    # 数据
    candidate_stocks: list
    data_analysis: list
    due_diligence: list
    debates: list
    decisions: list
    
    # 元数据
    start_time: datetime
    end_time: datetime
    error_message: str
```

---

## 定时任务配置

```yaml
schedule:
  pre_market:
    time: "09:00"
    days: ["mon", "tue", "wed", "thu", "fri"]
    steps: ["screener"]
    
  post_market:
    time: "15:30"
    days: ["mon", "tue", "wed", "thu", "fri"]
    steps: ["data_analyst", "due_diligence", "debater", "judge", "push"]
```

---

## 数据存储路径

```
data/
├── candidates/
│   └── YYYY-MM-DD.json       # 每日候选池
│
├── analysis/
│   └── YYYY-MM-DD.json       # 技术面分析结果
│
├── diligence/
│   └── YYYY-MM-DD.json       # 基本面分析结果
│
├── debates/
│   └── YYYY-MM-DD.json       # 辩论记录
│
├── decisions/
│   └── YYYY-MM-DD.json       # 决策报告
│
└── logs/
    └── YYYY-MM-DD.log        # 每日运行日志
```