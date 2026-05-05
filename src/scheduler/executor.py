"""任务执行器 - 使用 Workspace 管理（无 SQLite）"""

from datetime import datetime
from pathlib import Path
from typing import Optional

from src.scheduler.task_queue import task_queue, Task
from src.scheduler.workspace_manager import (
    create_task_folder,
    write_log,
    write_result,
    write_status,
    read_status,
    update_status,
    get_task_folder_by_id,
    generate_task_id
)
from src.core.logger import logger as app_logger


class TaskExecutor:
    """任务执行器"""

    def __init__(self):
        self.queue = task_queue
        self.current_folder: Optional[Path] = None

    def create_task(
        self,
        task_type: str,
        stocks: Optional[list[dict]] = None,
        description: Optional[str] = None,
        params: Optional[dict] = None
    ) -> Task:
        """创建任务（创建文件夹 + 初始化状态）

        Args:
            task_type: market_analysis / stock_analysis / backtest
            stocks: 股票列表 [{code, position}]
            description: 回测策略描述（仅 backtest 类型）
            params: 回测参数（仅 backtest 类型）

        Returns:
            Task 对象
        """
        task_id = generate_task_id()

        # 创建任务文件夹（会自动创建 status.json）
        folder = create_task_folder(task_type, task_id, stocks, description, params)

        # 创建 Task 对象（内存）
        task = Task(
            task_id=task_id,
            task_type=task_type,
            stocks=stocks,
            created_at=datetime.now(),
            logs=[]
        )

        # 添加到内存队列
        self.queue.tasks[task_id] = task

        app_logger.info(f"创建任务 {task_id} ({task_type})")
        return task

    def execute_task(self, task: Task) -> dict:
        """执行任务"""
        app_logger.info(f"开始执行任务 {task.task_id} ({task.task_type})")

        # 获取任务文件夹
        self.current_folder = get_task_folder_by_id(task.task_id)
        if not self.current_folder:
            # 如果文件夹不存在，创建它
            self.current_folder = create_task_folder(
                task.task_type,
                task.task_id,
                task.stocks
            )

        # 读取任务参数（回测任务）
        status_data = read_status(self.current_folder)
        description = status_data.get("description") if status_data else None
        params = status_data.get("params") if status_data else None

        # 写入初始日志
        write_log(self.current_folder, f"任务开始: {task.task_id}")
        write_log(self.current_folder, f"任务类型: {task.task_type}")

        # 使用新格式 stocks
        if task.stocks:
            write_log(self.current_folder, f"股票列表: {[s['code'] for s in task.stocks]}")
            positions = {s['code']: s['position'] for s in task.stocks}
            write_log(self.current_folder, f"持仓信息: {positions}")

        # 回测任务日志
        if task.task_type == "backtest" and description:
            write_log(self.current_folder, f"策略描述: {description}")
            if params:
                write_log(self.current_folder, f"回测参数: {params}")

        # 更新状态为 running
        update_status(
            self.current_folder,
            status="running",
            started_at=datetime.now()
        )

        # 更新内存队列
        self.queue.update_task(
            task.task_id,
            status="running",
            started_at=datetime.now()
        )

        try:
            if task.task_type == "market_analysis":
                result = self._run_market_analysis(task)
            elif task.task_type == "stock_analysis":
                result = self._run_stock_analysis(task)
            elif task.task_type == "backtest":
                result = self._run_backtest(task, description, params)
            else:
                raise ValueError(f"未知任务类型: {task.task_type}")

            # 保存结果
            write_result(self.current_folder, result)
            write_log(self.current_folder, "任务完成")

            # 更新状态为 completed
            update_status(
                self.current_folder,
                status="completed",
                completed_at=datetime.now()
            )

            # 更新内存队列
            self.queue.update_task(
                task.task_id,
                status="completed",
                completed_at=datetime.now(),
                result=result
            )

            app_logger.info(f"任务 {task.task_id} 执行成功")
            return result

        except Exception as e:
            app_logger.error(f"任务 {task.task_id} 执行失败: {e}")

            write_log(self.current_folder, f"任务失败: {e}")

            # 保存错误结果
            write_result(self.current_folder, {"error": str(e)})

            # 更新状态为 failed
            update_status(
                self.current_folder,
                status="failed",
                completed_at=datetime.now()
            )

            # 更新内存队列
            self.queue.update_task(
                task.task_id,
                status="failed",
                completed_at=datetime.now(),
                error=str(e)
            )

            return {"error": str(e)}

    def _run_market_analysis(self, task: Task) -> dict:
        """运行市场分析"""
        from src.workflows.market_analysis import run_market_analysis

        write_log(self.current_folder, "启动市场分析 Workflow")

        # 记录 workflow 步骤开始
        update_status(
            self.current_folder,
            workflow_step={"name": "macro_analyzer", "started_at": datetime.now().isoformat()}
        )
        write_log(self.current_folder, "步骤: 宏观分析")

        result = run_market_analysis(self.current_folder)

        # 记录 workflow 步骤完成
        update_status(
            self.current_folder,
            workflow_step={"name": "market_analysis_end", "completed_at": datetime.now().isoformat()}
        )

        return result

    def _run_stock_analysis(self, task: Task) -> dict:
        """运行股票分析（支持每只股票独立持仓）"""
        from src.workflows.stock_analysis import run_stock_analysis

        # 获取股票列表和持仓
        stocks = task.stocks or []

        if len(stocks) == 0:
            raise ValueError("未提供股票代码")

        if len(stocks) == 1:
            code = stocks[0]["code"]
            position = stocks[0]["position"]
            write_log(self.current_folder, f"启动股票分析 Workflow: {code}")
            write_log(self.current_folder, f"当前持仓: {position} 元")

            # 记录 workflow 步骤
            update_status(
                self.current_folder,
                workflow_step={"name": f"stock_analysis_{code}", "started_at": datetime.now().isoformat()}
            )

            result = run_stock_analysis(
                code,
                position,
                self.current_folder
            )

            update_status(
                self.current_folder,
                workflow_step={"name": f"stock_analysis_{code}_end", "completed_at": datetime.now().isoformat()}
            )

            return result

        # 批量分析（每只股票独立持仓）
        write_log(self.current_folder, f"启动批量股票分析: {len(stocks)} 只")
        results = {}

        for stock in stocks:
            code = stock["code"]
            position = stock["position"]
            write_log(self.current_folder, f"---")
            write_log(self.current_folder, f"分析股票: {code}, 持仓: {position} 元")

            # 记录 workflow 步骤
            update_status(
                self.current_folder,
                workflow_step={"name": f"stock_analysis_{code}", "started_at": datetime.now().isoformat()}
            )

            try:
                results[code] = run_stock_analysis(
                    code,
                    position,
                    self.current_folder
                )
                update_status(
                    self.current_folder,
                    workflow_step={"name": f"stock_analysis_{code}_end", "completed_at": datetime.now().isoformat()}
                )
            except Exception as e:
                write_log(self.current_folder, f"股票 {code} 分析失败: {e}")
                results[code] = {"error": str(e)}
                update_status(
                    self.current_folder,
                    workflow_step={"name": f"stock_analysis_{code}_failed", "completed_at": datetime.now().isoformat()}
                )

        write_log(self.current_folder, "批量分析完成")

        # 汇总结果
        summary = []
        for code, result in results.items():
            if "error" not in result:
                summary.append({
                    "code": code,
                    "decision": result.get("final_decision", {}).get("decision", "N/A"),
                    "action": result.get("suggested_action", "N/A"),
                    "amount": result.get("suggested_amount", 0)
                })
            else:
                summary.append({
                    "code": code,
                    "error": result["error"]
                })

        return {
            "batch_results": results,
            "summary": summary
        }

    def _run_backtest(self, task: Task, description: str, params: dict) -> dict:
        """运行回测任务 - 使用 LangGraph workflow"""
        from src.workflows.backtest import run_backtest_with_logging

        write_log(self.current_folder, "启动策略回测 Workflow")

        try:
            # 使用 LangGraph workflow 执行
            result = run_backtest_with_logging(
                task_id=task.task_id,
                description=description,
                params=params,
                log_folder=self.current_folder
            )

            # 提取关键结果
            summary = result.get("summary", {})
            reflection = result.get("reflection", {})
            strategy_log_path = result.get("strategy_log_path", "")

            return {
                "summary": summary,
                "trades_count": len(result.get("trades", [])),
                "reflection": reflection,
                "strategy_log": strategy_log_path,
                "workflow_steps": result.get("logs", [])
            }

        except Exception as e:
            write_log(self.current_folder, f"回测 Workflow 失败: {e}")
            raise


executor = TaskExecutor()