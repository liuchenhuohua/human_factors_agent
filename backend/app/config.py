from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "人因工程个人助手"
    database_path: Path = Path("human_factors.db")
    allowed_origins: list[str] = ["http://localhost:3000"]

    model_config = SettingsConfigDict(env_prefix="HFA_", env_file=".env")


settings = Settings()

