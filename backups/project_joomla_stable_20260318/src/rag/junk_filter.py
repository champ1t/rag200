
import re

def clean_junk_text(text: str) -> str:
    """
    Rule JR-1: Remove junk terms from RAG articles/summaries.
    Removes common web UI elements that leak into technical summaries.
    """
    if not text:
        return text
        
    junk_patterns = [
        r"(?:yesterday|today|tomorrow|online|hits?|views?|comments?)\b",
        r"(?i)(?:total|reset|search|login|logout|menu|nav|sidebar|footer|header)\b",
        r"(?i)(?:powered\s+by|all\s+rights?\s+reserved)\b",
        r"\d+\s+(?:views?|hits?|online)",
        r"(?i)(?:click\s+here|read\s+more|download\s+pdf|download\s+file)\b"
    ]
    
    # Phase 236: Prompt Artifacts (Rule SA-1)
    # Remove lines starting with INSTRUCTION: or If MENU_MODE:
    text = re.sub(r"(?im)^INSTRUCTION:.*?\n", "", text)
    text = re.sub(r"(?im)^If MENU_MODE:.*?\n", "", text)
    # Also handle blocks if they don't end in newline immediately
    text = re.sub(r"(?im)^INSTRUCTION:.*$", "", text)
    text = re.sub(r"(?im)^If MENU_MODE:.*$", "", text)
    
    cleaned = text
    for pattern in junk_patterns:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
        
    # Clean up multiple spaces/newlines
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    cleaned = re.sub(r' +', ' ', cleaned)
    
    return cleaned.strip()
