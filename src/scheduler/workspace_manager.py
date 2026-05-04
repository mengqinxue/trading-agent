"""Workspace 任务管理

管理任务文件夹结构：
- workspace/
  - ma_20260503_123456_abc12345/    # 市场分析任务
    - status.json                  # 任务状态
    - logs.txt                     # 执行日志
    - result.json                  # 分析结果
  - stock_20260503_123456_def67890/  # 股票分析任务
    - status.json
    - logs.txt
    - result.json
  - bt_20260503_123456_ghi89012/    # 回测任务
    - status.json                  # 任务状态 + 策略参数
    - logs.txt                     # 执行日志
    - strategy_log.md              # 策略详细日志
    - result.json                  # 回测结果

状态定义：
- pending: 待执行（只有 status.json）
- running: 执行中（logs.txt 有内容，无 result.json）
- completed: 已完成（有 result.json 且无 error）
- failed: 失败（result.json 包含 error 字段）
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import uuid4

# 项目根目录下的 workspace
WORKSPACE_DIR = Path(__file__).parent.parent.parent / "workspace"


def create_task_folder(
    task_type: str,
    task_id: str,
    stocks: Optional[list[dict]] = None,
    description: Optional[str] = None,
    params: Optional[dict] = None
) -> Path:
    """创建任务文件夹并初始化 status.json

    Args:
        task_type: market_analysis / stock_analysis / backtest
        task_id: 任务 ID
        stocks: 股票列表 [{code, position}]
        description: 回测策略描述（仅 backtest 类型）
        params: 回测参数（仅 backtest 类型）

    Returns:
        任务文件夹路径
    """
    # 确保目录存在
    WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)

    # 生成文件夹名称（根据任务类型）
    if task_type == "market_analysis":
        prefix = "ma"
    elif task_type == "stock_analysis":
        prefix = "stock"
    elif task_type == "backtest":
        prefix = "bt"
    else:
        prefix = "task"

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    short_id = task_id[:8]

    folder_name = f"{prefix}_{timestamp}_{short_id}"
    folder_path = WORKSPACE_DIR / folder_name

    # 创建文件夹
    folder_path.mkdir(parents=True, exist_ok=True)

    # 创建空的 logs.txt
    logs_file = folder_path / "logs.txt"
    logs_file.write_text("", encoding="utf-8")

    # 创建 status.json（初始状态：pending）
    status_data = {
        "task_id": task_id,
        "task_type": task_type,
        "status": "pending",
        "created_at": datetime.now().isoformat(),
        "started_at": None,
        "completed_at": None,
        "stocks": stocks,
        "workflow_steps": [],
        "description": description,
        "params": params
    }
    write_status(folder_path, status_data)

    return folder_path


def write_status(folder_path: Path, status_data: dict):
    """写入/更新状态文件

    Args:
        folder_path: 任务文件夹路径
        status_data: 状态数据
    """
    status_file = folder_path / "status.json"
    with open(status_file, "w", encoding="utf-8") as f:
        json.dump(status_data, f, ensure_ascii=False, indent=2)


def read_status(folder_path: Path) -> Optional[dict]:
    """读取状态文件

    Args:
        folder_path: 任务文件夹路径

    Returns:
        状态数据，如果不存在返回 None
    """
    status_file = folder_path / "status.json"
    if not status_file.exists():
        return None
    try:
        return json.loads(status_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, IOError):
        return None


def update_status(
    folder_path: Path,
    status: Optional[str] = None,
    started_at: Optional[datetime] = None,
    completed_at: Optional[datetime] = None,
    workflow_step: Optional[dict] = None
):
    """更新状态

    Args:
        folder_path: 任务文件夹路径
        status: 新状态（pending/running/completed/failed）
        started_at: 开始时间
        completed_at: 完成时间
        workflow_step: Workflow 步骤 {name, started_at, completed_at}
    """
    status_data = read_status(folder_path)
    if not status_data:
        return

    if status:
        status_data["status"] = status
    if started_at:
        status_data["started_at"] = started_at.isoformat()
    if completed_at:
        status_data["completed_at"] = completed_at.isoformat()
    if workflow_step:
        status_data["workflow_steps"].append(workflow_step)

    write_status(folder_path, status_data)


def get_task_status(folder_path: Path) -> str:
    """从文件推断任务状态

    Args:
        folder_path: 任务文件夹路径

    Returns:
        状态字符串
    """
    # 先读取 status.json
    status_data = read_status(folder_path)
    if status_data and status_data.get("status"):
        return status_data["status"]

    # 推断状态
    result_file = folder_path / "result.json"
    logs_file = folder_path / "logs.txt"

    if result_file.exists():
        try:
            result = json.loads(result_file.read_text(encoding="utf-8"))
            if "error" in result:
                return "failed"
            return "completed"
        except:
            return "completed"

    if logs_file.exists() and logs_file.read_text(encoding="utf-8").strip():
        return "running"

    return "pending"


def write_log(folder_path: Path, message: str):
    """写入日志到任务文件夹

    Args:
        folder_path: 任务文件夹路径
        message: 日志消息
    """
    logs_file = folder_path / "logs.txt"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] {message}\n"

    with open(logs_file, "a", encoding="utf-8") as f:
        f.write(log_line)


def write_result(folder_path: Path, result: dict):
    """保存结果到任务文件夹

    Args:
        folder_path: 任务文件夹路径
        result: 分析结果
    """
    result_file = folder_path / "result.json"
    with open(result_file, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)


def get_task_folder_by_id(task_id: str) -> Optional[Path]:
    """根据任务 ID 找到对应的文件夹

    Args:
        task_id: 任务 ID（完整或前8位）

    Returns:
        文件夹路径，如果不存在返回 None
    """
    short_id = task_id[:8]
    for folder in WORKSPACE_DIR.iterdir():
        if folder.is_dir() and folder.name.endswith(short_id):
            return folder
    return None


def list_task_folders() -> list[Path]:
    """列出所有任务文件夹

    Returns:
        任务文件夹列表（按时间倒序）
    """
    if not WORKSPACE_DIR.exists():
        return []

    folders = [f for f in WORKSPACE_DIR.iterdir() if f.is_dir()]
    # 按名称排序（包含时间戳）
    folders.sort(reverse=True)
    return folders


def list_all_tasks() -> list[dict]:
    """列出所有任务及其状态

    Returns:
        任务列表 [{folder_name, task_id, task_type, status, created_at, stocks, description, params}]
    """
    folders = list_task_folders()
    tasks = []

    for folder in folders:
        status_data = read_status(folder)
        if status_data:
            tasks.append({
                "folder_name": folder.name,
                "folder_path": str(folder),
                "task_id": status_data.get("task_id", ""),
                "task_type": status_data.get("task_type", ""),
                "status": get_task_status(folder),
                "created_at": status_data.get("created_at"),
                "stocks": status_data.get("stocks"),
                "description": status_data.get("description"),
                "params": status_data.get("params")
            })
        else:
            # 无 status.json，从文件夹名推断
            folder_name = folder.name
            parts = folder_name.split("_")
            prefix = parts[0]
            if prefix == "ma":
                task_type = "market_analysis"
            elif prefix == "stock":
                task_type = "stock_analysis"
            elif prefix == "bt":
                task_type = "backtest"
            else:
                task_type = "unknown"
            tasks.append({
                "folder_name": folder_name,
                "folder_path": str(folder),
                "task_id": parts[-1] if len(parts) > 3 else "",
                "task_type": task_type,
                "status": get_task_status(folder),
                "created_at": None,
                "stocks": None,
                "description": None,
                "params": None
            })

    return tasks


def get_task_detail(folder_path: Path) -> dict:
    """获取任务详情

    Args:
        folder_path: 任务文件夹路径

    Returns:
        任务详情（包含 status、logs、result）
    """
    status_data = read_status(folder_path) or {}

    # 读取日志
    logs_file = folder_path / "logs.txt"
    logs = []
    if logs_file.exists():
        logs = logs_file.read_text(encoding="utf-8").strip().split("\n")

    # 读取结果
    result_file = folder_path / "result.json"
    result = None
    summary = None
    if result_file.exists():
        try:
            result = json.loads(result_file.read_text(encoding="utf-8"))
            # 提取 summary
            if "summary" in result:
                summary = result["summary"]
            elif "final_decision" in result:
                summary = result["final_decision"]
            elif "batch_results" in result:
                # 批量分析的 summary
                summary = result.get("summary")
        except:
            pass

    return {
        "folder_name": folder_path.name,
        "folder_path": str(folder_path),
        "task_id": status_data.get("task_id", ""),
        "task_type": status_data.get("task_type", ""),
        "status": get_task_status(folder_path),
        "created_at": status_data.get("created_at"),
        "started_at": status_data.get("started_at"),
        "completed_at": status_data.get("completed_at"),
        "stocks": status_data.get("stocks"),
        "workflow_steps": status_data.get("workflow_steps", []),
        "summary": summary,
        "result": result,
        "logs": logs,
        "description": status_data.get("description"),
        "params": status_data.get("params")
    }


def generate_task_id() -> str:
    """生成任务 ID"""
    return str(uuid4())