from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "feedback-svc"
    port: int = 8060
    debug: bool = False

    # DB
    db_url: str = "postgresql+asyncpg://ilbuy:ilbuy@localhost:5432/ilbuy_l8"

    # RabbitMQ
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"
    rabbitmq_exchange: str = "ilbuy.l8"
    rabbitmq_input_queue: str = "l8.feedback.delivery.q"
    rabbitmq_input_routing_key: str = "l6.delivery.completed"
    rabbitmq_output_routing_key: str = "l8.feedback.collected"

    # L6 delivery svc URL
    l6_delivery_url: str = "http://delivery-svc:8065"
    
    # Follow-up delay hours after delivery
    followup_delay_hours: int = 24

@lru_cache
def get_settings() -> Settings:
    return Settings()
