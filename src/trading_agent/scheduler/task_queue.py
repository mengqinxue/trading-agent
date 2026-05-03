"""任务队列"""

from datetime import datetime
from typing import Optional
from uuid import uuid4
from pydantic import BaseModel


class Task(BaseModel):
    """任务定义"""
    task_id: str
    task_type: str  # market_analysis / stock_analysis
    stock_codes: Optional[list[str]] = None  # 旧格式
    current_position: Optional[float] = None  # 旧格式
    stocks: Optional[list[dict]] = None  # 新格式：[{code, position}]
    status: str = "pending"  # pending / running / completed / failed
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[dict] = None
    logs: list[str] = []
    error: Optional[str] = None


class TaskQueue:
    """任务队列"""

    def __init__(self):
        self.tasks: dict[str, Task] = {}

    def add_task(
        self,
        task_type: str,
        stock_codes: Optional[list[str]] = None,
        current_position: Optional[float] = None,
        stocks: Optional[list[dict]] = None
    ) -> Task:
        """添加任务"""
        task_id = str(uuid4())

        # 如果使用旧格式，转换为新格式
        if stock_codes and not stocks:
            default_position = current_position or 0
            stocks = [{"code": code, "position": default_position} for code in stock_codes]

        task = Task(
            task_id=task_id,
            task_type=task_type,
            stock_codes=stock_codes,
            current_position=current_position,
            stocks=stocks,
            created_at=datetime.now(),
            logs=[]
        )
        self.tasks[task_id] = task
        return task

    def get_task(self, task_id: str) -> Optional[Task]:
        """获取任务"""
        return self.tasks.get(task_id)

    def get_pending_tasks(self) -> list[Task]:
        """获取待执行任务"""
        return [t for t in self.tasks.values() if t.status == "pending"]

    def get_all_tasks(self) -> list[Task]:
        """获取所有任务"""
        return list(self.tasks.values())

    def update_task(self, task_id: str, **updates) -> Optional[Task]:
        """更新任务"""
        task = self.tasks.get(task_id)
        if task:
            for key, value in updates.items():
                if hasattr(task, key):
                    setattr(task, key, value)
        return task


task_queue = TaskQueue()