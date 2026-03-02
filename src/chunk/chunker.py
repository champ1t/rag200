from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, List


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    text: str
    metadata: Dict[str, Any]


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 80) -> List[str]:
    text = text.strip()
    if not text:
        return []

    chunks: List[str] = []
    start = 0
    n = len(text)

    while start < n:
        end = min(start + chunk_size, n)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        if end == n:
            break

        start = max(0, end - overlap)

    return chunks


def make_chunks(doc: Dict[str, Any], chunk_size: int, overlap: int) -> List[Chunk]:
    url = doc.get("url", "")
    title = doc.get("title", "")
    category = doc.get("category", "")
    full_text = doc.get("text", "")

    parts = chunk_text(full_text, chunk_size=chunk_size, overlap=overlap)
    out: List[Chunk] = []

    content_type = doc.get("content_type", "general")

    base_meta = {
        "url": url,
        "title": title,
        "category": category,
        "content_type": content_type,
    }

    for i, t in enumerate(parts):
        cid = f"{url}::chunk{i}"
        meta = dict(base_meta)
        meta["chunk_index"] = i
        out.append(Chunk(chunk_id=cid, text=t, metadata=meta))

    return out
