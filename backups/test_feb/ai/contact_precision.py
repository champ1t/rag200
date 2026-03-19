"""
Contact Trigger Precision Prompt

Purpose: Prevent false-positive CONTACT_LOOKUP triggers from technical/configuration contexts
"""

PROMPT_CONTACT_PRECISION = """
You are a Contact Intent Validator.

CONTACT_LOOKUP is allowed ONLY when the query clearly indicates
an intention to retrieve contact information.

Valid CONTACT signals include:
- Explicit phone-related intent:
  "เบอร์", "เบอร์ติดต่อ", "โทรหา", "ติดต่อ", "call", "phone number"
- Asking for a person, unit, or organization to contact
  "ติดต่อ OMC", "เบอร์ช่าง", "โทรหาใคร"

INVALID CONTACT cases:
- The word "โทร" used as a feature, configuration, or capacity
  (e.g. "เปิดโทร 3 สาย", "โทรได้กี่สาย", "ตั้งค่าโทร", "config โทร")
- Technical queries about phone systems/features
  (e.g. "IP Phone config", "SIP proxy", "โทรภายใน")

SPECIAL RULE:
If the word "โทร" is followed by:
- "กี่สาย", "2 สาย", "3 สาย", "line", "lines", "บน ONU", "บน ONT"

THEN:
- Treat the query as HOWTO_PROCEDURE or TECHNICAL_CONFIG
- DO NOT trigger CONTACT_LOOKUP

CONTACT_LOOKUP must never be inferred from ambiguous technical context.

Examples:
- "เบอร์ OMC" → CONTACT_LOOKUP ✓
- "เปิดโทร 3 สาย บน ONU" → HOWTO_PROCEDURE ✓
- "ติดต่อช่าง FTTx" → CONTACT_LOOKUP ✓
- "config IP Phone" → HOWTO_PROCEDURE ✓

Input Query: {query}

Output: CONTACT_LOOKUP or NOT_CONTACT (one word only)
"""

def is_valid_contact_query(query: str) -> bool:
    """
    Deterministic check for valid contact queries.
    
    Returns True if query is clearly asking for contact information.
    Returns False if query is about technical configuration.
    """
    query_lower = query.lower()
    
    # Strong contact signals
    contact_keywords = ["เบอร์", "เบอร์ติดต่อ", "โทรหา", "ติดต่อ", "call", "phone number"]
    
    # Technical configuration signals (should NOT trigger CONTACT)
    tech_config_patterns = [
        "เปิดโทร",
        "ปิดโทร", 
        "ตั้งค่าโทร",
        "config โทร",
        "โทร 2 สาย",
        "โทร 3 สาย",
        "โทรได้กี่สาย",
        "โทรบน onu",
        "โทรบน ont",
        "ip phone config",
        "sip proxy",
        "โทรภายใน"
    ]
    
    # Check for technical patterns first (higher priority)
    for pattern in tech_config_patterns:
        if pattern in query_lower:
            return False
    
    # Check for valid contact signals
    for keyword in contact_keywords:
        if keyword in query_lower:
            return True
    
    # If "โทร" appears with line count, it's NOT a contact query
    if "โทร" in query_lower and any(x in query_lower for x in ["สาย", "line", "onu", "ont"]):
        return False
    
    return False
