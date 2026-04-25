"""
Tests for Screener node

Tests the screener_node business logic including:
- Hot news fetching
- Sector analysis
- Leader identification
- Candidate generation
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from trading_agent.graph.nodes.screener import (
    screener_node,
    _fetch_hot_news,
    _analyze_hot_sectors,
    _identify_leaders,
    _save_candidates,
    SECTOR_LEADERS,
)
from trading_agent.graph.state import (
    WorkflowState,
    StepStatus,
    Stock,
    Sector,
    create_initial_state,
)
from trading_agent.data_sources import HotNewsItem


# ============== Fixtures ==============


@pytest.fixture
def sample_state() -> WorkflowState:
    """Create a sample workflow state for testing"""
    return create_initial_state()


@pytest.fixture
def sample_hot_news() -> list[HotNewsItem]:
    """Create sample hot news for testing"""
    return [
        HotNewsItem(
            title="AI芯片需求激增，英伟达股价创历史新高",
            source="zhihu",
            heat_score=95.5,
            sector="半导体",
            rank=1,
        ),
        HotNewsItem(
            title="新能源汽车销量突破百万，比亚迪领跑市场",
            source="weibo",
            heat_score=88.2,
            sector="新能源汽车",
            rank=2,
        ),
        HotNewsItem(
            title="央行降准释放流动性，A股市场迎来利好",
            source="toutiao",
            heat_score=82.0,
            sector="金融",
            rank=3,
        ),
        HotNewsItem(
            title="茅台年报公布，净利润同比增长15%",
            source="zhihu",
            heat_score=75.8,
            sector="白酒",
            rank=4,
        ),
        HotNewsItem(
            title="光伏组件价格触底，行业整合加速",
            source="weibo",
            heat_score=70.3,
            sector="光伏",
            rank=5,
        ),
    ]


@pytest.fixture
def sample_sectors() -> list[Sector]:
    """Create sample hot sectors for testing"""
    return [
        Sector(name="半导体", heat_score=95.5, leaders=["000063"], news_count=1),
        Sector(name="新能源汽车", heat_score=88.2, leaders=["000333"], news_count=1),
        Sector(name="金融", heat_score=82.0, leaders=["000001", "600036"], news_count=1),
    ]


# ============== Test: screener_node ==============


class TestScreenerNode:
    """Tests for the main screener_node function"""

    def test_screener_node_returns_updates(self, sample_state: WorkflowState):
        """Test that screener_node returns a dict of updates"""
        result = screener_node(sample_state)

        assert isinstance(result, dict)
        assert "screener_status" in result
        assert "hot_news" in result
        assert "hot_sectors" in result
        assert "candidate_stocks" in result

    def test_screener_node_status_running_to_completed(self, sample_state: WorkflowState):
        """Test that screener_node transitions from RUNNING to COMPLETED"""
        result = screener_node(sample_state)

        assert result["screener_status"] == StepStatus.COMPLETED.value

    def test_screener_node_generates_candidates(self, sample_state: WorkflowState):
        """Test that screener_node generates candidate stocks"""
        result = screener_node(sample_state)

        candidates = result.get("candidate_stocks", [])
        assert len(candidates) >= 3  # At least 3 candidates

        # Check candidate structure
        for candidate in candidates:
            assert "code" in candidate
            assert "name" in candidate
            assert "market" in candidate

    def test_screener_node_identifies_sectors(self, sample_state: WorkflowState):
        """Test that screener_node identifies hot sectors"""
        result = screener_node(sample_state)

        sectors = result.get("hot_sectors", [])
        assert len(sectors) > 0

        # Check sector structure
        for sector in sectors:
            assert "name" in sector
            assert "heat_score" in sector
            assert "leaders" in sector

    def test_screener_node_saves_candidates(self, sample_state: WorkflowState):
        """Test that screener_node saves candidates to file"""
        result = screener_node(sample_state)

        # Check candidates directory has files
        settings_path = Path("data/candidates")
        if settings_path.exists():
            files = list(settings_path.glob("candidates_*.json"))
            # Should have at least one file after running
            assert len(files) >= 1


# ============== Test: _fetch_hot_news ==============


class TestFetchHotNews:
    """Tests for hot news fetching"""

    def test_fetch_hot_news_returns_list(self):
        """Test that _fetch_hot_news returns a list"""
        news = _fetch_hot_news("test_run")

        assert isinstance(news, list)

    def test_fetch_hot_news_returns_hot_news_items(self):
        """Test that fetched items are HotNewsItem"""
        news = _fetch_hot_news("test_run")

        for item in news:
            assert isinstance(item, HotNewsItem)

    def test_fetch_hot_news_has_required_fields(self):
        """Test that hot news items have required fields"""
        news = _fetch_hot_news("test_run")

        for item in news:
            assert item.title is not None
            assert item.source is not None


# ============== Test: _analyze_hot_sectors ==============


class TestAnalyzeHotSectors:
    """Tests for hot sector analysis"""

    def test_analyze_returns_list(self, sample_hot_news: list[HotNewsItem]):
        """Test that analysis returns a list"""
        sectors = _analyze_hot_sectors(sample_hot_news, "test_run")

        assert isinstance(sectors, list)

    def test_analyze_returns_sector_objects(self, sample_hot_news: list[HotNewsItem]):
        """Test that analysis returns Sector objects"""
        sectors = _analyze_hot_sectors(sample_hot_news, "test_run")

        for sector in sectors:
            assert isinstance(sector, Sector)

    def test_analyze_counts_news_per_sector(self, sample_hot_news: list[HotNewsItem]):
        """Test that analysis counts news per sector"""
        sectors = _analyze_hot_sectors(sample_hot_news, "test_run")

        # Should have sectors from sample news
        sector_names = [s.name for s in sectors]
        assert "半导体" in sector_names

    def test_analyze_calculates_heat_score(self, sample_hot_news: list[HotNewsItem]):
        """Test that analysis calculates heat score"""
        sectors = _analyze_hot_sectors(sample_hot_news, "test_run")

        for sector in sectors:
            assert sector.heat_score > 0
            assert sector.heat_score <= 100

    def test_analyze_sorts_by_heat(self, sample_hot_news: list[HotNewsItem]):
        """Test that analysis sorts sectors by heat score"""
        sectors = _analyze_hot_sectors(sample_hot_news, "test_run")

        # Should be sorted descending by heat_score
        heat_scores = [s.heat_score for s in sectors]
        assert heat_scores == sorted(heat_scores, reverse=True)

    def test_analyze_limits_to_top_sectors(self, sample_hot_news: list[HotNewsItem]):
        """Test that analysis limits to top 5 sectors"""
        sectors = _analyze_hot_sectors(sample_hot_news, "test_run")

        assert len(sectors) <= 5

    def test_analyze_empty_news(self):
        """Test analysis with empty news list"""
        sectors = _analyze_hot_sectors([], "test_run")

        assert sectors == []


# ============== Test: _identify_leaders ==============


class TestIdentifyLeaders:
    """Tests for leader identification"""

    def test_identify_returns_list(
        self,
        sample_sectors: list[Sector],
        sample_hot_news: list[HotNewsItem],
    ):
        """Test that identification returns a list"""
        leaders = _identify_leaders(sample_sectors, sample_hot_news, "test_run")

        assert isinstance(leaders, list)

    def test_identify_returns_stock_objects(
        self,
        sample_sectors: list[Sector],
        sample_hot_news: list[HotNewsItem],
    ):
        """Test that identification returns Stock objects"""
        leaders = _identify_leaders(sample_sectors, sample_hot_news, "test_run")

        for leader in leaders:
            assert isinstance(leader, Stock)

    def test_identify_has_required_fields(
        self,
        sample_sectors: list[Sector],
        sample_hot_news: list[HotNewsItem],
    ):
        """Test that leaders have required fields"""
        leaders = _identify_leaders(sample_sectors, sample_hot_news, "test_run")

        for leader in leaders:
            assert leader.code is not None
            assert leader.name is not None
            assert leader.market is not None

    def test_identify_no_duplicates(
        self,
        sample_sectors: list[Sector],
        sample_hot_news: list[HotNewsItem],
    ):
        """Test that identification doesn't produce duplicates"""
        leaders = _identify_leaders(sample_sectors, sample_hot_news, "test_run")

        codes = [l.code for l in leaders]
        assert len(codes) == len(set(codes))

    def test_identify_minimum_candidates(
        self,
        sample_sectors: list[Sector],
        sample_hot_news: list[HotNewsItem],
    ):
        """Test that identification produces at least 3 candidates"""
        leaders = _identify_leaders(sample_sectors, sample_hot_news, "test_run")

        assert len(leaders) >= 3

    def test_identify_from_sector_mapping(self):
        """Test that leaders come from sector mapping"""
        # Create sector that exists in mapping
        sector = Sector(name="白酒", heat_score=80, leaders=["600519", "000858"], news_count=1)
        leaders = _identify_leaders([sector], [], "test_run")

        # Should include at least mapped leaders
        codes = [l.code for l in leaders]
        assert "600519" in codes or "000858" in codes


# ============== Test: _save_candidates ==============


class TestSaveCandidates:
    """Tests for candidate saving"""

    def test_save_creates_file(
        self,
        sample_sectors: list[Sector],
        sample_hot_news: list[HotNewsItem],
    ):
        """Test that saving creates a file"""
        candidates = [
            Stock(code="600519", name="贵州茅台", market="SH", sector="白酒"),
            Stock(code="000001", name="平安银行", market="SZ", sector="金融"),
        ]

        _save_candidates(candidates, sample_sectors, sample_hot_news, "test_run")

        # Check file exists
        candidates_dir = Path("data/candidates")
        files = list(candidates_dir.glob("candidates_*.json"))
        assert len(files) >= 1

    def test_save_file_has_correct_structure(
        self,
        sample_sectors: list[Sector],
        sample_hot_news: list[HotNewsItem],
    ):
        """Test that saved file has correct JSON structure"""
        candidates = [
            Stock(code="600519", name="贵州茅台", market="SH", sector="白酒"),
        ]

        _save_candidates(candidates, sample_sectors, sample_hot_news, "test_run_2")

        # Load and check structure
        candidates_dir = Path("data/candidates")
        files = list(candidates_dir.glob("candidates_*test_run_2*.json"))
        assert len(files) >= 1

        with open(files[0], "r", encoding="utf-8") as f:
            data = json.load(f)

        assert "run_id" in data
        assert "candidates" in data
        assert "hot_sectors" in data
        assert data["candidate_count"] >= 1


# ============== Test: SECTOR_LEADERS Mapping ==============


class TestSectorLeadersMapping:
    """Tests for sector-leader mapping"""

    def test_mapping_has_entries(self):
        """Test that mapping has entries"""
        assert len(SECTOR_LEADERS) > 0

    def test_mapping_values_are_lists(self):
        """Test that mapping values are lists"""
        for leaders in SECTOR_LEADERS.values():
            assert isinstance(leaders, list)

    def test_mapping_entries_have_required_fields(self):
        """Test that mapping entries have required fields"""
        for leaders in SECTOR_LEADERS.values():
            for leader in leaders:
                assert "code" in leader
                assert "name" in leader
                assert "market" in leader


# ============== Integration Tests ==============


class TestScreenerIntegration:
    """Integration tests for full screener workflow"""

    def test_full_workflow(self, sample_state: WorkflowState):
        """Test full screener workflow"""
        result = screener_node(sample_state)

        # Check all expected outputs
        assert result["screener_status"] == StepStatus.COMPLETED.value
        assert len(result["hot_news"]) > 0
        assert len(result["hot_sectors"]) > 0
        assert len(result["candidate_stocks"]) >= 3

        # Check candidates have sectors assigned
        for candidate in result["candidate_stocks"]:
            if candidate.get("sector"):
                assert candidate["sector"] in [s["name"] for s in result["hot_sectors"]]

    def test_workflow_with_run_id(self):
        """Test workflow with custom run_id"""
        state = create_initial_state()
        state["run_id"] = "custom_test_001"

        result = screener_node(state)

        assert result["screener_status"] == StepStatus.COMPLETED.value

        # Check saved file contains run_id
        candidates_dir = Path("data/candidates")
        files = list(candidates_dir.glob("candidates_*custom_test_001*.json"))
        if files:
            with open(files[0], "r", encoding="utf-8") as f:
                data = json.load(f)
            assert data["run_id"] == "custom_test_001"


# ============== Error Handling Tests ==============


class TestErrorHandling:
    """Tests for error handling"""

    @patch("trading_agent.graph.nodes.screener._fetch_hot_news")
    def test_handles_fetch_error(self, mock_fetch, sample_state: WorkflowState):
        """Test that screener handles fetch errors gracefully"""
        mock_fetch.side_effect = Exception("Mock fetch error")

        result = screener_node(sample_state)

        # Should return FAILED status
        assert result["screener_status"] == StepStatus.FAILED.value
        assert result["error_step"] == "screener"
        assert "Mock fetch error" in result["error_message"]

    @patch("trading_agent.graph.nodes.screener._save_candidates")
    def test_handles_save_error(self, mock_save, sample_state: WorkflowState):
        """Test that screener handles save errors"""
        mock_save.side_effect = Exception("Mock save error")

        result = screener_node(sample_state)

        # Should return FAILED status
        assert result["screener_status"] == StepStatus.FAILED.value


# ============== Run Tests ==============


if __name__ == "__main__":
    pytest.main([__file__, "-v"])