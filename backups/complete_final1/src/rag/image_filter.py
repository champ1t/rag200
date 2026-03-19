"""
Image Filter Module
Rule-based image filtering and relevance scoring for RAG system.
Excludes irrelevant images (counters, icons, buttons) and ranks by relevance.
"""
from typing import List, Dict, Any
import re


# Patterns to exclude (irrelevant images)
EXCLUDE_PATTERNS = [
    "counter", "visitor", "stats", "icon", "button", 
    "print", "email", "pdf", "template", "mod_vvisit",
    "digit", "arrow", "logo", "banner", "header", "footer"
]

# Keywords that boost relevance
RELEVANT_KEYWORDS = {
    "table": ["table", "ตาราง", "tbl"],
    "diagram": ["diagram", "แผนภูมิ", "แผนผัง", "flow", "chart"],
    "config": ["config", "configuration", "ตั้งค่า", "setting"],
    "network": ["network", "เครือข่าย", "topology", "wan", "lan"],
    "screenshot": ["screen", "capture", "หน้าจอ"],
}


def is_relevant_image(img: Dict[str, str]) -> bool:
    """
    Check if image is relevant (not a counter/icon/button).
    
    Args:
        img: Image dict with 'url', 'alt', 'caption'
        
    Returns:
        True if image is relevant, False if should be excluded
    """
    url = img.get("url", "").lower()
    alt = img.get("alt", "").lower()
    caption = img.get("caption", "").lower()
    
    # Combine all text for pattern matching
    combined = f"{url} {alt} {caption}"
    
    # Exclude if matches any exclude pattern
    for pattern in EXCLUDE_PATTERNS:
        if pattern in combined:
            return False
    
    return True


def score_image_relevance(img: Dict[str, str], query: str) -> float:
    """
    Score image relevance based on query keywords.
    
    Args:
        img: Image dict with 'url', 'alt', 'caption'
        query: User query (Thai/English)
        
    Returns:
        Relevance score 0.0-1.0
    """
    url = img.get("url", "").lower()
    alt = img.get("alt", "").lower()
    caption = img.get("caption", "").lower()
    query_lower = query.lower()
    
    # Extract filename from URL
    filename = url.split("/")[-1] if "/" in url else url
    
    score = 0.0
    
    # Base score for having alt text or caption
    if alt or caption:
        score += 0.1
    
    # Check for relevant keyword categories
    for category, keywords in RELEVANT_KEYWORDS.items():
        for keyword in keywords:
            # Boost if keyword in query AND in image metadata
            if keyword in query_lower:
                if keyword in filename or keyword in alt or keyword in caption:
                    score += 0.3
                    break
    
    # Direct query word matches in filename/alt/caption
    query_words = re.findall(r'\w+', query_lower)
    for word in query_words:
        if len(word) < 3:  # Skip short words
            continue
        if word in filename:
            score += 0.2
        if word in alt:
            score += 0.15
        if word in caption:
            score += 0.15
    
    # Cap at 1.0
    return min(score, 1.0)


def filter_and_rank_images(
    images: List[Dict[str, str]], 
    query: str, 
    max_images: int = 3
) -> List[Dict[str, str]]:
    """
    Filter irrelevant images and rank by relevance.
    
    Args:
        images: List of image dicts
        query: User query
        max_images: Maximum images to return
        
    Returns:
        Filtered and ranked list of images (top N)
    """
    if not images:
        return []
    
    # Filter out irrelevant images
    relevant = [img for img in images if is_relevant_image(img)]
    
    if not relevant:
        return []
    
    # Score and sort by relevance
    scored = [(img, score_image_relevance(img, query)) for img in relevant]
    scored.sort(key=lambda x: x[1], reverse=True)
    
    # Return top N with score > 0
    result = [img for img, score in scored[:max_images] if score > 0]
    
    return result


def detect_image_intent(query: str) -> bool:
    """
    Detect if user explicitly requests images.
    
    Args:
        query: User query (Thai/English)
        
    Returns:
        True if image intent detected
    """
    query_lower = query.lower()
    
    image_keywords = [
        "รูป", "ภาพ", "ตาราง", "แผนภูมิ", "แผนผัง",
        "diagram", "chart", "graph", "table", "image", 
        "picture", "screenshot", "capture"
    ]
    
    return any(kw in query_lower for kw in image_keywords)
