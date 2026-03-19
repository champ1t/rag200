
import hashlib
import json
import time
from typing import List, Dict, Any, Optional
from src.cache.semantic import SemanticCache

class CacheManager:
    def __init__(self, semantic_cache: Optional[SemanticCache] = None):
        self.semantic_cache = semantic_cache
        # L1 Retrieval Cache (In-Memory for now, could be Redis/File)
        # Key: hash(norm_q + strategy + index_ver) -> Value: {hits: [], ts: float}
        self._l1_cache: Dict[str, Any] = {}
        self.l1_ttl = 3600 # 1 Hour for Retrieval Results
        self.doc_fingerprint_version = "v1" 
        
        # L3 Answer Cache (Exact Match In-Memory)
        # Key: hash(q + intent + fingerprint) -> Value: {answer: str, meta: dict, ts: float}
        self._l3_cache: Dict[str, Any] = {}
        self.l3_ttl = 3600 * 24 # 24 Hours

    def get_retrieval_cache(self, query: str, strategy_mode: str) -> Optional[List[Any]]:
        """
        L1: Check if we have exact hits for this query + strategy.
        """
        key = self._hash_key(query, strategy_mode)
        entry = self._l1_cache.get(key)
        
        if entry:
            if time.time() - entry["ts"] < self.l1_ttl:
                return entry["hits"]
            else:
                del self._l1_cache[key]
        return None

    def set_retrieval_cache(self, query: str, strategy_mode: str, hits: List[Any]):
        """
        L1: Store hits.
        """
        key = self._hash_key(query, strategy_mode)
        self._l1_cache[key] = {
            "hits": hits,
            "ts": time.time()
        }

    def compute_fingerprint(self, hits: List[Any]) -> str:
        """
        Create a hash signature of the evidence used.
        If docs change (content or ranking), this hash changes.
        """
        if not hits: return "empty"
        
        # Sort IDs to ensure stability if order flips slightly (optional, but safer to keep order if ranking matters)
        # Actually RAG depends on ranking, so order matters.
        sigs = []
        for h in hits:
            doc_id = getattr(h, "id", "") or "unknown"
            # If possible use content hash, but ID is faster proxy if immutable
            text_snippet = getattr(h, "text", "")[:50] 
            sigs.append(f"{doc_id}:{text_snippet}")
            
        return hashlib.sha256("|".join(sigs).encode()).hexdigest()

    def get_answer_cache(self, query: str, intent: str, fingerprint: str) -> Optional[Dict[str, Any]]:
        """
        L2: Check Semantic Answer Cache with strict Fingerprint.
        Also checks L3 (Memory) first.
        """
        # 1. Check L3 Memory Cache (Fastest)
        l3_key = self._hash_l3(query, intent, fingerprint)
        entry = self._l3_cache.get(l3_key)
        if entry:
             if time.time() - entry["ts"] < self.l3_ttl:
                 # Return in format expected by ChatEngine
                 return {
                     "answer": entry["answer"],
                     "score": 1.0,
                     "latency": 0,
                     "source": "l3_memory",
                     "meta": entry["meta"]
                 }
             else:
                 del self._l3_cache[l3_key]

        if not self.semantic_cache:
            return None
            
        filter_meta = {"fingerprint": fingerprint}
        
        # Use Semantic Cache check
        # It handles similarity search + metadata filtering
        hit = self.semantic_cache.check(
            query, 
            intent=intent, 
            route="rag", 
            filter_meta=filter_meta
        )
        
        # Backfill L3? Maybe.
        if hit:
             self._l3_cache[l3_key] = {
                 "answer": hit["answer"],
                 "meta": hit.get("meta", {}),
                 "ts": time.time()
             }
             
        return hit

    def set_answer_cache(self, query: str, answer: str, intent: str, fingerprint: str, meta: Dict[str, Any]):
        """
        L2: Store answer with fingerprint.
        """
        # Save to L3 Memory
        l3_key = self._hash_l3(query, intent, fingerprint)
        self._l3_cache[l3_key] = {
            "answer": answer,
            "meta": meta,
            "ts": time.time()
        }

        if not self.semantic_cache:
            return
            
        meta["fingerprint"] = fingerprint
        meta["intent"] = intent # Ensure intent is saved
        self.semantic_cache.store(query, answer, meta)

    def _hash_key(self, q: str, mode: str) -> str:
        raw = f"{q.lower().strip()}|{mode}"
        return hashlib.sha256(raw.encode()).hexdigest()
        
    def _hash_l3(self, q: str, intent: str, fp: str) -> str:
        raw = f"{q.lower().strip()}|{intent}|{fp}"
        return hashlib.sha256(raw.encode()).hexdigest()
