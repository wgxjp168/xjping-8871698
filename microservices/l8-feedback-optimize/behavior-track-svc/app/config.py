from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "behavior-track-svc"
    port: int = 8061
    debug: bool = False

    # PostgreSQL (for session/funnel persistence)
    db_url: str = "postgresql+asyncpg://ilbuy:ilbuy@localhost:5432/ilbuy_l8"

    # ClickHouse (L4)
    clickhouse_host: str = "localhost"
    clickhouse_port: int = 9000
    clickhouse_db: str = "ilbuy_analytics"
    clickhouse_user: str = "default"
    clickhouse_password: str = ""

    # RabbitMQ
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"
    rabbitmq_exchange: str = "ilbuy.l8"
    rabbitmq_input_queue: str = "l8.behavior.feedback.q"
    rabbitmq_input_routing_key: str = "l8.feedback.collected"
    rabbitmq_output_routing_key: str = "l8.behavior.aggregated"

    # Aggregation batch size / interval
    aggregation_batch_size: int = 1000
    aggregation_interval_minutes: int = 60

@lru_cache
def get_settings() -> Settings:
    return Settings()
