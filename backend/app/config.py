from pathlib import Path

from pydantic import Field
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

    @property
    def resolved_data_dir(self) -> Path:
        return (BACKEND_DIR / self.data_dir).resolve()

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024
