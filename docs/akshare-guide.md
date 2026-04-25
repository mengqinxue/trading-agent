# AKShare 数据接口使用指南

> 基于 2026-04-25 测试结果
> akshare 版本: 1.18.57

---

## 可用接口总结

| 类别 | 接口 | 数据源 | 状态 |
|-----|------|--------|------|
| 日线行情 | `stock_zh_a_hist` | 东方财富 | ✅ 可用 |
| 资金流向 | `stock_individual_fund_flow` | 东方财富 | ✅ 可用 |
| 个股新闻 | `stock_news_em` | 东方财富 | ✅ 可用 |
| 个股研报 | `stock_research_report_em` | 东方财富 | ✅ 可用 |
| 财务摘要 | `stock_financial_abstract_ths` | 同花顺 | ✅ 可用 |
| 利润表 | `stock_financial_benefit_ths` | 同花顺 | ✅ 可用 |
| 资产负债 | `stock_financial_debt_ths` | 同花顺 | ✅ 可用 |
| 现金流量 | `stock_financial_cash_ths` | 同花顺 | ✅ 可用 |

---

## 技术分析数据接口

### 1. 日线历史行情

```python
import akshare as ak

# 获取日线数据（前复权）
df = ak.stock_zh_a_hist(
    symbol="600519",      # 股票代码
    period="daily",       # 日线
    start_date="20260101", # 开始日期
    end_date="20260425",   # 结束日期
    adjust="qfq"          # 前复权
)

# 返回字段：
# 日期, 股票代码, 开盘, 收盘, 最高, 最低, 成交量, 成交额, 
# 振幅, 涨跌幅, 涨跌额, 换手率
```

**用途**：
- 计算 MA（均线）
- 计算 MACD
- 计算 RSI
- K 线形态识别
- 支撑/阻力位分析

### 2. 个股资金流向

```python
# 获取资金流向数据
df = ak.stock_individual_fund_flow(
    stock="600519",       # 股票代码
    market="sh"           # 市场：sh/sz
)

# 返回字段：
# 日期, 收盘价, 涨跌幅, 主力净流入-净额, 主力净流入-净占比,
# 超大单净流入-净额, 超大单净流入-净占比, 大单净流入-净额, 大单净流入-净占比,
# 中单净流入-净额, 中单净流入-净占比, 小单净流入-净额, 小单净流入-净占比
```

**用途**：
- 主力资金动向分析
- 超大单/大单/中单/小单资金流
- 判断机构资金进出

---

## 基本面数据接口（同花顺）

### 3. 财务摘要

```python
# 获取财务摘要（多年度汇总）
df = ak.stock_financial_abstract_ths(symbol="600519")

# 返回字段（25列）：
# 报告期, 净利润, 净利润同比增长率, 扣非净利润, 
# 营业总收入, 营业总收入同比增长率, 
# ... (包含 ROE、毛利率、负债率等关键指标)
```

**用途**：
- 快速获取公司财务概况
- ROE、毛利率、负债率等关键指标
- 多年度对比分析

### 4. 利润表

```python
# 获取利润表详细数据
df = ak.stock_financial_benefit_ths(symbol="600519")

# 返回字段：
# 报告期, *净利润, *营业总收入, *营业总成本, 
# *归属于母公司所有者的净利润, ...
```

### 5. 资产负债表

```python
# 获取资产负债表
df = ak.stock_financial_debt_ths(symbol="600519")
```

### 6. 现金流量表

```python
# 获取现金流量表
df = ak.stock_financial_cash_ths(symbol="600519")
```

---

## 新闻/研报接口

### 7. 个股新闻

```python
# 获取个股相关新闻
df = ak.stock_news_em(symbol="600519")

# 返回字段：
# 关键词, 新闻标题, 新闻内容, 发布时间, 文章来源, 新闻链接
```

**用途**：
- 获取公司相关新闻
- 分析市场情绪
- 获取重要公告

### 8. 个股研报

```python
# 获取研究报告
df = ak.stock_research_report_em(symbol="600519")

# 返回字段：
# 股票代码, 股票简称, 报告名称, 东财评级, 机构, 
# 盈利预测-收益, 盈利预测-市盈率, 行业, 日期
```

**用途**：
- 获取机构观点
- 目标价预测
- 行业评级

---

## 注意事项

1. **数据源差异**：
   - 东方财富（`_em`）接口部分有网络问题
   - 同花顺（`_ths`）接口更稳定
   - 财务数据推荐使用同花顺接口

2. **股票代码格式**：
   - A股：6位数字（如 `600519`）
   - 港股：5位数字（如 `00700`）
   - 美股：字母代码（如 `AAPL`）

3. **市场标识**：
   - 沪市：`sh`
   - 深市：`sz`
   - 港股：`hk`
   - 美股：`us`

4. **复权方式**：
   - `qfq`：前复权（推荐）
   - `hfq`：后复权
   - ``：不复权

---

## Trading Agent 数据需求

### tech_analyst 节点需要：
- `stock_zh_a_hist` - 日线行情（K线、均线、MACD、RSI）
- `stock_individual_fund_flow` - 资金流向（主力资金分析）

### fund_analyst 节点需要：
- `stock_financial_abstract_ths` - 财务摘要（ROE、毛利率、负债率）
- `stock_news_em` - 新闻（市场情绪、重要事件）
- `stock_research_report_em` - 研报（机构观点、目标价）