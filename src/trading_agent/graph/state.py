"""
Workflow state definitions
"""

from typing import TypedDict, List, Optional
from datetime import datetime
from enum import Enum
from pydantic import BaseModel


# Enums
class Recommendation(str, Enum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


class RunType(str, Enum):
    PRE_MARKET = "pre_market"
    POST_MARKET = "post_market"


class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


# Models
class Stock(BaseModel):
    """股票信息"""
    code: str
    name: str
    market: str
    sector: Optional[str] = None


class Sector(BaseModel):
    """热点板块"""
    name: str
    heat_score: float
    leaders: List[str]
    news_count: int


class AnalysisResult(BaseModel):
    """分析结果"""
    stock: Stock
    recommendation: Recommendation
    confidence: float
    arguments: List[str]
    signals: List[str]


class DebateRound(BaseModel):
    """辩论回合"""
    round: int
    buyer_argument: str
    seller_argument: str


class DebateResult(BaseModel):
    """辩论结果"""
    stock: Stock
    rounds: List[DebateRound]
    consensus_reached: bool
    buyer_final: str
    seller_final: str
    summary: str


class Decision(BaseModel):
    """最终决策"""
    stock: Stock
    recommendation: Recommendation
    confidence: float
    position_advice: str
    reasoning: str
    risks: List[str]


# Workflow State (TypedDict for LangGraph)
class WorkflowState(TypedDict):
    """
    LangGraph workflow state

    This state flows through all nodes in the workflow.
    Each node reads from and writes to this state.
    """
    # Run metadata
    run_id: str
    run_type: str
    status: str

    # Step status tracking
    screener_status: str
    data_analyst_status: str
    due_diligence_status: str
    debater_status: str
    judge_status: str
    push_status: str

    # Portfolio context
    portfolio_positions: List[dict]
    portfolio_keywords: List[str]

    # Step 1: Screener outputs
    hot_news: List[dict]
    hot_sectors: List[Sector]
    candidate_stocks: List[Stock]

    # Step 2a: Data Analyst outputs
    data_analysis_results: List[AnalysisResult]

    # Step 2b: Due Diligence outputs
    due_diligence_results: List[AnalysisResult]

    # Step 3: Debater outputs
    debate_results: List[DebateResult]

    # Step 4: Judge outputs
    decisions: List[Decision]

    # Error handling
    error_step: Optional[str]
    error_message: Optional[str]

    # Timing
    start_time: str
    current_step_start: str
    end_time: Optional[str]


def create_initial_state(run_type: RunType, portfolio: dict = None) -> WorkflowState:
    """Create initial workflow state"""
    now = datetime.now().isoformat()

    return WorkflowState(
        run_id=datetime.now().strftime("%Y%m%d-%H%M%S"),
        run_type=run_type.value,
        status=StepStatus.PENDING.value,

        screener_status=StepStatus.PENDING.value,
        data_analyst_status=StepStatus.PENDING.value,
        due_diligence_status=StepStatus.PENDING.value,
        debater_status=StepStatus.PENDING.value,
        judge_status=StepStatus.PENDING.value,
        push_status=StepStatus.PENDING.value,

        portfolio_positions=portfolio.get("positions", []) if portfolio else [],
        portfolio_keywords=portfolio.get("keywords", []) if portfolio else [],

        hot_news=[],
        hot_sectors=[],
        candidate_stocks=[],

        data_analysis_results=[],
        due_diligence_results=[],
        debate_results=[],
        decisions=[],

        error_step=None,
        error_message=None,

        start_time=now,
        current_step_start=now,
        end_time=None,
    )