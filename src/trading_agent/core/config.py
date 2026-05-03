"""配置管理模块"""

import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel


class LLMConfig(BaseModel):
    """LLM 配置"""
    api_key: str
    base_url: str = "https://coding.dashscope.aliyuncs.com/v1"
    model: str = "glm-5"


class AppConfig(BaseModel):
    """应用配置"""
    llm: LLMConfig
    log_level: str = "INFO"
    log_dir: Path = Path("logs")


def load_config() -> AppConfig:
    """加载配置"""
    load_dotenv()

    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        raise ValueError("DASHSCOPE_API_KEY environment variable is required")

    llm_config = LLMConfig(
        api_key=api_key,
        base_url=os.getenv("DASHSCOPE_BASE_URL", "https://coding.dashscope.aliyuncs.com/v1"),
        model=os.getenv("DASHSCOPE_MODEL", "glm-5")
    )

    log_dir = Path(os.getenv("LOG_DIR", "logs"))

    return AppConfig(
        llm=llm_config,
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        log_dir=log_dir
    )


config = load_config()