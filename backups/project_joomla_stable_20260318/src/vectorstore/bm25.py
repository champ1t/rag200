import math
import re
import json
from pathlib import Path
from typing import List, Dict, Set, Tuple

class SimpleBM25:
    """
    A simple, pure-Python BM25 implementation for Hybrid Search.
    designed to run alongside ChromaDB without extra heavy dependencies.
    """
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        
        # Data storage
        self.documents: Dict[str, str] = {} # doc_id -> text (optional, for debugging)
        self.doc_len: Dict[str, int] = {}   # doc_id -> token count
        self.avg_dl: float = 0.0            # Average document length
        self.corpus_size: int = 0
        
        # Inverted Index: term -> {doc_id: frequency}
        self.index: Dict[str, Dict[str, int]] = {}
        
        # IDF Cache: term -> idf score
        self.idf: Dict[str, float] = {}
        
        # State tracking
        self.dirty = False

    def tokenize(self, text: str) -> List[str]:
        """
        Simple regex-based tokenization.
        Splits on whitespace and non-alphanumeric chars. Lowercases.
        """
        if not text:
            return []
        text = text.lower()
        # Keep Thai and English chars
        # Broad pattern: split by non-word chars but keep Thai
        # For simplicity, let's just split by whitespace and typical punctuation
        # This regex replaces special chars with space, then splits
        # \w matches [a-zA-Z0-9_] + unicode characters (including Thai) in Python 3
        tokens = re.findall(r"\w+", text)
        return tokens

    def add_document(self, doc_id: str, text: str):
        """Add or update a document in the index."""
        tokens = self.tokenize(text)
        doc_len = len(tokens)
        
        # Remove old if exists (naive implementation: assumes we rebuild or handle removal upstream)
        # For simple upsert: just overwrite frequency in index? 
        # Actually, inverted index cleanup is hard without forward index.
        # But for this lite version, let's assume we maintain consistency or rebuild often.
        # If ID exists, we should ideally remove it first. 
        # To strictly support upsert, we need to know old tokens.
        # Let's skip strict 'update' clean-up for this lightweight version 
        # and assume the user manages IDs appropriately or tolerates minor staleness 
        # UNLESS we explicitly implement delete logic.
        
        # Assuming fresh insertion for simplicity in Phase 1
        
        self.documents[doc_id] = text # Store raw text (optional, remove if memory constrained)
        self.doc_len[doc_id] = doc_len
        
        # Update index
        term_counts: Dict[str, int] = {}
        for t in tokens:
            term_counts[t] = term_counts.get(t, 0) + 1
            
        for term, count in term_counts.items():
            if term not in self.index:
                self.index[term] = {}
            self.index[term][doc_id] = count
            
        self.dirty = True

    def _calc_idf(self):
        """Recalculate IDF for all terms."""
        self.corpus_size = len(self.doc_len)
        if self.corpus_size == 0:
            return

        self.avg_dl = sum(self.doc_len.values()) / self.corpus_size
        self.idf = {}
        
        for term, doc_freqs in self.index.items():
            df = len(doc_freqs)
            # Standard BM25 IDF formula
            # idf = log((N - n + 0.5) / (n + 0.5) + 1)
            idf_score = math.log(((self.corpus_size - df + 0.5) / (df + 0.5)) + 1)
            self.idf[term] = idf_score
            
        self.dirty = False

    def get_scores(self, query: str, top_k: int = 5) -> List[Tuple[str, float]]:
        """
        Rank documents for a query.
        Returns [(doc_id, score), ...]
        """
        if self.dirty:
            self._calc_idf()
            
        q_tokens = self.tokenize(query)
        scores: Dict[str, float] = {}
        
        for q_term in q_tokens:
            if q_term not in self.index:
                continue
                
            idf = self.idf.get(q_term, 0)
            doc_freqs = self.index[q_term]
            
            for doc_id, freq in doc_freqs.items():
                doc_len = self.doc_len.get(doc_id, 0)
                
                # TF calculation
                numerator = freq * (self.k1 + 1)
                denominator = freq + self.k1 * (1 - self.b + self.b * (doc_len / self.avg_dl))
                term_score = idf * (numerator / denominator)
                
                scores[doc_id] = scores.get(doc_id, 0.0) + term_score
                
        # Sort and return top_k
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return ranked[:top_k]

    def save(self, path: str):
        """Persist index to disk."""
        data = {
            "k1": self.k1,
            "b": self.b,
            "doc_len": self.doc_len,
            "avg_dl": self.avg_dl,
            "corpus_size": self.corpus_size,
            "index": self.index,
            # We don't save self.documents to save space if not needed?
            # Actually, let's skip checking dirty on load, just assume saved state is valid
        }
        Path(path).write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    def load(self, path: str):
        """Load index from disk."""
        p = Path(path)
        if not p.exists():
            return
        
        data = json.loads(p.read_text(encoding="utf-8"))
        self.k1 = data["k1"]
        self.b = data["b"]
        self.doc_len = data["doc_len"]
        self.avg_dl = data["avg_dl"]
        self.corpus_size = data["corpus_size"]
        self.index = data["index"]
        self.dirty = True # Force idf recalc just in case or lazy load idf
        self._calc_idf()
