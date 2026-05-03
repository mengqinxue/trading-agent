"""反方辩论 Agent（卖方）"""

from ..base import BaseAgent


class BearAdvocate(BaseAgent):
    """反方辩论 Agent - 提出卖出/观望理由"""

    name = "bear_advocate"
    role = "投资反方辩论师（支持卖出/观望）"

    def get_system_prompt(self) -> str:
        return """你是投资辩论的反方，你的任务是提出卖出或观望的理由。

你必须：
1. 从基本面、技术面找出风险点
2. 提出消极的市场预期
3. 强调投资风险
4. 反驳正方的观点

你的论点应该：
- 有数据支撑
- 逻辑清晰
- 真实客观
- 不夸大风险

请用简洁有力的语言提出3-5条卖出/观望理由，并尝试反驳正方的观点。"""

    def get_user_prompt(self, context: dict) -> str:
        stock_code = context.get("stock_code", "")
        fundamentals = context.get("fundamentals", {})
        technical = context.get("technical", {})
        bull_arguments = context.get("bull_arguments", [])
        debate_round = context.get("debate_rounds", 0)

        prompt = f"""股票代码：{stock_code}

基本面分析（反方可以利用劣势）：
- 评分：{fundamentals.get('score', 'N/A')}
- 劣势：{fundamentals.get('weaknesses', [])}

技术面分析（反方可以利用劣势）：
- 评分：{technical.get('score', 'N/A')}
- 劣势：{technical.get('weaknesses', [])}
- 卖出信号：{technical.get('sell_signal', False)}

"""

        if bull_arguments and debate_round > 0:
            prompt += f"""正方（买方）观点：
{bull_arguments[-1] if bull_arguments else '暂无'}

请反驳正方的观点，并提出新的卖出/观望理由。"""

        return prompt

    def run(self, context: dict) -> str:
        return super().run(context)