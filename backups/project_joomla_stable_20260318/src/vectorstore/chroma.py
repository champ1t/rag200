from __future__ import annotations

from typing import Any, Dict, List, Optional
from pathlib import Path
import json

import chromadb

from .base import SearchResult
from .bm25 import SimpleBM25

class ChromaVectorStore:
    def __init__(
        self,
        persist_dir: str,
        collection_name: str = "web_knowledge",
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
        bm25_path: str = "data/bm25_index.json"
    ) -> None:
        self.persist_dir = str(Path(persist_dir))
        Path(self.persist_dir).mkdir(parents=True, exist_ok=True)
        
        self.bm25_path = bm25_path

        self.client = chromadb.PersistentClient(path=self.persist_dir)
        
        # Try to use SentenceTransformer, fallback to default if torch incompatible
        try:
            from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
            self.embed_fn = SentenceTransformerEmbeddingFunction(model_name=embedding_model)
            print(f"[VectorStore] Using SentenceTransformer: {embedding_model}")
        except Exception as e:
            print(f"[VectorStore] SentenceTransformer unavailable (torch compatibility): {e}")
            print("[VectorStore] Using default embedding function (fallback)")
            from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
            self.embed_fn = DefaultEmbeddingFunction()

        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=self.embed_fn,
            metadata={"hnsw:space": "cosine"},
        )
        
        # Initialize BM25
        self.bm25 = SimpleBM25()
        if Path(self.bm25_path).exists():
            print(f"[VectorStore] Loading BM25 index from {self.bm25_path}...")
            try:
                self.bm25.load(self.bm25_path)
            except Exception as e:
                print(f"[VectorStore] Failed to load BM25 index: {e}. Starting fresh.")
        else:
             # print(f"[VectorStore] No BM25 index found at {self.bm25_path}. Will be built on next upsert.")
             pass # Suppress warning for cleaner startup

    def upsert(self, ids: List[str], texts: List[str], metadatas: List[Dict[str, Any]]) -> None:
        if not (len(ids) == len(texts) == len(metadatas)):
            raise ValueError("ids, texts, metadatas must have the same length")

        # 1. Update Chroma (Vector)
        self.collection.upsert(ids=ids, documents=texts, metadatas=metadatas)
        
        # 2. Update BM25 (Keyword)
        # Note: In a real system you'd want to handle deletions too.
        # Here we just add/update.
        for doc_id, text in zip(ids, texts):
            self.bm25.add_document(doc_id, text)
            
        # 3. Save BM25 immediately (Simple consistency)
        # Might be slow for bulk updates, but fine for this scale
        try:
            self.bm25.save(self.bm25_path)
        except Exception as e:
            print(f"[VectorStore] Failed to save BM25 index: {e}")

    def query(
        self,
        query_text: str,
        top_k: int = 3,
        where: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        """Standard Vector Search"""
        res = self.collection.query(
            query_texts=[query_text],
            n_results=top_k,
            where=where,
            include=["documents", "metadatas", "distances"],
        )

        docs = res.get("documents", [[]])[0] or []
        metas = res.get("metadatas", [[]])[0] or []
        dists = res.get("distances", [[]])[0] or []

        out: List[SearchResult] = []
        for doc, meta, dist in zip(docs, metas, dists):
            score = float(1.0 - dist) if dist is not None else 0.0
            out.append(SearchResult(text=str(doc), score=score, metadata=dict(meta or {})))
        return out
        
    def hybrid_query(
        self,
        query_text: str,
        top_k: int = 3,
        alpha: float = 0.5, # Weight for Vector (0.0=Pure BM25, 1.0=Pure Vector)
        where: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        """
        Hybrid Search: Combined Vector + BM25 using Weighted Sum.
        """
        # 1. Vector Search (Get more candidates to fuse)
        # Fetch 2x candidates for fusion
        vector_res = self.query(query_text, top_k=top_k*2, where=where)
        
        # 2. BM25 Search
        bm25_scores = self.bm25.get_scores(query_text, top_k=top_k*2)
        # bm25_scores is list of (doc_id, score)
        # We need Doc content to fuse? 
        # Wait, BM25 returns doc_ids. We need to fetch metadata/text if not stored.
        # But our BM25 doesn't store metadata, only text (optionally).
        # Chroma has the data. 
        # Strategy: 
        #  - Get Union of doc_ids from both.
        #  - Fetch missing details from Chroma? Or just rely on what we have?
        #  - Actually, fusion usually requires reranking the union.
        
        # Let's simplify:
        # Use a map to store scores: doc_id -> {vector_score: 0, bm25_score: 0, ...}
        
        combined_scores = {}
        
        # Normalize Vector Scores (Assume 0-1 from Cosine impl)
        # Chroma Distance (Cosine) is 0..2 (if not normalized) or 0..1 typically. 
        # Our `query` method converts dist to 1-dist. So it is <= 1.
        
        # Collect Vector Results
        # Problem: 'query' returns SearchResult, which doesn't expose ID easily unless added to metadata?
        # Standard Chroma response includes IDs but our `query` wrapper swallows them.
        # WE NEED IDS.
        
        # Let's re-implement query internals here to get IDs
        v_raw = self.collection.query(
            query_texts=[query_text],
            n_results=top_k*3, # increased window
            where=where,
            include=["documents", "metadatas", "distances"] 
        )
        
        v_ids = v_raw["ids"][0]
        v_dists = v_raw["distances"][0]
        v_docs = v_raw["documents"][0]
        v_metas = v_raw["metadatas"][0]
        
        # Map ID -> Object
        doc_map = {} # id -> {text, metadata}
        
        max_v_score = 0.0
        for vid, dist, doc, meta in zip(v_ids, v_dists, v_docs, v_metas):
            score = 1.0 - dist
            combined_scores[vid] = {"v": score, "bm25": 0.0}
            doc_map[vid] = {"text": doc, "metadata": meta}
            if score > max_v_score: max_v_score = score
            
        # Collect BM25 Results
        # Normalize BM25? It's unbounded.
        # Simple normalization: score / max_score
        max_bm25_score = 0.0
        if bm25_scores:
            max_bm25_score = bm25_scores[0][1] # Sorted desc
            
        for vid, score in bm25_scores:
            if max_bm25_score > 0:
                norm_score = score / max_bm25_score
            else:
                norm_score = 0
            
            if vid not in combined_scores:
                 combined_scores[vid] = {"v": 0.0, "bm25": 0.0}
                 # We need to fetch content if this ID wasn't in Vector set
                 # In Phase 1, to avoid extra DB calls, let's only re-rank overlapping candidates?
                 # No, that defeats the purpose (finding keyword matches that vector missed).
                 # We must fetch. 
                 try:
                     got = self.collection.get(ids=[vid])
                     if got["documents"]:
                         doc_map[vid] = {"text": got["documents"][0], "metadata": got["metadatas"][0]}
                 except Exception:
                     pass
            
            combined_scores[vid]["bm25"] = norm_score

        # 3. Fuse Scores
        final_ranked = []
        for vid, scores in combined_scores.items():
            # Weighted Sum
            # final = alpha * vector + (1-alpha) * bm25
            final_score = (alpha * scores["v"]) + ((1 - alpha) * scores["bm25"])
            if vid in doc_map:
                final_ranked.append({
                    "id": vid,
                    "score": final_score,
                    "text": doc_map[vid]["text"],
                    "metadata": doc_map[vid]["metadata"]
                })
        
        # Sort desc
        final_ranked.sort(key=lambda x: x["score"], reverse=True)
        
        # Convert to SearchResult
        results = []
        for item in final_ranked[:top_k]:
             results.append(SearchResult(
                 text=str(item["text"]),
                 score=item["score"],
                 metadata=dict(item["metadata"] or {})
             ))
             
        return results

    def delete(self, ids: List[str]) -> None:
        if not ids:
            return
        self.collection.delete(ids=ids)
        # TODO: removing from BM25 is not supported in simple version yet
        # But it won't crash, just stale index.

    def persist(self) -> None:
        return

    def health_check(self) -> bool:
        try:
            _ = self.collection.count()
            return True
        except Exception:
            return False

    def delete_by_url(self, url: str) -> None:
        self.collection.delete(where={"url": url})
