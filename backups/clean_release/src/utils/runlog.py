from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, Optional


def make_run_id() -> str:
    # e.g. run_20251222_091530
    return "run_" + time.strftime("%Y%m%d_%H%M%S")


def ensure_run_dir(run_id: str) -> Path:
    p = Path("results") / "runs" / run_id
    p.mkdir(parents=True, exist_ok=True)
    return p


def append_jsonl(path: Path, record: Dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def now_ts() -> float:
    return time.time()
