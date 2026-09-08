"""Eval fixture loading."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

FIXTURES_DIR = Path(__file__).resolve().parent


def list_fixtures() -> List[str]:
    """Return fixture stem names (without .json)."""
    return sorted(p.stem for p in FIXTURES_DIR.glob("*.json"))


def load_fixture(name: str = "lost_valley_dnd") -> Dict[str, Any]:
    """Load a fixture by stem name or absolute/relative path."""
    path = Path(name)
    if not path.suffix:
        path = FIXTURES_DIR / f"{name}.json"
    if not path.exists():
        available = ", ".join(list_fixtures()) or "(none)"
        raise FileNotFoundError(f"Fixture not found: {name}. Available: {available}")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    data["_fixture_path"] = str(path)
    return data
