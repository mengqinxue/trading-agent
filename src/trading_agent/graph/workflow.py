"""
LangGraph workflow definition V2
Based on refined business requirements

Flow: init → screener → [tech_analyst, fund_analyst] → aggregator → debater → judge → position_advisor → push
"""

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from .state import WorkflowState, StepStatus
from .nodes import (
    init_node,
    screener_node,
    tech_analyst_node,
    fund_analyst_node,
    aggregator_node,
    debater_node,
    judge_node,
    position_advisor_node,
    push_node,
)


def build_workflow() -> StateGraph:
    """
    Build the complete LangGraph workflow
    
    Flow:
    1. init - 系统初始化 + 检测
    2. screener - 粗筛候选池
    3. tech_analyst + fund_analyst (并行) - 技术/基本面分析
    4. aggregator - 汇总分析结果
    5. debater - 买卖方辩论 (最多20轮)
    6. judge - 决策
    7. position_advisor - 持仓建议
    8. push - 推送报告
    """
    
    workflow = StateGraph(WorkflowState)
    
    # Add nodes
    workflow.add_node("init", init_node)
    workflow.add_node("screener", screener_node)
    workflow.add_node("tech_analyst", tech_analyst_node)
    workflow.add_node("fund_analyst", fund_analyst_node)
    workflow.add_node("aggregator", aggregator_node)
    workflow.add_node("debater", debater_node)
    workflow.add_node("judge", judge_node)
    workflow.add_node("position_advisor", position_advisor_node)
    workflow.add_node("push", push_node)
    
    # Define entry point
    workflow.set_entry_point("init")
    
    # Define edges
    workflow.add_edge("init", "screener")
    
    # Parallel branch: screener → tech_analyst + fund_analyst
    workflow.add_edge("screener", "tech_analyst")
    workflow.add_edge("screener", "fund_analyst")
    
    # Merge to aggregator
    workflow.add_edge("tech_analyst", "aggregator")
    workflow.add_edge("fund_analyst", "aggregator")
    
    # Sequential from aggregator
    workflow.add_edge("aggregator", "debater")
    workflow.add_edge("debater", "judge")
    workflow.add_edge("judge", "position_advisor")
    workflow.add_edge("position_advisor", "push")
    
    # End
    workflow.add_edge("push", END)
    
    # Compile with memory checkpointer
    checkpointer = MemorySaver()
    app = workflow.compile(checkpointer=checkpointer)
    
    return app


def build_pre_market_workflow() -> StateGraph:
    """
    Build pre-market workflow (only screener)
    For 09:00 run: init → screener → END
    """
    
    workflow = StateGraph(WorkflowState)
    
    workflow.add_node("init", init_node)
    workflow.add_node("screener", screener_node)
    
    workflow.set_entry_point("init")
    workflow.add_edge("init", "screener")
    workflow.add_edge("screener", END)
    
    checkpointer = MemorySaver()
    app = workflow.compile(checkpointer=checkpointer)
    
    return app


# Global workflow instances
workflow_app = build_workflow()
pre_market_app = build_pre_market_workflow()