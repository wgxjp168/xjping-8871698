from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from pathlib import Path

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "model-iteration-svc"
    port: int = 8062
    debug: bool = False

    db_url: str = "postgresql+asyncpg://ilbuy:ilbuy@localhost:5432/ilbuy_l8"

    clickhouse_host: str = "localhost"
    clickhouse_port: int = 9000
    clickhouse_db: str = "ilbuy_analytics"
    clickhouse_user: str = "default"
    clickhouse_password: str = ""

    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"
    rabbitmq_exchange: str = "ilbuy.l8"
    rabbitmq_input_queue: str = "l8.iteration.behavior.q"
    rabbitmq_input_routing_key: str = "l8.behavior.aggregated"
    rabbitmq_output_routing_key: str = "l8.model.ready"

    # Model storage
    model_store_path: str = "/app/model_store"
    min_training_samples: int = 100
    # Evaluation thresholds
    min_auc: float = 0.65
    min_f1: float = 0.60

    # A/B test defaults
    ab_test_min_sample_size: int = 200
    ab_test_confidence_level: float = 0.95

@lru_cache
def get_settings() -> Settings:
    return Settings()
