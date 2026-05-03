"""Agent 基类"""

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage


class BaseAgent:
    """Agent 基类"""

    name: str = "base_agent"
    role: str = "基础 Agent"

    def __init__(self, llm: BaseChatModel):
        self.llm = llm

    def get_system_prompt(self) -> str:
        """获取系统 prompt"""
        return f"你是一个专业的{self.role}。请根据提供的信息进行分析。"

    def get_user_prompt(self, context: dict) -> str:
        """获取用户 prompt"""
        raise NotImplementedError

    def run(self, context: dict) -> str:
        """执行 agent"""
        system_prompt = self.get_system_prompt()
        user_prompt = self.get_user_prompt(context)

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]

        response = self.llm.invoke(messages)
        return response.content