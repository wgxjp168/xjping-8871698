from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    APP_NAME: str = "ilbuy-llm-svc"
    PORT: int = 8011
    DEBUG: bool = False

    # OpenAI
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_MODEL: str = "gpt-4-turbo-preview"

    # Anthropic Claude
    ANTHROPIC_API_KEY: Optional[str] = None
    CLAUDE_MODEL: str = "claude-opus-4-6"

    # 文心一言
    ERNIE_API_KEY: Optional[str] = None
    ERNIE_SECRET_KEY: Optional[str] = None

    # 默认使用的模型提供商
    DEFAULT_PROVIDER: str = "openai"  # openai | claude | ernie

    # 采购决策专用System Prompt
    SYSTEM_PROMPT: str = """你是我来购(ILbuy)平台的AI采购决策专家。
你的职责是帮助用户做出最优的采购决策。
请根据用户需求，结合商品数据，生成专业、客观、结构化的采购建议报告。
对B2B企业采购，重点关注：供应商资质、批量价格、交期、认证资质、售后保障。
对B2C个人消费，重点关注：性价比、品质可靠性、用户口碑、售后服务。"""

    class Config:
        env_file = ".env"


settings = Settings()
