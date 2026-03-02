
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


# ============================================================================
# STEP 1: Rule-Based Article Content Classifier (Non-Invasive)
# ============================================================================

def classify_article_content(
    article_title: str,
    article_type: str = None,
    article_content: str = None
) -> str:
    """
    Simple rule-based classifier for Step 1 roadmap.
    Classifies article into categories WITHOUT using LLM.
    
    Categories:
    - command_reference: Technical commands, CLI syntax
    - narrative: Conceptual explanations, overviews
    - index: Directory pages, command collections
    - table_heavy: Primarily tabular data
    - image_heavy: Primarily diagrams/images
    
    Args:
        article_title: Title of the article
        article_type: Existing article type (COMMAND_REFERENCE, OVERVIEW, etc.)
        article_content: Optional article text content
        
    Returns:
        Content type string
    """
    
    # Rule 1: Use existing article_type if available (most reliable)
    if article_type:
        if article_type == "COMMAND_REFERENCE":
            return "command_reference"
        elif article_type == "OVERVIEW":
            return "index"  # OVERVIEW typically means collection/directory
        elif article_type == "MIGRATION_CONVERSION":
            return "command_reference"  # Migration guides often contain commands
    
    # Rule 2: Title-based classification
    title_lower = article_title.lower()
    
    # Command indicators
    command_keywords = ["command", "คำสั่ง", "cli", "config", "telnet", "ssh", "show", "set"]
    if any(kw in title_lower for kw in command_keywords):
        # Check if it's a command collection/index (but NOT single command queries)
        # "ZTE-SW Command" → index, but "ONU Command" → command_reference
        index_indicators = ["index", "รวม", "collection", "list", "directory", "zte-sw"]
        # Only treat as index if it has index indicator AND compound structure (e.g., hyphenated)
        has_index_indicator = any(ind in title_lower for ind in index_indicators)
        if has_index_indicator:
            return "index"
        return "command_reference"
    
    # Index/Overview indicators
    index_keywords = ["overview", "introduction", "index", "รวม", "ทำความรู้จัก", "directory"]
    if any(kw in title_lower for kw in index_keywords):
        return "index"
    
    # Narrative indicators
    narrative_keywords = ["concept", "theory", "principle", "คืออะไร", "หลักการ", "ทฤษฎี", "explanation"]
    if any(kw in title_lower for kw in narrative_keywords):
        return "narrative"
    
    # Rule 3: Content-based classification (if content available)
    if article_content:
        content_lower = article_content.lower()
        
        # Table-heavy detection
        table_count = content_lower.count("<table") + content_lower.count("| ---")
        if table_count >= 3:
            return "table_heavy"
        
        # Image-heavy detection
        image_count = content_lower.count("<img") + content_lower.count("![")
        if image_count >= 5:
            return "image_heavy"
        
        # Command syntax detection in content
        command_indicators_content = ["syntax:", "usage:", "example:", "```", "$ ", "# "]
        command_count = sum(1 for ind in command_indicators_content if ind in content_lower)
        if command_count >= 2:
            return "command_reference"
    
    # Default: narrative (safest assumption for unknown content)
    return "narrative"

