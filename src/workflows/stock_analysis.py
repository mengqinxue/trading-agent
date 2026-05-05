"""股票分析 Workflow - 带日志记录（完整 9 节点）"""

from pathlib import Path
from typing import Optional

from langgraph.graph import StateGraph, END

from src.workflows.state import StockAnalysisState
from src.agents.stock.init import init_node
from src.agents.stock.fundamentals import FundamentalsAnalyzer
from src.agents.stock.technical import TechnicalAnalyzer
from src.agents.stock.aggregator import aggregator_node
from src.agents.stock.bull_advocate import BullAdvocate
from src.agents.stock.bear_advocate import BearAdvocate
from src.agents.stock.judge import Judge, judge_node
from src.agents.stock.position_advisor import PositionAdvisor
from src.agents.stock.feishu_push import feishu_push_node
from src.core.llm import get_llm
from src.core.logger import logger
from src.data_sources.data_adapter import get_adapter
from src.scheduler.workspace_manager import write_log

MAX_DEBATE_ROUNDS = 10


def create_stock_analysis_workflow(log_folder: Optional[Path] = None):
    """创建股票分析 workflow（完整 9 节点）

    流程：
    [Init] -> [基本面] -> [技术面] -> [汇总] -> [辩论] -> [Judge] -> [持仓建议] -> [推送]
    """

    llm = get_llm()
    data_adapter = get_adapter()  # 使用多数据源适配器

    fundamentals_analyzer = FundamentalsAnalyzer(llm)
    technical_analyzer = TechnicalAnalyzer(llm)
    bull_advocate = BullAdvocate(llm)
    bear_advocate = BearAdvocate(llm)
    judge = Judge(llm)
    position_advisor = PositionAdvisor(llm)

    def init_node_wrapper(state: StockAnalysisState) -> dict:
        """初始化节点"""
        return init_node(state, log_folder)

    def fundamentals_node(state: StockAnalysisState) -> dict:
        """基本面分析节点"""
        stock_code = state.get("stock_code", "")

        if log_folder:
            write_log(log_folder, "=== Node: 基本面分析 [开始] ===")

        logger.info(f"分析 {stock_code} 基本面...")

        stock_info = data_adapter.get_stock_info(stock_code)
        financial_data = data_adapter.get_stock_financial(stock_code)

        if log_folder:
            write_log(log_folder, f"股票名称: {stock_info.get('name', 'N/A')}")
            write_log(log_folder, f"行业: {stock_info.get('industry', 'N/A')}")

        result = fundamentals_analyzer.run({
            "stock_code": stock_code,
            "stock_info": stock_info,
            "financial_data": financial_data
        })

        score = result.get("score", "N/A")
        logger.info(f"基本面评分: {score}")

        if log_folder:
            write_log(log_folder, f"分析结果: 评分={score}")
            write_log(log_folder, f"优势: {result.get('strengths', [])}")
            write_log(log_folder, f"劣势: {result.get('weaknesses', [])}")
            write_log(log_folder, "=== Node: 基本面分析 [结束] ===")

        return {
            "stock_name": stock_info.get("name", ""),
            "fundamentals": result,
            "logs": state.get("logs", []) + ["基本面分析完成"]
        }

    def technical_node(state: StockAnalysisState) -> dict:
        """技术面分析节点"""
        stock_code = state.get("stock_code", "")

        if log_folder:
            write_log(log_folder, "=== Node: 技术面分析 [开始] ===")

        logger.info(f"分析 {stock_code} 技术面...")

        realtime_data = data_adapter.get_stock_realtime(stock_code)
        kline_data = data_adapter.get_stock_kline(stock_code, days=60)

        if log_folder:
            write_log(log_folder, f"当前价格: {realtime_data.get('price', 'N/A')}")
            write_log(log_folder, f"涨跌幅: {realtime_data.get('change', 'N/A')}%")

        result = technical_analyzer.run({
            "stock_code": stock_code,
            "realtime_data": realtime_data,
            "kline_data": kline_data
        })

        score = result.get("score", "N/A")
        trend = result.get("trend", "N/A")
        logger.info(f"技术面评分: {score}, 趋势: {trend}")

        if log_folder:
            write_log(log_folder, f"分析结果: 评分={score}, 趋势={trend}")
            write_log(log_folder, f"买入信号: {result.get('buy_signal', False)}")
            write_log(log_folder, f"卖出信号: {result.get('sell_signal', False)}")
            write_log(log_folder, "=== Node: 技术面分析 [结束] ===")

        return {
            "technical": result,
            "logs": state.get("logs", []) + ["技术面分析完成"]
        }

    def aggregator_node_wrapper(state: StockAnalysisState) -> dict:
        """汇总节点"""
        return aggregator_node(state, log_folder)

    def bull_node(state: StockAnalysisState) -> dict:
        """正方辩论节点"""
        debate_rounds = state.get("debate_rounds", 0) + 1

        if log_folder:
            write_log(log_folder, f"=== Node: 正方辩论 (第{debate_rounds}轮) [开始] ===")

        logger.info(f"正方发言（轮数 {debate_rounds}）...")

        # 使用汇总节点的论据作为基础
        analysis_summary = state.get("analysis_summary", {})
        buy_args = analysis_summary.get("buy_arguments", [])

        argument = bull_advocate.run({
            "stock_code": state.get("stock_code", ""),
            "fundamentals": state.get("fundamentals", {}),
            "technical": state.get("technical", {}),
            "bear_arguments": state.get("bear_arguments", []),
            "debate_rounds": state.get("debate_rounds", 0),
            "base_arguments": buy_args  # 传入基础论据
        })

        if log_folder:
            arg_preview = argument[:200] if len(argument) > 200 else argument
            write_log(log_folder, f"正方论点: {arg_preview}...")
            write_log(log_folder, "=== Node: 正方辩论 [结束] ===")

        current_arguments = state.get("bull_arguments", [])
        current_history = state.get("debate_history", [])

        return {
            "bull_arguments": current_arguments + [argument],
            "debate_history": current_history + [f"[正方轮{debate_rounds}] {argument[:100]}..."],
            "logs": state.get("logs", []) + ["正方发言完成"]
        }

    def bear_node(state: StockAnalysisState) -> dict:
        """反方辩论节点"""
        debate_rounds = state.get("debate_rounds", 0) + 1

        if log_folder:
            write_log(log_folder, f"=== Node: 反方辩论 (第{debate_rounds}轮) [开始] ===")

        logger.info(f"反方发言（轮数 {debate_rounds}）...")

        # 使用汇总节点的论据作为基础
        analysis_summary = state.get("analysis_summary", {})
        sell_args = analysis_summary.get("sell_arguments", [])

        argument = bear_advocate.run({
            "stock_code": state.get("stock_code", ""),
            "fundamentals": state.get("fundamentals", {}),
            "technical": state.get("technical", {}),
            "bull_arguments": state.get("bull_arguments", []),
            "debate_rounds": state.get("debate_rounds", 0),
            "base_arguments": sell_args  # 传入基础论据
        })

        if log_folder:
            arg_preview = argument[:200] if len(argument) > 200 else argument
            write_log(log_folder, f"反方论点: {arg_preview}...")
            write_log(log_folder, "=== Node: 反方辩论 [结束] ===")

        current_arguments = state.get("bear_arguments", [])
        current_history = state.get("debate_history", [])

        return {
            "bear_arguments": current_arguments + [argument],
            "debate_history": current_history + [f"[反方轮{debate_rounds}] {argument[:100]}..."],
            "debate_rounds": debate_rounds,
            "logs": state.get("logs", []) + ["反方发言完成"]
        }

    def should_continue_debate(state: StockAnalysisState) -> str:
        """判断是否继续辩论"""
        debate_rounds = state.get("debate_rounds", 0)

        if log_folder:
            write_log(log_folder, f"辩论轮数判断: 当前{debate_rounds}轮, 最大{MAX_DEBATE_ROUNDS}轮")

        if debate_rounds >= MAX_DEBATE_ROUNDS:
            logger.info(f"辩论结束（达到最大轮数 {MAX_DEBATE_ROUNDS}）")
            if log_folder:
                write_log(log_folder, f"辩论结束: 达到最大轮数 {MAX_DEBATE_ROUNDS}")
            return "end"

        if log_folder:
            write_log(log_folder, "继续辩论...")
        return "continue"

    def judge_node_wrapper(state: StockAnalysisState) -> dict:
        """决策节点"""
        return judge_node(state, log_folder)

    def position_node(state: StockAnalysisState) -> dict:
        """持仓建议节点"""
        if log_folder:
            write_log(log_folder, "=== Node: 持仓建议 [开始] ===")

        logger.info("生成持仓建议...")

        realtime_data = data_adapter.get_stock_realtime(state.get("stock_code", ""))
        current_price = realtime_data.get("price", 0)

        result = position_advisor.run({
            "stock_code": state.get("stock_code", ""),
            "stock_name": state.get("stock_name", ""),
            "current_price": current_price,
            "current_position": state.get("current_position", 0),
            "final_decision": state.get("final_decision", {}),
            "fundamentals": state.get("fundamentals", {}),
            "counterfactual": state.get("counterfactual", {})  # 传入反事实分析
        })

        action = result.get("action", "持有")
        amount = result.get("amount", 0)
        logger.info(f"建议: {action}")

        if log_folder:
            write_log(log_folder, f"建议操作: {action}")
            write_log(log_folder, f"建议金额: {amount} 元")
            write_log(log_folder, f"止损位: {result.get('stop_loss', 'N/A')}")
            write_log(log_folder, f"止盈位: {result.get('take_profit', 'N/A')}")
            write_log(log_folder, f"风险提示: {result.get('risk_warnings', [])}")
            write_log(log_folder, "=== Node: 持仓建议 [结束] ===")

        return {
            "suggested_action": action,
            "suggested_amount": amount,
            "position_advice": result,
            "risk_warnings": result.get("risk_warnings", []),
            "logs": state.get("logs", []) + ["持仓建议完成"]
        }

    def feishu_push_node_wrapper(state: StockAnalysisState) -> dict:
        """飞书推送节点"""
        return feishu_push_node(state, log_folder)

    workflow = StateGraph(StockAnalysisState)

    # 添加节点（完整 9 节点）
    workflow.add_node("init", init_node_wrapper)
    workflow.add_node("fundamentals", fundamentals_node)
    workflow.add_node("technical", technical_node)
    workflow.add_node("aggregator", aggregator_node_wrapper)
    workflow.add_node("bull", bull_node)
    workflow.add_node("bear", bear_node)
    workflow.add_node("judge", judge_node_wrapper)
    workflow.add_node("position", position_node)
    workflow.add_node("push", feishu_push_node_wrapper)

    # 定义边（完整流程）
    workflow.add_edge("init", "fundamentals")
    workflow.add_edge("fundamentals", "technical")
    workflow.add_edge("technical", "aggregator")
    workflow.add_edge("aggregator", "bull")
    workflow.add_edge("bull", "bear")

    workflow.add_conditional_edges(
        "bear",
        should_continue_debate,
        {
            "continue": "bull",
            "end": "judge"
        }
    )

    workflow.add_edge("judge", "position")
    workflow.add_edge("position", "push")
    workflow.add_edge("push", END)

    workflow.set_entry_point("init")

    return workflow.compile()


def run_stock_analysis(
    stock_code: str,
    current_position: float = 0,
    log_folder: Optional[Path] = None
) -> dict:
    """运行股票分析

    Args:
        stock_code: 股票代码
        current_position: 当前持仓金额
        log_folder: 日志目录（可选，None 表示不记录详细日志到文件）

    Returns:
        分析结果字典
    """
    # 清除缓存，确保获取最新数据
    from src.data_sources.data_adapter import DataAdapter
    DataAdapter.clear_cache()

    if log_folder:
        write_log(log_folder, f"初始化 Stock Analysis Workflow: {stock_code}")

    workflow = create_stock_analysis_workflow(log_folder)

    initial_state = {
        "messages": [],
        "stock_code": stock_code,
        "stock_name": "",
        "current_position": current_position,
        "fundamentals": {},
        "technical": {},
        "analysis_summary": {},
        "bull_arguments": [],
        "bear_arguments": [],
        "debate_rounds": 0,
        "debate_history": [],
        "final_decision": {},
        "causal_chain": [],
        "counterfactual": {},
        "suggested_action": "",
        "suggested_amount": 0,
        "position_advice": {},
        "risk_warnings": [],
        "system_status": {},
        "portfolio": {},
        "push_result": {},
        "logs": [f"开始分析股票 {stock_code}"]
    }

    result = workflow.invoke(initial_state)
    return result