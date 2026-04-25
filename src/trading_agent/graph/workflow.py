"""
LangGraph workflow definition

This module defines the main workflow structure:
- Pre-market: screener → save candidates
- Post-market: load candidates → data_analyst + due_diligence → debater → judge → push
"""

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from .state import WorkflowState, StepStatus
from .nodes import (
    screener_node,
    data_analyst_node,
    due_diligence_node,
    debater_node,
    judge_node,
    push_node,
)


def build_workflow() -> StateGraph:
    """
    Build the LangGraph workflow

    Workflow structure:
    - Entry point: screener
    - screener → data_analyst (parallel with due_diligence)
    - data_analyst → debater
    - due_diligence → debater
    - debater → judge
    - judge → push
    - push → END
    """

    workflow = StateGraph(WorkflowState)

    # Add nodes
    workflow.add_node("screener", screener_node)
    workflow.add_node("data_analyst", data_analyst_node)
    workflow.add_node("due_diligence", due_diligence_node)
    workflow.add_node("debater", debater_node)
    workflow.add_node("judge", judge_node)
    workflow.add_node("push", push_node)

    # Define entry point
    workflow.set_entry_point("screener")

    # Define edges
    # screener → data_analyst (start technical analysis)
    workflow.add_edge("screener", "data_analyst")

    # screener → due_diligence (parallel start)
    workflow.add_edge("screener", "due_diligence")

    # Both analysis → debater (need to wait for both to complete)
    workflow.add_edge("data_analyst", "debater")
    workflow.add_edge("due_diligence", "debater")

    # debater → judge
    workflow.add_edge("debater", "judge")

    # judge → push
    workflow.add_edge("judge", "push")

    # push → END
    workflow.add_edge("push", END)

    # Compile with memory checkpointer
    checkpointer = MemorySaver()
    app = workflow.compile(checkpointer=checkpointer)

    return app


def build_pre_market_workflow() -> StateGraph:
    """
    Build simplified pre-market workflow (only screener)

    For 09:00 run: screener → save candidates → END
    """

    workflow = StateGraph(WorkflowState)

    workflow.add_node("screener", screener_node)

    workflow.set_entry_point("screener")
    workflow.add_edge("screener", END)

    checkpointer = MemorySaver()
    app = workflow.compile(checkpointer=checkpointer)

    return app


# Global workflow instances
workflow_app = build_workflow()
pre_market_app = build_pre_market_workflow()