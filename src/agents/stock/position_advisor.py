"""持仓建议 Agent"""

import json
from ..base import BaseAgent


class PositionAdvisor(BaseAgent):
    """持仓建议 Agent - 根据决策给出具体操作建议"""

    name = "position_advisor"
    role = "持仓顾问"

    def get_system_prompt(self) -> str:
        return """你是持仓顾问，你的任务是根据投资决策给出具体的操作建议。

你需要考虑：
1. 当前持仓情况
2. 冺策类型（buy/sell/hold）
3. 股票价格
4. 风险控制

建议原则：
- 分批建仓，不要一次性买入
- 设置止损位
- 控制仓位比例
- 留有安全边际

请用 JSON 格式返回：
{
    "action": "买入/卖出/持有",
    "amount": 建议金额（元）,
    "quantity": 建议股数（整数）,
    "position_ratio": 建议仓位比例（0-1）,
    "stop_loss": 止损价位,
    "take_profit": 止盈价位,
    "timing": "立即/分批/观望",
    "risk_warnings": ["风险提示1", ...],
    "detailed_suggestion": "详细操作建议"
}"""

    def get_user_prompt(self, context: dict) -> str:
        stock_code = context.get("stock_code", "")
        stock_name = context.get("stock_name", "")
        current_price = context.get("current_price", 0)
        current_position = context.get("current_position", 0)
        decision = context.get("final_decision", {})
        fundamentals = context.get("fundamentals", {})

        return f"""股票：{stock_code} {stock_name}
当前价格：{current_price} 元
当前持仓：{current_position} 元

决策：{decision.get('decision', 'hold')}
决策置信度：{decision.get('confidence', 0.5)}
决策理由：{decision.get('reason', '')}

请给出具体的持仓操作建议。"""

    def run(self, context: dict) -> dict:
        response = super().run(context)
        try:
            result = json.loads(response)
            return result
        except json.JSONDecodeError:
            return {
                "action": "持有",
                "amount": 0,
                "error": "无法解析建议结果",
                "raw_response": response
            }