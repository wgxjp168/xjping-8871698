"""
决策编排服务配置
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    APP_NAME: str = "ilbuy-decision-svc"
    PORT: int = 8012
    DEBUG: bool = False

    # 内部服务地址
    INTENT_SVC_URL: str = "http://ilbuy-intent-svc:8010"
    LLM_SVC_URL: str = "http://ilbuy-llm-svc:8011"

    # Redis（结果缓存）
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: Optional[str] = None
    REDIS_DB: int = 1
    CACHE_TTL: int = 3600          # 决策结果缓存 1 小时

    # RabbitMQ（异步任务）
    RABBITMQ_URL: str = "amqp://ilbuy:ilbuy@2024@localhost:5672/"
    DECISION_QUEUE: str = "ilbuy.decision.tasks"

    # Nacos
    NACOS_SERVER: str = "localhost:8848"
    NACOS_NAMESPACE: str = "dev"

    # 超时设置（秒）
    INTENT_SVC_TIMEOUT: float = 5.0
    LLM_SVC_TIMEOUT: float = 30.0
    DATA_COLLECT_TIMEOUT: float = 10.0

    # 推荐候选商品数量上限
    MAX_CANDIDATES: int = 20
    REPORT_TOP_N: int = 5          # 进入报告的商品数量

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
