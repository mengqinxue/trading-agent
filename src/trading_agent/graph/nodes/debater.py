"""
Debater node - 博弈辩论引擎 V2

Responsibilities:
- Buyer agent vs Seller agent debate
- Max 20 rounds
- Early termination: 5 rounds no new arguments
- Score both sides
- Generate debate log
"""

from datetime import datetime
from typing import Dict, List, Any

from trading_agent.graph.state import (
    WorkflowState,
    StepStatus,
    DebateRound,
    AnalysisSummary,
)
from trading_agent.utils.logger import get_logger

logger = get_logger("DEBATER")

# Debate configuration
MAX_ROUNDS = 20
NO_NEW_ARGS_THRESHOLD = 5  # Stop if 5 rounds no new arguments


def debater_node(state: WorkflowState) -> Dict:
    """
    Debater node entry function

    This node runs buyer vs seller debate on analysis summary.

    Debate mechanism:
    - Round 1: Both sides state core arguments
    - Round 2-N: Counter-arguments and rebuttals
    - Early stop: 5 consecutive rounds with no new arguments
    - Max rounds: 20

    Args:
        state: Current workflow state

    Returns:
        Dict with updated state fields
    """
    run_id = state.get("run_id", "unknown")
    logger.info(f"[{run_id}] Debater node started")

    # Check prerequisites
    aggregator_status = state.get("aggregator_status")
    logger.info(f"[{run_id}] Prerequisites: aggregator={aggregator_status}")

    # Update status to RUNNING
    updates: Dict[str, Any] = {
        "debater_status": StepStatus.RUNNING.value,
        "current_step_start": datetime.now().isoformat(),
    }

    try:
        # Load analysis summary
        analysis_summary = state.get("analysis_summary", [])
        portfolio = state.get("portfolio", {})
        hot_sectors = state.get("hot_sectors", [])

        logger.info(f"[{run_id}] Analysis entries: {len(analysis_summary)}")
        logger.info(f"[{run_id}] Hot sectors: {len(hot_sectors)}")

        if not analysis_summary:
            logger.warning(f"[{run_id}] No analysis summary to debate")
            updates["debate_log"] = []
            updates["buyer_score"] = 0.0
            updates["seller_score"] = 0.0
            updates["consensus"] = True
            updates["debater_status"] = StepStatus.COMPLETED.value
            return updates

        # Initialize debate log
        debate_log: List[DebateRound] = []
        total_buyer_score = 0.0
        total_seller_score = 0.0
        consensus = False

        # Run debate for each stock
        for summary in analysis_summary:
            # Convert to AnalysisSummary if needed
            if isinstance(summary, dict):
                summary_obj = AnalysisSummary(**summary)
            else:
                summary_obj = summary

            stock_code = summary_obj.stock_code
            stock_name = summary_obj.stock_name

            logger.info(f"[{run_id}] Starting debate for {stock_code} - {stock_name}")

            # Run debate for this stock
            stock_debate_log, buyer_score, seller_score, stock_consensus = _run_debate(
                summary_obj, portfolio, hot_sectors, run_id
            )

            # Append debate rounds
            debate_log.extend(stock_debate_log)

            # Aggregate scores
            total_buyer_score += buyer_score
            total_seller_score += seller_score

            if stock_consensus:
                consensus = True

            logger.info(
                f"[{run_id}] Debate completed for {stock_code}: "
                f"buyer={buyer_score:.1f}, seller={seller_score:.1f}, "
                f"consensus={stock_consensus}"
            )

        # Calculate average scores
        num_stocks = len(analysis_summary)
        avg_buyer_score = total_buyer_score / num_stocks if num_stocks > 0 else 0.0
        avg_seller_score = total_seller_score / num_stocks if num_stocks > 0 else 0.0

        # Update state
        updates["debate_log"] = [d.model_dump() for d in debate_log]
        updates["buyer_score"] = round(avg_buyer_score, 1)
        updates["seller_score"] = round(avg_seller_score, 1)
        updates["consensus"] = consensus
        updates["debater_status"] = StepStatus.COMPLETED.value

        logger.info(f"[{run_id}] Debater node completed successfully")
        logger.info(f"[{run_id}] Buyer score: {avg_buyer_score:.1f}, Seller score: {avg_seller_score:.1f}")
        logger.info(f"[{run_id}] Debate rounds: {len(debate_log)}")
        logger.info(f"[{run_id}] Consensus reached: {consensus}")

    except Exception as e:
        logger.error(f"[{run_id}] Debater node failed: {e}")
        updates["debater_status"] = StepStatus.FAILED.value
        updates["error_step"] = "debater"
        updates["error_message"] = str(e)
        updates["debate_log"] = []
        updates["buyer_score"] = 0.0
        updates["seller_score"] = 0.0
        updates["consensus"] = False

    return updates


# ============== Debate Engine ==============


def _run_debate(
    summary: AnalysisSummary,
    portfolio: dict,
    hot_sectors: List[Any],
    run_id: str,
) -> tuple[List[DebateRound], float, float, bool]:
    """
    Run buyer vs seller debate for a single stock

    Args:
        summary: AnalysisSummary for this stock
        portfolio: Current portfolio state
        hot_sectors: List of hot sectors
        run_id: Run ID for logging

    Returns:
        Tuple of (debate_rounds, buyer_score, seller_score, consensus)
    """
    stock_code = summary.stock_code

    # Initialize buyer and seller agents
    buyer_agent = BuyerAgent(summary, portfolio, hot_sectors, run_id)
    seller_agent = SellerAgent(summary, portfolio, hot_sectors, run_id)

    # Track arguments for early termination
    buyer_arguments_set: set = set()
    seller_arguments_set: set = set()
    no_new_args_count = 0

    debate_rounds: List[DebateRound] = []

    for round_num in range(1, MAX_ROUNDS + 1):
        logger.info(f"[{run_id}] Round {round_num} for {stock_code}")

        # Buyer argues
        buyer_arg, buyer_is_new = buyer_agent.argue(round_num, seller_agent.last_argument)

        # Seller argues
        seller_arg, seller_is_new = seller_agent.argue(round_num, buyer_agent.last_argument)

        # Track unique arguments
        buyer_key = buyer_arg[:100]  # Use first 100 chars as key
        seller_key = seller_arg[:100]

        buyer_is_new = buyer_key not in buyer_arguments_set
        seller_is_new = seller_key not in seller_arguments_set

        if buyer_is_new:
            buyer_arguments_set.add(buyer_key)
        if seller_is_new:
            seller_arguments_set.add(seller_key)

        # Record round
        debate_round = DebateRound(
            stock_code=stock_code,
            round=round_num,
            buyer_argument=buyer_arg,
            seller_argument=seller_arg,
            buyer_new=buyer_is_new,
            seller_new=seller_is_new,
        )
        debate_rounds.append(debate_round)

        logger.info(f"[{run_id}] Buyer argues: {buyer_arg[:80]}...")
        logger.info(f"[{run_id}] Seller argues: {seller_arg[:80]}...")
        logger.info(f"[{run_id}] New args: buyer={buyer_is_new}, seller={seller_is_new}")

        # Check early termination
        if not buyer_is_new and not seller_is_new:
            no_new_args_count += 1
            logger.info(f"[{run_id}] No new args count: {no_new_args_count}")
            if no_new_args_count >= NO_NEW_ARGS_THRESHOLD:
                logger.info(
                    f"[{run_id}] Early termination: {NO_NEW_ARGS_THRESHOLD} rounds no new args"
                )
                break
        else:
            no_new_args_count = 0

    # Calculate scores
    buyer_score = buyer_agent.calculate_score()
    seller_score = seller_agent.calculate_score()

    # Check consensus (if scores close enough)
    consensus = abs(buyer_score - seller_score) < 15

    logger.info(
        f"[{run_id}] Debate finished for {stock_code}: "
        f"{round_num} rounds, buyer={buyer_score:.1f}, seller={seller_score:.1f}"
    )

    return (debate_rounds, buyer_score, seller_score, consensus)


# ============== Buyer Agent ==============


class BuyerAgent:
    """Buyer side agent - argues for buying the stock"""

    def __init__(
        self,
        summary: AnalysisSummary,
        portfolio: dict,
        hot_sectors: List[Any],
        run_id: str,
    ):
        self.summary = summary
        self.portfolio = portfolio
        self.hot_sectors = hot_sectors
        self.run_id = run_id
        self.last_argument = ""
        self.arguments_made: List[str] = []
        self.score_points: float = 0.0

    def argue(self, round_num: int, seller_last_arg: str) -> tuple[str, bool]:
        """
        Generate buyer argument for this round

        Args:
            round_num: Current debate round
            seller_last_arg: Seller's last argument (to counter)

        Returns:
            Tuple of (argument, is_new_argument)
        """
        argument = ""

        if round_num == 1:
            # Round 1: Core thesis
            argument = self._core_thesis()
        else:
            # Counter-argument or new point
            argument = self._counter_or_new(seller_last_arg, round_num)

        self.last_argument = argument
        is_new = argument not in self.arguments_made
        if is_new:
            self.arguments_made.append(argument)

        return (argument, is_new)

    def _core_thesis(self) -> str:
        """Build core thesis for buying"""
        points = []

        # Use buy_arguments from summary
        if self.summary.buy_arguments:
            points.extend(self.summary.buy_arguments[:3])

        # Add sector heat if relevant
        for sector in self.hot_sectors:
            if isinstance(sector, dict):
                name = sector.get("name", "")
                heat = sector.get("heat_score", 0)
            else:
                name = sector.name
                heat = sector.heat_score
            if heat > 70:
                points.append(f"所属板块'{name}'热度高({heat:.1f})，行业景气度提升")

        # Add combined score
        if self.summary.combined_score >= 70:
            points.append(f"综合评分优秀({self.summary.combined_score:.1f})，买入信号强烈")

        if not points:
            points.append("技术面和基本面分析支持买入，风险可控")

        return f"【买入理由】{'; '.join(points)}"

    def _counter_or_new(self, seller_arg: str, round_num: int) -> str:
        """
        Counter seller's argument or introduce new point

        Args:
            seller_arg: Seller's last argument
            round_num: Current round

        Returns:
            Buyer's counter argument
        """
        # Check if we should counter seller
        if seller_arg:
            # Counter common sell arguments
            if "风险" in seller_arg or "下跌" in seller_arg:
                return self._counter_risk(seller_arg)
            if "估值" in seller_arg or "PE" in seller_arg:
                return self._counter_valuation(seller_arg)
            if "趋势" in seller_arg and "向下" in seller_arg:
                return self._counter_trend(seller_arg)

        # Or introduce new point
        return self._new_point(round_num)

    def _counter_risk(self, seller_arg: str) -> str:
        """Counter risk arguments"""
        if "高负债" in seller_arg:
            return "【反驳】负债率虽高但现金流稳定，且公司处于扩张期，财务风险可控"
        if "利润下滑" in seller_arg:
            return "【反驳】短期利润下滑是行业周期波动，但核心业务依然强劲，长期前景向好"
        if "估值偏高" in seller_arg:
            return "【反驳】高估值反映市场对其成长性的认可，PEG指标合理，不算泡沫"

        return "【反驳】风险因素已被市场充分认知，当前价格已计入风险溢价，适合建仓"

    def _counter_valuation(self, seller_arg: str) -> str:
        """Counter valuation arguments"""
        if self.summary.fund_score >= 70:
            return "【反驳】高估值配合强劲基本面，属于成长股特征，不应简单以PE判断"

        return "【反驳】估值相对行业龙头仍有优势，且业绩增长预期支撑当前估值"

    def _counter_trend(self, seller_arg: str) -> str:
        """Counter trend arguments"""
        if self.summary.tech_score >= 60:
            return "【反驳】短期技术回调是正常波动，中长期技术面依然支撑向上趋势"

        return "【反驳】技术面信号显示超卖迹象，可能迎来反弹，当前是布局时机"

    def _new_point(self, round_num: int) -> str:
        """Introduce new buy point"""
        # Remaining buy_arguments not yet used
        remaining_args = [
            a for a in self.summary.buy_arguments if a not in self.arguments_made
        ]

        if remaining_args:
            return f"【补充】{remaining_args[0]}"

        # Generate new points based on analysis
        if round_num <= 5:
            return self._generate_market_context_point()
        elif round_num <= 10:
            return self._generate_strategy_point()
        else:
            return self._generate_final_point()

    def _generate_market_context_point(self) -> str:
        """Generate market context argument"""
        return "【市场】当前市场情绪回暖，流动性充裕，有利于股票表现"

    def _generate_strategy_point(self) -> str:
        """Generate strategy argument"""
        return "【策略】建议分批建仓，首仓30%，后续根据走势加仓，降低风险"

    def _generate_final_point(self) -> str:
        """Generate final closing argument"""
        return f"【总结】综合技术面({self.summary.tech_score:.1f})和基本面({self.summary.fund_score:.1f})分析，建议买入"

    def calculate_score(self) -> float:
        """Calculate buyer's debate score"""
        # Base score from combined_score
        base_score = self.summary.combined_score * 0.5

        # Bonus for number of unique arguments
        arg_bonus = min(len(self.arguments_made) * 5, 30)

        # Bonus for strong buy signal
        if self.summary.combined_score >= 70:
            arg_bonus += 20

        total = base_score + arg_bonus

        return min(100, total)


# ============== Seller Agent ==============


class SellerAgent:
    """Seller side agent - argues for selling/avoiding the stock"""

    def __init__(
        self,
        summary: AnalysisSummary,
        portfolio: dict,
        hot_sectors: List[Any],
        run_id: str,
    ):
        self.summary = summary
        self.portfolio = portfolio
        self.hot_sectors = hot_sectors
        self.run_id = run_id
        self.last_argument = ""
        self.arguments_made: List[str] = []
        self.score_points: float = 0.0

    def argue(self, round_num: int, buyer_last_arg: str) -> tuple[str, bool]:
        """
        Generate seller argument for this round

        Args:
            round_num: Current debate round
            buyer_last_arg: Buyer's last argument (to counter)

        Returns:
            Tuple of (argument, is_new_argument)
        """
        argument = ""

        if round_num == 1:
            # Round 1: Core thesis
            argument = self._core_thesis()
        else:
            # Counter-argument or new point
            argument = self._counter_or_new(buyer_last_arg, round_num)

        self.last_argument = argument
        is_new = argument not in self.arguments_made
        if is_new:
            self.arguments_made.append(argument)

        return (argument, is_new)

    def _core_thesis(self) -> str:
        """Build core thesis for selling/avoiding"""
        points = []

        # Use sell_arguments from summary
        if self.summary.sell_arguments:
            points.extend(self.summary.sell_arguments[:3])

        # Add risk signals
        if self.summary.combined_score < 50:
            points.append(f"综合评分偏低({self.summary.combined_score:.1f})，建议谨慎")

        # Check if already holding with loss
        positions = self.portfolio.get("positions", [])
        for pos in positions:
            if pos.get("symbol") == self.summary.stock_code:
                pnl_pct = pos.get("pnl_pct", 0)
                if pnl_pct < -10:
                    points.append(f"当前持仓亏损{pnl_pct:.1f}%，建议止损离场")

        if not points:
            points.append("技术面和基本面存在风险因素，建议观望或卖出")

        return f"【卖出理由】{'; '.join(points)}"

    def _counter_or_new(self, buyer_arg: str, round_num: int) -> str:
        """
        Counter buyer's argument or introduce new point

        Args:
            buyer_arg: Buyer's last argument
            round_num: Current round

        Returns:
            Seller's counter argument
        """
        # Check if we should counter buyer
        if buyer_arg:
            # Counter common buy arguments
            if "热度" in buyer_arg or "板块" in buyer_arg:
                return self._counter_sector_heat(buyer_arg)
            if "买入" in buyer_arg or "评分优秀" in buyer_arg:
                return self._counter_buy_signal(buyer_arg)
            if "技术面" in buyer_arg and "向上" in buyer_arg:
                return self._counter_tech_up(buyer_arg)

        # Or introduce new point
        return self._new_point(round_num)

    def _counter_sector_heat(self, buyer_arg: str) -> str:
        """Counter sector heat arguments"""
        return "【反驳】板块热度往往领先股价表现，当前热度可能已透支未来涨幅，存在追高风险"

    def _counter_buy_signal(self, buyer_arg: str) -> str:
        """Counter buy signal arguments"""
        if self.summary.sell_arguments:
            return f"【反驳】评分虽高但存在风险因素：{self.summary.sell_arguments[0] if self.summary.sell_arguments else '估值偏高'}"

        return "【反驳】评分仅反映历史数据，未来不确定性因素多，买入风险不容忽视"

    def _counter_tech_up(self, buyer_arg: str) -> str:
        """Counter tech trend arguments"""
        return "【反驳】技术面上涨趋势可能已接近尾声，MACD/RSI指标显示超买迹象，回调风险增加"

    def _new_point(self, round_num: int) -> str:
        """Introduce new sell point"""
        # Remaining sell_arguments not yet used
        remaining_args = [
            a for a in self.summary.sell_arguments if a not in self.arguments_made
        ]

        if remaining_args:
            return f"【补充】{remaining_args[0]}"

        # Generate new points based on analysis
        if round_num <= 5:
            return self._generate_risk_point()
        elif round_num <= 10:
            return self._generate_market_risk_point()
        else:
            return self._generate_final_point()

    def _generate_risk_point(self) -> str:
        """Generate risk argument"""
        return "【风险】市场波动加剧，个股受大盘拖累风险高，建议控制仓位"

    def _generate_market_risk_point(self) -> str:
        """Generate market risk argument"""
        return "【宏观】宏观经济不确定性增加，可能影响行业景气度"

    def _generate_final_point(self) -> str:
        """Generate final closing argument"""
        return f"【总结】风险因素多于利好因素，评分({self.summary.combined_score:.1f})不足以支撑买入决策"

    def calculate_score(self) -> float:
        """Calculate seller's debate score"""
        # Base score from (100 - combined_score) - inverse
        base_score = (100 - self.summary.combined_score) * 0.5

        # Bonus for number of unique arguments
        arg_bonus = min(len(self.arguments_made) * 5, 30)

        # Bonus for strong sell signal
        if self.summary.combined_score < 40:
            arg_bonus += 20

        # Bonus for existing sell_arguments
        if len(self.summary.sell_arguments) >= 3:
            arg_bonus += 10

        total = base_score + arg_bonus

        return min(100, total)