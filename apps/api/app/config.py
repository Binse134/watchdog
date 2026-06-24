from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    encryption_key: str
    session_secret: str

    resend_api_key: str = ""
    alerts_from_email: str = "alerts@example.com"

    frontend_url: str = "http://localhost:3000"

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "gemma4:e4b"

    sync_interval_minutes: int = 15


settings = Settings()
