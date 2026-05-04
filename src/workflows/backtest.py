"""回测 Workflow - 使用 LangGraph 构建回测流程

节点流程：
Init -> Backtest -> Reflection -> Report -> END
"""

from pathlib import Path
from typing import Optional

from langgraph.graph import StateGraph, END

from src.workflows.state import BacktestState
from src.backtest.strategy_parser import parse_strategy_description, StrategyParams
from src.backtest.strategy_generator import generate_strategy_code
from src.backtest.runner import BacktestRunner
from src.backtest.reflection_agent import reflect_on_strategy
from src.backtest.monthly_settlement import calculate_monthly_settlements
from src.backtest.log_generator import generate_strategy_log, save_strategy_log
from src.core.logger import logger
from src.scheduler.workspace_manager import write_log


def create_backtest_workflow(log_folder: Optional[Path] = None):
    """创建回测 workflow

    Args:
        log_folder: 日志文件夹路径

    Returns:
        编译后的 LangGraph workflow
    """

    def init_node(state: BacktestState) -> dict:
        """Init Node - 解析用户需求"""
        if log_folder:
            write_log(log_folder, "=== Node: Init [开始] ===")

        logger.info("[Backtest Init] 解析策略描述...")

        description = state.get("description", "")
        params = state.get("params", {})

        # 调用策略解析器
        strategy_params = parse_strategy_description(description)

        # 合合用户参数到 strategy_params
        if params.get("start_date"):
            strategy_params.start_date = params["start_date"]
        if params.get("end_date"):
            strategy_params.end_date = params["end_date"]
        if params.get("initial_capital"):
            strategy_params.initial_capital = params["initial_capital"]

        logger.info(f"[Backtest Init] 策略名称: {strategy_params.name}")
        logger.info(f"[Backtest Init] 买入条件: {strategy_params.buy_condition}")
        logger.info(f"[Backtest Init] 止盈止损: {strategy_params.profit_target}%/{strategy_params.stop_loss}%")

        if log_folder:
            write_log(log_folder, f"策略名称: {strategy_params.name}")
            write_log(log_folder, f"买入条件: {strategy_params.buy_condition}")
            write_log(log_folder, f"止盈止损: {strategy_params.profit_target}%/{strategy_params.stop_loss}%")
            write_log(log_folder, f"回测区间: {strategy_params.start_date} ~ {strategy_params.end_date}")
            write_log(log_folder, f"初始资金: {strategy_params.initial_capital}")
            write_log(log_folder, "=== Node: Init [结束] ===")

        return {
            "strategy_params": strategy_params.to_dict(),
            "logs": state.get("logs", []) + ["Init: 解析策略描述完成"],
            "current_step": "backtest"
        }

    def backtest_node(state: BacktestState) -> dict:
        """Backtest Node - 执行回测"""
        if log_folder:
            write_log(log_folder, "=== Node: Backtest [开始] ===")

        logger.info("[Backtest] 执行回测...")

        strategy_params_dict = state.get("strategy_params", {})

        # 重建 StrategyParams 对象
        strategy_params = StrategyParams(
            name=strategy_params_dict.get("name", "generated_strategy"),
            start_date=strategy_params_dict.get("start_date", "2020-01-01"),
            end_date=strategy_params_dict.get("end_date", "2024-12-31"),
            initial_capital=float(strategy_params_dict.get("initial_capital", 100000)),
            buy_condition=strategy_params_dict.get("buy_condition", "涨停板"),
            buy_threshold=float(strategy_params_dict.get("buy_threshold", 9.9)),
            max_positions=int(strategy_params_dict.get("max_positions", 5)),
            buy_ratio=float(strategy_params_dict.get("buy_ratio", 0.1)),
            buy_frequency=strategy_params_dict.get("buy_frequency", "每周"),
            buy_limit=int(strategy_params_dict.get("buy_limit", 3)),
            sell_condition=strategy_params_dict.get("sell_condition", "止盈止损"),
            profit_target=float(strategy_params_dict.get("profit_target", 8.0)),
            stop_loss=float(strategy_params_dict.get("stop_loss", -3.0)),
            market_filter=strategy_params_dict.get("market_filter", "非熊市"),
            exclude_st=strategy_params_dict.get("exclude_st", True),
            exclude_new=strategy_params_dict.get("exclude_new", True),
            min_list_days=int(strategy_params_dict.get("min_list_days", 60)),
        )

        # 生成策略代码
        logger.info("[Backtest] 生成策略代码...")
        strategy_code = generate_strategy_code(strategy_params)

        if log_folder:
            write_log(log_folder, f"策略代码长度: {len(strategy_code)} 字符")

        # 执行回测 - 使用 run_from_strategy 避免重复解析
        runner = BacktestRunner()

        # 从代码加载策略实例
        strategy = runner._load_strategy_from_code(strategy_code, strategy_params.name)

        if strategy is None:
            logger.error("[Backtest] 策略加载失败")
            if log_folder:
                write_log(log_folder, "策略加载失败")
            return {
                "error": "策略加载失败",
                "logs": state.get("logs", []) + ["Backtest: 策略加载失败"],
            }

        # 运行策略回测
        result = runner.run_from_strategy(
            strategy=strategy,
            start_date=strategy_params.start_date,
            end_date=strategy_params.end_date,
            initial_capital=strategy_params.initial_capital,
        )

        trades = result.get("trades", [])
        equity_curve = result.get("equity_curve", [])
        summary = result.get("summary", {})

        logger.info(f"[Backtest] 回测完成: {len(trades)} 笔交易")
        logger.info(f"[Backtest] 总收益率: {summary.get('total_return', 0):.2f}%")

        if log_folder:
            write_log(log_folder, f"交易次数: {len(trades)}")
            write_log(log_folder, f"总收益率: {summary.get('total_return', 0):.2f}%")
            write_log(log_folder, f"最大回撤: {summary.get('max_drawdown', 0):.2f}%")
            write_log(log_folder, f"胜率: {summary.get('win_rate', 0):.2f}%")
            write_log(log_folder, "=== Node: Backtest [结束] ===")

        return {
            "strategy_code": strategy_code,
            "trades": trades,
            "equity_curve": equity_curve,
            "summary": summary,
            "logs": state.get("logs", []) + ["Backtest: 回测执行完成"],
            "current_step": "reflection"
        }

    def reflection_node(state: BacktestState) -> dict:
        """Reflection Node - Advisor评估策略"""
        if log_folder:
            write_log(log_folder, "=== Node: Reflection [开始] ===")

        logger.info("[Backtest Reflection] AI策略反思...")

        description = state.get("description", "")
        params = state.get("params", {})
        summary = state.get("summary", {})
        trades = state.get("trades", [])

        # 调用反思 Agent
        reflection = reflect_on_strategy(
            description=description,
            params=params,
            summary=summary,
            trades=trades
        )

        strengths = reflection.get("strengths", [])
        weaknesses = reflection.get("weaknesses", [])
        improvements = reflection.get("improvements", [])
        risk_warnings = reflection.get("risk_warnings", [])

        logger.info(f"[Backtest Reflection] 策略优势: {len(strengths)} 条")
        logger.info(f"[Backtest Reflection] 改进建议: {len(improvements)} 条")

        if log_folder:
            write_log(log_folder, f"策略优势: {len(strengths)} 条")
            for s in strengths:
                write_log(log_folder, f"  + {s}")
            write_log(log_folder, f"策略劣势: {len(weaknesses)} 条")
            for w in weaknesses:
                write_log(log_folder, f"  - {w}")
            write_log(log_folder, f"改进建议: {len(improvements)} 条")
            for i in improvements:
                write_log(log_folder, f"  * {i}")
            write_log(log_folder, f"风险提示: {len(risk_warnings)} 条")
            for r in risk_warnings:
                write_log(log_folder, f"  ! {r}")
            write_log(log_folder, "=== Node: Reflection [结束] ===")

        return {
            "reflection": reflection,
            "strengths": strengths,
            "weaknesses": weaknesses,
            "improvements": improvements,
            "risk_warnings": risk_warnings,
            "logs": state.get("logs", []) + ["Reflection: 策略反思完成"],
            "current_step": "report"
        }

    def report_node(state: BacktestState) -> dict:
        """Report Node - 生成最终报告"""
        if log_folder:
            write_log(log_folder, "=== Node: Report [开始] ===")

        logger.info("[Backtest Report] 生成策略报告...")

        task_id = state.get("task_id", "")
        description = state.get("description", "")
        params = state.get("params", {})
        trades = state.get("trades", [])
        equity_curve = state.get("equity_curve", [])
        summary = state.get("summary", {})
        reflection = state.get("reflection", {})

        # 计算月度结算
        start_date = params.get("start_date", "2020-01-01")
        end_date = params.get("end_date", "2024-12-31")

        monthly_settlements = calculate_monthly_settlements(
            trades=trades,
            equity_curve=equity_curve,
            start_date=start_date,
            end_date=end_date
        )

        logger.info(f"[Backtest Report] 月度结算: {len(monthly_settlements)} 个月")

        # 生成策略日志
        log_content = generate_strategy_log(
            task_id=task_id,
            description=description,
            params=params,
            trades=trades,
            equity_curve=equity_curve,
            summary=summary,
            reflection=reflection,
        )

        # 保存日志文件
        if log_folder:
            log_path = save_strategy_log(log_content, log_folder)
            logger.info(f"[Backtest Report] 策略日志保存: {log_path}")

            write_log(log_folder, f"月度结算: {len(monthly_settlements)} 个月")
            write_log(log_folder, f"策略日志: {log_path.name}")
            write_log(log_folder, "=== Node: Report [结束] ===")
            write_log(log_folder, "Workflow 执行完成")

            return {
                "monthly_settlements": monthly_settlements,
                "strategy_log": log_content,
                "strategy_log_path": str(log_path),
                "logs": state.get("logs", []) + ["Report: 报告生成完成", "回测结束"],
                "current_step": "end"
            }
        else:
            return {
                "monthly_settlements": monthly_settlements,
                "strategy_log": log_content,
                "strategy_log_path": "",
                "logs": state.get("logs", []) + ["Report: 报告生成完成", "回测结束"],
                "current_step": "end"
            }

    # 构建 Workflow
    workflow = StateGraph(BacktestState)

    workflow.add_node("init", init_node)
    workflow.add_node("backtest", backtest_node)
    workflow.add_node("reflection", reflection_node)
    workflow.add_node("report", report_node)

    workflow.add_edge("init", "backtest")
    workflow.add_edge("backtest", "reflection")
    workflow.add_edge("reflection", "report")
    workflow.add_edge("report", END)

    workflow.set_entry_point("init")

    return workflow.compile()


def run_backtest_with_logging(
    task_id: str,
    description: str,
    params: dict,
    log_folder: Path
) -> dict:
    """运行回测 workflow（带日志记录）

    Args:
        task_id: 任务ID
        description: 策略描述
        params: 回测参数
        log_folder: 日志文件夹

    Returns:
        workflow 执行结果
    """
    write_log(log_folder, "初始化 Backtest Workflow")

    workflow = create_backtest_workflow(log_folder)

    initial_state = {
        "messages": [],
        "task_id": task_id,
        "description": description,
        "params": params,
        "strategy_params": {},
        "strategy_code": "",
        "trades": [],
        "equity_curve": [],
        "summary": {},
        "reflection": {},
        "strengths": [],
        "weaknesses": [],
        "improvements": [],
        "risk_warnings": [],
        "monthly_settlements": [],
        "strategy_log": "",
        "strategy_log_path": "",
        "current_step": "init",
        "logs": ["开始回测"],
        "error": None
    }

    result = workflow.invoke(initial_state)
    return result