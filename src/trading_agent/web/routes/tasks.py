"""任务 API 路由 - 基于 Workspace 文件系统"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

from trading_agent.scheduler.executor import executor
from trading_agent.scheduler.workspace_manager import (
    list_all_tasks,
    get_task_folder_by_id,
    get_task_detail,
    read_status,
    get_task_status
)

router = APIRouter()


class StockWithPosition(BaseModel):
    """股票及持仓"""
    code: str
    position: float = 0


class CreateTaskRequest(BaseModel):
    """创建任务请求"""
    task_type: str  # market_analysis / stock_analysis
    stocks: Optional[list[StockWithPosition]] = None  # 每只股票单独持仓


class TaskResponse(BaseModel):
    """任务响应"""
    task_id: str
    task_type: str
    status: str  # pending / running / completed / failed
    created_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    stocks: Optional[list[dict]] = None
    folder_name: Optional[str] = None


class TaskDetailResponse(BaseModel):
    """任务详情响应"""
    task_id: str
    task_type: str
    status: str
    created_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    stocks: Optional[list[dict]] = None
    workflow_steps: list[dict] = []
    summary: Optional[dict] = None
    result: Optional[dict] = None
    logs: list[str] = []
    folder_name: str


def run_task_background(task_id: str):
    """后台执行任务"""
    from trading_agent.scheduler.task_queue import task_queue
    task = task_queue.get_task(task_id)
    if task:
        executor.execute_task(task)


@router.post("", response_model=TaskResponse)
async def create_task(request: CreateTaskRequest, background_tasks: BackgroundTasks):
    """创建分析任务"""
    if request.task_type not in ["market_analysis", "stock_analysis"]:
        raise HTTPException(status_code=400, detail="Invalid task_type")

    # 处理股票列表
    stocks_with_positions = []

    if request.task_type == "stock_analysis":
        if request.stocks:
            stocks_with_positions = [{"code": s.code, "position": s.position} for s in request.stocks]
        else:
            raise HTTPException(status_code=400, detail="stocks is required for stock_analysis")

    # 创建任务（会创建文件夹和 status.json）
    task = executor.create_task(
        task_type=request.task_type,
        stocks=stocks_with_positions
    )

    # 后台执行
    background_tasks.add_task(run_task_background, task.task_id)

    return TaskResponse(
        task_id=task.task_id,
        task_type=task.task_type,
        status="pending",
        created_at=task.created_at.isoformat() if task.created_at else None,
        stocks=stocks_with_positions
    )


@router.get("", response_model=list[TaskResponse])
async def list_tasks():
    """获取任务列表"""
    tasks = list_all_tasks()
    return [
        TaskResponse(
            task_id=t["task_id"],
            task_type=t["task_type"],
            status=t["status"],
            created_at=t["created_at"],
            stocks=t["stocks"],
            folder_name=t["folder_name"]
        ) for t in tasks
    ]


@router.get("/{task_id}", response_model=TaskDetailResponse)
async def get_task(task_id: str):
    """获取任务详情"""
    folder = get_task_folder_by_id(task_id)
    if not folder:
        raise HTTPException(status_code=404, detail="Task not found")

    detail = get_task_detail(folder)

    return TaskDetailResponse(
        task_id=detail["task_id"],
        task_type=detail["task_type"],
        status=detail["status"],
        created_at=detail["created_at"],
        started_at=detail["started_at"],
        completed_at=detail["completed_at"],
        stocks=detail["stocks"],
        workflow_steps=detail["workflow_steps"],
        summary=detail["summary"],
        result=detail["result"],
        logs=detail["logs"],
        folder_name=detail["folder_name"]
    )


@router.get("/{task_id}/logs")
async def get_task_logs(task_id: str):
    """获取任务日志"""
    folder = get_task_folder_by_id(task_id)
    if not folder:
        raise HTTPException(status_code=404, detail="Task not found")

    detail = get_task_detail(folder)

    return {"task_id": task_id, "logs": detail["logs"]}


@router.delete("/{task_id}")
async def delete_task(task_id: str):
    """删除任务"""
    import shutil

    folder = get_task_folder_by_id(task_id)
    if not folder:
        raise HTTPException(status_code=404, detail="Task not found")

    # 检查任务状态，running 状态不能删除
    status = get_task_status(folder)
    if status == "running":
        raise HTTPException(status_code=400, detail="Cannot delete running task")

    # 删除文件夹
    shutil.rmtree(folder)

    return {"message": "Task deleted", "task_id": task_id}