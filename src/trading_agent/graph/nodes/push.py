"""
Push node - 推送报告

Responsibilities:
- Format final decision report
- Push to Feishu webhook (reserved interface)
- Save decision record to data/decisions/
- Update workflow status to completed
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

from trading_agent.graph.state import (
    WorkflowState,
    StepStatus,
    PositionAdvice,
    Decision,
)
from trading_agent.utils.logger import get_logger

logger = get_logger("PUSH")

# Decision record directory
DECISIONS_DIR = Path("data/decisions")


def push_node(state: WorkflowState) -> Dict:
    """
    Push node entry function

    This node pushes final decisions to notification channels.

    Steps:
    1. Format decision report
    2. Push to Feishu webhook (reserved)
    3. Save decision record to file
    4. Update workflow status

    Args:
        state: Current workflow state

    Returns:
        Dict with updated state fields
    """
    run_id = state.get("run_id", "unknown")
    logger.info(f"[{run_id}] Push node started")

    # Check prerequisites
    position_status = state.get("position_status")
    logger.info(f"[{run_id}] Prerequisites: position_advisor={position_status}")

    # Update status to RUNNING
    updates: Dict[str, Any] = {
        "push_status": StepStatus.RUNNING.value,
        "current_step_start": datetime.now().isoformat(),
    }

    try:
        # Load all relevant state
        decision = state.get("decision", {})
        position_advice = state.get("position_advice", {})
        analysis_summary = state.get("analysis_summary", [])
        debate_log = state.get("debate_log", [])
        buyer_score = state.get("buyer_score", 0.0)
        seller_score = state.get("seller_score", 0.0)
        hot_sectors = state.get("hot_sectors", [])
        candidate_stocks = state.get("candidate_stocks", [])
        portfolio = state.get("portfolio", {})

        logger.info(f"[{run_id}] Decision: {decision.get('action', 'unknown')}")
        logger.info(f"[{run_id}] Position: {position_advice.get('position_action', 'unknown')}")
        logger.info(f"[{run_id}] Analysis entries: {len(analysis_summary)}")
        logger.info(f"[{run_id}] Debate rounds: {len(debate_log)}")

        # Step 1: Format decision report
        logger.info(f"[{run_id}] Step 1: Formatting decision report")
        report = _format_report(
            run_id,
            decision,
            position_advice,
            analysis_summary,
            debate_log,
            buyer_score,
            seller_score,
            hot_sectors,
            portfolio,
            run_id,
        )

        # Step 2: Push to Feishu webhook (reserved)
        logger.info(f"[{run_id}] Step 2: Push to Feishu (reserved interface)")
        feishu_result = _push_to_feishu(report, run_id)

        # Step 3: Save decision record
        logger.info(f"[{run_id}] Step 3: Saving decision record")
        save_result = _save_decision_record(report, run_id)

        # Build push result
        push_result = {
            "feishu_sent": feishu_result.get("sent", False),
            "feishu_message": feishu_result.get("message", ""),
            "log_saved": save_result.get("saved", False),
            "log_path": save_result.get("path", ""),
            "report_summary": report.get("summary", ""),
        }

        updates["push_result"] = push_result

        # Update workflow status to completed
        updates["push_status"] = StepStatus.COMPLETED.value
        updates["status"] = StepStatus.COMPLETED.value
        updates["end_time"] = datetime.now().isoformat()

        logger.info(f"[{run_id}] Push node completed successfully")
        logger.info(f"[{run_id}] Feishu sent: {feishu_result.get('sent', False)}")
        logger.info(f"[{run_id}] Decision log saved: {save_result.get('saved', False)}")
        logger.info(f"[{run_id}] Workflow finished with status: completed")

    except Exception as e:
        logger.error(f"[{run_id}] Push node failed: {e}")
        updates["push_status"] = StepStatus.FAILED.value
        updates["status"] = StepStatus.FAILED.value
        updates["error_step"] = "push"
        updates["error_message"] = str(e)
        updates["end_time"] = datetime.now().isoformat()
        updates["push_result"] = {
            "feishu_sent": False,
            "log_saved": False,
            "error": str(e),
        }

    return updates


# ============== Report Formatting ==============


def _format_report(
    run_id: str,
    decision: Dict[str, Any],
    position_advice: Dict[str, Any],
    analysis_summary: List[Any],
    debate_log: List[Any],
    buyer_score: float,
    seller_score: float,
    hot_sectors: List[Any],
    portfolio: Dict[str, Any],
    run_id_log: str,
) -> Dict[str, Any]:
    """
    Format comprehensive decision report

    Report structure:
    - Header: run info, timestamp
    - Summary: key decision, position action
    - Market context: hot sectors
    - Analysis: tech + fund scores
    - Debate: buyer/seller scores, key arguments
    - Decision: action, confidence, reasoning
    - Position advice: size, stop-loss, take-profit
    - Attribution: causal chain
    - Counterfactual: scenarios

    Args:
        run_id: Run ID
        decision: Decision dict
        position_advice: PositionAdvice dict
        analysis_summary: Analysis summaries
        debate_log: Debate rounds
        buyer_score: Buyer debate score
        seller_score: Seller debate score
        hot_sectors: Hot sectors
        portfolio: Current portfolio
        run_id_log: Run ID for logging

    Returns:
        Report dict
    """
    now = datetime.now()

    # Parse decision
    stock_code = decision.get("stock_code", "")
    stock_name = decision.get("stock_name", "")
    action = decision.get("action", "hold")
    confidence = decision.get("confidence", 0.5)
    reasoning = decision.get("reasoning", "")
    should_enter = decision.get("should_enter", False)
    risk_level = decision.get("risk_level", "medium")

    # Parse position advice
    position_action = position_advice.get("position_action", "skip")
    suggested_amount = position_advice.get("suggested_amount", 0)
    stop_loss = position_advice.get("stop_loss")
    take_profit = position_advice.get("take_profit")

    # Build summary line
    summary = f"【交易建议】{stock_name}({stock_code}): {action} | 仓位建议: {position_action} {suggested_amount:.1f}%"

    # Build report
    report: Dict[str, Any] = {
        "header": {
            "run_id": run_id,
            "timestamp": now.isoformat(),
            "run_type": "post_market",
        },
        "summary": summary,
        "decision": {
            "stock_code": stock_code,
            "stock_name": stock_name,
            "action": action,
            "confidence": confidence,
            "reasoning": reasoning,
            "should_enter": should_enter,
            "risk_level": risk_level,
        },
        "position_advice": {
            "action": position_action,
            "suggested_amount_pct": suggested_amount,
            "stop_loss_pct": stop_loss,
            "take_profit_pct": take_profit,
        },
        "market_context": {
            "hot_sectors": _format_hot_sectors(hot_sectors),
            "portfolio_summary": _format_portfolio_summary(portfolio),
        },
        "analysis_summary": _format_analysis_summary(analysis_summary),
        "debate_result": {
            "buyer_score": buyer_score,
            "seller_score": seller_score,
            "winner": "buyer" if buyer_score > seller_score else "seller",
            "margin": abs(buyer_score - seller_score),
            "total_rounds": len(debate_log),
        },
        "causal_chain": decision.get("causal_chain", {}),
        "counterfactual": decision.get("counterfactual", {}),
    }

    logger.info(f"[{run_id_log}] Report formatted: {summary}")

    return report


def _format_hot_sectors(hot_sectors: List[Any]) -> List[Dict[str, Any]]:
    """Format hot sectors for report"""
    formatted = []
    for sector in hot_sectors:
        if isinstance(sector, dict):
            formatted.append({
                "name": sector.get("name", ""),
                "heat_score": sector.get("heat_score", 0),
                "leaders": sector.get("leaders", []),
            })
        else:
            formatted.append({
                "name": sector.name,
                "heat_score": sector.heat_score,
                "leaders": sector.leaders,
            })
    return formatted


def _format_portfolio_summary(portfolio: Dict[str, Any]) -> Dict[str, Any]:
    """Format portfolio summary"""
    return {
        "cash": portfolio.get("cash", 0),
        "total_value": portfolio.get("total_value", 0),
        "positions_count": len(portfolio.get("positions", [])),
        "pnl_total": portfolio.get("pnl_total", 0),
    }


def _format_analysis_summary(analysis_summary: List[Any]) -> List[Dict[str, Any]]:
    """Format analysis summaries for report"""
    formatted = []
    for summary in analysis_summary:
        if isinstance(summary, dict):
            formatted.append({
                "stock_code": summary.get("stock_code", ""),
                "stock_name": summary.get("stock_name", ""),
                "tech_score": summary.get("tech_score", 0),
                "fund_score": summary.get("fund_score", 0),
                "combined_score": summary.get("combined_score", 0),
                "buy_arguments": summary.get("buy_arguments", []),
                "sell_arguments": summary.get("sell_arguments", []),
            })
        else:
            formatted.append({
                "stock_code": summary.stock_code,
                "stock_name": summary.stock_name,
                "tech_score": summary.tech_score,
                "fund_score": summary.fund_score,
                "combined_score": summary.combined_score,
                "buy_arguments": summary.buy_arguments,
                "sell_arguments": summary.sell_arguments,
            })
    return formatted


# ============== Feishu Push (Reserved) ==============


def _push_to_feishu(report: Dict[str, Any], run_id: str) -> Dict[str, Any]:
    """
    Push report to Feishu webhook

    This is a reserved interface - actual push will be implemented
    when webhook URL is configured.

    Args:
        report: Report dict
        run_id: Run ID

    Returns:
        Result dict with sent status
    """
    # Reserved interface - mock implementation
    # TODO: Implement actual Feishu webhook push when URL is configured

    # Format Feishu message card (mock)
    message_card = _format_feishu_card(report)

    logger.info(f"[{run_id}] Feishu push reserved - would send message card")
    logger.info(f"[{run_id}] Message preview: {message_card['summary']}")

    # Mock: not actually sent
    return {
        "sent": False,
        "message": "Feishu webhook not configured - reserved interface",
        "card_preview": message_card,
    }


def _format_feishu_card(report: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format Feishu message card

    Feishu card format reference:
    https://open.feishu.cn/document/ukTMukTMukTM/uYjNwUjL2YDM14iN2ATN

    Args:
        report: Report dict

    Returns:
        Feishu card dict (mock)
    """
    decision = report.get("decision", {})
    position = report.get("position_advice", {})
    debate = report.get("debate_result", {})

    # Mock card structure
    card = {
        "summary": report.get("summary", ""),
        "title": f"【交易决策】{decision.get('stock_name', '')}",
        "content": [
            f"**股票**: {decision.get('stock_code', '')} - {decision.get('stock_name', '')}",
            f"**决策**: {decision.get('action', '')} (置信度: {decision.get('confidence', 0):.2f})",
            f"**仓位**: {position.get('action', '')} {position.get('suggested_amount_pct', 0):.1f}%",
            f"**风控**: 止损 {position.get('stop_loss_pct', 'N/A')}% | 止盈 {position.get('take_profit_pct', 'N/A')}%",
            f"**辩论**: 买方 {debate.get('buyer_score', 0):.1f} vs 卖方 {debate.get('seller_score', 0):.1f}",
        ],
        "timestamp": report.get("header", {}).get("timestamp", ""),
    }

    return card


# ============== Decision Record Saving ==============


def _save_decision_record(report: Dict[str, Any], run_id: str) -> Dict[str, Any]:
    """
    Save decision record to file

    Saves report to data/decisions/{run_id}.json

    Args:
        report: Report dict
        run_id: Run ID

    Returns:
        Result dict with save status and path
    """
    try:
        # Ensure directory exists
        DECISIONS_DIR.mkdir(parents=True, exist_ok=True)

        # Build file path
        file_path = DECISIONS_DIR / f"{run_id}.json"

        # Write report to file
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        logger.info(f"[{run_id}] Decision record saved: {file_path}")

        return {
            "saved": True,
            "path": str(file_path),
        }

    except Exception as e:
        logger.error(f"[{run_id}] Failed to save decision record: {e}")

        return {
            "saved": False,
            "path": "",
            "error": str(e),
        }