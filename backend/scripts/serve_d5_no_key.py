"""Serve the built UI with an explicitly keyless, isolated backend on localhost:8001.

For manual failure-path acceptance only. Does not alter environment variables or the main store.
Build frontend first; run from backend/: uv run --locked python scripts/serve_d5_no_key.py
"""
from pathlib import Path
import sys

import uvicorn
from fastapi.staticfiles import StaticFiles
from pydantic import SecretStr

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.config import Settings
from app.main import create_app


def main():
    dist = Path(__file__).resolve().parents[2] / "frontend/dist"
    if not (dist / "index.html").is_file():
        raise SystemExit("Build frontend first: npm.cmd run build")
    app = create_app(Settings(_env_file=None, deepseek_api_key=SecretStr(""), data_dir=Path("data/d5-no-key")))
    app.mount("/", StaticFiles(directory=dist, html=True), name="built-ui")
    uvicorn.run(app, host="127.0.0.1", port=8001, log_level="warning")


if __name__ == "__main__":
    main()
