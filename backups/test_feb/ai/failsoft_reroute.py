"""
Fail-Soft Reroute Logic

Purpose: Recover from CONTACT_LOOKUP misses by rerouting to HOWTO_PROCEDURE
when the query is clearly technical/configuration-related.
"""

PROMPT_FAILSOFT_REROUTE = """
You are a Fail-Soft Recovery Controller.

If a query has been routed to CONTACT_LOOKUP
AND the result is contact_miss_strict (no matches found),

THEN evaluate for a safe reroute.

SAFE REROUTE CONDITIONS:
- The query contains technical entities such as:
  ONU, ONT, Router, Switch, VLAN, SIP, IP Phone, ipphone, proxy, BRAS, OLT, DSLAM
AND
- The query contains configuration-related verbs:
  เปิด, ตั้งค่า, เพิ่ม, แก้, enable, disable, config, ดู, แสดง, show

AND
- No contact records were found

ACTION:
- Reroute the query ONCE to HOWTO_PROCEDURE
- Do NOT invoke additional LLM normalization
- Use the original normalized query

If the rerouted HOWTO_PROCEDURE also fails,
return a graceful "ไม่พบข้อมูล" without suggestions.

Input Query: {query}

Output: REROUTE or NO_REROUTE (one word only)
"""

def should_reroute_to_howto(query: str, route: str) -> tuple[bool, str]:
    """
    Check for fail-soft reroute eligibility.
    
    Args:
        query: The normalized query
        route: The current route/intent (e.g. "CONTACT_LOOKUP", "contact_miss_strict")
        
    Returns:
        (should_reroute: bool, new_intent: str)
    """
    # Allow reroute if it's a miss OR a preemptive CONTACT_LOOKUP check
    valid_triggers = ["contact_miss_strict", "team_miss", "CONTACT_LOOKUP"]
    if route not in valid_triggers:
        return False, route
    
    query_lower = query.lower()
    
    # Technical entities
    technical_entities = [
        "onu", "ont", "router", "switch", "vlan", "sip", 
        "ip phone", "ipphone", "proxy", "bras", "olt", "dslam",
        "modem", "wifi", "network", "config", "command"
    ]
    
    # Configuration verbs
    config_verbs = [
        "เปิด", "ปิด", "ตั้งค่า", "แก้", "เพิ่ม", "ลบ",
        "enable", "disable", "config", "ดู", "แสดง", "show",
        "วิธี", "ทำยังไง", "คำสั่ง"
    ]
    
    # Check for technical entity
    has_tech_entity = any(entity in query_lower for entity in technical_entities)
    
    # Check for config verb
    has_config_verb = any(verb in query_lower for verb in config_verbs)
    
    # Reroute if both conditions are met
    if has_tech_entity and has_config_verb:
        return True, "HOWTO_PROCEDURE"
        
    return False, route


def get_reroute_intent(query: str, original_intent: str, route: str) -> str:
    """
    Determine the reroute intent based on query characteristics.
    
    Args:
        query: The normalized query
        original_intent: The original intent classification
        route: The current route result
        
    Returns:
        New intent to route to, or original_intent if no reroute
    """
    if should_reroute_to_howto(query, route):
        return "HOWTO_PROCEDURE"
    
    return original_intent
