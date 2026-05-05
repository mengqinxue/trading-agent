"""市场分析 Workflow - 使用策略模块进行牛熊判断"""

from pathlib import Path
from typing import Optional, Dict, Any

from langgraph.graph import StateGraph, END

from src.workflows.state import MarketAnalysisState
from src.agents.market.sector_analyzer import SectorAnalyzer
from src.agents.market.industry_analyzer import IndustryAnalyzer
from src.agents.market.stock_screener import StockScreener
from src.core.llm import get_llm
from src.core.logger import logger
from src.data_sources import load_index_daily
from src.scheduler.workspace_manager import write_log

# 策略模块
from strategies import MarketTrendStrategy, BullBearCycleDetector


def create_market_analysis_workflow(log_folder: Optional[Path] = None):
    """创建市场分析 workflow"""

    llm = get_llm()

    # 策略实例
    trend_strategy = MarketTrendStrategy()
    cycle_detector = BullBearCycleDetector()

    sector_analyzer = SectorAnalyzer(llm)
    industry_analyzer = IndustryAnalyzer(llm)
    stock_screener = StockScreener(llm)

    def macro_node(state: MarketAnalysisState) -> dict:
        """宏观分析节点 - 使用策略模块判断牛熊"""
        if log_folder:
            write_log(log_folder, "=== Node: 宏观分析 [开始] ===")

        logger.info("执行宏观分析...")

        # 加载上证指数历史数据
        df = load_index_daily("000001")

        if df is None or df.empty:
            logger.warning("[宏观分析] 无法加载上证指数数据")
            if log_folder:
                write_log(log_folder, "无法加载上证指数数据，使用默认判断")

            return {
                "market_sentiment": "震荡市",
                "sentiment_confidence": 0.5,
                "market_trend_detail": {"status": "unknown"},
                "bull_bear_cycles": [],
                "logs": state.get("logs", []) + ["宏观分析完成（数据缺失）"],
                "current_step": "sector"
            }

        # 使用 MarketTrendStrategy 判断当前市场状态
        trend_result = trend_strategy.analyze(df)
        market_sentiment = trend_result.get("status", "震荡市")
        confidence = trend_result.get("confidence", 0.5)

        logger.info(f"[宏观分析] 当前市场状态: {market_sentiment}, 置信度: {confidence:.2f}")
        logger.info(f"[宏观分析] 趋势强度: {trend_result.get('trend_strength', 0)}")

        for signal in trend_result.get("signals", []):
            logger.info(f"[宏观分析] 信号: {signal}")

        if log_folder:
            write_log(log_folder, f"市场状态: {market_sentiment}")
            write_log(log_folder, f"置信度: {confidence:.2f}")
            write_log(log_folder, f"趋势强度: {trend_result.get('trend_strength', 0)}")
            for signal in trend_result.get("signals", []):
                write_log(log_folder, f"  - {signal}")

        # 可选：检测历史牛熊周期（用于参考）
        cycles = []
        try:
            cycles = cycle_detector.detect_cycles(df)
            cycle_summary = cycle_detector.get_cycle_summary(cycles)
            logger.info(f"[宏观分析] 历史周期数: {len(cycles)}")

            if log_folder:
                write_log(log_folder, f"历史周期数: {len(cycles)}")
                write_log(log_folder, f"牛市周期: {cycle_summary.get('bull_count', 0)} 个")
                write_log(log_folder, f"熊市周期: {cycle_summary.get('bear_count', 0)} 个")
        except Exception as e:
            logger.warning(f"[宏观分析] 周期检测失败: {e}")

        if log_folder:
            write_log(log_folder, "=== Node: 宏观分析 [结束] ===")

        return {
            "market_sentiment": market_sentiment,
            "sentiment_confidence": confidence,
            "market_trend_detail": trend_result,
            "bull_bear_cycles": cycles,
            "logs": state.get("logs", []) + ["宏观分析完成"],
            "current_step": "sector"
        }

    def sector_node(state: MarketAnalysisState) -> dict:
        """板块分析节点"""
        if log_folder:
            write_log(log_folder, "=== Node: 板块分析 [开始] ===")

        logger.info("执行板块分析...")

        # 使用策略模块获取板块数据
        from src.data_sources import get_hot_sectors

        try:
            sector_data = get_hot_sectors(top_n=10)
        except Exception as e:
            logger.warning(f"[板块分析] 获取板块数据失败: {e}")
            sector_data = []

        if log_folder:
            write_log(log_folder, f"获取板块数据: {len(sector_data)} 个板块")

        result = sector_analyzer.run({
            "sector_data": sector_data,
            "market_sentiment": state.get("market_sentiment", "")
        })

        hot_sectors = result.get("hot_sectors", [])
        logger.info(f"热点板块: {len(hot_sectors)} 个")

        if log_folder:
            sector_names = [s.get("name", "") for s in hot_sectors[:5]]
            write_log(log_folder, f"分析结果: 热点板块={sector_names}")
            write_log(log_folder, "=== Node: 板块分析 [结束] ===")

        return {
            "hot_sectors": hot_sectors,
            "logs": state.get("logs", []) + ["板块分析完成"],
            "current_step": "industry"
        }

    def industry_node(state: MarketAnalysisState) -> dict:
        """行业分析节点"""
        if log_folder:
            write_log(log_folder, "=== Node: 行业分析 [开始] ===")

        logger.info("执行行业分析...")

        result = industry_analyzer.run({
            "hot_sectors": state.get("hot_sectors", [])
        })

        industries = result.get("industries", [])
        logger.info(f"行业分析: {len(industries)} 个")

        if log_folder:
            industry_names = [i.get("name", "") for i in industries[:5]]
            write_log(log_folder, f"分析结果: 行业={industry_names}")
            write_log(log_folder, "=== Node: 行业分析 [结束] ===")

        return {
            "industries": industries,
            "logs": state.get("logs", []) + ["行业分析完成"],
            "current_step": "screener"
        }

    def screener_node(state: MarketAnalysisState) -> dict:
        """个股筛选节点"""
        if log_folder:
            write_log(log_folder, "=== Node: 个股筛选 [开始] ===")

        logger.info("执行个股筛选...")

        result = stock_screener.run({
            "industries": state.get("industries", []),
            "stock_data": []
        })

        recommended_stocks = result.get("recommended_stocks", [])
        logger.info(f"推荐个股: {len(recommended_stocks)} 个")

        if log_folder:
            stock_codes = [s.get("code", "") for s in recommended_stocks[:10]]
            write_log(log_folder, f"分析结果: 推荐个股={stock_codes}")
            write_log(log_folder, "=== Node: 个股筛选 [结束] ===")
            write_log(log_folder, "Workflow 执行完成")

        return {
            "recommended_stocks": recommended_stocks,
            "logs": state.get("logs", []) + ["个股筛选完成", "分析结束"],
            "current_step": "end"
        }

    workflow = StateGraph(MarketAnalysisState)

    workflow.add_node("macro", macro_node)
    workflow.add_node("sector", sector_node)
    workflow.add_node("industry", industry_node)
    workflow.add_node("screener", screener_node)

    workflow.add_edge("macro", "sector")
    workflow.add_edge("sector", "industry")
    workflow.add_edge("industry", "screener")
    workflow.add_edge("screener", END)

    workflow.set_entry_point("macro")

    return workflow.compile()


def run_market_analysis(log_folder: Optional[Path] = None) -> dict:
    """运行市场分析

    Args:
        log_folder: 日志目录（可选，None 表示不记录详细日志到文件）

    Returns:
        分析结果字典
    """
    if log_folder:
        write_log(log_folder, "初始化 Market Analysis Workflow")

    workflow = create_market_analysis_workflow(log_folder)

    initial_state = {
        "messages": [],
        "market_sentiment": "",
        "sentiment_confidence": 0.0,
        "market_trend_detail": {},
        "bull_bear_cycles": [],
        "hot_sectors": [],
        "industries": [],
        "recommended_stocks": [],
        "current_step": "macro",
        "logs": ["开始市场分析"]
    }

    result = workflow.invoke(initial_state)
    return result