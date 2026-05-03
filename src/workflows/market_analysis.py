"""市场分析 Workflow - 带日志记录"""

from pathlib import Path
from typing import Optional

from langgraph.graph import StateGraph, END

from src.workflows.state import MarketAnalysisState
from src.agents.market.macro_analyzer import MarketMacroAnalyzer
from src.agents.market.sector_analyzer import SectorAnalyzer
from src.agents.market.industry_analyzer import IndustryAnalyzer
from src.agents.market.stock_screener import StockScreener
from src.core.llm import get_llm
from src.core.logger import logger
from src.data_sources.data_adapter import get_adapter
from src.scheduler.workspace_manager import write_log


def create_market_analysis_workflow(log_folder: Optional[Path] = None):
    """创建市场分析 workflow"""

    llm = get_llm()
    data_adapter = get_adapter()  # 使用多数据源适配器

    macro_analyzer = MarketMacroAnalyzer(llm)
    sector_analyzer = SectorAnalyzer(llm)
    industry_analyzer = IndustryAnalyzer(llm)
    stock_screener = StockScreener(llm)

    def macro_node(state: MarketAnalysisState) -> dict:
        """宏观分析节点"""
        if log_folder:
            write_log(log_folder, "=== Node: 宏观分析 [开始] ===")

        logger.info("执行宏观分析...")

        market_data = data_adapter.get_market_overview()

        if log_folder:
            write_log(log_folder, f"获取市场数据: {list(market_data.keys())}")

        result = macro_analyzer.run({"market_data": market_data})

        sentiment = result.get("market_sentiment", "震荡市")
        logger.info(f"宏观分析结果: {sentiment}")

        if log_folder:
            write_log(log_folder, f"分析结果: 市场形势={sentiment}, 置信度={result.get('confidence', 0)}")
            write_log(log_folder, "=== Node: 宏观分析 [结束] ===")

        return {
            "market_sentiment": sentiment,
            "logs": state.get("logs", []) + ["宏观分析完成"],
            "current_step": "sector"
        }

    def sector_node(state: MarketAnalysisState) -> dict:
        """板块分析节点"""
        if log_folder:
            write_log(log_folder, "=== Node: 板块分析 [开始] ===")

        logger.info("执行板块分析...")

        sector_data = data_adapter.get_hot_sectors(top_n=10)

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


def run_market_analysis_with_logging(log_folder: Path) -> dict:
    """运行市场分析（带日志记录）"""
    write_log(log_folder, "初始化 Market Analysis Workflow")

    workflow = create_market_analysis_workflow(log_folder)

    initial_state = {
        "messages": [],
        "market_sentiment": "",
        "hot_sectors": [],
        "industries": [],
        "recommended_stocks": [],
        "current_step": "macro",
        "logs": ["开始市场分析"]
    }

    result = workflow.invoke(initial_state)
    return result


def run_market_analysis() -> dict:
    """运行市场分析（无日志记录，兼容旧接口）"""
    workflow = create_market_analysis_workflow()

    initial_state = {
        "messages": [],
        "market_sentiment": "",
        "hot_sectors": [],
        "industries": [],
        "recommended_stocks": [],
        "current_step": "macro",
        "logs": ["开始市场分析"]
    }

    result = workflow.invoke(initial_state)
    return result