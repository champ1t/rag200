"""
Knowledge Type Classifier

Classifies the nature of knowledge requested AFTER intent routing is completed.
This is a READ-ONLY layer that does NOT affect routing decisions.

Classification Types:
- GENERAL_NETWORK_KNOWLEDGE: Industry-standard concepts
- NT_SPECIFIC_PROCEDURE: NT internal commands, configs, workflows
- POLICY_OR_CONTACT: Organizational info, contacts, policies
"""

from typing import Dict, Any


# Knowledge type enum
class KnowledgeType:
    GENERAL_NETWORK_KNOWLEDGE = "GENERAL_NETWORK_KNOWLEDGE"
    NT_SPECIFIC_PROCEDURE = "NT_SPECIFIC_PROCEDURE"
    POLICY_OR_CONTACT = "POLICY_OR_CONTACT"


def classify_knowledge_type(query: str, intent: str, routing_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Classify knowledge type AFTER routing is completed.
    
    Args:
        query: Original user query
        intent: Intent from router (READ-ONLY)
        routing_result: Full routing result (READ-ONLY)
    
    Returns:
        {
            "knowledge_type": str,  # ENUM value
            "confidence": float,    # 0.0 - 1.0
            "explanation": str      # For debugging
        }
    
    CRITICAL: This function MUST NOT modify intent or routing_result
    """
    
    # Step 1: Intent-based fast path (deterministic)
    if intent in ["CONTACT_LOOKUP", "POSITION_HOLDER_LOOKUP", "TEAM_LOOKUP", "PERSON_LOOKUP"]:
        return {
            "knowledge_type": KnowledgeType.POLICY_OR_CONTACT,
            "confidence": 1.0,
            "explanation": f"Intent '{intent}' is deterministically POLICY_OR_CONTACT"
        }
    
    # Step 2: Query keyword analysis
    query_lower = query.lower()
    
    # NT-specific tokens (brands, models, internal terms)
    nt_specific_identifiers = [
        "nt", "zte", "huawei", "nokia", "alcatel", "c320", "c300", 
        "c600", "c650", "c6xx", "ma5600", "ma5800", "msan", "dslam", 
        "olt", "asr", "bng", "ncs", "edge", "ribbon", "csoc", "omc", "noc"
    ]
    
    # NT-specific procedure indicators (HIGH PRIORITY)
    nt_procedure_keywords = [
        "ตั้งค่า", "config", "คำสั่ง", "command", "วิธี", "แก้",
        "เช็ค", "check", "show", "set", "enable", "disable",
        "troubleshoot", "ปัญหา", "แก้ไข", "configure", "monitor"
    ]
    
    # General knowledge indicators
    general_keywords = [
        "คืออะไร", "หมายถึง", "definition", "ทำงานยังไง",
        "อธิบาย", "explain", "principle", "หลักการ", "คือ",
        "สาเหตุ", "cause", "เกิดจาก", "meaning", "concept",
        "diagram", "ไดอะแกรม", "flow", "work", "function"
    ]
    
    # Troubleshooting / Symptoms keywords (Logic 1)
    trouble_keywords = [
        "los", "alarm", "ไฟ", "red", "blink", "fail", "slow", "down", 
        "drop", "cannot", "connect", "signal", "strength", "db", "red light",
        "กระพริบ", "แดง", "ช้า", "หลุด", "ใช้งานไม่ได้", "เข้าไม่ได้"
    ]
    
    # Nonsense / Out-of-domain procedure keywords (Logic 2)
    nonsense_actions = [
        "ชง", "ต้ม", "กิน", "ทำอาหาร", "ซัก", "ล้าง", "นอน", "วิ่ง", "กระโดด",
        "brew", "cook", "eat", "wash", "sleep", "run", "jump", "dance"
    ]
    
    # Network domain keywords (Safety Net for Logic 2)
    network_domain_kw = [
        "internet", "wifi", "lan", "wan", "fiber", "optic", "route", "sf",
        "ais", "dtac", "true", "3bb", "tot", "cat", "telecom", "net",
        "speed", "test", "upload", "download", "ping", "latency",
        "onu", "ont", "router", "modem", "ap", "access point"
    ]
    
    # Check checks
    has_nt_identifier = any(kw in query_lower for kw in nt_specific_identifiers)
    has_procedure_keyword = any(kw in query_lower for kw in nt_procedure_keywords)
    has_general_keyword = any(kw in query_lower for kw in general_keywords)
    
    
    # Step 3: Classification decision
    
    # LOGIC 1: Troubleshooting Allowance (Patch 1362) -- HIGH PRIORITY
    # If intent is HowTo/Troubleshoot but query is about symptoms (LOS, Red Light),
    # AND lacks specific config keywords -> Treat as GENERAL (Allow Expert Explainer).
    has_trouble = any(kw in query_lower for kw in trouble_keywords)
    has_config_specific = any(kw in query_lower for kw in ["config", "set", "enable", "disable", "cli", "profile"])
    
    if intent in ["HOWTO_PROCEDURE", "TROUBLESHOOT"] and has_trouble and not has_config_specific:
        return {
            "knowledge_type": KnowledgeType.GENERAL_NETWORK_KNOWLEDGE,
            "confidence": 0.85,
            "explanation": "Troubleshooting/Symptom explanation (Logic 1) -> Routed to Expert Explainer"
        }

    # LOGIC 2: Nonsense Procedure Fast-Path Refusal (Patch 1362)
    # If query asks for method (HOWTO) but action is Nonsense (Make coffee) OR irrelevant to network.
    has_nonsense = any(kw in query_lower for kw in nonsense_actions)
    has_network_domain = any(kw in query_lower for kw in network_domain_kw) or has_nt_identifier
    
    if intent == "HOWTO_PROCEDURE": 
        if has_nonsense:
            # Force GENERAL with specific explanation to trigger Refusal
            return {
                "knowledge_type": KnowledgeType.GENERAL_NETWORK_KNOWLEDGE,
                "confidence": 0.9,
                "explanation": "Nonsense procedure request (Logic 2: Forbidden Action) -> Expert Refusal"
            }
        # If it's a generic procedure but NO network domain context?
        # e.g. "How to build a house"
        # Only strict if we are sure.
        if not has_network_domain and not has_trouble and not has_procedure_keyword:
             # Weak signal? Check if "Method" word exists
             if "วิธี" in query_lower or "how" in query_lower:
                return {
                    "knowledge_type": KnowledgeType.GENERAL_NETWORK_KNOWLEDGE,
                    "confidence": 0.75,
                    "explanation": "Out-of-domain procedure request (Logic 2: No Network Context) -> Expert Refusal"
                }

    # CASE A: Explicit NT Procedure (Identifier + Procedure Keyword)
    if has_nt_identifier and has_procedure_keyword:
        return {
            "knowledge_type": KnowledgeType.NT_SPECIFIC_PROCEDURE,
            "confidence": 0.95,
            "explanation": "Query contains NT identifier AND procedure keywords"
        }

    # CASE B: Generic Procedure (Procedure Keyword ONLY) -> Treat as GENERAL to trigger Refusal/Explanation
    # Example: "config ONU" (No brand) -> Refuse via Expert Explainer
    if has_procedure_keyword and not has_nt_identifier:
        # Exception: Specific command patterns might not have brand but are obviously commands
        # But generally, "config ..." without context is dangerous/ambiguous.
        # We classify as GENERAL to let Expert Explainer handle the "Refusal w/ Explanation".
        return {
            "knowledge_type": KnowledgeType.GENERAL_NETWORK_KNOWLEDGE,
            "confidence": 0.8,
            "explanation": "Generic procedure request (no NT identifier) -> Routed to Expert Explainer for safe handling"
        }
    
    # CASE C: General Knowledge keywords
    if has_general_keyword:
        return {
            "knowledge_type": KnowledgeType.GENERAL_NETWORK_KNOWLEDGE,
            "confidence": 0.85,
            "explanation": "Query contains definition/explanation/cause keywords"
        }
    
    # Step 4: Intent-based fallback
    if intent == "DEFINE_TERM":
        return {
            "knowledge_type": KnowledgeType.GENERAL_NETWORK_KNOWLEDGE,
            "confidence": 0.8,
            "explanation": "DEFINE_TERM intent suggests general knowledge"
        }
    
    # Step 5: Fail-safe (conservative default)
    
    if intent in ["HOWTO_PROCEDURE", "TROUBLESHOOT"]:
        # If we reached here, it didn't have strong keywords.
        # Default to NT_SPECIFIC as fail-safe for intent match?
        # NO, if intent is HOWTO but no NT identifier, it might be generic.
        # But Intent Router already said it's HOWTO.
        # Let's trust intent but keep confidence lower?
        # Actually, let's Stick to NT_SPECIFIC for safety (Prompt will try to answer based on context).
        return {
            "knowledge_type": KnowledgeType.NT_SPECIFIC_PROCEDURE,
            "confidence": 0.7,
            "explanation": f"{intent} intent suggests specific procedure (fallback)"
        }
    
    # Step 5: Fail-safe (conservative default)
    # When uncertain, default to more restrictive type
    return {
        "knowledge_type": KnowledgeType.NT_SPECIFIC_PROCEDURE,
        "confidence": 0.6,
        "explanation": "Low confidence - defaulting to more restrictive type (NT_SPECIFIC_PROCEDURE)"
    }
