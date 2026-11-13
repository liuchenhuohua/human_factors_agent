from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "人因工程个人助手"
    database_path: Path = Path("human_factors.db")
    checkpoint_database_path: Path = Path("workflow_checkpoints.sqlite")
    allowed_origins: list[str] = ["http://localhost:3000"]
    llm_api_key: SecretStr | None = None
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-6-luna"
    llm_timeout_seconds: float = 60.0
    crossref_base_url: str = "https://api.crossref.org/v1"
    crossref_timeout_seconds: float = 30.0
    crossref_mailto: str | None = None
    document_storage_path: Path = Path("data/uploads")
    max_pdf_upload_mb: int = 25
    max_pdf_pages: int = 250
    dataset_storage_path: Path = Path("data/datasets")
    max_csv_upload_mb: int = 20

    model_config = SettingsConfigDict(env_prefix="HFA_", env_file=".env")


settings = Settings()

