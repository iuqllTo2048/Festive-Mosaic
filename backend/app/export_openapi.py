"""Run from backend/: uv run python -m app.export_openapi."""
import json

from .config import BACKEND_DIR
from .main import app

if __name__ == "__main__":
    target = BACKEND_DIR.parent / "frontend" / "openapi.json"
    target.write_text(json.dumps(app.openapi(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Exported {target}")
