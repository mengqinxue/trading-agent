"""初始化 Agent - 系统检测和持仓加载"""

import json
from pathlib import Path
from typing import Optional

from ..base import BaseAgent


class InitAgent(BaseAgent):
    """初始化 Agent - 系统检测、参数加载、持仓加载"""

    name = "init"
    role = "系统初始化助手"

    def get_system_prompt(self) -> str:
        return """你是系统初始化助手，负责：
1. 检测系统状态（API 连接、数据源）
2. 加载配置参数
3. 加载持仓信息
4. 初始化 Workflow 状态

请返回初始化结果。"""

    def get_user_prompt(self, context: dict) -> str:
        stock_code = context.get("stock_code", "")
        current_position = context.get("current_position", 0)

        return f"""初始化股票分析任务：
股票代码：{stock_code}
当前持仓：{current_position} 元

请确认系统状态并初始化任务。"""

    def run(self, context: dict) -> dict:
        """执行初始化

        Returns:
            dict: {
                "system_status": {"akshare": "OK", "llm": "OK"},
                "stock_code": "...",
                "stock_name": "...",
                "current_position": ...,
                "portfolio": {...},
                "initialized": True
            }
        """
        import os

        stock_code = context.get("stock_code", "")
        current_position = context.get("current_position", 0)

        # 检测系统状态
        system_status = {
            "akshare": "OK",
            "llm": "OK" if os.environ.get("DASHSCOPE_API_KEY") else "MISSING_KEY",
            "feishu": "OK" if os.environ.get("FEISHU_WEBHOOK") else "NOT_CONFIGURED"
        }

        # 加载持仓配置（如果有）
        portfolio = self._load_portfolio()

        # 获取股票名称
        stock_name = self._get_stock_name(stock_code)

        return {
            "system_status": system_status,
            "stock_code": stock_code,
            "stock_name": stock_name,
            "current_position": current_position,
            "portfolio": portfolio,
            "initialized": True,
            "logs": ["系统初始化完成", f"股票代码: {stock_code}", f"当前持仓: {current_position}"]
        }

    def _load_portfolio(self) -> dict:
        """加载持仓配置"""
        # 尝试从配置文件加载
        config_path = Path("config/portfolio.yaml")
        if config_path.exists():
            import yaml
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    return yaml.safe_load(f)
            except Exception:
                pass

        return {"positions": [], "total_value": 0}

    def _get_stock_name(self, stock_code: str) -> str:
        """获取股票名称"""
        # 使用 DataAdapter 获取（多数据源支持）
        try:
            from src.data_sources.data_adapter import get_adapter
            adapter = get_adapter()
            name = adapter.batch_get_stock_names([stock_code]).get(stock_code)
            return name or stock_code
        except Exception:
            return stock_code


def init_node(state: dict, log_folder: Optional[Path] = None) -> dict:
    """初始化节点函数"""
    from src.core.logger import logger
    from src.scheduler.workspace_manager import write_log

    if log_folder:
        write_log(log_folder, "=== Node: 初始化 [开始] ===")

    logger.info("初始化 Workflow...")

    init_agent = InitAgent(None)  # 不需要 LLM
    result = init_agent.run(state)

    if log_folder:
        write_log(log_folder, f"系统状态: {result['system_status']}")
        write_log(log_folder, f"股票名称: {result['stock_name']}")
        write_log(log_folder, f"当前持仓: {result['current_position']} 元")
        write_log(log_folder, "=== Node: 初始化 [结束] ===")

    return {
        "stock_name": result["stock_name"],
        "system_status": result["system_status"],
        "portfolio": result["portfolio"],
        "logs": state.get("logs", []) + result["logs"]
    }