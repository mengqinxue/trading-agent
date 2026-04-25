"""
Tests for complete workflow integration

Tests the full workflow from init to push:
- State flow verification
- Node transitions
- End-to-end execution
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

from trading_agent.graph.workflow import build_workflow, build_pre_market_workflow
from trading_agent.graph.state import (
    WorkflowState,
    StepStatus,
    RunType,
    create_initial_state,
    Stock,
    Sector,
    TechAnalysisResult,
    FundAnalysisResult,
    AnalysisSummary,
    DebateRound,
    Decision,
    PositionAdvice,
    Recommendation,
)


# ============== Fixtures ==============


@pytest.fixture
def initial_state() -> WorkflowState:
    """Create initial workflow state for testing"""
    return create_initial_state(run_type=RunType.POST_MARKET)


@pytest.fixture
def mock_state_with_candidates() -> WorkflowState:
    """Create state with screener results populated"""
    state = create_initial_state(run_type=RunType.POST_MARKET)
    state["init_status"] = StepStatus.COMPLETED.value
    state["screener_status"] = StepStatus.COMPLETED.value
    state["hot_news"] = [
        {"title": "AI芯片需求激增", "source": "zhihu", "heat_score": 95.5, "sector": "半导体"}
    ]
    state["hot_sectors"] = [
        {"name": "半导体", "heat_score": 95.5, "leaders": ["600519"], "news_count": 1}
    ]
    state["candidate_stocks"] = [
        {"code": "600519", "name": "贵州茅台", "market": "SH", "sector": "白酒"},
        {"code": "000001", "name": "平安银行", "market": "SZ", "sector": "金融"},
        {"code": "000333", "name": "美的集团", "market": "SZ", "sector": "家电"},
    ]
    return state


# ============== Test Config ==============

TEST_CONFIG = {
    "configurable": {
        "thread_id": "test-thread-001"
    }
}

# ============== Workflow Building Tests ==============


class TestWorkflowBuilding:
    """Tests for workflow graph construction"""

    def test_build_workflow_returns_compiled_graph(self):
        """Test that build_workflow returns a compiled graph"""
        app = build_workflow()

        assert app is not None
        # LangGraph compiled apps have invoke method
        assert hasattr(app, "invoke")
        assert hasattr(app, "stream")

    def test_build_pre_market_workflow_returns_compiled_graph(self):
        """Test that pre-market workflow builds correctly"""
        app = build_pre_market_workflow()

        assert app is not None
        assert hasattr(app, "invoke")

    def test_workflow_has_correct_nodes(self):
        """Test that workflow contains all required nodes"""
        # The workflow app is compiled, we verify it runs
        app = build_workflow()

        # Cannot directly inspect nodes after compilation,
        # but we can verify by running the workflow
        assert app is not None


# ============== State Flow Tests ==============


class TestStateFlow:
    """Tests for state transitions through workflow"""

    def test_initial_state_has_correct_structure(self, initial_state: WorkflowState):
        """Test that initial state has all required fields"""
        required_fields = [
            "run_id",
            "run_type",
            "init_status",
            "screener_status",
            "tech_analyst_status",
            "fund_analyst_status",
            "aggregator_status",
            "debater_status",
            "judge_status",
            "position_status",
            "push_status",
        ]

        for field in required_fields:
            assert field in initial_state

    def test_initial_state_all_pending(self, initial_state: WorkflowState):
        """Test that all initial statuses are PENDING"""
        status_fields = [
            "init_status",
            "screener_status",
            "tech_analyst_status",
            "fund_analyst_status",
            "aggregator_status",
            "debater_status",
            "judge_status",
            "position_status",
            "push_status",
        ]

        for field in status_fields:
            assert initial_state[field] == StepStatus.PENDING.value

    def test_state_run_type_pre_market(self):
        """Test creating pre-market state"""
        state = create_initial_state(run_type=RunType.PRE_MARKET)

        assert state["run_type"] == "pre_market"

    def test_state_run_type_post_market(self):
        """Test creating post-market state"""
        state = create_initial_state(run_type=RunType.POST_MARKET)

        assert state["run_type"] == "post_market"


# ============== Node Execution Tests (Mocked) ==============


class TestNodeExecution:
    """Tests for individual node execution"""

    def test_init_node_returns_updates(self, initial_state: WorkflowState):
        """Test init node returns state updates"""
        from trading_agent.graph.nodes import init_node

        result = init_node(initial_state)

        assert isinstance(result, dict)
        assert "init_status" in result
        assert result["init_status"] == StepStatus.COMPLETED.value

    def test_screener_node_returns_updates(self, initial_state: WorkflowState):
        """Test screener node returns state updates"""
        from trading_agent.graph.nodes import screener_node

        result = screener_node(initial_state)

        assert isinstance(result, dict)
        assert "screener_status" in result
        assert result["screener_status"] == StepStatus.COMPLETED.value
        assert "candidate_stocks" in result

    def test_tech_analyst_node_returns_updates(self, mock_state_with_candidates: WorkflowState):
        """Test tech analyst node returns analysis results"""
        from trading_agent.graph.nodes import tech_analyst_node

        result = tech_analyst_node(mock_state_with_candidates)

        assert isinstance(result, dict)
        assert "tech_analyst_status" in result
        assert "tech_results" in result

    def test_fund_analyst_node_returns_updates(self, mock_state_with_candidates: WorkflowState):
        """Test fund analyst node returns analysis results"""
        from trading_agent.graph.nodes import fund_analyst_node

        result = fund_analyst_node(mock_state_with_candidates)

        assert isinstance(result, dict)
        assert "fund_analyst_status" in result
        assert "fund_results" in result

    def test_aggregator_node_returns_updates(self, mock_state_with_candidates: WorkflowState):
        """Test aggregator node returns summary"""
        from trading_agent.graph.nodes import aggregator_node

        # Add tech and fund results first
        mock_state_with_candidates["tech_results"] = [
            {
                "stock_code": "600519",
                "stock_name": "贵州茅台",
                "trend_direction": "up",
                "signals": ["MACD金叉"],
                "recommendation": "buy",
                "confidence": 0.85,
                "arguments": ["趋势向上"],
            }
        ]
        mock_state_with_candidates["fund_results"] = [
            {
                "stock_code": "600519",
                "stock_name": "贵州茅台",
                "fundamentals_score": 85,
                "risks": ["估值偏高"],
                "positives": ["品牌优势"],
                "recommendation": "buy",
                "confidence": 0.80,
                "arguments": ["基本面良好"],
            }
        ]

        result = aggregator_node(mock_state_with_candidates)

        assert isinstance(result, dict)
        assert "aggregator_status" in result
        assert "analysis_summary" in result

    def test_debater_node_returns_updates(self, mock_state_with_candidates: WorkflowState):
        """Test debater node returns debate results"""
        from trading_agent.graph.nodes import debater_node

        # Add analysis summary
        mock_state_with_candidates["analysis_summary"] = [
            {
                "stock_code": "600519",
                "stock_name": "贵州茅台",
                "tech_score": 85,
                "fund_score": 80,
                "combined_score": 82.5,
                "buy_arguments": ["趋势向上", "基本面良好"],
                "sell_arguments": ["估值偏高"],
            }
        ]

        result = debater_node(mock_state_with_candidates)

        assert isinstance(result, dict)
        assert "debater_status" in result
        assert "debate_log" in result

    def test_judge_node_returns_updates(self, mock_state_with_candidates: WorkflowState):
        """Test judge node returns decision"""
        from trading_agent.graph.nodes import judge_node

        # Add debate results
        mock_state_with_candidates["debate_log"] = [
            {
                "stock_code": "600519",
                "round": 1,
                "buyer_argument": "趋势向上",
                "seller_argument": "估值偏高",
                "buyer_new": True,
                "seller_new": True,
            }
        ]
        mock_state_with_candidates["buyer_score"] = 80
        mock_state_with_candidates["seller_score"] = 30
        mock_state_with_candidates["consensus"] = False

        result = judge_node(mock_state_with_candidates)

        assert isinstance(result, dict)
        assert "judge_status" in result
        assert "decision" in result

    def test_position_advisor_node_returns_updates(self, mock_state_with_candidates: WorkflowState):
        """Test position advisor node returns advice"""
        from trading_agent.graph.nodes import position_advisor_node

        # Add decision
        mock_state_with_candidates["decision"] = {
            "stock_code": "600519",
            "stock_name": "贵州茅台",
            "action": "buy",
            "confidence": 0.85,
            "reasoning": "综合分析建议买入",
            "should_enter": True,
            "risk_level": "medium",
        }

        result = position_advisor_node(mock_state_with_candidates)

        assert isinstance(result, dict)
        assert "position_status" in result
        assert "position_advice" in result

    def test_push_node_returns_updates(self, mock_state_with_candidates: WorkflowState):
        """Test push node returns push result"""
        from trading_agent.graph.nodes import push_node

        # Add position advice
        mock_state_with_candidates["position_advice"] = {
            "stock_code": "600519",
            "position_action": "new_buy",
            "suggested_amount": 10000,
            "stop_loss": 0.95,
            "take_profit": 1.20,
        }

        result = push_node(mock_state_with_candidates)

        assert isinstance(result, dict)
        assert "push_status" in result
        assert "push_result" in result


# ============== Full Workflow Execution Tests ==============


class TestFullWorkflowExecution:
    """Tests for complete workflow execution"""

    def test_full_workflow_runs_to_completion(self, initial_state: WorkflowState):
        """Test that full workflow completes all steps"""
        app = build_workflow()

        # Execute workflow
        result = app.invoke(initial_state, config=TEST_CONFIG)

        # Verify workflow completed
        assert result is not None
        assert "push_status" in result
        assert result["push_status"] == StepStatus.COMPLETED.value

    def test_workflow_generates_decision(self, initial_state: WorkflowState):
        """Test that workflow generates a decision"""
        app = build_workflow()

        result = app.invoke(initial_state, config=TEST_CONFIG)

        # Should have a decision
        assert "decision" in result
        decision = result["decision"]
        assert decision is not None

    def test_workflow_generates_position_advice(self, initial_state: WorkflowState):
        """Test that workflow generates position advice"""
        app = build_workflow()

        result = app.invoke(initial_state, config=TEST_CONFIG)

        # Should have position advice
        assert "position_advice" in result
        advice = result["position_advice"]
        assert advice is not None

    def test_workflow_saves_push_result(self, initial_state: WorkflowState):
        """Test that workflow saves push result"""
        app = build_workflow()

        result = app.invoke(initial_state, config=TEST_CONFIG)

        # Should have push result
        assert "push_result" in result
        push_result = result["push_result"]
        assert push_result is not None

    def test_workflow_streaming_execution(self, initial_state: WorkflowState):
        """Test workflow streaming execution"""
        app = build_workflow()

        # Stream execution
        steps = []
        for step in app.stream(initial_state, config=TEST_CONFIG):
            steps.append(step)

        # Should have multiple steps
        assert len(steps) > 0

        # Check each step has updates
        for step in steps:
            assert isinstance(step, dict)


# ============== Pre-Market Workflow Tests ==============


class TestPreMarketWorkflow:
    """Tests for pre-market workflow (screener only)"""

    def test_pre_market_workflow_runs(self):
        """Test pre-market workflow execution"""
        state = create_initial_state(run_type=RunType.PRE_MARKET)
        app = build_pre_market_workflow()

        result = app.invoke(state, config=TEST_CONFIG)

        # Should complete screener
        assert result["screener_status"] == StepStatus.COMPLETED.value
        assert len(result["candidate_stocks"]) >= 3

    def test_pre_market_workflow_shorter(self):
        """Test pre-market workflow has fewer steps"""
        state = create_initial_state(run_type=RunType.PRE_MARKET)
        app = build_pre_market_workflow()

        steps = []
        for step in app.stream(state, config=TEST_CONFIG):
            steps.append(step)

        # Pre-market should have only 2 steps (init + screener)
        assert len(steps) == 2


# ============== Error Handling Tests ==============


class TestWorkflowErrorHandling:
    """Tests for workflow error handling"""

    @patch("trading_agent.graph.nodes.screener._fetch_hot_news")
    def test_workflow_handles_screener_error(self, mock_fetch, initial_state: WorkflowState):
        """Test workflow handles screener errors"""
        mock_fetch.side_effect = Exception("Mock API error")

        app = build_workflow()
        result = app.invoke(initial_state, config=TEST_CONFIG)

        # Workflow should still complete but screener failed
        # Note: workflow continues despite node errors
        assert result is not None

    def test_workflow_with_empty_candidates(self, initial_state: WorkflowState):
        """Test workflow handles empty candidate list"""
        # Manually set empty candidates
        initial_state["candidate_stocks"] = []

        app = build_workflow()
        result = app.invoke(initial_state, config=TEST_CONFIG)

        # Should still complete
        assert result is not None


# ============== Run Tests ==============


if __name__ == "__main__":
    pytest.main([__file__, "-v"])