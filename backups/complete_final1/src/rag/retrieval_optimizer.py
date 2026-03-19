from typing import List, Dict, Any
import json
from src.rag.ollama_client import ollama_generate

class RetrievalOptimizer:
    def __init__(self, llm_cfg: Dict[str, Any]):
        self.base_url = llm_cfg.get("base_url", "http://localhost:11434")
        # Decouple: Use fast model for Optimization
        self.model = llm_cfg.get("fast_model", llm_cfg.get("model", "qwen3:8b"))
        self.temperature = 0.0
        
    def optimize(self, query: str, results: List[Any]) -> List[Any]:
        """
        Determine optimal Top-K and return sliced results.
        """
        if not results:
            return []
            
        # Format candidates for LLM review
        candidates_str = "\n".join([
            f"[Chunk {i+1}] (Score: {r.score:.4f}): {r.text[:200]}..." 
            for i, r in enumerate(results)
        ])
        
        prompt = (
            f"You are an AI retrieval controller.\n\n"
            f"Given:\n"
            f"- User question: {query}\n"
            f"- A list of candidate chunks with similarity scores:\n{candidates_str}\n\n"
            f"Your task:\n"
            f"Determine how many chunks (top-k) are sufficient to answer the question accurately.\n\n"
            f"Guidelines:\n"
            f"- Use fewer chunks if one contains strong, explicit evidence.\n"
            f"- Increase k only if information is fragmented.\n"
            f"- Avoid unnecessary chunks that may introduce noise.\n\n"
            f"Output format (JSON only):\n"
            f"{{ \"recommended_top_k\": 1-5, \"justification\": \"...\" }}"
        )

        try:
            resp = ollama_generate(
                base_url=self.base_url,
                model=self.model,
                prompt=prompt,
                temperature=self.temperature,
                format="json",
                num_predict=256, # Phase 127: Fast Optimize
                num_ctx=2048     # Phase 127: Short Context
            )
            data = json.loads(resp)
            k = int(data.get("recommended_top_k", len(results)))
            # Ensure k is valid
            k = max(1, min(k, len(results)))
            return results[:k]
        except Exception as e:
            print(f"[RetrievalOptimizer] Error: {e}")
            return results # Fallback to all

    def re_rank(self, results: List[Any], query: str) -> List[Any]:
        """
        Deterministic Re-ranking based on Heuristics.
        1. Acronym Boost: If query acronym matches text substantially.
        2. Generic Penalty: Penalize chunks with generic titles unless they have strong content match.
        3. System Page Filter: Remove known system pages.
        """
        if not results: return []
        
        q_lower = query.lower().strip()
        q_tokens = set(q_lower.split())
        
        # Keywords that suggest "Generic" content
        GENERIC_TITLES = ["home", "หน้าหลัก", "main menu", "login", "เข้าสู่ระบบ", "search", "ค้นหา", "index", "สารบัญ"]
        
        # System Page Patterns (Strict Filter)
        SYSTEM_URL_PATTERNS = ["login", "register", "cart", "checkout", "profile", "reset", "remind"]
        
        ranked = []
        for r in results:
            # Unwrap SearchResult object
            # It usually has .score, .text, .metadata
            score = getattr(r, "score", 0.0)
            text = getattr(r, "text", "") or ""
            meta = getattr(r, "metadata", {}) or {}
            
            title = str(meta.get("title", "")).lower()
            url = str(meta.get("url", "") or meta.get("source", "")).lower()
            content_lower = text.lower()
            
            # 1. System Page & Junk File Filter (Hard Reject)
            # Filter binaries and non-text formats (URL or Title)
            JUNK_EXTENSIONS = [".mp4", ".avi", ".mov", ".mkv", ".mp3", ".wav", ".zip", ".rar", ".7z", ".exe", ".dmg", ".iso", ".apk", ".ipa"]
            # Check URL end
            if any(url.endswith(ext) for ext in JUNK_EXTENSIONS):
                print(f"[Optimizer] Filtered Junk File (Ext): {url}")
                continue
            
            # Check Title end (common for Google Drive previews e.g. "Video.mp4")
            if any(title.lower().endswith(ext) for ext in JUNK_EXTENSIONS):
                 print(f"[Optimizer] Filtered Junk File (Title): {title}")
                 continue

            if any(p in url for p in SYSTEM_URL_PATTERNS):
                print(f"[Optimizer] Filtered System Page: {url}")
                continue
                
            # 2. Generic Title Penalty
            # If title is generic AND score is borderline, penalize
            if any(g == title for g in GENERIC_TITLES) or len(title) < 3:
                score *= 0.5
            
            # 3. Acronym Boost / Exact Phrase Boost
            # Checks if the query appears as an exact substring in title
            if q_lower in title:
                score *= 1.2 # Strong Title Match
            elif q_lower in content_lower[:200]: # Match in intro
                score *= 1.1
                
            # 4. Token Coverage Check (Anti-Hallucination)
            # If less than 50% of query tokens appear in text, penalize heavily
            # (Only for longer queries > 2 words to avoid penalizing single keyword synonyms)
            if len(q_tokens) > 2:
                found_tokens = sum(1 for t in q_tokens if t in content_lower)
                coverage = found_tokens / len(q_tokens)
                if coverage < 0.5:
                     score *= 0.8
            
            # Update score (Mocking property setter by creating new object or modifying if mutable)
            # SearchResult might be immutable or standard class. 
            # Assuming we can modify. If not, we wrapper.
            try:
                r.score = score
            except:
                pass # If immutable, we just use the tuple for sorting
                
            ranked.append((score, r))
            
        # Sort desc
        ranked.sort(key=lambda x: x[0], reverse=True)
        return [x[1] for x in ranked]
