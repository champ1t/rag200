from typing import List, Dict, Any
import json
from src.rag.ollama_client import ollama_generate

class RAGEvaluator:
    def __init__(self, llm_cfg: Dict[str, Any]):
        self.base_url = llm_cfg.get("base_url")
        # Decouple: Use fast model for Verification
        self.model = llm_cfg.get("router_model", "llama3.2:3b")
        if self.model == "qwen3:8b": self.model = "llama3.2:3b"
        self.temperature = 0.0 # Strict verification
        
    def verify(self, query: str, context_docs: List[str], generated_answer: str) -> Dict[str, Any]:
        """
        Verify if the answer is supported by context.
        Returns: { "confidence": float, "verdict": "PASS | REJECT", "missing_evidence": "..." }
        """
        if len(context_docs) > 3:
            context_docs = context_docs[:3]
            
        context_text = "\n".join(context_docs)
        
        prompt = (
            f"You are an AI answer evaluator.\n\n"
            f"Given:\n"
            f"- The user question: {query}\n"
            f"- The retrieved context: {context_text}\n"
            f"- The generated answer: {generated_answer}\n\n"
            f"Your task is to assess whether the answer is fully supported by the context.\n\n"
            f"Evaluation criteria:\n"
            f"- 1.0: Answer is explicitly supported by the context\n"
            f"- 0.7–0.9: Answer is mostly supported, minor inference only\n"
            f"- 0.4–0.6: Partial support, some assumptions\n"
            f"- <0.4: Weak or no support\n\n"
            f"If confidence < 0.6, the answer must be rejected.\n\n"
            f"Output format (JSON only):\n"
            f"{{ \"confidence\": 0.00-1.00, \"verdict\": \"PASS | REJECT\", \"missing_evidence\": \"...\" }}"
        )

        try:
            resp = ollama_generate(
                base_url=self.base_url,
                model=self.model,
                prompt=prompt,
                temperature=self.temperature,
                format="json",
                num_predict=256, # Phase 127: Fast Verify
                num_ctx=2048     # Phase 127: Short Context
            )
            return json.loads(resp)
        except Exception as e:
            print(f"[RAGEvaluator] Error: {e}")
            # Fail safe: Return TIMEOUT/ERROR verdict to allow ChatEngine to degrade gracefully
            return {
                "confidence": 0.5, 
                "verdict": "TIMEOUT", 
                "missing_evidence": f"Evaluator Error: {e}"
            }

    def check_coverage(self, results: List[Any], query: str = "", intent: str = "UNKNOWN") -> Dict[str, Any]:
        """
        Analyze retrieval result coverage.
        Returns dict with status: 'PASS' | 'LOW_CONFIDENCE' | 'MISS'
        """
        if not results:
            return {"status": "MISS", "reason": "No results found"}
            
        max_score = max((getattr(r, "score", 0) for r in results), default=0)
        
        # Phase R5: Dynamic Thresholds
        # CONCEPT/EXPLAIN -> Lower threshold (0.25) but stricter keyword matching
        # OTHERS -> Strict threshold (0.35)
        concept_intents = {"EXPLAIN", "CONCEPT", "SUMMARY", "WHAT_IS", "KNOWLEDGE"}
        is_concept = intent in concept_intents
        
        threshold = 0.20 # Phase 237: Unified lower threshold for coverage-first
        if is_concept:
            threshold = 0.15
        elif intent == "HOWTO_PROCEDURE":
            threshold = 0.15
        
        # 1. Absolute Low Score -> MISS
        if max_score < threshold:
            return {"status": "MISS", "reason": f"Max score {max_score:.2f} too low (Threshold: {threshold})", "max_score": max_score}
            
        # 1.1 Keyword Constraint for Low-Score Concepts
        # If we are in the "risk zone" (0.25 - 0.35), ensure at least ONE significant query keyword exists in the text.
        if is_concept and max_score < 0.35 and query:
             top_result = max(results, key=lambda r: getattr(r, "score", 0))
             # Handle various object types (LangChain vs custom)
             text = getattr(top_result, "page_content", None) or getattr(top_result, "text", "")
             text = text.lower()
             
             # Extract tokens > 2 chars
             q_tokens = [t.lower() for t in query.split() if len(t) > 2]
             
             # Check for overlap
             has_kw = any(t in text for t in q_tokens)
             if not has_kw and q_tokens:
                  return {"status": "MISS", "reason": "Concept score low and no keyword match"}

        # 2. Single Source Risk
        # If we have multiple results but they all come from the same document ID/URL
        sources = set()
        for r in results:
            m = getattr(r, "metadata", {})
            src = m.get("source") or m.get("url") or "unknown"
            sources.add(src)
            
        if len(sources) == 1 and max_score < 0.75:
            return {"status": "LOW_CONFIDENCE", "reason": "Single source with medium score"}
            
        return {"status": "PASS", "max_score": max_score, "sources": len(sources)}
