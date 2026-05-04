"""Workflow 状态定义"""

from typing import TypedDict, Annotated, Optional
from langgraph.graph.message import add_messages


class MarketAnalysisState(TypedDict):
    """市场分析 workflow 状态"""
    messages: Annotated[list, add_messages]
    market_sentiment: str  # 牛市/熊市/震荡市
    sentiment_confidence: float  # 置信度
    market_trend_detail: dict  # 详细趋势分析结果
    bull_bear_cycles: list[dict]  # 历史牛熊周期列表
    hot_sectors: list[dict]  # 热点板块
    industries: list[dict]  # 行业分析
    recommended_stocks: list[dict]  # 推荐个股
    current_step: str  # 当前步骤
    logs: list[str]  # 日志


class StockAnalysisState(TypedDict):
    """股票分析 workflow 状态（完整 9 节点）"""
    messages: Annotated[list, add_messages]

    # 初始化节点
    stock_code: str  # 股票代码
    stock_name: str  # 股票名称
    current_position: float  # 当前持仓金额
    system_status: dict  # 系统状态
    portfolio: dict  # 持仓配置

    # 基本面节点
    fundamentals: dict  # 基本面分析结果

    # 技术面节点
    technical: dict  # 技术面分析结果

    # 汇总节点
    analysis_summary: dict  # 综合分析摘要

    # 辩论节点
    bull_arguments: list[str]  # 正方论点
    bear_arguments: list[str]  # 反方论点
    debate_rounds: int  # 辩论轮数
    debate_history: list[str]  # 辩论历史

    # 决策节点（含归因和反事实）
    final_decision: dict  # 最终决策
    causal_chain: list[dict]  # 归因链
    counterfactual: dict  # 反事实分析

    # 持仓建议节点
    suggested_action: str  # 建议操作
    suggested_amount: float  # 建议金额
    position_advice: dict  # 持仓建议详情
    risk_warnings: list[str]  # 风险提示

    # 推送节点
    push_result: dict  # 推送结果

    # 元数据
    logs: list[str]  # 日志
    error: Optional[str]  # 错误信息


class BacktestState(TypedDict):
    """回测 workflow 状态（4 节点）"""
    messages: Annotated[list, add_messages]

    # Init Node - 解析用户需求
    description: str  # 用户策略描述
    params: dict  # 回测参数 (start_date, end_date, initial_capital等)
    strategy_params: dict  # 解析后的策略参数

    # Backtest Node - 执行回测
    strategy_code: str  # 生成的策略代码
    trades: list[dict]  # 交易记录
    equity_curve: list[dict]  # 净值曲线
    summary: dict  # 回测摘要 (total_return, win_rate等)

    # Reflection Node - Advisor评估
    reflection: dict  # AI反思结果
    strengths: list[str]  # 策略优势
    weaknesses: list[str]  # 策略劣势
    improvements: list[str]  # 改进建议
    risk_warnings: list[str]  # 风险提示

    # Report Node - 生成报告
    monthly_settlements: list[dict]  # 月度结算
    strategy_log: str  # markdown日志内容
    strategy_log_path: str  # 日志文件路径

    # 元数据
    task_id: str  # 任务ID
    current_step: str  # 当前步骤
    logs: list[str]  # 执行日志
    error: Optional[str]  # 错误信息