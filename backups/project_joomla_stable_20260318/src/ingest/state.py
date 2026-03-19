from __future__ import annotations

import json
import hashlib
from pathlib import Path
from typing import Dict, Any


STATE_PATH = Path("data/state.json")


def compute_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()


def load_state() -> Dict[str, Any]:
    if not STATE_PATH.exists():
        return {"pages": {}}
    return json.loads(STATE_PATH.read_text(encoding="utf-8"))


def save_state(state: Dict[str, Any]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def get_page_hash(state: Dict[str, Any], url: str) -> str | None:
    return state.get("pages", {}).get(url, {}).get("content_hash")


def set_page_hash(state: Dict[str, Any], url: str, content_hash: str, meta: Dict[str, Any] | None = None) -> None:
    state.setdefault("pages", {})
    state["pages"][url] = {
        "content_hash": content_hash,
        **(meta or {}),
    }

def get_indexed_hash(state: Dict[str, Any], url: str) -> str | None:
    return state.get("pages", {}).get(url, {}).get("indexed_hash")


def set_indexed_hash(state: Dict[str, Any], url: str, indexed_hash: str) -> None:
    state.setdefault("pages", {})
    state.setdefault("pages", {}).setdefault(url, {})
    state["pages"][url]["indexed_hash"] = indexed_hash
