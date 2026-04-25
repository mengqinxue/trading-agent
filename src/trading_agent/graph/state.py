"""
Workflow state definitions V2
Based on refined business requirements
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


class PositionAction(str, Enum):
    NEW_BUY = "new_buy"
    ADD = "add"
    REDUCE = "reduce"
    CLEAR = "clear"
    HOLD = "hold"
    SKIP = "skip"


# Models
class Stock(BaseModel):
    """Stock information"""
    code: str
    name: str
    market: str
    sector: Optional[str] = None


class Sector(BaseModel):
    """Hot sector"""
    name: str
    heat_score: float
    leaders: List[str]
    news_count: int


class TechAnalysisResult(BaseModel):
    """Technical analysis result"""
    stock_code: str
    stock_name: str
    trend_direction: str  # up/down/neutral
    signals: List[str]
    recommendation: Recommendation
    confidence: float  # 0-1
    arguments: List[str]


class FundAnalysisResult(BaseModel):
    """Fundamental analysis result"""
    stock_code: str
    stock_name: str
    fundamentals_score: float  # 0-100
    risks: List[str]
    positives: List[str]
    recommendation: Recommendation
    confidence: float
    arguments: List[str]


class AnalysisSummary(BaseModel):
    """Aggregated analysis summary"""
    stock_code: str
    stock_name: str
    tech_score: float  # 0-100
    fund_score: float  # 0-100
    combined_score: float
    buy_arguments: List[str]
    sell_arguments: List[str]


class DebateRound(BaseModel):
    """Debate round record"""
    stock_code: str
    round: int
    buyer_argument: str
    seller_argument: str
    buyer_new: bool  # Whether buyer introduced new argument
    seller_new: bool


class CausalChain(BaseModel):
    """归因分析因果链"""
    chain: List[dict]  # [{step: "A", description: "热点板块炒作", evidence: "TrendRadar热度"}]
    final_conclusion: str  # 最终结论
    confidence: float  # 因果链置信度


class CounterfactualScenario(BaseModel):
    """反事实推断场景"""
    scenario: str  # 场景描述：如"下跌10%"
    impact: str  # 影响：如"持仓市值减少 X 元"
    probability: float  # 发生概率估计
    expected_behavior: str  # 预期行为
    recommendation: str  # 建议


class CounterfactualAnalysis(BaseModel):
    """反事实推断结果"""
    scenarios: List[CounterfactualScenario]
    worst_case: str  # 最坏情况
    mitigation: str  # 风险缓解措施
    exit_strategy: str  # 退出策略


class Decision(BaseModel):
    """Final decision"""
    stock_code: str
    stock_name: str
    action: Recommendation
    confidence: float
    reasoning: str
    should_enter: bool
    risk_level: str  # high/medium/low
    causal_chain: Optional[CausalChain] = None  # 归因分析
    counterfactual: Optional[CounterfactualAnalysis] = None  # 反事实推断


class PositionAdvice(BaseModel):
    """Position advice"""
    stock_code: str
    position_action: PositionAction
    suggested_amount: float  # Position size percentage
    stop_loss: Optional[float]
    take_profit: Optional[float]
    current_position: Optional[dict]


# Workflow State (TypedDict for LangGraph)
class WorkflowState(TypedDict):
    """
    LangGraph workflow state V2
    
    This state flows through all nodes in the workflow.
    Each node reads from and writes to this state.
    """
    # Init
    run_id: str
    run_type: str  # pre_market / post_market
    system_status: dict
    portfolio: dict
    
    # Step 1: Init
    init_status: str
    
    # Step 2: Screener
    screener_status: str
    hot_news: List[dict]  # Raw hot news from TrendRadar
    hot_sectors: List[Sector]
    candidate_stocks: List[Stock]
    
    # Step 3: Analysis (parallel)
    tech_analyst_status: str
    fund_analyst_status: str
    tech_results: List[TechAnalysisResult]
    fund_results: List[FundAnalysisResult]
    
    # Step 4: Aggregator
    aggregator_status: str
    analysis_summary: List[AnalysisSummary]
    
    # Step 5: Debater
    debater_status: str
    debate_log: List[DebateRound]
    buyer_score: float
    seller_score: float
    consensus: bool
    
    # Step 6: Judge
    judge_status: str
    decision: Decision
    
    # Step 7: Position Advisor
    position_status: str
    position_advice: PositionAdvice
    
    # Step 8: Push
    push_status: str
    push_result: dict
    
    # Error handling
    error_step: Optional[str]
    error_message: Optional[str]
    
    # Timing
    start_time: str
    current_step_start: str
    end_time: Optional[str]

    # Overall workflow status
    status: Optional[str]  # Overall workflow status (completed/failed)


def create_initial_state(run_type: RunType = RunType.POST_MARKET, portfolio: dict = None) -> WorkflowState:
    """Create initial workflow state"""
    now = datetime.now().isoformat()
    
    return WorkflowState(
        run_id=datetime.now().strftime("%Y%m%d-%H%M%S"),
        run_type=run_type.value,
        system_status={},
        portfolio=portfolio.get("portfolio", {}) if portfolio else {},
        
        init_status=StepStatus.PENDING.value,
        
        screener_status=StepStatus.PENDING.value,
        hot_news=[],
        hot_sectors=[],
        candidate_stocks=[],
        
        tech_analyst_status=StepStatus.PENDING.value,
        fund_analyst_status=StepStatus.PENDING.value,
        tech_results=[],
        fund_results=[],
        
        aggregator_status=StepStatus.PENDING.value,
        analysis_summary=[],
        
        debater_status=StepStatus.PENDING.value,
        debate_log=[],
        buyer_score=0.0,
        seller_score=0.0,
        consensus=False,
        
        judge_status=StepStatus.PENDING.value,
        decision={},
        
        position_status=StepStatus.PENDING.value,
        position_advice={},
        
        push_status=StepStatus.PENDING.value,
        push_result={},
        
        error_step=None,
        error_message=None,

        start_time=now,
        current_step_start=now,
        end_time=None,
        status=None,
    )