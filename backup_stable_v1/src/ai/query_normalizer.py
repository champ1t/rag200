
from typing import Dict, Any
import time
import json
from src.rag.ollama_client import ollama_generate

PROMPT_QUERY_NORMALIZER = """You are a Query Paraphraser for an enterprise directory system.

GOAL: Rephrase the user's query into a canonical form that the system can understand.

STRICT RULES (CRITICAL):
1. Preserve abbreviations EXACTLY: OMC, RNOC, CSOC, FTTx, NOC, HelpDesk, SMC
2. Do NOT add spaces inside acronyms (OMC, not O M C or OM C)
3. Do NOT invent entities, phone numbers, or names
4. Only fix typos and rephrase for clarity
5. Keep the core meaning unchanged
6. Output ONLY the canonical query (no explanations)

ABBREVIATION PROTECTION (HIGHEST PRIORITY):
- OMC → OMC (never "O M C" or "OM C")
- RNOC → RNOC (never "R N O C")
- CSOC → CSOC (never "C S O C")
- FTTx → FTTx (never "FTT x" or "FT Tx")
- NOC → NOC (never "N O C")

COMMON FIXES:
- "เบอ" → "เบอร์"
- "help desk" → "HelpDesk"
- "fttx" → "FTTx"
- "omc" → "OMC"
- "ติดต่อ" → "เบอร์ติดต่อ" (if asking for phone)

EXAMPLES:
Input: "เบอ OMC หาดใหญ่"
Output: "เบอร์ OMC หาดใหญ่"

Input: "ติดต่อ help desk"
Output: "เบอร์ติดต่อ HelpDesk"

Input: "สมาชิก fttx"
Output: "สมาชิก FTTx"

Input: "OMC"
Output: "OMC"

USER_QUERY: "{query}"

OUTPUT (canonical query only, no JSON, no explanation):
"""

class QueryNormalizer:
    """
    LLM-based Query Normalizer (Phase 2.1)
    
    Purpose: Paraphrase user queries into canonical forms while preserving
    abbreviations and entities. Acts as a HELPER to deterministic logic.
    """
    
    def __init__(self, llm_cfg: Dict[str, Any]):
        self.llm_cfg = llm_cfg
        self.model = llm_cfg.get("fast_model", "llama3.2:3b")
        self.base_url = llm_cfg.get("base_url", "http://localhost:11434")
        
        # Known abbreviations to protect
        self.protected_abbrevs = {
            "OMC", "RNOC", "CSOC", "NOC", "FTTx", "HelpDesk", "SMC",
            "BRAS", "ATM", "IIG", "SBC", "MSAN", "DSLAM"
        }
    
    def normalize(self, query: str, trigger_reason: str = "deterministic_miss") -> Dict[str, Any]:
        """
        Normalize a query using LLM paraphrasing.
        
        Args:
            query: Original user query
            trigger_reason: Why normalization was triggered
            
        Returns:
            {
                "normalized_query": str,
                "changed": bool,
                "confidence": float,
                "latency_ms": float,
                "trigger": str
            }
        """
        if len(query.strip()) < 2:
            return {
                "normalized_query": query,
                "changed": False,
                "confidence": 1.0,
                "latency_ms": 0,
                "trigger": trigger_reason
            }
        
        # Quick check: if query is already clean, skip LLM
        if self._is_already_canonical(query):
            return {
                "normalized_query": query,
                "changed": False,
                "confidence": 1.0,
                "latency_ms": 0,
                "trigger": "skip_already_canonical"
            }
        
        prompt = PROMPT_QUERY_NORMALIZER.format(query=query)
        
        try:
            t0 = time.time()
            res = ollama_generate(
                base_url=self.base_url,
                model=self.model,
                prompt=prompt,
                temperature=0.0,
                num_predict=128,
                num_ctx=1024
            )
            latency = (time.time() - t0) * 1000
            
            normalized = res.strip()
            
            # Strip quotes if LLM added them
            if normalized.startswith('"') and normalized.endswith('"'):
                normalized = normalized[1:-1]
            if normalized.startswith("'") and normalized.endswith("'"):
                normalized = normalized[1:-1]
            
            # Safety: Validate abbreviations are preserved
            if not self._validate_abbreviations(query, normalized):
                print(f"[QueryNormalizer] ABORT: Abbreviation corruption detected")
                return {
                    "normalized_query": query,
                    "changed": False,
                    "confidence": 0.0,
                    "latency_ms": latency,
                    "trigger": "validation_failed"
                }
            
            changed = (normalized.lower() != query.lower())
            
            if changed:
                print(f"[QueryNormalizer] '{query}' → '{normalized}' ({latency:.1f}ms)")
            
            return {
                "normalized_query": normalized,
                "changed": changed,
                "confidence": 0.8 if changed else 1.0,
                "latency_ms": latency,
                "trigger": trigger_reason
            }
            
        except Exception as e:
            print(f"[QueryNormalizer] Error: {e}")
            return {
                "normalized_query": query,
                "changed": False,
                "confidence": 0.0,
                "latency_ms": 0,
                "trigger": "error"
            }
    
    def _is_already_canonical(self, query: str) -> bool:
        """Check if query is already in canonical form."""
        # Simple heuristic: if it contains proper abbreviations and no obvious typos
        q_upper = query.upper()
        
        # If it contains protected abbreviations in correct form, likely canonical
        for abbrev in self.protected_abbrevs:
            if abbrev.upper() in q_upper:
                # Check for spaces inside (corruption)
                spaced = " ".join(list(abbrev))
                if spaced in query:
                    return False  # Corrupted, needs normalization
        
        # If query is very short and clean, skip
        if len(query) < 10 and query.replace(" ", "").isalnum():
            return True
        
        return False
    
    def _validate_abbreviations(self, original: str, normalized: str) -> bool:
        """
        Validate that abbreviations are preserved correctly.
        
        Returns False if any protected abbreviation was corrupted.
        """
        orig_upper = original.upper()
        norm_upper = normalized.upper()
        
        for abbrev in self.protected_abbrevs:
            if abbrev.upper() in orig_upper:
                # Check if it's still intact in normalized
                if abbrev.upper() not in norm_upper:
                    return False
                
                # Check for space corruption (e.g., "OMC" → "O M C")
                spaced = " ".join(list(abbrev))
                if spaced in normalized:
                    return False
        
        return True
