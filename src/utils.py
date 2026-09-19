"""Small, dependency-light file and text utilities."""
import json
import re
from pathlib import Path
from typing import Any


def clean_text(text: str) -> str:
    return re.sub(r"[ \t]+", " ", re.sub(r"\n{3,}", "\n\n", text)).strip()


def jsonable(data: Any) -> Any:
    return data.model_dump() if hasattr(data, "model_dump") else data


def write_json(path: str | Path, data: Any) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(jsonable(data), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return target


def safe_stem(path: str | Path) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", Path(path).stem).strip("_") or "document"