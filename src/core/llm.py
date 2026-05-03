"""LLM 集成模块 - 阿里云 DashScope + GLM-5"""

from langchain_openai import ChatOpenAI

from .config import config


def get_llm(temperature: float = 0.7) -> ChatOpenAI:
    """获取 LLM 实例

    Args:
        temperature: 生成温度，控制随机性

    Returns:
        ChatOpenAI 实例
    """
    return ChatOpenAI(
        model=config.llm.model,
        api_key=config.llm.api_key,
        base_url=config.llm.base_url,
        temperature=temperature
    )


llm = get_llm()