from __future__ import annotations

import requests
from typing import Any, Dict


def ollama_generate(base_url: str, model: str, prompt: str, temperature: float = 0.2, **kwargs) -> str:
    url = base_url.rstrip("/") + "/api/generate"
    payload: Dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": temperature},
    }
    payload.update(kwargs)
    r = requests.post(url, json=payload, timeout=180)  # Increased for article extraction
    r.raise_for_status()
    data = r.json()
    return (data.get("response") or "").strip()
