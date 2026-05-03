"""飞书推送 Agent - 推送决策报告到飞书"""

import os
from typing import Optional
from pathlib import Path

import httpx

from ..base import BaseAgent


class FeishuPush(BaseAgent):
    """飞书推送 Agent - 推送决策报告"""

    name = "feishu_push"
    role = "飞书消息推送助手"

    def __init__(self, llm=None, webhook_url: str = None):
        super().__init__(llm)
        self.webhook_url = webhook_url or os.environ.get("FEISHU_WEBHOOK", "")

    def get_system_prompt(self) -> str:
        return "你是飞书消息推送助手，负责格式化决策报告并推送。"

    def get_user_prompt(self, context: dict) -> str:
        return "格式化决策报告。"

    def run(self, context: dict) -> dict:
        """执行推送"""
        decision = context.get("final_decision", {})
        position_advice = context.get("position_advice", {})
        stock_code = context.get("stock_code", "")
        stock_name = context.get("stock_name", stock_code)

        # 格式化消息
        message = self._format_message(stock_code, stock_name, decision, position_advice)

        # 推送
        if self.webhook_url:
            success = self._send_to_feishu(message)
            return {
                "push_success": success,
                "push_target": "feishu",
                "message_preview": message.get("title", "")
            }
        else:
            return {
                "push_success": False,
                "push_target": "none",
                "message_preview": "飞书 Webhook 未配置"
            }

    def _format_message(self, stock_code: str, stock_name: str, decision: dict, position: dict) -> dict:
        """格式化飞书消息"""
        action = decision.get("decision", "hold")
        confidence = decision.get("confidence", 0)
        reason = decision.get("reason", "")

        # 动作颜色
        action_color = {
            "buy": "green",
            "sell": "red",
            "hold": "grey"
        }.get(action, "grey")

        # 动作中文
        action_cn = {
            "buy": "买入",
            "sell": "卖出",
            "hold": "观望"
        }.get(action, "观望")

        return {
            "title": f"📊 股票分析报告：{stock_name} ({stock_code})",
            "content": f"""
**决策**: {action_cn}
**置信度**: {confidence:.0%}
**建议金额**: {position.get('suggested_amount', 0)} 元
**止损位**: {position.get('stop_loss', 'N/A')}
**止盈位**: {position.get('take_profit', 'N/A')}

**决策理由**:
{reason}

**风险提示**:
{', '.join(position.get('risk_warnings', []))}
""",
            "color": action_color
        }

    def _send_to_feishu(self, message: dict) -> bool:
        """发送到飞书 Webhook"""
        try:
            payload = {
                "msg_type": "interactive",
                "card": {
                    "header": {
                        "title": {
                            "tag": "plain_text",
                            "content": message["title"]
                        },
                        "template": message["color"]
                    },
                    "elements": [
                        {
                            "tag": "div",
                            "text": {
                                "tag": "lark_md",
                                "content": message["content"]
                            }
                        }
                    ]
                }
            }

            response = httpx.post(
                self.webhook_url,
                json=payload,
                timeout=10
            )

            return response.status_code == 200
        except Exception:
            return False


def feishu_push_node(state: dict, log_folder: Optional[Path] = None) -> dict:
    """飞书推送节点函数"""
    from src.core.logger import logger
    from src.scheduler.workspace_manager import write_log

    if log_folder:
        write_log(log_folder, "=== Node: 飞书推送 [开始] ===")

    logger.info("推送决策报告到飞书...")

    push_agent = FeishuPush()
    result = push_agent.run(state)

    if log_folder:
        if result["push_success"]:
            write_log(log_folder, "飞书推送成功")
        else:
            write_log(log_folder, f"飞书推送失败: {result['message_preview']}")
        write_log(log_folder, "=== Node: 飞书推送 [结束] ===")

    return {
        "push_result": result,
        "logs": state.get("logs", []) + ["推送完成"]
    }