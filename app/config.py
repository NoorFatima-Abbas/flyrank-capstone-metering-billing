from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/meterly"
    stripe_api_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_pro_price_id: str = ""
    app_base_url: str = "http://127.0.0.1:8000"

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()