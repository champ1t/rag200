from __future__ import annotations

from typing import Any, Dict

from .chroma import ChromaVectorStore


def build_vectorstore(cfg: Dict[str, Any]):
    vs_cfg = cfg.get("vectorstore", {})
    vs_type = vs_cfg.get("type", "chroma")

    if vs_type == "chroma":
        return ChromaVectorStore(
            persist_dir=vs_cfg.get("persist_dir", "data/vectorstore"),
            collection_name=vs_cfg.get("collection_name", "web_knowledge"),
            embedding_model=vs_cfg.get("embedding_model", "sentence-transformers/all-MiniLM-L6-v2"),
        )

    raise ValueError(f"Unsupported vectorstore type: {vs_type}")
