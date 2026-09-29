"""
StudyMate AI - Application Configuration
All configuration is loaded from environment variables via .env
"""
import os
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    app_name: str = "StudyMate AI"
    app_version: str = "1.0.0"
    app_env: str = Field(default="development", env="APP_ENV")
    app_host: str = Field(default="127.0.0.1", env="APP_HOST")
    app_port: int = Field(default=8000, env="APP_PORT")
    debug: bool = Field(default=True, env="DEBUG")

    # Ollama Local AI - loaded from environment, never hardcoded
    ollama_base_url: str = Field(
        default="http://localhost:11434", env="OLLAMA_BASE_URL"
    )
    ollama_model: str = Field(
        default="qwen2.5:7b", env="OLLAMA_MODEL"
    )
    ollama_timeout_seconds: int = Field(
        default=120, env="OLLAMA_TIMEOUT_SECONDS"
    )

    # Database
    database_url: str = Field(
        default="sqlite:///./data/studymate.db", env="DATABASE_URL"
    )

    # File Upload
    max_file_size_mb: int = Field(default=20, env="MAX_FILE_SIZE_MB")
    upload_dir: str = Field(default="uploads", env="UPLOAD_DIR")
    allowed_extensions: list[str] = [".pdf", ".docx", ".txt"]

    # Security
    secret_key: str = Field(
        default="dev-secret-key-change-in-production", env="SECRET_KEY"
    )

    model_config = {"env_file": ".env", "case_sensitive": False}

    @property
    def max_file_size_bytes(self) -> int:
        return self.max_file_size_mb * 1024 * 1024

    @property
    def upload_path(self) -> Path:
        path = Path(self.upload_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def data_path(self) -> Path:
        path = Path("data")
        path.mkdir(parents=True, exist_ok=True)
        return path

    def is_ollama_configured(self) -> bool:
        """Check if Ollama configuration is set."""
        return bool(self.ollama_base_url.strip() and self.ollama_model.strip())


# Singleton settings instance
settings = Settings()
