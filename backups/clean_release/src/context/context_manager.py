"""
Conversation Context Manager

Handles conversation scope memory for follow-up queries.
Enables queries like "ขอเบอร์" after "ศูนย์หาดใหญ่โทรอะไร".
"""

import re
import time
from typing import Dict, Any, Optional


# =============================================================================
# KNOWN_ACRONYMS: Confirmed org/device/unit names used in the contact database.
# These are used for detecting new entities even when typed in lowercase (e.g.,
# "jna", "umux"). Sourced from:
#   - lightweight_entity_detector.py (UMUX, SMC, OMC, RNOC, NOC, CSOC)
#   - query_normalizer.py (BRAS, ATM, IIG, SBC, MSAN, DSLAM)
#   - directory_handler.py fuzzy contact book (JNA, HELPDESK, FTTX, MSAN)
# =============================================================================
KNOWN_ACRONYMS: set = {
    # --- Organizations / Operational Centers ---
    "smc", "omc", "rnoc", "noc", "csoc", "iig", "helpdesk",
    # --- Device / System Acronyms ---
    "umux", "olt", "onu", "bras", "dslam", "msan", "fttx",
    "atm", "sbc", "cmts", "tacacs",
    # --- Team / Unit Names (contact record abbreviations) ---
    "jna", "sopa", "mdes", "tot", "senate",
}


def should_use_context(query: str, last_context: Optional[Dict[str, Any]]) -> bool:
    """
    Detect if query is a follow-up that should use conversation context.
    
    Args:
        query: The current query
        last_context: The previous conversation context
        
    Returns:
        True if query should inherit context from last_context
    """
    # No context available
    if not last_context or is_context_expired(last_context):
        return False
    
    q_lower = query.lower().strip()
    
    # Patterns that indicate follow-up queries
    followup_patterns = [
        # Contact-related follow-ups
        "ขอเบอร์", "ขอแค่เบอร์", "เบอร์พอ", "เบอร์ติดต่อ",
        "โทรอะไร", "โทรเบอร์", "เบอร์อะไร",
        
        # Continuation patterns (Thai)
        "อีกคน", "อีกที่", "อีกอันหนึ่ง", "อีกเรื่อง",
        "ละ", "ล่ะ", "อีกคน", "คนอื่น",
        "ของ", "แล้ว", "อันนี้", "อันนั้น",
        
        # Request for more info
        "คำสั่งอะไรบ้าง", "มีอะไรบ้าง", "มีอะไรอีก",
        "เพิ่มเติม", "อื่น", "รายละเอียด", "ขยาย",
        "ช่วยบอก", "บอกหน่อย", "อธิบาย",
        
        # Selection/clarification
        "อันแรก", "อันที่สอง", "ตัวแรก", "ตัวที่",
        "นี่", "นั่น", "โน่น"
    ]
    
    # Check for follow-up patterns
    has_followup_pattern = any(pattern in q_lower for pattern in followup_patterns)
    
    # Very short queries likely need context (e.g., "ขอเบอร์", "ละ", "อีกคน")
    is_short_query = len(query) < 10
    
    # =========================================================================
    # NEW TOPIC DETECTION (Clear context on topic change)
    # =========================================================================
    # Detect if query is about completely different topic
    # Examples that should CLEAR context:
    # - Previous: "ศูนย์หาดใหญ่" → Current: "huawei command" → CLEAR
    # - Previous: "contact" → Current: "ใครคือผจ" → CLEAR
    
    # Strong topic indicators (if present, likely NEW topic, not follow-up)
    new_topic_patterns = [
        # Technical queries
        "huawei", "cisco", "juniper", "command", "คำสั่ง", "config", "configuration",
        # Position queries (when previous was CONTACT)
        "ใครคือ", "ผจ", "ผส", "ผู้จัดการ", "ผู้อำนวยการ",
        #General queries
        "กระจกแปรง", "อะไร", "คือ", "หมายถึง", "อธิบาย"
    ]
    
    has_new_topic = any(pattern in q_lower for pattern in new_topic_patterns)
    
    # If new topic detected and no follow-up pattern, clear context
    if has_new_topic and not has_followup_pattern:
        print(f"[CONTEXT_NEW_TOPIC] Detected new topic in '{query}' - clearing context")
        return False
    
    if not (has_followup_pattern or is_short_query):
        return False
    
    # =========================================================================
    # INTENT COMPATIBILITY CHECK
    # =========================================================================
    # Prevent cross-domain context application
    # Example: Don't apply TECH_ARTICLE context to CONTACT queries
    
    last_intent = last_context.get("intent", "")
    
    # Contact-related patterns in query
    contact_patterns = ["เบอร์", "โทร", "ติดต่อ", "call", "phone"]
    is_contact_query = any(p in q_lower for p in contact_patterns)
    
    # Technical patterns in query
    tech_patterns = ["คำสั่ง", "config", "command", "วิธี", "ทำยังไง", "show"]
    is_tech_query = any(p in q_lower for p in tech_patterns)
    
    # Block incompatible combinations
    if last_intent == "TECH_ARTICLE_LOOKUP" and is_contact_query:
        print(f"[CONTEXT_COMPAT] Blocked: TECH context → CONTACT query")
        return False
    
    if last_intent == "CONTACT_LOOKUP" and is_tech_query:
        print(f"[CONTEXT_COMPAT] Blocked: CONTACT context → TECH query")
        return False
    
    return True


def is_context_expired(last_context: Optional[Dict[str, Any]]) -> bool:
    """Check if last_context has expired (5 min timeout)."""
    if not last_context:
        return True
    
    # Check timestamp if available
    timestamp = last_context.get("timestamp", 0)
    if timestamp > 0:
        age_seconds = time.time() - timestamp
        return age_seconds > 300  # 5 minutes
    
    # No timestamp = assume not expired (legacy context)
    return False


def get_context_entities(last_context: Optional[Dict[str, Any]]) -> Dict[str, str]:
    """
    Extract entities from last_context for query enrichment.
    Supports multiple entities from various context sources.
    """
    if not last_context:
        return {}
    
    entities = {}
    
    # Source 1: New schema - explicitly stored entities
    stored_entities = last_context.get("entities", {})
    if stored_entities:
        entities.update(stored_entities)
    
    # Source 2: Legacy schema - extract from ref_name
    ref_name = last_context.get("ref_name", "")
    if ref_name and ref_name not in entities:
        # Try to extract entities from ref_name
        # Example: "ศูนย์ OMC หาดใหญ่" → {"หาดใหญ่": "LOCATION", "OMC": "ORGANIZATION"}
        
        # Simple extraction heuristics
        parts = ref_name.split()
        for part in parts:
            if part and part not in entities:
                # Infer type based on common patterns
                part_lower = part.lower()
                if any(loc in part_lower for loc in ["หาดใหญ่", "ภูเก็ต", "พังงา", "นครศรี", "สงขลา", "ชุมพร"]):
                    entities[part] = "LOCATION"
                elif part.upper() in ["OMC", "RNOC", "CSOC", "NOC", "SMC"]:
                    entities[part] = "ORGANIZATION"
                elif part in ["ศูนย์", "ฝ่าย", "แผนก"]:
                    entities[part] = "ORG_TYPE"
                else:
                    entities[part] = "UNKNOWN"
    
    # Source 3: Result data (for contact hits)
    data = last_context.get("data", [])
    if isinstance(data, list) and data:
        first_result = data[0]
        if isinstance(first_result, dict):
            name = first_result.get("name", "")
            if name and name not in entities:
                entities[name] = "CONTACT"
    
    return entities


def enrich_query_with_context(query: str, last_context: Optional[Dict[str, Any]]) -> str:
    """
    Enrich query with entity from conversation context.
    Supports multi-entity contexts and smart entity selection.
    
    Args:
        query: Original query (e.g., "ขอเบอร์")
        last_context: Previous context with entities
        
    Returns:
        Enriched query (e.g., "ขอเบอร์ หาดใหญ่")
    """
    if not should_use_context(query, last_context):
        return query
    
    entities = get_context_entities(last_context)
    print(f"[DEBUG_ENTITIES] Extracted entities: {entities}")  # DEBUG
    
    if not entities:
        return query
    
    # =========================================================================
    # MULTI-ENTITY SUPPORT: Smart Entity Selection
    # =========================================================================
    # If multiple entities exist, pick the most relevant one for the query
    
    q_lower = query.lower()
    
    # =========================================================================
    # CRITICAL FIX: Match Query Keywords First
    # =========================================================================
    # If user mentions specific entity in query (e.g., "ของ RNOC ละ"),
    # select that entity instead of using type-based priority.
    # This fixes: "ของ RNOC ละ" + context(OMC, RNOC) → should pick RNOC
    
    matched_entity = None
    matched_type = None
    
    # Try to find entity that appears in query
    for entity_value, e_type in entities.items():
        entity_lower = entity_value.lower()
        
        # =====================================================================
        # WORD-LEVEL MATCHING: Check if any word from entity appears in query
        # =====================================================================
        # Example: entity="ศูนย์ RNOC หาดใหญ่", query="ของ RNOC ละ"
        # → Extract ["ศูนย์", "rnoc", "หาดใหญ่"]
        # → Check if "rnoc" appears in query → MATCH!
        
        entity_words = entity_lower.split()
        query_matched = False
        
        # Check each significant word in entity name
        for word in entity_words:
            # Skip common words
            if word in ["ศูนย์", "ฝ่าย", "แผนก", "งาน", "ทีม"]:
                continue
            
            # Check if word appears in query (with and without spaces)
            if word in q_lower or word in q_lower.replace(" ", ""):
                matched_entity = entity_value
                matched_type = e_type
                query_matched = True
                print(f"[CONTEXT_ENTITY_MATCH] Query keyword '{word}' (from '{entity_value}') matched in '{query}'")
                break
        
        if query_matched:
            break
    
    # If keyword match found, use it immediately
    if matched_entity:
        # =====================================================================
        # DUPLICATE CHECK: Don't add if key words already in query
        # =====================================================================
        # Check if the significant words from matched entity are already in query
        # Example: query="หาดใหญ่มีอะไร", matched="ศูนย์ OMC หาดใหญ่"
        # → "หาดใหญ่" already in query → don't add full entity
        
        matched_words = matched_entity.lower().split()
        # Filter common prefix words but also filter suffix noise like "-", "test"
        noise_words = {"ศูนย์", "ฝ่าย", "แผนก", "งาน", "ทีม", "-", "test"}
        significant_words = [w for w in matched_words if w not in noise_words]
        
        # -----------------------------------------------------------------------
        # DUPLICATE CHECK 1: All significant words already in query?
        # -----------------------------------------------------------------------
        if significant_words:
            all_words_present = all(
                w in q_lower or w in q_lower.replace(" ", "")
                for w in significant_words
            )
            if all_words_present:
                return query  # nothing new to add
        
        # -----------------------------------------------------------------------
        # DUPLICATE CHECK 2: Primary identifier already in query?
        # Handles cases like "ขอ JNA" + entity="JNA - test"
        # significant_words=['jna','test'] but 'test' is noise suffix.
        # We check if any ASCII uppercase acronym from entity exists in query.
        # -----------------------------------------------------------------------
        matched_words_orig = matched_entity.split()
        for word in matched_words_orig:
            # If word is ASCII uppercase acronym (like JNA, OMC) and is in query → already there
            if word.isascii() and word.upper() == word and len(word) >= 2 and word.isalpha():
                if word.lower() in q_lower:
                    return query  # primary org/device name already in query
        
        enriched = f"{query} {matched_entity}"
        print(f"[CONTEXT_ENRICHMENT] '{query}' → '{enriched}' (Keyword Match: {matched_type})")
        return enriched
    
    # =========================================================================
    # NEW ENTITY CONFLICT CHECK: "New Entity Wins" Rule
    # =========================================================================
    # If the new query contains a word that is NOT in context entities
    # but looks like a RIVAL entity (different name/org), skip enrichment.
    #
    # Examples that should NOT be enriched:
    #   Context={JNA: CONTACT}, Query="เบอร์ umux"  → return raw query
    #   Context={หาดใหญ่: LOC}, Query="ขอเบอร์ภูเก็ต" → return raw query
    #   Context={OMC: ORG},    Query="ขอเบอร์ RNOC"  → return raw query
    #
    # Examples that SHOULD still be enriched (no new entity):
    #   Context={JNA: CONTACT}, Query="แล้วเบอร์มือถือ" → enrich with JNA
    #   Context={หาดใหญ่: LOC}, Query="ขอเบอร์"         → enrich with หาดใหญ่

    # Collect all significant tokens from context entities for comparison
    # Use both lower and original case for matching
    context_entity_tokens = set()
    context_entity_tokens_orig = set()
    for entity_val in entities.keys():
        for token in entity_val.split():
            if token.lower() not in ["ศูนย์", "ฝ่าย", "แผนก", "งาน", "ทีม", "-", "test"]:
                context_entity_tokens.add(token.lower())
                context_entity_tokens_orig.add(token)  # preserve original case

    # Extract tokens from BOTH original query and lowercased version
    query_tokens_orig = set(query.split())   # original case (for uppercase detection)
    query_tokens_low  = set(q_lower.split()) # lowercase (for Thai location detection)

    # Find tokens in query that are NOT in context (potential new entities)
    novel_tokens_orig = {t for t in query_tokens_orig if t.lower() not in context_entity_tokens}
    novel_tokens_low  = query_tokens_low - context_entity_tokens

    # Filter out stopwords / common Thai words that aren't real entities
    stopwords = {
        "ขอ", "เบอร์", "โทร", "ติดต่อ", "หน่อย", "ด้วย", "นะ", "ครับ", "ค่ะ",
        "ได้", "ไหม", "มั้ย", "เลย", "แล้ว", "ของ", "phone",
    }
    novel_tokens_low -= stopwords
    novel_tokens_orig = {t for t in novel_tokens_orig if t.lower() not in stopwords}

    # -------------------------------------------------------------------------
    # CHECK 0: Regex scan of raw query for known acronyms (handles no-space)
    # -----------------------------------------------------------------
    # Problem: 'เบอร์jna'.split() = ['เบอร์jna'] — 'jna' is hidden inside.
    # Solution: extract ALL ASCII alphabetical substrings from the raw query
    # using regex, then check against KNOWN_ACRONYMS.
    # Examples:
    #   'เบอร์jna'  → ascii_segments = ['jna'] → in KNOWN_ACRONYMS → BLOCK
    #   'เบอร์umux' → ascii_segments = ['umux'] → in KNOWN_ACRONYMS → BLOCK
    #   'เบอร์ JNA' → ascii_segments = ['JNA'] → uppercase → caught by CHECK 1
    #   'ขอเบอร์'   → ascii_segments = []     → no entity found → proceed
    # -------------------------------------------------------------------------
    ascii_segments_in_query = re.findall(r'[A-Za-z][A-Za-z0-9\-]{1,}', query)
    new_entity_detected = False
    for seg in ascii_segments_in_query:
        seg_lower = seg.lower()
        # Skip if segment is already the context entity (not a NEW entity)
        if seg_lower in context_entity_tokens:
            continue
        # Skip common non-entity words that might appear in queries
        if seg_lower in {"phone", "the", "and", "for", "not", "url"}:
            continue
        # Matches a known acronym (works for both uppercase and lowercase)
        if seg_lower in KNOWN_ACRONYMS:
            new_entity_detected = True
            print(f"[CONTEXT_CONFLICT] Known acronym '{seg}' found (regex) in query "
                  f"→ blocking enrichment with {list(entities.keys())}")
            break
        # OR: is an all-uppercase ASCII word (e.g., RNOC, CSOC typed with spaces)
        if seg.isascii() and seg.upper() == seg and len(seg) >= 2:
            new_entity_detected = True
            print(f"[CONTEXT_CONFLICT] New uppercase entity '{seg}' (regex) in query "
                  f"→ blocking enrichment with {list(entities.keys())}")
            break

    if new_entity_detected:
        return query

    # -------------------------------------------------------------------------
    # DETECT (token-level): All-caps ASCII tokens or known acronyms (with spaces)
    # -------------------------------------------------------------------------
    new_entity_detected = False
    for token in novel_tokens_orig:
        token_lower = token.lower()

        # --- CHECK 1: All-uppercase ASCII word (JNA, RNOC, CSOC, UMUX, ...) ---
        # MUST be ASCII-only: Thai chars have no case, so 'ละ'.upper() == 'ละ'
        if (token.isascii() and token.upper() == token
                and len(token) >= 2 and token.replace("-", "").isalpha()):
            new_entity_detected = True
            print(f"[CONTEXT_CONFLICT] New uppercase entity '{token}' in query "
                  f"→ blocking enrichment with {list(entities.keys())}")
            break

        # --- CHECK 2: Known acronym typed in lowercase (jna, umux, omc, ...) ---
        # Catches the case where user types a known entity name in lowercase.
        # Only triggers if the token is NOT already in context (novel_tokens_orig
        # already filtered out tokens whose lowercase form is in context).
        if token_lower in KNOWN_ACRONYMS:
            new_entity_detected = True
            print(f"[CONTEXT_CONFLICT] Known acronym '{token}' (lowercase) detected in query "
                  f"→ blocking enrichment with {list(entities.keys())}")
            break

    # -------------------------------------------------------------------------
    # DETECT new Thai location names differing from context
    # -------------------------------------------------------------------------
    if not new_entity_detected:
        known_locations = ["ภูเก็ต", "ชุมพร", "กรุงเทพ", "นครศรี", "พังงา", "สงขลา",
                           "ระนอง", "ตรัง", "สตูล", "ยะลา", "ปัตตานี", "นราธิวาส",
                           "หาดใหญ่"]
        for token in novel_tokens_low:
            if any(loc in token for loc in known_locations):
                new_entity_detected = True
                print(f"[CONTEXT_CONFLICT] New location '{token}' differs from context "
                      f"→ blocking enrichment")
                break

    if new_entity_detected:
        return query  # New entity wins — use raw query, don't mix old context

    # =========================================================================
    # FALLBACK: Type-Based Priority Selection
    # =========================================================================
    # No keyword match AND no conflicting new entity → use type-based priority
    
    # Priority order based on query type
    if "เบอร์" in q_lower or "โทร" in q_lower or "ติดต่อ" in q_lower:
        # Contact query: Prefer LOCATION > ORGANIZATION > DEVICE
        priority = ["LOCATION", "ORGANIZATION", "ORG_TYPE", "DEVICE", "PERSON", "UNKNOWN"]
    elif "คำสั่ง" in q_lower or "command" in q_lower or "config" in q_lower:
        # Technical query: Prefer DEVICE > ORGANIZATION
        priority = ["DEVICE", "ORGANIZATION", "LOCATION", "PERSON", "UNKNOWN"]
    else:
        # Default: Use first entity
        priority = ["LOCATION", "ORGANIZATION", "DEVICE", "PERSON", "ORG_TYPE", "UNKNOWN"]
    
    # Select best entity based on priority
    selected_entity = None
    selected_type = None
    
    for entity_type in priority:
        for entity_value, e_type in entities.items():
            if e_type == entity_type:
                selected_entity = entity_value
                selected_type = entity_type
                break
        if selected_entity:
            break
    
    # Fallback: use first entity
    if not selected_entity:
        selected_entity = list(entities.keys())[0]
        selected_type = entities[selected_entity]
    
    # Don't add if entity already in query
    if selected_entity.lower() in query.lower():
        return query
    
    # Append entity to query
    enriched = f"{query} {selected_entity}"
    print(f"[CONTEXT_ENRICHMENT] '{query}' → '{enriched}' (Type: {selected_type})")
    
    return enriched


def save_session_context(session_id: str, context: Dict[str, Any]) -> bool:
    """
    Save conversation context to persistent storage.
    
    Args:
        session_id: Unique session identifier
        context: Context dict from create_context()
    
    Returns:
        True if saved successfully
    """
    if not session_id or not context:
        return False
    
    try:
        from src.context.session_store import SessionStore
        store = SessionStore()
        return store.save_context(session_id, context)
    except Exception as e:
        print(f"[CONTEXT] Error saving session context: {e}")
        return False


def load_session_context(session_id: str) -> Optional[Dict[str, Any]]:
    """
    Load conversation context from persistent storage.
    
    Args:
        session_id: Unique session identifier
    
    Returns:
        Context dict or None if not found/expired
    """
    if not session_id:
        return None
    
    try:
        from src.context.session_store import SessionStore
        store = SessionStore()
        return store.load_context(session_id)
    except Exception as e:
        print(f"[CONTEXT] Error loading session context: {e}")
        return None


def create_context(
    query: str,
    intent: str,
    route: str,
    entities: Optional[Dict[str, str]] = None,
    result_data: Optional[Dict[str, Any]] = None,
    result_summary: str = ""
) -> Dict[str, Any]:
    """
    Create a new conversation context for storage.
    
    Args:
        query: Original query
        intent: Resolved intent
        route: Result route
        entities: Detected entities {value: type}
        result_data: Result data (for legacy compat)
        result_summary: Summary of results
        
    Returns:
        Context dict to save in last_context
    """
    return {
        "type": route,
        "query": query,
        "entities": entities or {},
        "intent": intent,
        "result_summary": result_summary,
        "timestamp": time.time(),
        "data": result_data or {}
    }
