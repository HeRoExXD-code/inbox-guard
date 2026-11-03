import json
from pathlib import Path

from app import config


def load_cases(path: Path | None = None) -> list[dict]:
    data = json.loads(Path(path or config.DATA_DIR / "eval_cases.json").read_text(encoding="utf-8"))
    return data["cases"]
