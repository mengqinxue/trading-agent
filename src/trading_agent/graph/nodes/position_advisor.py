"""
Position Advisor node - 持仓建议

Responsibilities:
- Check if stock is already in portfolio
- Determine position action (new_buy/add/reduce/clear)
- Calculate suggested position size
- Set stop-loss and take-profit levels
"""

from datetime import datetime
from typing import Dict, Any, Optional

from trading_agent.graph.state import (
    WorkflowState,
    StepStatus,
    PositionAction,
    PositionAdvice,
    Recommendation,
)
from trading_agent.utils.logger import get_logger

logger = get_logger("POSITION_ADVISOR")

# Position sizing configuration
MAX_POSITION_PERCENT = 30.0  # 单只股票最大仓位比例
MIN_POSITION_PERCENT = 5.0   # 单只股票最小仓位比例
DEFAULT_STOP_LOSS = -10.0    # 默认止损线 -10%
DEFAULT_TAKE_PROFIT = 20.0   # 默认止盈线 20%


def position_advisor_node(state: WorkflowState) -> Dict:
    """
    Position Advisor node entry function

    This node generates position advice based on decision and current portfolio.

    Logic:
    - If holding stock + buy decision → add position
    - If holding stock + sell decision → reduce/clear based on P&L
    - If not holding + buy decision → new buy
    - If not holding + sell decision → skip

    Args:
        state: Current workflow state

    Returns:
        Dict with updated state fields
    """
    run_id = state.get("run_id", "unknown")
    logger.info(f"[{run_id}] Position Advisor node started")

    # Check prerequisites
    judge_status = state.get("judge_status")
    logger.info(f"[{run_id}] Prerequisites: judge={judge_status}")

    # Update status to RUNNING
    updates: Dict[str, Any] = {
        "position_status": StepStatus.RUNNING.value,
        "current_step_start": datetime.now().isoformat(),
    }

    try:
        # Load decision and portfolio
        decision = state.get("decision", {})
        portfolio = state.get("portfolio", {})
        positions = portfolio.get("positions", [])
        total_cash = portfolio.get("cash", 100000.0)  # Default cash
        total_value = portfolio.get("total_value", 100000.0)  # Default total

        # Parse decision
        stock_code = decision.get("stock_code", "")
        stock_name = decision.get("stock_name", "")
        action_str = decision.get("action", "hold")
        confidence = decision.get("confidence", 0.5)
        should_enter = decision.get("should_enter", False)
        risk_level = decision.get("risk_level", "medium")

        logger.info(f"[{run_id}] Decision: {stock_code} - {action_str}")
        logger.info(f"[{run_id}] Confidence: {confidence:.2f}, Should enter: {should_enter}")
        logger.info(f"[{run_id}] Risk level: {risk_level}")
        logger.info(f"[{run_id}] Current positions: {len(positions)}")
        logger.info(f"[{run_id}] Cash: {total_cash:.0f}, Total value: {total_value:.0f}")

        # Find current position for this stock
        current_position = _find_position(stock_code, positions, run_id)

        # Determine position action
        logger.info(f"[{run_id}] Step 1: Determining position action")
        position_action = _determine_action(
            action_str, current_position, should_enter, run_id
        )

        # Calculate suggested position size
        logger.info(f"[{run_id}] Step 2: Calculating position size")
        suggested_amount = _calculate_position_size(
            position_action,
            current_position,
            confidence,
            risk_level,
            total_cash,
            total_value,
            run_id,
        )

        # Set stop-loss level
        logger.info(f"[{run_id}] Step 3: Setting stop-loss")
        stop_loss = _set_stop_loss(
            position_action,
            current_position,
            risk_level,
            run_id,
        )

        # Set take-profit level
        logger.info(f"[{run_id}] Step 4: Setting take-profit")
        take_profit = _set_take_profit(
            position_action,
            current_position,
            confidence,
            run_id,
        )

        # Build PositionAdvice
        position_advice = PositionAdvice(
            stock_code=stock_code,
            position_action=position_action,
            suggested_amount=suggested_amount,
            stop_loss=stop_loss,
            take_profit=take_profit,
            current_position=current_position,
        )

        updates["position_advice"] = position_advice.model_dump()
        updates["position_status"] = StepStatus.COMPLETED.value

        logger.info(f"[{run_id}] Position Advisor node completed successfully")
        logger.info(f"[{run_id}] Position action: {position_action.value}")
        logger.info(f"[{run_id}] Suggested amount: {suggested_amount:.1f}%")
        if stop_loss is not None:
            logger.info(f"[{run_id}] Stop-loss: {stop_loss:.1f}%")
        if take_profit is not None:
            logger.info(f"[{run_id}] Take-profit: {take_profit:.1f}%")

    except Exception as e:
        logger.error(f"[{run_id}] Position Advisor node failed: {e}")
        updates["position_status"] = StepStatus.FAILED.value
        updates["error_step"] = "position_advisor"
        updates["error_message"] = str(e)
        updates["position_advice"] = {}

    return updates


# ============== Position Finding ==============


def _find_position(
    stock_code: str,
    positions: list,
    run_id: str,
) -> Optional[Dict[str, Any]]:
    """
    Find current position for the stock

    Args:
        stock_code: Stock code to find
        positions: List of current positions
        run_id: Run ID for logging

    Returns:
        Position dict if holding, None otherwise
    """
    for pos in positions:
        if pos.get("symbol") == stock_code:
            position = {
                "symbol": stock_code,
                "quantity": pos.get("quantity", 0),
                "avg_cost": pos.get("avg_cost", 0),
                "current_price": pos.get("current_price", 0),
                "pnl_pct": pos.get("pnl_pct", 0),
                "weight": pos.get("weight", 0),
                "market_value": pos.get("quantity", 0) * pos.get("current_price", 0),
            }
            logger.info(
                f"[{run_id}] Found position: qty={position['quantity']}, "
                f"pnl={position['pnl_pct']:.1f}%, weight={position['weight']:.1f}%"
            )
            return position

    logger.info(f"[{run_id}] No current position for {stock_code}")
    return None


# ============== Action Determination ==============


def _determine_action(
    action_str: str,
    current_position: Optional[Dict[str, Any]],
    should_enter: bool,
    run_id: str,
) -> PositionAction:
    """
    Determine position action based on decision and current position

    Decision → Position Action mapping:
    - buy + not holding → new_buy
    - buy + holding → add
    - sell + holding + loss → clear
    - sell + holding + profit → reduce
    - sell + not holding → skip
    - hold → hold/skip

    Args:
        action_str: Decision action (buy/sell/hold)
        current_position: Current position info or None
        should_enter: Whether should enter position
        run_id: Run ID for logging

    Returns:
        PositionAction enum
    """
    holding = current_position is not None

    # Map decision action to position action
    if action_str == Recommendation.BUY.value:
        if holding:
            # Already holding, add position
            action = PositionAction.ADD
            logger.info(f"[{run_id}] Action: ADD (buy decision, already holding)")
        else:
            # Not holding, new buy
            if should_enter:
                action = PositionAction.NEW_BUY
                logger.info(f"[{run_id}] Action: NEW_BUY (buy decision, should enter)")
            else:
                action = PositionAction.SKIP
                logger.info(f"[{run_id}] Action: SKIP (buy decision, but should_enter=False)")

    elif action_str == Recommendation.SELL.value:
        if holding:
            # Check P&L to decide reduce or clear
            pnl_pct = current_position.get("pnl_pct", 0)
            if pnl_pct < -10:
                # Heavy loss, clear position
                action = PositionAction.CLEAR
                logger.info(f"[{run_id}] Action: CLEAR (sell decision, heavy loss {pnl_pct:.1f}%)")
            else:
                # Reduce position
                action = PositionAction.REDUCE
                logger.info(f"[{run_id}] Action: REDUCE (sell decision, pnl={pnl_pct:.1f}%)")
        else:
            # Not holding, skip
            action = PositionAction.SKIP
            logger.info(f"[{run_id}] Action: SKIP (sell decision, not holding)")

    else:  # hold
        if holding:
            # Hold existing position
            action = PositionAction.HOLD
            logger.info(f"[{run_id}] Action: HOLD (hold decision, existing position)")
        else:
            # Not holding, skip
            action = PositionAction.SKIP
            logger.info(f"[{run_id}] Action: SKIP (hold decision, not holding)")

    return action


# ============== Position Size Calculation ==============


def _calculate_position_size(
    position_action: PositionAction,
    current_position: Optional[Dict[str, Any]],
    confidence: float,
    risk_level: str,
    total_cash: float,
    total_value: float,
    run_id: str,
) -> float:
    """
    Calculate suggested position size percentage

    Position sizing strategy:
    - new_buy: Based on confidence and risk, 5-30%
    - add: Additional 5-15%
    - reduce: Reduce 30-50% of current
    - clear: 100% (clear all)
    - hold/skip: 0%

    Args:
        position_action: Position action
        current_position: Current position info
        confidence: Decision confidence
        risk_level: Risk level (high/medium/low)
        total_cash: Available cash
        total_value: Total portfolio value
        run_id: Run ID for logging

    Returns:
        Suggested position percentage
    """
    # Base percentage based on action type
    if position_action == PositionAction.NEW_BUY:
        # New buy: calculate based on confidence and risk
        base_pct = MIN_POSITION_PERCENT

        # Adjust by confidence
        if confidence >= 0.8:
            base_pct = MAX_POSITION_PERCENT
        elif confidence >= 0.6:
            base_pct = 20.0
        elif confidence >= 0.4:
            base_pct = 10.0

        # Adjust by risk level
        if risk_level == "high":
            base_pct *= 0.5  # Reduce by half for high risk
        elif risk_level == "low":
            base_pct *= 1.2  # Increase for low risk

        # Cap to max/min
        base_pct = min(MAX_POSITION_PERCENT, max(MIN_POSITION_PERCENT, base_pct))

        # Check cash availability
        if total_cash < total_value * 0.2:
            # Low cash, reduce position size
            base_pct *= 0.5

        logger.info(
            f"[{run_id}] NEW_BUY size: {base_pct:.1f}% "
            f"(confidence={confidence:.2f}, risk={risk_level})"
        )

        return round(base_pct, 1)

    elif position_action == PositionAction.ADD:
        # Add to existing: smaller increment
        current_weight = current_position.get("weight", 0) if current_position else 0

        # Don't exceed max
        remaining_capacity = MAX_POSITION_PERCENT - current_weight
        if remaining_capacity <= 0:
            logger.info(f"[{run_id}] ADD size: 0% (already at max)")
            return 0.0

        # Add 5-10% more
        add_pct = min(10.0, remaining_capacity)
        add_pct *= confidence  # Scale by confidence

        add_pct = max(0, min(remaining_capacity, add_pct))

        logger.info(f"[{run_id}] ADD size: {add_pct:.1f}% (current={current_weight:.1f}%)")

        return round(add_pct, 1)

    elif position_action == PositionAction.REDUCE:
        # Reduce: 30-50% of current position
        current_weight = current_position.get("weight", 0) if current_position else 0

        reduce_pct = current_weight * 0.5  # Reduce 50%

        logger.info(f"[{run_id}] REDUCE size: {reduce_pct:.1f}% (from {current_weight:.1f}%)")

        return round(reduce_pct, 1)

    elif position_action == PositionAction.CLEAR:
        # Clear all
        logger.info(f"[{run_id}] CLEAR size: 100% (clear all)")
        return 100.0

    else:
        # HOLD or SKIP
        logger.info(f"[{run_id}] {position_action.value} size: 0%")
        return 0.0


# ============== Stop-Loss Setting ==============


def _set_stop_loss(
    position_action: PositionAction,
    current_position: Optional[Dict[str, Any]],
    risk_level: str,
    run_id: str,
) -> Optional[float]:
    """
    Set stop-loss percentage

    Stop-loss strategy:
    - new_buy/add: Set stop-loss based on risk level
    - reduce/clear/hold/skip: No stop-loss change

    Args:
        position_action: Position action
        current_position: Current position info
        risk_level: Risk level
        run_id: Run ID for logging

    Returns:
        Stop-loss percentage (negative), or None
    """
    if position_action in [PositionAction.NEW_BUY, PositionAction.ADD]:
        # Set stop-loss for new/add positions

        # Base stop-loss
        stop_loss = DEFAULT_STOP_LOSS

        # Adjust by risk level
        if risk_level == "high":
            stop_loss = -5.0  # Tighter stop-loss for high risk
        elif risk_level == "low":
            stop_loss = -15.0  # Wider stop-loss for low risk

        logger.info(f"[{run_id}] Stop-loss set: {stop_loss:.1f}% (risk={risk_level})")

        return stop_loss

    elif position_action in [PositionAction.REDUCE, PositionAction.CLEAR]:
        # For reduce/clear, use existing stop-loss if set
        if current_position:
            # Already reducing/clearing, no new stop-loss
            logger.info(f"[{run_id}] No stop-loss change for {position_action.value}")
            return None

    else:
        # HOLD/SKIP: no stop-loss change
        logger.info(f"[{run_id}] No stop-loss for {position_action.value}")
        return None


# ============== Take-Profit Setting ==============


def _set_take_profit(
    position_action: PositionAction,
    current_position: Optional[Dict[str, Any]],
    confidence: float,
    run_id: str,
) -> Optional[float]:
    """
    Set take-profit percentage

    Take-profit strategy:
    - new_buy/add: Set take-profit based on confidence
    - reduce/clear/hold/skip: No take-profit change

    Args:
        position_action: Position action
        current_position: Current position info
        confidence: Decision confidence
        run_id: Run ID for logging

    Returns:
        Take-profit percentage (positive), or None
    """
    if position_action in [PositionAction.NEW_BUY, PositionAction.ADD]:
        # Set take-profit for new/add positions

        # Base take-profit
        take_profit = DEFAULT_TAKE_PROFIT

        # Adjust by confidence
        if confidence >= 0.8:
            take_profit = 30.0  # Higher target for high confidence
        elif confidence >= 0.6:
            take_profit = 20.0
        elif confidence < 0.4:
            take_profit = 10.0  # Lower target for low confidence

        logger.info(f"[{run_id}] Take-profit set: {take_profit:.1f}% (confidence={confidence:.2f})")

        return take_profit

    elif position_action in [PositionAction.REDUCE, PositionAction.CLEAR]:
        # For reduce/clear, check if current profit exceeds target
        if current_position:
            pnl_pct = current_position.get("pnl_pct", 0)
            if pnl_pct > 0:
                # Already profitable, set target slightly above current
                take_profit = pnl_pct + 5.0
                logger.info(
                    f"[{run_id}] Take-profit adjusted: {take_profit:.1f}% "
                    f"(current pnl={pnl_pct:.1f}%)"
                )
                return take_profit

        logger.info(f"[{run_id}] No take-profit change for {position_action.value}")
        return None

    else:
        # HOLD/SKIP: no take-profit change
        logger.info(f"[{run_id}] No take-profit for {position_action.value}")
        return None