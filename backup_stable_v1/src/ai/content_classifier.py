
from typing import Dict, Any
import time
import json
from src.rag.ollama_client import ollama_generate

PROMPT_CONTENT_CLASSIFIER = """You are a content-type classifier for an internal knowledge assistant.

Input:
- TITLE: {title}
- URL: {url}
- CONTENT_PREVIEW: {content_preview}
- EXTRACT_META: {meta_hint}

Task:
Classify the content into ONE of:
1) TEXT_ARTICLE: Has sufficient readable text to summarize.
2) LINK_MENU: Mostly a list of links / portal page with little real content.
3) IMAGE_ONLY: Content is mostly images/scans; little extractable text.
4) TABLE_HEAVY: Mostly structured table rows; too many rows to paste cleanly.

Rules:
- If text_length > 500 and no excessive tables/images → TEXT_ARTICLE
- If content is mostly links (>5 links, little text) → LINK_MENU
- If detected_images > 3 and text_length < 300 → IMAGE_ONLY
- If detected_table_rows > 20 → TABLE_HEAVY
- Output must be exactly one label, nothing else.

Return one label only (TEXT_ARTICLE, LINK_MENU, IMAGE_ONLY, or TABLE_HEAVY):
"""

class ContentClassifier:
    """
    Classifies content type to determine if it should be summarized or just linked.
    
    Purpose: Prevent LLM from trying to summarize unsuitable content like
    link menus, image galleries, or large tables.
    """
    
    def __init__(self, llm_cfg: Dict[str, Any]):
        self.llm_cfg = llm_cfg
        self.model = llm_cfg.get("fast_model", "llama3.2:3b")
        self.base_url = llm_cfg.get("base_url", "http://localhost:11434")
    
    def classify(self, title: str, url: str, content: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Classify content type.
        
        Args:
            title: Document title
            url: Document URL
            content: Full content or preview (first 800-1500 chars recommended)
            metadata: Optional metadata (detected_table_rows, detected_images, text_length)
            
        Returns:
            {
                "content_type": str,  # TEXT_ARTICLE | LINK_MENU | IMAGE_ONLY | TABLE_HEAVY
                "should_summarize": bool,
                "confidence": float,
                "latency_ms": float
            }
        """
        # Extract metadata
        meta = metadata or {}
        content_preview = content[:1500] if len(content) > 1500 else content
        
        # Build meta hint
        meta_hint = {
            "text_length": meta.get("text_length", len(content)),
            "detected_table_rows": meta.get("detected_table_rows", 0),
            "detected_images": meta.get("detected_images", 0)
        }
        
        # Deterministic pre-checks (fast path)
        text_len = meta_hint["text_length"]
        table_rows = meta_hint["detected_table_rows"]
        images = meta_hint["detected_images"]
        
        # Fast path: obvious cases
        if table_rows > 50:
            return {
                "content_type": "TABLE_HEAVY",
                "should_summarize": False,
                "confidence": 1.0,
                "latency_ms": 0,
                "reason": "deterministic_table_heavy"
            }
        
        if images > 5 and text_len < 200:
            return {
                "content_type": "IMAGE_ONLY",
                "should_summarize": False,
                "confidence": 1.0,
                "latency_ms": 0,
                "reason": "deterministic_image_only"
            }
        
        # LLM classification for ambiguous cases
        prompt = PROMPT_CONTENT_CLASSIFIER.format(
            title=title,
            url=url,
            content_preview=content_preview,
            meta_hint=json.dumps(meta_hint, ensure_ascii=False)
        )
        
        try:
            t0 = time.time()
            res = ollama_generate(
                base_url=self.base_url,
                model=self.model,
                prompt=prompt,
                temperature=0.0,
                num_predict=32,
                num_ctx=2048
            )
            latency = (time.time() - t0) * 1000
            
            classification = res.strip().upper()
            
            # Validate classification
            valid_types = ["TEXT_ARTICLE", "LINK_MENU", "IMAGE_ONLY", "TABLE_HEAVY"]
            if classification not in valid_types:
                # Fallback: if we can't classify, assume TEXT_ARTICLE if text is long enough
                classification = "TEXT_ARTICLE" if text_len > 300 else "LINK_MENU"
                confidence = 0.5
            else:
                confidence = 0.9
            
            should_summarize = (classification == "TEXT_ARTICLE")
            
            print(f"[ContentClassifier] '{title[:50]}...' → {classification} (summarize={should_summarize}, {latency:.1f}ms)")
            
            return {
                "content_type": classification,
                "should_summarize": should_summarize,
                "confidence": confidence,
                "latency_ms": latency,
                "reason": "llm_classification"
            }
            
        except Exception as e:
            print(f"[ContentClassifier] Error: {e}")
            # Fallback: assume TEXT_ARTICLE if text is substantial
            return {
                "content_type": "TEXT_ARTICLE" if text_len > 300 else "LINK_MENU",
                "should_summarize": text_len > 300,
                "confidence": 0.5,
                "latency_ms": 0,
                "reason": "error_fallback"
            }
