"""
Phase 174: Synonym/Alias System
Maps colloquial usage to canonical system keywords.
"""
import re

# Deterministic Alias Map (Phase 230 Enhancement)
# Maps set of keywords to a Canonical Title for high-precision jumping
ALIAS_MAP = {
    frozenset(["bridge", "port"]): "การทำ Bridge ระหว่างพอร์ตใน Cisco Router",
    frozenset(["bridge", "พอร์ต"]): "การทำ Bridge ระหว่างพอร์ตใน Cisco Router",
    frozenset(["bridgedomain"]): "การทำ Bridge ระหว่างพอร์ตใน Cisco Router",
}

SYNONYM_MAP = [
    # Pattern (Regex) -> Replacement (Canonical)
    
    # 0. Normalization (English-Thai Boundary) happens in normalize_query, 
    # but we can enforce specific spacing here if needed.
    
    # 1. Action Keywords (Additive - keep Thai words for BM25)
    (r"(?i)(วิธีแก้|แก้ยังไง|วิธีทำ|แก้ไขปัญหา|แก้ปัญหา|how\s*to)", "howto วิธีแก้"), 
    (r"(?i)(เข้าเว็บ|ลิงก์|ขอลิงก์|link|url|website)", "link ลิงก์"),
    (r"(?i)(ติดต่อ|เบอร์โทร|เบอร์)", "phone ติดต่อ"),
    
    # 2. Tech Terms & Product Names (Canonicalization)
    (r"(?i)(tr-?069|cwmp)", "TR069 CWMP"),
    (r"(?i)(edoc|e-doc|edocument|e\s+document)", "Edocument"),
    (r"(?i)(ipphone|ip\s*phone)", "ipphone"),
    (r"(?i)(fttx|fiber)", "FTTx"),
    (r"(?i)(bridge)", "bridge บริดจ์"), # Enhance 'bridge' recall
    (r"(?i)(port)", "port พอร์ต"),      # Enhance 'port' recall
]

def normalize_query(query: str) -> str:
    """
    Normalize query by splitting Thai/English boundaries and cleaning syntax.
    e.g. "ทำbridgeระหว่างport" -> "ทำ bridge ระหว่าง port"
    """
    if not query: return ""
    q = query.lower().strip()
    
    # 1. Insert space between Thai and English
    q = re.sub(r"([ก-๙])([a-z0-9])", r"\1 \2", q)
    q = re.sub(r"([a-z0-9])([ก-๙])", r"\1 \2", q)
    
    # 2. Remove special chars (keep spaces)
    q = re.sub(r"[-_/+]", " ", q)
    
    # 3. Collapse spaces
    q = re.sub(r"\s+", " ", q).strip()
    return q

def expand_synonyms(query: str) -> tuple[str, str | None]:
    """
    Expand synonyms in the query string.
    Returns: (expanded_query, applied_rule_name_or_None)
    """
    if not query: return "", None
    
    # Step 0: Normalize first
    normalized = normalize_query(query)
    
    # Step 1: Check Deterministic Aliases (Exact/Set Match)
    # We check if *all* keywords in an alias set are present in the normalized query
    terms = set(normalized.split())
    for keyword_set, target_title in ALIAS_MAP.items():
        # Check if all keywords in set are present in query terms
        # This allows "bridge ระหว่าง port" to match {bridge, port}
        if keyword_set.issubset(terms):
             return target_title, "ALIAS_REWRITE"

    expanded = normalized
    applied_rule = None

    # Rule QR-1: Rewrite once/Prevent recursion
    # If query already has "phone" or "ติดต่อ" (expanded form), stop to prevent "หาศูนย์อร์ศูนย์"
    if "phone" in expanded or "ติดต่อ" in expanded:
         return expanded, None
    
    for pattern, repl in SYNONYM_MAP:
        # Check if pattern matches
        if re.search(pattern, expanded):
            # Apply substitution
            new_val = re.sub(pattern, repl, expanded)
            if new_val != expanded:
                expanded = new_val
                if not applied_rule:
                    applied_rule = repl.split()[0]  # "howto" from "howto TR069"
    
    return expanded.strip(), applied_rule
