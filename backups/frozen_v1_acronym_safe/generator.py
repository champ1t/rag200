
import time
from typing import List, Dict, Any, Optional
from src.rag.ollama_client import ollama_generate
from src.rag.prompts import get_template, SYSTEM_PROMPT_STRICT

class RAGGenerator:
    def __init__(self, llm_config: Dict[str, Any]):
        self.base_url = llm_config.get("base_url")
        self.model = llm_config.get("model")
        self.temperature = llm_config.get("temperature", 0.0)
        self.timeout = float(llm_config.get("timeout_sec", 120))
        
    def generate(
        self, 
        query: str, 
        context_docs: List[Any], 
        intent: str,
        profile: str = "STRICT"
    ) -> Dict[str, Any]:
        """
        Generate answer using strict templates and token budgeting.
        """
        t_start = time.time()
        
        # 1. Context Budgeting
        # Cap context to prevent "Context Stuffing"
        # Optimized: Reduced to 3 chunks to improve Latency (User Request: "Faster")
        MAX_CHUNKS = 3 
        MAX_CHARS_PER_CHUNK = 1200
        
        valid_docs = context_docs[:MAX_CHUNKS]
        context_str = ""
        for i, doc in enumerate(valid_docs):
            text = getattr(doc, "text", str(doc))
            # Truncate overly long chunks
            if len(text) > MAX_CHARS_PER_CHUNK:
                text = text[:MAX_CHARS_PER_CHUNK] + "...(truncated)"
                
            meta = getattr(doc, "metadata", {})
            title = meta.get("title", f"Doc {i+1}")
            context_str += f"\n[Source: {title}]\n{text}\n"

        # 2. Token Budgeting (Dynamic Logic)
        num_predict = 512 # Default
        if intent in ["HOWTO_PROCEDURE", "CONTACT_LOOKUP"]:
            num_predict = 256 # Short, snappy for facts
        elif intent in ["SUMMARIZE", "EXPLAIN"]:
            num_predict = 640 # Longer for concepts
            
        # 3. Prompt Construction
        template = get_template(intent)
        
        # Phase 232: Override System Prompt for Whitelisted Concepts
        if intent == "CONCEPT_EXPLAIN_WHITELIST":
            # This template contains its own System Persona ("Internal Technical Explainer")
            full_prompt = template.format(context_str=context_str, query=query)
        else:
            full_prompt = f"{SYSTEM_PROMPT_STRICT}\n\n{template.format(context_str=context_str, query=query)}"
        
        # 4. LLM Call
        try:
            print(f"[Generator] Intent={intent}, Profile={profile}, predict={num_predict}")
            ans = ollama_generate(
                base_url=self.base_url,
                model=self.model,
                prompt=full_prompt,
                temperature=self.temperature,
                timeout=self.timeout,
                num_predict=num_predict,
                num_ctx=4096
            )
            
            latency = (time.time() - t_start) * 1000
            
            # 5. Post-Processing / Grounding Check (Basic)
            # Ensure "evidence" is mentioned if required? 
            # (Left for Evaluator, but we can do string check)
            
            return {
                "answer": ans,
                "latency": latency,
                "token_cap": num_predict,
                "prompt_len": len(full_prompt)
            }
            
        except Exception as e:
            print(f"[Generator] Error: {e}")
            return {
                "answer": "เกิดข้อผิดพลาดในการสร้างคำตอบ (Generator Error)",
                "latency": (time.time() - t_start) * 1000,
                "error": str(e)
            }
