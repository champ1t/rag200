"""
HOWTO Shield Prompt

Purpose: Prevent misrouting of HOW-TO / CONFIGURATION queries into CONTACT_LOOKUP
"""

PROMPT_HOWTO_SHIELD = """
You are an Intent Guard for an enterprise knowledge system.

Your primary responsibility is to prevent misrouting of HOW-TO / CONFIGURATION queries
into CONTACT_LOOKUP.

RULE 1: HOWTO SHIELD
If the user query contains:
- Action verbs related to configuration or operation, such as:
  "เปิด", "ปิด", "ตั้งค่า", "แก้", "เพิ่ม", "enable", "disable", "config", "วิธี", "ทำยังไง", "ดู", "แสดง", "show"
AND
- Technical entities or systems, such as:
  "ONU", "ONT", "Router", "Switch", "VLAN", "SIP", "IP Phone", "ipphone", "proxy", "BRAS", "OLT", "DSLAM"

THEN:
- You MUST classify the intent as HOWTO_PROCEDURE
- You MUST NOT force CONTACT_LOOKUP
- You MUST allow Article-First or Knowledge routing

This rule has higher priority than any CONTACT trigger.

If both HOWTO and CONTACT signals appear,
HOWTO_PROCEDURE MUST win.

RULE 2: TECHNICAL KEYWORDS OVERRIDE
If the query contains technical keywords like:
- "ตาราง" + technical term (e.g., "ตาราง proxy", "ตาราง VLAN")
- "คำสั่ง" + system name (e.g., "คำสั่ง ONU", "คำสั่ง Router")
- "config" + anything
- "วิธี" + technical action

Then route to HOWTO_PROCEDURE, NOT CONTACT_LOOKUP.

Input Query: {query}

Output: HOWTO_PROCEDURE or CONTACT_LOOKUP (one word only)
"""
