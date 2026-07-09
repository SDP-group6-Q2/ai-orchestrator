"""Application settings, loaded from environment / .env."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "ai-orchestrator"
    host: str = "0.0.0.0"
    port: int = 8001

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1"


settings = Settings()
