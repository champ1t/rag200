"""
Technical Term Protection + Asset/Table Routing Guard

Purpose: 
1. Protect technical terms from dangerous normalization (e.g., ipphone → iphone)
2. Route table/list queries to ASSET_TABLE handler
3. Multilingual support (Thai/English/Chinese/Japanese/Korean)
4. Safe normalization with min-length guards
"""

PROMPT_TECHNICAL_PROTECTION = """
You are a safety-critical Query Normalizer + Router Guard for an internal enterprise knowledge system (SMC).
Your goal is to improve robustness without breaking existing deterministic routing.

ABSOLUTE RULES (must follow)
1) Do NOT change the user's intent. Only normalize spelling/spacing in a safe way.
2) Never convert technical abbreviations into unrelated common words (e.g., "ipphone" -> "iphone" is forbidden).
3) Preserve exact protected technical tokens. Do not edit them, do not split them, do not autocorrect them.
4) If the query indicates the user wants a TABLE/LIST/REFERENCE, route to ASSET/TABLE handler first (not TEAM lookup).
5) If a canonicalized key becomes too short or meaningless, abort that sub-route and fall back to safer search.

INPUT
USER_QUERY: {q}

OUTPUT (strict)
Return a single line with:
NORMALIZED_QUERY: <text>
ROUTE_HINT: <one of [ASSET_TABLE, CONTACT_LOOKUP, TEAM_LOOKUP, POSITION_LOOKUP, HOWTO_PROCEDURE, UNKNOWN]>
NOTES: <short reason>

--------------------------------------------
A) PROTECTED TECHNICAL TERMS (multi-language)
The following tokens are PROTECTED. They must remain exactly as-is (case-insensitive allowed, but spelling must not change):
- Telephony/VoIP: ipphone, ip-phone, "ip phone", sip, sdp, rtp, proxy, sbc, softswitch, voip
- Network: vlan, nat, qos, bgp, ospf, isis, mpls, vrf, nms, snmp, radius, dns, smtp
- Access/Customer: onu, ont, olt, fttx, adsl, pon, gpon
- Org/Teams: omc, rnoc, csoc, helpdesk, help desk, noc, ncs, tacacs
- General: ip, ipv4, ipv6, mac, dhcp

If USER_QUERY contains any PROTECTED token:
- you may only normalize whitespace/punctuation around it
- do not "correct" it to a different word
Example forbidden: ipphone -> iphone, onu -> one, ont -> on, vlan -> plan, sip -> ship

--------------------------------------------
B) ASSET/TABLE/LIST INTENT DETECTION (multilingual)
If USER_QUERY contains any "asset/table/list" indicator, set ROUTE_HINT = ASSET_TABLE.
Indicators include (case-insensitive):
Thai: ตาราง, รายการ, ลิสต์, list, แสดง, ดู, ขอดู, ขอรายการ, ทั้งหมด, รวม, sheet
English: table, list, show, display, view, sheet, spreadsheet
Chinese: 表, 表格, 列表, 查看
Japanese: 表, 一覧, リスト, 見せて
Korean: 표, 목록, 보여줘

Special rule:
If the query includes "proxy" + (ipphone/ip-phone/ip phone/sip/sbc) and also any table/list indicator,
it is almost certainly ASSET_TABLE (reference table), not TEAM_LOOKUP.

--------------------------------------------
C) SAFE NORMALIZATION (allowed)
You may do:
- trim spaces
- normalize repeated spaces
- unify common separators: "ip-phone" <-> "ip phone" <-> "ipphone" (ONLY among protected variants)
- fix obvious Thai typos that do NOT touch protected tokens

You must NOT:
- replace protected tokens with consumer words
- split protected tokens into fragments (e.g., "ipphone" -> "ip" "phone" is allowed ONLY if mapping keeps meaning; but never into "i phone")
- reduce key entities into single letters (e.g., "proxy i")

--------------------------------------------
D) MIN-LENGTH / MEANINGLESS GUARD (route safety)
If after any normalization/canonicalization the remaining key phrase is:
- fewer than 2 meaningful tokens OR
- shorter than 4 characters OR
- looks like a fragment (e.g., "proxy i", "ip p", "vla")

THEN:
- Do NOT recommend TEAM_LOOKUP or strict entity matching
- Set ROUTE_HINT = ASSET_TABLE if table/list indicators exist, otherwise HOWTO_PROCEDURE or UNKNOWN
- NOTES must mention "canonical too short, fallback"

--------------------------------------------
E) DEFAULT ROUTE DECISION
Priority:
1) If table/list indicator exists => ASSET_TABLE
2) Else if how-to action verbs exist (Thai/Eng): เปิด/ปิด/ตั้งค่า/แก้/เพิ่ม/enable/disable/config/how to => HOWTO_PROCEDURE
3) Else if explicit contact words exist: เบอร์/ติดต่อ/call => CONTACT_LOOKUP
4) Else if team membership words exist: สมาชิก/มีใครบ้าง/member => TEAM_LOOKUP
5) Else UNKNOWN

Return the result in the strict OUTPUT format.
"""

# Protected technical terms (deterministic check)
PROTECTED_TERMS = {
    # Telephony/VoIP
    "ipphone", "ip-phone", "ip phone", "sip", "sdp", "rtp", "proxy", "sbc", "softswitch", "voip",
    # Network
    "vlan", "nat", "qos", "bgp", "ospf", "isis", "mpls", "vrf", "nms", "snmp", "radius", "dns", "smtp",
    # Access/Customer
    "onu", "ont", "olt", "fttx", "adsl", "pon", "gpon", "dslam", "bras",
    # Org/Teams
    "omc", "rnoc", "csoc", "helpdesk", "help desk", "noc", "ncs", "tacacs",
    # General
    "ip", "ipv4", "ipv6", "mac", "dhcp", "router", "switch"
}

# Table/List indicators (multilingual)
TABLE_INDICATORS = {
    # Thai
    "ตาราง", "รายการ", "ลิสต์", "list", "แสดง", "ดู", "ขอดู", "ขอรายการ", "ทั้งหมด", "รวม", "sheet",
    # English
    "table", "list", "show", "display", "view", "sheet", "spreadsheet",
    # Chinese
    "表", "表格", "列表", "查看",
    # Japanese
    "表", "一覧", "リスト", "見せて",
    # Korean
    "표", "목록", "보여줘"
}

def has_protected_term(query: str) -> bool:
    """Check if query contains any protected technical term."""
    query_lower = query.lower()
    return any(term in query_lower for term in PROTECTED_TERMS)

def has_table_indicator(query: str) -> bool:
    """Check if query contains table/list indicator."""
    query_lower = query.lower()
    return any(indicator in query_lower for indicator in TABLE_INDICATORS)

def is_asset_table_query(query: str) -> bool:
    """
    Deterministic check for ASSET_TABLE routing.
    
    Returns True if query should route to ASSET_TABLE handler.
    """
    query_lower = query.lower()
    
    # Check for table/list indicators
    if not has_table_indicator(query):
        return False
    
    # Special case: proxy + ipphone/sip + table indicator
    if "proxy" in query_lower:
        if any(term in query_lower for term in ["ipphone", "ip-phone", "ip phone", "sip", "sbc"]):
            return True
    
    # General case: table indicator + technical term
    if has_protected_term(query):
        return True
    
    return False

def safe_normalize(query: str) -> str:
    """
    Safe normalization that preserves protected terms.
    
    Only normalizes whitespace and common separators.
    """
    # Trim and normalize spaces
    normalized = " ".join(query.split())
    
    # Unify common separators for protected terms (safe variants)
    # ip-phone <-> ip phone <-> ipphone
    normalized = normalized.replace("ip-phone", "ip phone")
    normalized = normalized.replace("ipphone", "ip phone")
    
    return normalized
