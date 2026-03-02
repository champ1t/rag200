"""
retrieval_filter.py — Intent-Aware Retrieval Reranker (v2)

Purpose:
    Reorder vector search hits so that articles compatible with the
    query intent are prioritized BEFORE incompatible ones.

Design principles:
    - Does NOT modify hit.score (preserves threshold logic downstream)
    - Does NOT drop any hits (no hard filtering — only reordering)
    - Falls back to original order on any error (safe by default)
    - Classifies article type from BOTH title AND chunk text (.text field)

Usage:
    from src.core.retrieval_filter import apply_intent_filter
    hits = vs.hybrid_query(q, top_k=10)
    hits = apply_intent_filter(hits, intent="TROUBLESHOOT", query=q)
"""
from typing import List, Optional


# ─── Article Type Inference ────────────────────────────────────────────────────

_TITLE_PATTERNS = {
    "TROUBLESHOOT": [
        "troubleshoot", "ปัญหา", "error", "fail", "fault",
        "แก้ไข", "แก้ปัญหา", "ขัดข้อง", "debug", "อาการ",
        "ไม่ทำงาน", "ไม่ได้", "ไม่ขึ้น", "ล่ม", "หลุด",
        "ข้อจำกัด", "limitation",  # บทความ constraint มักมี troubleshoot content
    ],
    "COMMAND": [
        "command", "commandline", "คำสั่ง", "cmd", "cli",
        "show ", "display ",
    ],
    "CONFIG": [
        "config", "configure", "configuration", "setup",
        "ตั้งค่า", "กำหนดค่า", "คู่มือ", "การตั้งค่า",
        "installation", "install",
    ],
    "HOWTO": [
        "วิธี", "ขั้นตอน", "how to", "how-to", "howto",
        "procedure", "guide", "step",
    ],
    "OVERVIEW": [
        "overview", "introduction", "คืออะไร",
        "architecture", "topology", "spec ",
    ],
    "PROTOCOL": [
        "bgp", "ospf", "isis", "mpls", "vlan", "vxlan", "evpn",
    ],
}

# Additional TEXT-level signals — 1st 300 chars of chunk content
_TEXT_SIGNALS = {
    "TROUBLESHOOT": [
        "แก้ปัญหา", "ปัญหาคือ", "ปัญหา", "แก้ isis", "แก้ ecmp",
        "error", "fail", "ขัดข้อง", "ตรวจสอบ", "debug",
        "ไม่ทำงาน", "ไม่ขึ้น", "log จะหาย",
    ],
    "COMMAND": [
        "คำสั่ง", "display ", "show ", "undo ", "commit",
        "interface ", "ip address", "set ", "นำ command",
    ],
    "CONFIG": [
        "ตั้งค่า", "configuration", "กำหนดค่า",
        "configure", "enable", "vlan id", "bridge",
    ],
    "HOWTO": [
        "วิธีการ", "ขั้นตอนที่", "ขั้นตอน", "how to",
        "step 1", "ทำการ",
    ],
}


def infer_article_type(title: str, text: str = "") -> str:
    """
    Classify an article's type from its title and optional chunk text.

    Priority: TROUBLESHOOT > COMMAND > CONFIG > HOWTO > PROTOCOL > OVERVIEW > UNKNOWN.
    Text signals add weight but title match still takes priority.
    """
    combined = f"{title} {text[:400]}".lower()

    # Score each type based on keyword matches in combined
    scores = {t: 0 for t in _TITLE_PATTERNS}

    # Title signals (weight 3)
    t_lower = title.lower()
    for atype, kws in _TITLE_PATTERNS.items():
        for kw in kws:
            if kw in t_lower:
                scores[atype] += 3

    # Text signals (weight 1)
    txt_lower = text[:400].lower()
    for atype, kws in _TEXT_SIGNALS.items():
        for kw in kws:
            if kw in txt_lower:
                scores[atype] += 1

    # Return the highest-scoring type, with priority tiebreaking
    priority = ["TROUBLESHOOT", "COMMAND", "CONFIG", "HOWTO", "PROTOCOL", "OVERVIEW"]
    best_type = "UNKNOWN"
    best_score = 0
    for atype in priority:
        if scores[atype] > best_score:
            best_score = scores[atype]
            best_type = atype

    return best_type


# ─── Intent → Compatible Article Types (Boost Table) ──────────────────────────

_BOOST_TABLE = {
    "TROUBLESHOOT": {
        "TROUBLESHOOT": 2.0,
        "HOWTO":        1.3,
        "CONFIG":       1.0,
        "COMMAND":      0.85,
        "PROTOCOL":     0.75,
        "OVERVIEW":     0.6,
        "UNKNOWN":      0.9,
    },
    "COMMAND": {
        "COMMAND":      2.0,
        "CONFIG":       1.4,
        "HOWTO":        1.1,
        "TROUBLESHOOT": 0.85,
        "PROTOCOL":     1.0,
        "OVERVIEW":     0.7,
        "UNKNOWN":      0.9,
    },
    "CONFIG": {
        "CONFIG":       2.0,
        "HOWTO":        1.6,
        "COMMAND":      1.3,
        "TROUBLESHOOT": 1.0,
        "PROTOCOL":     0.9,
        "OVERVIEW":     0.7,
        "UNKNOWN":      0.9,
    },
    "HOWTO": {
        "HOWTO":        2.0,
        "CONFIG":       1.8,
        "COMMAND":      1.3,
        "TROUBLESHOOT": 1.1,
        "PROTOCOL":     0.9,
        "OVERVIEW":     0.7,
        "UNKNOWN":      0.9,
    },
    "HOWTO_PROCEDURE": {
        "HOWTO":        2.0,
        "CONFIG":       1.8,
        "COMMAND":      1.3,
        "TROUBLESHOOT": 1.1,
        "PROTOCOL":     0.9,
        "OVERVIEW":     0.7,
        "UNKNOWN":      0.9,
    },
    "PROTOCOL": {
        "PROTOCOL":     2.0,
        "CONFIG":       1.4,
        "COMMAND":      1.2,
        "OVERVIEW":     1.1,
        "HOWTO":        1.0,
        "TROUBLESHOOT": 0.9,
        "UNKNOWN":      0.9,
    },
    "OVERVIEW": {
        "OVERVIEW":     2.0,
        "PROTOCOL":     1.3,
        "CONFIG":       1.0,
        "HOWTO":        0.9,
        "COMMAND":      0.8,
        "TROUBLESHOOT": 0.7,
        "UNKNOWN":      0.9,
    },
}


# ─── Main Filter Function ──────────────────────────────────────────────────────

def apply_intent_filter(hits: list, intent: str, query: str = "", debug: bool = True) -> list:
    """
    Reorder vector search hits to prioritize intent-compatible articles.

    Args:
        hits:   List of VectorStore hit objects (each has .score, .metadata, .text)
        intent: Classified query intent e.g. "TROUBLESHOOT", "COMMAND", "HOWTO"
        query:  Original query string (used for query-token bonus)
        debug:  Print debug info to stdout

    Returns:
        Reordered list of the same hits (no drops, no score modification).
        If intent unknown or error occurs, original order is returned.
    """
    if not hits:
        return hits

    boost_map = _BOOST_TABLE.get(intent)
    if not boost_map:
        if debug:
            print(f"[RetrievalFilter] Unknown intent '{intent}' — no reranking")
        return hits

    # Query tokens for bonus scoring
    q_tokens = set(query.lower().split())

    try:
        scored = []
        for h in hits:
            meta   = h.metadata or {}
            title  = meta.get("title", "")
            text   = getattr(h, "text", "") or ""

            art_type = infer_article_type(title, text)
            boost    = boost_map.get(art_type, 1.0)

            # Query-token bonus: if title contains a query token, +5% boost
            title_l = title.lower()
            token_bonus = 1.05 if any(t in title_l for t in q_tokens if len(t) > 2) else 1.0

            composite = h.score * boost * token_bonus

            if debug:
                print(
                    f"[RetrievalFilter] '{title[:35]}' "
                    f"type={art_type} boost={boost:.1f} orig={h.score:.3f} "
                    f"token={token_bonus:.2f} → {composite:.3f}"
                )
            scored.append((composite, h))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [h for _, h in scored]

    except Exception as e:
        print(f"[RetrievalFilter] Error: {e} — using original order")
        return hits


def classify_title(title: str, text: str = "") -> str:
    """Public alias for infer_article_type."""
    return infer_article_type(title, text)
