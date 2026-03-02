
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
        profile: str = "STRICT",
        knowledge_type: str = None,
        **kwargs
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
        source_urls_list = []
        
        for i, doc in enumerate(valid_docs):
            text = getattr(doc, "text", str(doc))
            # Truncate overly long chunks
            if len(text) > MAX_CHARS_PER_CHUNK:
                text = text[:MAX_CHARS_PER_CHUNK] + "...(truncated)"
                
            meta = getattr(doc, "metadata", {})
            title = meta.get("title", f"Doc {i+1}")
            url = meta.get("url") or meta.get("source")
            if url: source_urls_list.append(url)
            
            context_str += f"\n[Source: {title}]\n{text}\n"

        # 2. Token Budgeting (Dynamic Logic)
        num_predict = 512 # Default
        if intent in ["HOWTO_PROCEDURE", "CONTACT_LOOKUP"]:
            num_predict = 256 # Short, snappy for facts
        elif intent in ["SUMMARIZE", "EXPLAIN"]:
            num_predict = 640 # Longer for concepts
            
        # 3. Prompt Construction
        template = get_template(intent, knowledge_type=knowledge_type)
        
        # Prepare params
        fmt_params = {
            "context_str": context_str,
            "context": context_str, # REDUNDANT KEY for safety (some templates use {context})
            "query": query,
            "source_urls": "\n".join(source_urls_list),
            "doc_type": kwargs.get("doc_type", "NONE"), # Default to NONE
            "policy_flags": kwargs.get("policy_flags", []) # Default to empty list
        }
        # Merge kwargs (e.g. mode_hint)
        fmt_params.update(kwargs)
        
        # Phase 232: Override System Prompt for Whitelisted Concepts
        if intent == "CONCEPT_EXPLAIN_WHITELIST":
            # This template contains its own System Persona ("Internal Technical Explainer")
            full_prompt = template.format(**fmt_params)
        elif intent == "NT_STRICT":
            # This template contains its own System Persona ("NT Strict Answer Controller")
            full_prompt = template.format(**fmt_params)
        elif knowledge_type == "GENERAL_NETWORK_KNOWLEDGE":
            # Phase 233: Expert Explainer has its own System Persona ("Network SME")
            # Skip default SYSTEM_PROMPT_STRICT to avoid Persona Clash
            full_prompt = template.format(**fmt_params)
        else:
            # Default templates share generic strict system prompt
            # Safety: .format accepts extra keys? No, python format fails if extra keys unless matched.
            # But get_template returns string.
            # We should only pass keys that exist in template to avoid KeyError?
            # Or use safe format?
            # Standard python .format needs matching keys.
            # Most templates only use {context_str} and {query}.
            # New template uses {mode_hint} etc.
            # We should try/except formatting?
            try:
                full_prompt = f"{SYSTEM_PROMPT_STRICT}\n\n{template.format(**fmt_params)}"
            except KeyError:
                 # Fallback for templates not expecting new keys?
                 # Actually, usually passing EXTRA keys to format is error? No, passing MISSING keys is error.
                 # Passing extra keys to .format() is OK in Python?
                 # No, standard string.format raises KeyError for missing.
                 # Does it raise error for extra? No.
                 # So we are safe passing extra kwargs.
                 full_prompt = f"{SYSTEM_PROMPT_STRICT}\n\n{template.format(**fmt_params)}"
        
        # 4. LLM Call
        try:
            print(f"[Generator] Intent={intent}, Profile={profile}, KnowledgeType={knowledge_type}, predict={num_predict}")
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
