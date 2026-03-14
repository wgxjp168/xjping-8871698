"""
意图识别服务配置
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    APP_NAME: str = "ilbuy-intent-svc"
    PORT: int = 8010
    DEBUG: bool = False

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: Optional[str] = None
    REDIS_DB: int = 0

    # Nacos
    NACOS_SERVER: str = "localhost:8848"
    NACOS_NAMESPACE: str = "dev"

    # NLP模型配置
    NLP_MODEL: str = "bert-base-chinese"
    MAX_SEQ_LENGTH: int = 512

    # B2B/B2C分类阈值
    INTENT_THRESHOLD: float = 0.7

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
