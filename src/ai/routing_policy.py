"""
Routing Policy & Orchestrator

Purpose: Central routing logic to prevent misrouting of technical/asset queries
"""

PROMPT_ROUTING_ORCHESTRATOR = """
You are an internal knowledge assistant for an enterprise RAG system.
Your top priorities are: (1) correct routing, (2) factual accuracy, (3) traceability.

ROUTING PRINCIPLES
- NEVER treat a technical request as a team lookup unless the user explicitly asks for a team/member/contact person.
- "Table/Sheet/List/Parameter/Config/Proxy/IP/Port/DNS/SIP" are strong signals of a TECHNICAL ASSET request.
- If a query is an ASSET request, the correct route is DOCUMENT/ARTICLE retrieval, not TEAM_LOOKUP.

INTENT RULES (HARD RULES)
1) If the user asks to "ดูตาราง", "ขอดูตาราง", "table", "sheet", "list", "รายการ", "config", "parameter",
   route = ASSET_LOOKUP (document-first).
2) ASSET_LOOKUP must never call TEAM_LOOKUP. Team lookup is allowed only if the user asks for:
   "ทีม", "หน่วยงานดูแล", "เจ้าของงาน", "ผู้รับผิดชอบ", "contact", "เบอร์", "ใครดูแล", "ใครรับผิดชอบ".
3) If ASSET_LOOKUP finds no exact asset record, immediately fall back to ARTICLE_SEARCH
   using the cleaned query + keyphrases. Do not output "ไม่พบข้อมูลทีม".
4) If both contact-like matches and article matches exist:
   - Show the TECHNICAL ARTICLE answer first.
   - Then show "Related contacts" as secondary (optional).

ANSWER FORMAT (FOR ASSET_LOOKUP / ARTICLE_SEARCH)
- Provide a short title
- Provide the extracted content in a clean list/table-like form
- Always include a source link
- If nothing is found, say: "ไม่พบเอกสาร/ตารางที่ตรงคำค้น" and suggest 2–3 alternative queries.

Input Query: {query}

Output: ASSET_LOOKUP, ARTICLE_SEARCH, TEAM_LOOKUP, CONTACT_LOOKUP, or POSITION_LOOKUP
"""

# Routing decision tree (deterministic)
class RoutingPolicy:
    """Deterministic routing policy for query classification."""
    
    # Asset/Table indicators (highest priority)
    ASSET_INDICATORS = {
        # Thai
        "ตาราง", "รายการ", "ลิสต์", "แสดง", "ดู", "ขอดู", "ขอรายการ",
        "ทั้งหมด", "รวม", "sheet", "config", "parameter",
        # English
        "table", "list", "show", "display", "view", "sheet", "spreadsheet",
        "configuration", "parameters", "settings"
    }
    
    # Technical entities (boost ASSET route)
    TECHNICAL_ENTITIES = {
        "proxy", "ip", "port", "dns", "sip", "sbc", "onu", "ont", "olt",
        "vlan", "router", "switch", "network", "ipphone", "ip-phone", "ip phone"
    }
    
    # Team/Contact indicators (only these trigger TEAM/CONTACT route)
    TEAM_CONTACT_INDICATORS = {
        # Team
        "ทีม", "หน่วยงาน", "หน่วยงานดูแล", "เจ้าของงาน", "ผู้รับผิดชอบ",
        "team", "unit", "department",
        # Contact
        "เบอร์", "เบอร์ติดต่อ", "โทรหา", "ติดต่อ", "contact", "phone", "call",
        "ใครดูแล", "ใครรับผิดชอบ", "who is responsible"
    }
    
    @staticmethod
    def route(query: str) -> str:
        """
        Determine the correct route for a query.
        
        Priority:
        1. ASSET_LOOKUP if asset indicators + technical entities
        2. CONTACT_LOOKUP if explicit contact request
        3. TEAM_LOOKUP if explicit team request
        4. ARTICLE_SEARCH as fallback
        
        Returns:
            Route name: ASSET_LOOKUP, ARTICLE_SEARCH, TEAM_LOOKUP, CONTACT_LOOKUP
        """
        query_lower = query.lower()
        
        # Priority 1: ASSET_LOOKUP (table/list + technical)
        has_asset_indicator = any(ind in query_lower for ind in RoutingPolicy.ASSET_INDICATORS)
        has_technical_entity = any(ent in query_lower for ent in RoutingPolicy.TECHNICAL_ENTITIES)
        
        if has_asset_indicator and has_technical_entity:
            return "ASSET_LOOKUP"
        
        # Priority 2: CONTACT_LOOKUP (explicit contact request)
        contact_keywords = {"เบอร์", "เบอร์ติดต่อ", "โทรหา", "ติดต่อ", "contact", "call"}
        if any(kw in query_lower for kw in contact_keywords):
            return "CONTACT_LOOKUP"
        
        # Priority 3: TEAM_LOOKUP (explicit team request)
        team_keywords = {"ทีม", "หน่วยงาน", "ผู้รับผิดชอบ", "team", "unit"}
        if any(kw in query_lower for kw in team_keywords):
            return "TEAM_LOOKUP"
        
        # Priority 4: ASSET_LOOKUP (asset indicator alone)
        if has_asset_indicator:
            return "ASSET_LOOKUP"
        
        # Default: ARTICLE_SEARCH
        return "ARTICLE_SEARCH"
    
    @staticmethod
    def should_fallback_to_article(route: str, result: str) -> bool:
        """
        Determine if we should fallback to article search.
        
        Args:
            route: Current route
            result: Result status (e.g., "team_miss", "asset_miss")
            
        Returns:
            True if should fallback to article search
        """
        # If ASSET_LOOKUP or TEAM_LOOKUP failed, fallback to article
        if route in ["ASSET_LOOKUP", "TEAM_LOOKUP"] and "miss" in result:
            return True
        
        return False
    
    @staticmethod
    def format_not_found_response(query: str, route: str) -> str:
        """
        Format a helpful not-found response with suggestions.
        
        Args:
            query: Original query
            route: Route that failed
            
        Returns:
            Formatted response string
        """
        # Extract key terms
        query_lower = query.lower()
        
        # Generate alternative queries
        alternatives = []
        
        if "proxy" in query_lower and "ip phone" in query_lower:
            alternatives = [
                "IP Phone proxy",
                "SIP proxy table",
                "proxy configuration IP phone"
            ]
        elif "ตาราง" in query_lower:
            # Extract technical term
            for term in RoutingPolicy.TECHNICAL_ENTITIES:
                if term in query_lower:
                    alternatives.append(f"{term} configuration")
                    alternatives.append(f"{term} parameters")
                    break
        
        # Build response
        response = f'ไม่พบเอกสาร/ตาราง "{query}" ที่ตรงคำค้นในระบบตอนนี้\n\n'
        
        if alternatives:
            response += "ลองค้นด้วยคำใกล้เคียง:\n"
            for alt in alternatives[:3]:
                response += f"- \"{alt}\"\n"
        
        # Add clarification question
        if "proxy" in query_lower and "ip phone" in query_lower:
            response += "\nคุณต้องการ \"ตารางค่า proxy\" ของศูนย์/พื้นที่ไหน (เช่น HYI / SNI / PKG) หรือเป็นตารางรวมทั้งประเทศ?"
        
        return response
