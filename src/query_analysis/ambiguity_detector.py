"""
Ambiguity Detector - Pre-check gate for broad/unclear queries.

Detects queries that are too ambiguous/broad and should request clarification
BEFORE routing to large/generic articles.

Purpose: Prevent "คำสั่งHuawei" from routing to 577K article.
"""

from typing import Tuple, Dict, Optional


class AmbiguityDetector:
    """Detect ambiguous queries using heuristic rules."""
    
    # Vendor keywords (lowercase)
    VENDOR_KEYWORDS = [
        "huawei", "zte", "cisco", "nokia", "alcatel", "ericsson",
        "ฮัวเว่ย", "ซีสโก้"
    ]
    
    # Generic protocol / technology keywords that are broad without specific action
    # e.g. "คำสั่ง telnet" should trigger multi-result just like "คำสั่ง Huawei"
    GENERIC_PROTOCOL_KEYWORDS = [
        "telnet", "ssh", "ping", "traceroute", "snmp",
        "vlan", "ospf", "bgp", "mpls", "nat", "dhcp", "dns",
        "forth", "fttx", "gpon", "epon", "bras", "nms", "osp",
        "fiber", "ftth", "fttb", "adsl",
    ]
    
    # Command intent keywords
    COMMAND_KEYWORDS = [
        "คำสั่ง", "command", "cmd", "commands", "cli"
    ]
    
    # Specific action verbs (indicates non-ambiguous query)
    SPECIFIC_ACTIONS = [
        "add", "show", "config", "set", "delete", "create", "remove",
        "enable", "disable", "get", "put", "update", "install", "reboot",
        "เพิ่ม", "ลบ", "แก้ไข", "ดู", "ตั้งค่า"
    ]
    
    # Index/collection indicators
    INDEX_INDICATORS = [
        "รวม", "list", "all", "index", "collection", "directory",
        "รายการ", "ทั้งหมด"
    ]
    
    # Device types (make query more specific)
    DEVICE_TYPES = [
        "olt", "onu", "switch", "router", "gateway", "firewall",
        "สวิตช์", "เราเตอร์"
    ]
    
    @classmethod
    def check_ambiguity(cls, query: str, intent: Optional[str] = None) -> Dict:
        """
        Check if query is ambiguous and needs clarification.
        
        Args:
            query: User query string
            intent: Detected intent (optional)
            
        Returns:
            {
                "is_ambiguous": bool,
                "reason": str or None,
                "suggestion": str or None
            }
        """
        query_lower = query.lower().strip()
        
        # Rule 0: Check if this looks like an exact title match (don't block these)
        # "ZTE-SW Command" should pass through
        if cls._looks_like_exact_title(query_lower):
            return {
                "is_ambiguous": False,
                "reason": None,
                "suggestion": None
            }
        
        # Rule 1: Index query indicators (check FIRST - higher priority)
        result = cls._check_index_query(query_lower)
        if result["is_ambiguous"]:
            return result
        
        # Rule 2: Broad vendor command (vendor + คำสั่ง/command without specific action)
        result = cls._check_broad_vendor_command(query_lower)
        if result["is_ambiguous"]:
            return result
        
        # Rule 2.5: Broad generic protocol command (e.g. "คำสั่ง telnet", "command ssh")
        result = cls._check_broad_generic_command(query_lower)
        if result["is_ambiguous"]:
            return result
        
        # Rule 3: Single vendor keyword only
        result = cls._check_single_vendor(query_lower)
        if result["is_ambiguous"]:
            return result
        
        # Not ambiguous
        return {
            "is_ambiguous": False,
            "reason": None,
            "suggestion": None
        }
    
    @classmethod
    def _looks_like_exact_title(cls, query_lower: str) -> bool:
        """
        Check if query looks like an exact article title (e.g., "ZTE-SW Command").
        These should bypass ambiguity checks.
        """
        # Normalize: replace underscores and multiple spaces with single space
        normalized = query_lower.replace('_', ' ').replace('-', ' ')
        normalized = ' '.join(normalized.split())  # Collapse multiple spaces
        
        # Known article title patterns (normalized form)
        title_patterns = [
            "zte sw command",       # Matches: zte-sw-command, zte__sw__command, zte sw command
            "huawei olt command",
            "cisco router command",
            "command huawei",       # Also a known title
            "command zte"
        ]
        
        # Check if query matches any title pattern
        if normalized in title_patterns:
            return True
        
        # Additional heuristic: if it contains "command" + vendor AND has underscore/hyphen
        # formatting, it's likely a title
        has_formatting = '_' in query_lower or '-' in query_lower
        has_command = 'command' in query_lower
        has_vendor = any(v in query_lower for v in cls.VENDOR_KEYWORDS)
        
        if has_formatting and has_command and has_vendor:
            return True
        
        return False
    
    @classmethod
    def _check_broad_vendor_command(cls, query_lower: str) -> Dict:
        """
        Check for pattern: {vendor} + คำสั่ง/command WITHOUT specific action.
        
        Examples:
        - Ambiguous: "คำสั่งHuawei", "Huawei command", "ZTE commands"
        - Not ambiguous: "Huawei add vlan", "ZTE show interface"
        """
        import re
        
        # Check 1: Separate keywords (original logic)
        has_vendor = any(v in query_lower for v in cls.VENDOR_KEYWORDS)
        has_command = any(c in query_lower for c in cls.COMMAND_KEYWORDS)
        has_action = any(a in query_lower for a in cls.SPECIFIC_ACTIONS)
        has_device = any(d in query_lower for d in cls.DEVICE_TYPES)
        
        # NEW: Check for model numbers (e.g., "NE8000", "5600", "MA5680T")
        has_model = bool(re.search(r'[a-zA-Z]+\d+|[0-9]{2,}', query_lower))
        
        # Check 2: Concatenated pattern (NEW FIX)
        # Pattern: (คำสั่ง|command|cmd|cli)(huawei|zte|cisco|...)
        # Build regex from keywords
        command_pattern = '|'.join(cls.COMMAND_KEYWORDS)
        vendor_pattern = '|'.join(cls.VENDOR_KEYWORDS)
        concatenated_pattern = f'({command_pattern})({vendor_pattern})|({vendor_pattern})({command_pattern})'
        
        has_concatenated = bool(re.search(concatenated_pattern, query_lower))
        
        if has_concatenated:
            # Force clarification for concatenated patterns
            return {
                "is_ambiguous": True,
                "reason": "BROAD_VENDOR_COMMAND",
                "suggestion": "กรุณาระบุคำสั่งเฉพาะ เช่น add vlan, show config"
            }
        
        if has_vendor and has_command and not has_action and not has_device and not has_model:
            # Very broad query like "คำสั่ง Huawei" (with space)
            return {
                "is_ambiguous": True,
                "reason": "BROAD_VENDOR_COMMAND",
                "suggestion": "กรุณาระบุคำสั่งเฉพาะ เช่น add vlan, show config"
            }
        
        return {"is_ambiguous": False, "reason": None, "suggestion": None}
    
    @classmethod
    def _check_single_vendor(cls, query_lower: str) -> Dict:
        """
        Check if query is ONLY a vendor keyword.
        
        Examples:
        - Ambiguous: "Huawei", "ZTE"
        - Not ambiguous: "Huawei OLT", "ZTE config"
        """
        # Normalize whitespace
        query_normalized = ' '.join(query_lower.split())
        
        # Check if query is exactly one vendor keyword (with some tolerance for whitespace)
        if query_normalized in cls.VENDOR_KEYWORDS:
            return {
                "is_ambiguous": True,
                "reason": "VENDOR_ONLY",
                "suggestion": "กรุณาระบุอุปกรณ์หรือคำสั่งที่ต้องการ"
            }
        
        # Check if it's vendor + very minimal context (< 3 words total)
        words = query_normalized.split()
        if len(words) < 3:
            if any(v in query_normalized for v in cls.VENDOR_KEYWORDS):
                # Check for model numbers
                import re
                has_model = bool(re.search(r'[a-zA-Z]+\d+|[0-9]{2,}', query_normalized))
                
                # Check if it's not a specific term
                if not any(a in query_normalized for a in cls.SPECIFIC_ACTIONS):
                    if not any(d in query_normalized for d in cls.DEVICE_TYPES):
                        if not has_model:
                            return {
                                "is_ambiguous": True,
                                "reason": "MINIMAL_VENDOR_CONTEXT",
                                "suggestion": "กรุณาระบุรายละเอียดเพิ่มเติม"
                            }
        
        return {"is_ambiguous": False, "reason": None, "suggestion": None}
    
    @classmethod
    def _check_broad_generic_command(cls, query_lower: str) -> Dict:
        """
        Rule 2.5: Detect 'คำสั่ง + generic_protocol' without a specific action.
        
        Examples:
        - Ambiguous: "คำสั่ง telnet", "command ssh", "คำสั่ง ping"
        - Not ambiguous: "telnet ไปที่ ONU", "telnet huawei แล้ว show ip"
        """
        has_command = any(c in query_lower for c in cls.COMMAND_KEYWORDS)
        has_protocol = any(p in query_lower for p in cls.GENERIC_PROTOCOL_KEYWORDS)
        has_action = any(a in query_lower for a in cls.SPECIFIC_ACTIONS)
        
        if has_command and has_protocol and not has_action:
            return {
                "is_ambiguous": True,
                "reason": "BROAD_GENERIC_COMMAND",
                "suggestion": "กรุณาระบุคำสั่งหรือการกระทำเฉพาะ เช่น 'telnet เข้า ONU วิธีทำ'"
            }
        
        return {"is_ambiguous": False, "reason": None, "suggestion": None}
    
    @classmethod
    def _check_index_query(cls, query_lower: str) -> Dict:
        """
        Check for index/collection query patterns.
        
        Examples:
        - Ambiguous: "รวมคำสั่ง", "command list", "all commands"
        - Not ambiguous: "specific command from list"
        """
        has_index = any(ind in query_lower for ind in cls.INDEX_INDICATORS)
        has_command = any(c in query_lower for c in cls.COMMAND_KEYWORDS)
        
        if has_index and has_command:
            return {
                "is_ambiguous": True,
                "reason": "INDEX_QUERY",
                "suggestion": "กรุณาระบุคำสั่งที่ต้องการโดยเฉพาะ"
            }
        
        return {"is_ambiguous": False, "reason": None, "suggestion": None}
    
    @classmethod
    def extract_vendor(cls, query: str) -> Optional[str]:
        """
        Extract vendor name from query.
        
        Args:
            query: User query string
            
        Returns:
            Normalized vendor name (e.g., "Huawei", "ZTE") or None
        """
        query_lower = query.lower()
        
        # Vendor name mapping (lowercase -> normalized)
        vendor_map = {
            "huawei": "Huawei",
            "ฮัวเว่ย": "Huawei",
            "zte": "ZTE",
            "cisco": "Cisco",
            "ซีสโก้": "Cisco",
            "nokia": "Nokia",
            "alcatel": "Alcatel",
            "ericsson": "Ericsson"
        }
        
        # Check each vendor keyword
        for vendor_key, vendor_name in vendor_map.items():
            if vendor_key in query_lower:
                return vendor_name
        
        return None


def check_ambiguity(query: str, intent: Optional[str] = None) -> Dict:
    """
    Convenience function to check query ambiguity.
    
    Args:
        query: User query
        intent: Detected intent (optional)
        
    Returns:
        Ambiguity result dict
    """
    return AmbiguityDetector.check_ambiguity(query, intent)
