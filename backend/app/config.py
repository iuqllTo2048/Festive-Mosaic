from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[1]
MANIFEST_PATH = BACKEND_DIR.parent / "samples" / "papers.json"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env", env_file_encoding="utf-8", extra="ignore"
    )
    data_dir: Path = Path("data")
    max_upload_mb: int = Field(default=20, ge=1, le=100)
    max_pdf_pages: int = Field(default=200, ge=1, le=1000)
    seed_timeout_seconds: float = Field(default=30, ge=1, le=120)
    deepseek_api_key: SecretStr = SecretStr("")
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-flash"
    llm_timeout_seconds: float = Field(default=40, ge=1, le=50)
    llm_max_tokens: int = Field(default=1800, ge=256, le=4096)
    agent_max_requests: int = Field(default=6, ge=1, le=6)
    agent_timeout_seconds: float = Field(default=100, ge=5, le=110)

    @property
    def resolved_data_dir(self) -> Path:
        return (BACKEND_DIR / self.data_dir).resolve()

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024
