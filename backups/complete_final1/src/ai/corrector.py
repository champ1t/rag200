
from typing import Dict, Any
from src.rag.ollama_client import ollama_generate

class QueryCorrector:
    """
    Uses LLM to correct spelling errors in user queries (Thai/English).
    Goal: Fix 'dbor' -> 'ber', 'hepl' -> 'help' to enable Regex Routing.
    """
    def __init__(self, llm_cfg: Dict[str, Any]):
        self.llm_cfg = llm_cfg

    
    def correct(self, query: str) -> str:
        # Optimization: Don't correct very short or very long queries
        if len(query) < 3 or len(query) > 100:
            return query
            
        # 1. Safety Masking: Protect Provinces and Technical Terms
        # Optimization: Protect technical keywords that shouldn't be touched
        TECH_KEYWORDS = ["ssh", "bgp", "sbc", "ip", "dns", "smtp", "olt", "onu", "ncs", "ospf", "isis"]
        
        from src.utils.section_filter import SCAN_KEYS
        
        protected_map = {}
        masked_query = query
        
        # Sort keys by length (desc) to handle overlap
        # Concatenate SCAN_KEYS and TECH_KEYWORDS for protection
        sorted_keys = sorted(list(SCAN_KEYS) + TECH_KEYWORDS, key=len, reverse=True)
        
        # Create masks
        import re
        idx = 0
        for key in sorted_keys:
             # Match whole words only for short technical terms
             pattern = re.compile(rf"\b{re.escape(key)}\b", re.IGNORECASE)
             if pattern.search(masked_query):
                  def repl(m):
                      nonlocal idx
                      token = f"__PROT_{idx}__"
                      protected_map[token] = m.group(0)
                      idx += 1
                      return token
                  masked_query = pattern.sub(repl, masked_query)

        prompt = (
            "Instruction: Correct any spelling mistakes or typos in the following text (Thai or English). "
            "Output ONLY the corrected text. If the text is already correct, output it exactly as is. "
            "Do not explain.\n\n"
            "CRITICAL RULES:\n"
            "- Do NOT correct Proper Nouns.\n"
            "- Do NOT change tokens like '__LOC_0__', '__LOC_1__'. Keep them EXACTLY as is.\n\n"
            f"Original: {masked_query}\n"
            "Corrected:"
        )

        try:
            res = ollama_generate(
                base_url=self.llm_cfg.get("base_url", "http://localhost:11434"),
                model=self.llm_cfg.get("model", "llama3.2:3b"),
                prompt=prompt,
                temperature=0.0
            )
            corrected = res.strip()
            
            # Safety cleanup
            if len(corrected) > len(masked_query) * 2:
                return query
                
            # 2. Restore Masks
            for token, original_text in protected_map.items():
                corrected = corrected.replace(token, original_text)
                
            return corrected
        except Exception as e:
            print(f"[corrector] Error: {e}")
            return query
