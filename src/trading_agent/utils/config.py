"""
Configuration management

Loads config from YAML files and environment variables.
"""

import os
import re
from pathlib import Path
from typing import Any, List, Optional
import yaml
from pydantic import BaseModel
from dotenv import load_dotenv


# Load .env file
load_dotenv()


class FallbackLLMConfig(BaseModel):
    """Fallback LLM configuration"""
    provider: str
    model: str
    api_key: Optional[str] = None


class LLMConfig(BaseModel):
    """LLM configuration"""
    provider: str = "openai"
    model: str = "gpt-4"
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 4000
    fallbacks: List[FallbackLLMConfig] = []


class DebateConfig(BaseModel):
    """Debate configuration"""
    max_rounds: int = 100
    convergence_threshold: float = 0.8
    buyer_agent_prompt: str = "agents/prompts/debater_buy.txt"
    seller_agent_prompt: str = "agents/prompts/debater_sell.txt"


class PreMarketSchedule(BaseModel):
    """Pre-market schedule configuration"""
    time: str = "09:00"
    days: List[str] = ["mon", "tue", "wed", "thu", "fri"]
    enabled: bool = True


class PostMarketSchedule(BaseModel):
    """Post-market schedule configuration"""
    time: str = "15:30"
    days: List[str] = ["mon", "tue", "wed", "thu", "fri"]
    enabled: bool = True


class ScheduleConfig(BaseModel):
    """Schedule configuration"""
    pre_market: PreMarketSchedule = PreMarketSchedule()
    post_market: PostMarketSchedule = PostMarketSchedule()


class FeishuPushConfig(BaseModel):
    """Feishu push configuration"""
    webhook: Optional[str] = None
    enabled: bool = True


class EmailPushConfig(BaseModel):
    """Email push configuration"""
    smtp_server: Optional[str] = None
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    to: Optional[str] = None
    enabled: bool = False


class PushConfig(BaseModel):
    """Push notification configuration"""
    feishu: FeishuPushConfig = FeishuPushConfig()
    email: EmailPushConfig = EmailPushConfig()


class TrendRadarConfig(BaseModel):
    """TrendRadar MCP configuration"""
    mcp_path: Optional[str] = None
    enabled: bool = True


class AkshareConfig(BaseModel):
    """Akshare data source configuration"""
    enabled: bool = True
    proxy: str = ""


class StockDBConfig(BaseModel):
    """Stock database configuration"""
    path: str = "data/stock_db/stocks.json"
    update_interval: str = "weekly"


class DataSourceConfig(BaseModel):
    """Data source configuration"""
    trendradar: TrendRadarConfig = TrendRadarConfig()
    akshare: AkshareConfig = AkshareConfig()
    stock_db: StockDBConfig = StockDBConfig()


class PathsConfig(BaseModel):
    """Paths configuration"""
    data_dir: str = "data"
    log_dir: str = "logs"
    candidates_dir: str = "data/candidates"
    decisions_dir: str = "data/decisions"


class PortfolioConfig(BaseModel):
    """Portfolio configuration"""
    config_path: str = "config/portfolio.yaml"
    keywords_path: str = "config/keywords.yaml"


class RuntimeConfig(BaseModel):
    """Runtime configuration"""
    debug: bool = False
    log_level: str = "INFO"


class Settings(BaseModel):
    """Application settings"""
    llm: LLMConfig = LLMConfig()
    debate: DebateConfig = DebateConfig()
    schedule: ScheduleConfig = ScheduleConfig()
    push: PushConfig = PushConfig()
    data_sources: DataSourceConfig = DataSourceConfig()
    paths: PathsConfig = PathsConfig()
    portfolio: PortfolioConfig = PortfolioConfig()
    runtime: RuntimeConfig = RuntimeConfig()


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


def _resolve_env_vars(value: Any) -> Any:
    """
    Resolve environment variables in config values

    Supports ${VAR_NAME} syntax anywhere in strings

    Args:
        value: Config value with potential env var references

    Returns:
        Config value with resolved environment variables
    """
    if isinstance(value, str):
        # Match ${VAR_NAME} pattern
        pattern = r"\$\{([^}]+)\}"

        def replace_env_var(match: re.Match) -> str:
            env_var = match.group(1)
            resolved = os.getenv(env_var)
            if resolved is not None:
                return resolved
            # Return original if env var not found
            return match.group(0)

        return re.sub(pattern, replace_env_var, value)

    elif isinstance(value, dict):
        return {k: _resolve_env_vars(v) for k, v in value.items()}

    elif isinstance(value, list):
        return [_resolve_env_vars(item) for item in value]

    else:
        return value


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get global settings instance"""
    if _settings is None:
        _settings = load_config()
    return _settings