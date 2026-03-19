from typing import List, Dict, Any
import json
import time
from src.rag.ollama_client import ollama_generate

class RAGController:
    def __init__(self, llm_cfg: Dict[str, Any]):
        self.base_url = llm_cfg.get("base_url", "http://localhost:11434")
        # Decouple: Use fast model for Controller logic
        self.model = llm_cfg.get("fast_model", "llama3.2:3b")
        if self.model == "qwen3:8b": self.model = "llama3.2:3b" # Hard override if config is ambiguous
        self.temperature = 0.0 # Deterministic
        
    def decide(self, query: str, context_docs: List[str]) -> Dict[str, Any]:
        """
        Decide the answering strategy based on context.
        Returns: { "strategy": "...", "confidence": float, "reason": "..." }
        """
        # Phase 232: Concept Whitelist (Allow AI/ML definitions without docs)
        ALLOWED_CONCEPTS = {
            "rag", "llm", "vector database", "embedding", "genai", "generative ai", 
            "artificial intelligence", "ai", "machine learning", "ml", "chatgpt", 
            "bert", "transformer", "semantic search", "retrieval augmented generation"
        }
        
        q_norm = query.lower().strip()
        is_whitelisted = False
        # Exact match or "What is <term>?"
        if q_norm.replace("คืออะไร","").strip() in ALLOWED_CONCEPTS:
             is_whitelisted = True
        
        if not context_docs:
            if is_whitelisted:
                 return {
                    "strategy": "CONCEPT_EXPLAIN_WHITELIST",
                    "confidence": 1.0,
                    "reason": "Whitelisted concept allowed for external explanation."
                 }
            
            return {
                "strategy": "NO_ANSWER",
                "confidence": 1.0,
                "reason": "No context documents provided."
            }

        # Context Formatting
        ctx_str = "\n".join([f"[Doc {i+1}]: {doc}" for i, doc in enumerate(context_docs)])
        
        prompt = (
            f"You are an Enterprise RAG Controller.\n"
            f"Your task is to decide the Strategy and Style based on the query and context.\n\n"
            f"STRATEGIES:\n"
            f"1) DIRECT_LOOKUP: Answer from structured data (Phone/Email/Link)\n"
            f"2) RAG_ANSWER: Answer from context text\n"
            f"3) CLARIFY: Ambiguous query (Note: 'reason' MUST be in Thai Language)\n"
            f"4) NO_ANSWER: Insufficient context\n\n"
            f"STYLES (if RAG_ANSWER):\n"
            f"- DEFINITION: Short factual explanation\n"
            f"- PROCEDURE: Step-by-step instructions\n"
            f"- TECH_CARD: Structured specs (Overview/Params/Example)\n"
            f"- GENERAL: Normal conversation\n\n"
            f"User Query: {query}\n\n"
            f"Retrieved Context:\n{ctx_str}\n\n"
            f"Output JSON: {{ \"strategy\": \"...\", \"style\": \"...\", \"confidence\": 0.0, \"reason\": \"...\" }}\n"
            f"Important: If strategy is CLARIFY, the 'reason' field must be a SINGLE direct question in Thai asking for the specific missing information (e.g. 'ใช้งานผ่านระบบใด' or 'ขอทราบรหัส Error'). Do NOT explain that the query is ambiguous."
        )

        try:
            # Enforce JSON mode if supported by Ollama/Model, otherwise prompt eng
            # Qwen usually handles JSON instruction well.
            resp = ollama_generate(
                base_url=self.base_url,
                model=self.model,
                prompt=prompt,
                temperature=self.temperature,
                format="json", # Ollama supports format='json'
                num_predict=256, # Phase 127: Fast Decision
                num_ctx=2048     # Phase 127: Short Context
            )
            
            return json.loads(resp)
        except Exception as e:
            print(f"[RAGController] Error: {e}")
            return {
                "strategy": "RAG_ANSWER", # Fallback to standard RAG
                "confidence": 0.0,
                "reason": "Controller failed, defaulting to RAG."
            }
