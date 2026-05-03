"""正方辩论 Agent（买方）"""

from ..base import BaseAgent


class BullAdvocate(BaseAgent):
    """正方辩论 Agent - 提出买入理由"""

    name = "bull_advocate"
    role = "投资正方辩论师（支持买入）"

    def get_system_prompt(self) -> str:
        return """你是投资辩论的正方，你的任务是提出买入该股票的理由。

你必须：
1. 从基本面、技术面找出支持买入的证据
2. 提出积极的市场预期
3. 强调投资机会
4. 反驳反方的观点

你的论点应该：
- 有数据支撑
- 逻辑清晰
- 真实客观
- 不夸大事实

请用简洁有力的语言提出3-5条买入理由，并尝试反驳反方的观点。"""

    def get_user_prompt(self, context: dict) -> str:
        stock_code = context.get("stock_code", "")
        fundamentals = context.get("fundamentals", {})
        technical = context.get("technical", {})
        bear_arguments = context.get("bear_arguments", [])
        debate_round = context.get("debate_rounds", 0)

        prompt = f"""股票代码：{stock_code}

基本面分析（正方可以利用优势）：
- 评分：{fundamentals.get('score', 'N/A')}
- 优势：{fundamentals.get('strengths', [])}

技术面分析（正方可以利用优势）：
- 评分：{technical.get('score', 'N/A')}
- 优势：{technical.get('strengths', [])}
- 买入信号：{technical.get('buy_signal', False)}

"""

        if bear_arguments and debate_round > 0:
            prompt += f"""反方（卖方）观点：
{bear_arguments[-1] if bear_arguments else '暂无'}

请反驳反方的观点，并提出新的买入理由。"""

        return prompt

    def run(self, context: dict) -> str:
        return super().run(context)