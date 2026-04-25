#!/usr/bin/env python3
"""
AKShare 能力测试脚本

测试技术分析 + 基本分析所需的核心接口
"""

import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
import json

print("=" * 60)
print("AKShare 能力测试")
print("=" * 60)

# 测试股票代码
TEST_STOCK = "600519"  # 贵州茅台

# ==================== 技术分析数据 ====================

print("\n" + "-" * 40)
print("【技术分析数据测试】")
print("-" * 40)

# 1. 日线历史行情
print("\n1. 日线历史行情 (stock_zh_a_hist)")
try:
    end_date = datetime.now().strftime("%Y%m%d")
    start_date = (datetime.now() - timedelta(days=60)).strftime("%Y%m%d")
    
    df = ak.stock_zh_a_hist(
        symbol=TEST_STOCK,
        period="daily",
        start_date=start_date,
        end_date=end_date,
        adjust="qfq"  # 前复权
    )
    print(f"   ✓ 成功获取 {len(df)} 条日线数据")
    print(f"   最近5条:\n{df.tail()}")
except Exception as e:
    print(f"   ✗ 失败: {e}")

# 2. 实时行情
print("\n2. 实时行情 (stock_zh_a_spot_em)")
try:
    df = ak.stock_zh_a_spot_em()
    # 查找测试股票
    stock_info = df[df['代码'] == TEST_STOCK]
    if len(stock_info) > 0:
        print(f"   ✓ 成功获取实时行情")
        print(f"   {TEST_STOCK} 信息:\n{stock_info.to_string()}")
    else:
        print(f"   ✓ 获取到 {len(df)} 只股票，但未找到 {TEST_STOCK}")
except Exception as e:
    print(f"   ✗ 失败: {e}")

# 3. 个股资金流向
print("\n3. 个股资金流向 (stock_individual_fund_flow)")
try:
    df = ak.stock_individual_fund_flow(stock=TEST_STOCK, market="sh")
    print(f"   ✓ 成功获取资金流向数据")
    print(f"   最近5条:\n{df.tail()}")
except Exception as e:
    print(f"   ✗ 失败: {e}")

# 4. 板块资金流向
print("\n4. 板块资金流向 (stock_board_industry_fund_flow_em)")
try:
    df = ak.stock_board_industry_fund_flow_em()
    print(f"   ✓ 成功获取板块资金流向")
    print(f"   前5个板块:\n{df.head()}")
except Exception as e:
    print(f"   ✗ 失败: {e}")

# ==================== 基本面数据 ====================

print("\n" + "-" * 40)
print("【基本面数据测试】")
print("-" * 40)

# 5. 资产负债表
print("\n5. 资产负债表 (stock_balance_sheet_by_report_em)")
try:
    df = ak.stock_balance_sheet_by_report_em(symbol=TEST_STOCK)
    print(f"   ✓ 成功获取资产负债表")
    print(f"   列: {list(df.columns)[:10]}...")
    print(f"   最近报告:\n{df.head(1).to_string()}")
except Exception as e:
    print(f"   ✗ 失败: {e}")

# 6. 利润表
print("\n6. 利润表 (stock_profit_sheet_by_report_em)")
try:
    df = ak.stock_profit_sheet_by_report_em(symbol=TEST_STOCK)
    print(f"   ✓ 成功获取利润表")
    print(f"   列: {list(df.columns)[:10]}...")
except Exception as e:
    print(f"   ✗ 失败: {e}")

# 7. 现金流量表
print("\n7. 现金流量表 (stock_cash_flow_sheet_by_report_em)")
try:
    df = ak.stock_cash_flow_sheet_by_report_em(symbol=TEST_STOCK)
    print(f"   ✓ 成功获取现金流量表")
    print(f"   列: {list(df.columns)[:10]}...")
except Exception as e:
    print(f"   ✗ 失败: {e}")

# 8. 财务指标
print("\n8. 财务指标 (stock_financial_analysis_indicator)")
try:
    df = ak.stock_financial_analysis_indicator(symbol=TEST_STOCK)
    print(f"   ✓ 成功获取财务指标")
    print(f"   列: {list(df.columns)}")
except Exception as e:
    print(f"   ✗ 失败: {e}")

# 9. 十大股东
print("\n9. 十大股东 (stock_shareholder_top10_em)")
try:
    df = ak.stock_shareholder_top10_em(symbol=TEST_STOCK)
    print(f"   ✓ 成功获取十大股东")
    print(f"   数据:\n{df.to_string()}")
except Exception as e:
    print(f"   ✗ 失败: {e}")

# 10. 主营构成
print("\n10. 主营构成 (stock_zygc_em)")
try:
    df = ak.stock_zygc_em(symbol=TEST_STOCK)
    print(f"   ✓ 成功获取主营构成")
    print(f"   数据:\n{df.to_string()}")
except Exception as e:
    print(f"   ✗ 失败: {e}")

# ==================== 新闻/研报数据 ====================

print("\n" + "-" * 40)
print("【新闻/研报数据测试】")
print("-" * 40)

# 11. 个股新闻
print("\n11. 个股新闻 (stock_news_em)")
try:
    df = ak.stock_news_em(symbol=TEST_STOCK)
    print(f"   ✓ 成功获取个股新闻")
    print(f"   条数: {len(df)}")
    if len(df) > 0:
        print(f"   最近新闻:\n{df.head(3).to_string()}")
except Exception as e:
    print(f"   ✗ 失败: {e}")

# 12. 个股研报
print("\n12. 个股研报 (stock_research_report_em)")
try:
    df = ak.stock_research_report_em(symbol=TEST_STOCK)
    print(f"   ✓ 成功获取个股研报")
    print(f"   条数: {len(df)}")
    if len(df) > 0:
        print(f"   列: {list(df.columns)}")
except Exception as e:
    print(f"   ✗ 失败: {e}")

# ==================== 板块/行业数据 ====================

print("\n" + "-" * 40)
print("【板块/行业数据测试】")
print("-" * 40)

# 13. 行业板块
print("\n13. 行业板块列表 (stock_board_industry_name_em)")
try:
    df = ak.stock_board_industry_name_em()
    print(f"   ✓ 成功获取行业板块列表")
    print(f"   板块数: {len(df)}")
    print(f"   前10板块:\n{df.head(10).to_string()}")
except Exception as e:
    print(f"   ✗ 失败: {e}")

# 14. 概念板块
print("\n14. 概念板块列表 (stock_board_concept_name_em)")
try:
    df = ak.stock_board_concept_name_em()
    print(f"   ✓ 成功获取概念板块列表")
    print(f"   概念数: {len(df)}")
    print(f"   前10概念:\n{df.head(10).to_string()}")
except Exception as e:
    print(f"   ✗ 失败: {e}")

# ==================== 总结 ====================

print("\n" + "=" * 60)
print("测试完成")
print("=" * 60)
print("""
关键结论:
- 日线行情: 用于技术分析（K线、均线、MACD、RSI）
- 资金流向: 用于判断主力资金动向
- 财务报表: 用于基本面分析（资产负债、利润、现金流）
- 财务指标: 用于快速评估公司质量（ROE、毛利率等）
- 新闻/研报: 用于获取市场情绪和研究观点
- 板块数据: 用于识别热点板块和龙头股
""")