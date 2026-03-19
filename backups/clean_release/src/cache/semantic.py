import time
import uuid
import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from typing import Optional, Dict, Any, Tuple

class SemanticCache:
    def __init__(
        self, 
        persist_dir: str = "data/cache_store",
        collection_name: str = "rag_cache",
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
        threshold: float = 0.95, # Strict threshold for cache hit
        cache_ttl_seconds: int = 86400 * 7, # 7 Days
        doc_version: str = "1.0"
    ):
        self.persist_dir = persist_dir
        self.doc_version = doc_version
        self.cache_ttl_seconds = cache_ttl_seconds
        self.client = chromadb.PersistentClient(path=persist_dir)
        self.embed_fn = SentenceTransformerEmbeddingFunction(model_name=embedding_model)
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=self.embed_fn,
            metadata={"hnsw:space": "cosine"}
        )
        self.threshold = threshold

    def normalize_key(self, text: str) -> str:
        """
        Normalize query for cache key matching.
        Lower, strip, and remove polite particles (ครับ/ค่ะ) at end.
        """
        text = text.lower().strip()
        # Remove polite particles at end only
        for suffix in ["ครับ", "ค่ะ", "นะครับ", "นะค่ะ", "คับ", "kha", "krub"]:
            if text.endswith(suffix):
                text = text[:-len(suffix)].strip()
                break # Only remove one layer
        return text

    def check(self, query_text: str, intent: str, route: str, filter_meta: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """
        Check cache with pro-level hygiene.
        
        Rules:
        1. Length Check: Skip if len < 6 chars.
        2. Intent Guard: Skip if greeting/thanks.
        3. Strict Meta: Must match intent/route exactly.
        """
        q_norm = self.normalize_key(query_text)
        
        # Rule 1: Length Guard (Too short = ambiguous/noise)
        if len(q_norm) < 6:
            return None
            
        # Rule 2: Intent Guard
        if intent in ["GREETING", "THANKS", "ACK", "GENERAL_QA_SHORT"]:
            return None

        t0 = time.time()
        
        # Build strict where clause
        base_where = {}
        if filter_meta:
            for k, v in filter_meta.items():
                base_where[k] = v
        
        # Always enforce intent/route match (Pro-Level)
        base_where["intent"] = intent
        base_where["doc_version"] = self.doc_version
        
        # Fix: ChromaDB requires $and for multiple conditions
        if len(base_where) > 1:
            where_clause = {"$and": [{k: v} for k, v in base_where.items()]}
        else:
            where_clause = base_where
        
        try:
            results = self.collection.query(
                query_texts=[query_text],
                n_results=1,
                include=["documents", "metadatas", "distances"],
                where=where_clause
            )
        except Exception:
            return None
        
        if not results["ids"] or not results["ids"][0]:
            return None
            
        dist = results["distances"][0][0]
        similarity = 1.0 - dist
        
        if similarity >= self.threshold:
            data = results["metadatas"][0][0]
            
            # Additional Hygiene: Intent/Route Mismatch Check (Double verification)
            cached_intent = data.get("intent")
            if cached_intent and cached_intent != intent:
                return None
            
            # Hygiene Check: Expiry (TTL)
            cached_timestamp = data.get("timestamp")
            if cached_timestamp and (time.time() - cached_timestamp > self.cache_ttl_seconds):
                return None
            
            # Phrase 24: Credential Safety Guard
            sensitive_kws = ["pass", "pwd", "password", "รหัส", "user", "login"]
            if any(k in q_norm.lower() for k in sensitive_kws):
                 return None
            
            if "answer" in data:
                return {
                    "answer": data["answer"],
                    "score": similarity,
                    "cached_at": data.get("timestamp"),
                    "latency": (time.time() - t0) * 1000,
                    "meta": data
                }
                
        return None

    def store(self, query_text: str, answer_text: str, meta: Dict[str, Any] = None):
        """
        Store with extensive context metadata.
        """
        if meta is None:
            meta = {}
            
        # Add required cache fields
        meta["answer"] = answer_text
        meta["timestamp"] = time.time()
        meta["doc_version"] = self.doc_version
        
        # Ensure values are strings/ints/floats for Chroma
        # Flatten simple dicts if needed, or just store top-level keys
        # We assume meta contains simple types: 'route', 'model', 'top_k'
        
        doc_id = str(uuid.uuid4())
        
        self.collection.upsert(
            ids=[doc_id],
            documents=[query_text],
            metadatas=[meta]
        )
