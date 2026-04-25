"""
Configuration management

Loads config from YAML files and environment variables.
"""

import os
from pathlib import Path
from typing import Any, Optional
import yaml
from pydantic import BaseModel
from dotenv import load_dotenv


# Load .env file
load_dotenv()


class LLMConfig(BaseModel):
    """LLM configuration"""
    provider: str = "openai"
    model: str = "gpt-4"
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 4000


class DebateConfig(BaseModel):
    """Debate configuration"""
    max_rounds: int = 100
    convergence_threshold: float = 0.8


class ScheduleConfig(BaseModel):
    """Schedule configuration"""
    pre_market_time: str = "09:00"
    post_market_time: str = "15:30"
    enabled: bool = True


class PushConfig(BaseModel):
    """Push notification configuration"""
    feishu_webhook: Optional[str] = None
    feishu_enabled: bool = False
    email_enabled: bool = False


class DataSourceConfig(BaseModel):
    """Data source configuration"""
    akshare_enabled: bool = True
    trendradar_mcp_path: Optional[str] = None
    stock_db_path: str = "data/stock_db/stocks.json"


class Settings(BaseModel):
    """Application settings"""
    llm: LLMConfig = LLMConfig()
    debate: DebateConfig = DebateConfig()
    schedule: ScheduleConfig = ScheduleConfig()
    push: PushConfig = PushConfig()
    data_sources: DataSourceConfig = DataSourceConfig()

    # Paths
    data_dir: Path = Path("data")
    log_dir: Path = Path("logs")

    # Runtime
    debug: bool = False


def load_config(config_path: Optional[Path] = None) -> Settings:
    """
    Load configuration from YAML file

    Args:
        config_path: Path to config.yaml (defaults to config/config.yaml)

    Returns:
        Settings instance
    """
    if config_path is None:
        # Look for config in standard locations
        candidates = [
            Path("config/config.yaml"),
            Path("config.yaml"),
            Path.cwd() / "config/config.yaml",
        ]
        for candidate in candidates:
            if candidate.exists():
                config_path = candidate
                break

    if config_path and config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f)

        # Resolve environment variables in config
        config_data = _resolve_env_vars(config_data)

        return Settings(**config_data)

    # Return default settings if no config file
    return Settings()


def _resolve_env_vars(config: dict) -> dict:
    """
    Resolve environment variables in config values

    Supports ${VAR_NAME} syntax

    Args:
        config: Config dict with potential env var references

    Returns:
        Config dict with resolved values
    """
    result = {}

    for key, value in config.items():
        if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
            env_var = value[2:-1]
            resolved = os.getenv(env_var)
            if resolved:
                result[key] = resolved
            else:
                result[key] = value  # Keep original if env var not found
        elif isinstance(value, dict):
            result[key] = _resolve_env_vars(value)
        else:
            result[key] = value

    return result


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get global settings instance"""
    if _settings is None:
        _settings = load_config()
    return _settings