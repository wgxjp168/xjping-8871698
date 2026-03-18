from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "model-deploy-svc"
    port: int = 8063
    debug: bool = False

    db_url: str = "postgresql+asyncpg://ilbuy:ilbuy@localhost:5432/ilbuy_l8"

    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"
    rabbitmq_exchange: str = "ilbuy.l8"
    rabbitmq_input_queue: str = "l8.deploy.model.q"
    rabbitmq_input_routing_key: str = "l8.model.ready"
    rabbitmq_output_routing_key: str = "l8.model.deployed"

    # Decision service endpoint for model hot-swap
    decision_svc_url: str = "http://decision-svc:8012"
    # Model artifact base path (shared PVC with model-iteration-svc)
    model_store_path: str = "/app/model_store"

    # Blue/green: max deployments to keep active
    max_active_deployments: int = 2


@lru_cache
def get_settings() -> Settings:
    return Settings()
