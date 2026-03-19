from typing import Dict, List, Any


def format_contact_answer(
    query: str,
    phones: List[str],
    rec: Dict[str, Any] | None,
) -> str:
    """
    Format contact answer in a consistent, production-ready way.
    """
    if not phones or not rec:
        return (
            "ไม่พบข้อมูลการติดต่อจากรายการสมุดโทรศัพท์หน้านี้\n"
            "(ลองพิมพ์ชื่อหน่วยงานหรือชื่อบุคคลให้ใกล้เคียงกับในตาราง)"
        )

    lines: List[str] = []

    # -----------------------------
    # Name
    # -----------------------------
    name = rec.get("name") or query
    lines.append(f"[{name}]")

    # -----------------------------
    # Phones
    # -----------------------------
    if phones:
        # Phase 34 Fix: Deduplicate phones
        uniq_phones = list(dict.fromkeys(phones))
        p_str = ", ".join(uniq_phones)
        lines.append(f"- เบอร์โทร: {p_str}")

    # -----------------------------
    # Faxes (Added)
    # -----------------------------
    faxes = rec.get("faxes")
    if faxes:
        f_str = ", ".join(faxes)
        lines.append(f"- โทรสาร: {f_str}")
    
    # -----------------------------
    # Source
    # -----------------------------
    src = rec.get("source_url")
    if src:
        lines.append(f"- Source: {src}")
    
    # -----------------------------
    # Team → show people (optional)
    # -----------------------------
    people = rec.get("people")
    if people:
        lines.append("- ผู้ติดต่อภายในทีม:")
        for p in people:
            pname = p.get("name", "").strip()
            pphones = ", ".join(p.get("phones", []))
            if pname and pphones:
                lines.append(f"  * {pname}: {pphones}")

    return "\n".join(lines)


def format_field_only(data: Dict[str, Any], field_type: str, entity_name: str) -> str:
    """
    Extract only requested field from structured data (Evidence-Grounded).
    LLM decides output_mode, but this function extracts actual values.
    
    Args:
        data: Structured data (position/contact record)
        field_type: PHONE_ONLY | EMAIL_ONLY | FAX_ONLY | LINK_ONLY | SOURCE_ONLY | NAME_ONLY
        entity_name: Entity name for error messages
        
    Returns:
        Formatted field-only output in Thai
    """
    if field_type == "PHONE_ONLY":
        phones = data.get("phones", [])
        if not phones:
            return f"ไม่พบข้อมูลเบอร์โทรศัพท์ของ {entity_name} ในระบบ"
        return "\n".join([f"- {p}" for p in phones])
    
    elif field_type == "EMAIL_ONLY":
        emails = data.get("emails", [])
        if not emails:
            return f"ไม่พบข้อมูลอีเมลของ {entity_name} ในระบบ"
        return "\n".join([f"- {e}" for e in emails])
    
    elif field_type == "FAX_ONLY":
        faxes = data.get("faxes", [])
        if not faxes:
            return f"ไม่พบข้อมูลโทรสารของ {entity_name} ในระบบ"
        return "\n".join([f"- {f}" for f in faxes])
    
    elif field_type == "LINK_ONLY" or field_type == "SOURCE_ONLY":
        source = data.get("source") or data.get("source_url")
        if not source:
            return f"ไม่พบข้อมูลลิงก์ของ {entity_name} ในระบบ"
        return f"- {source}"
    
    elif field_type == "NAME_ONLY":
        name = data.get("name") or data.get("role")
        if not name:
            return f"ไม่พบข้อมูลชื่อของ {entity_name} ในระบบ"
        return f"- {name}"
    
    else:  # FULL_CARD or unknown
        # Return full formatted answer
        phones = data.get("phones", [])
        return format_contact_answer(entity_name, phones, data)


def format_candidate_list(candidates: List[Dict[str, Any]], max_items: int = 10) -> str:
    """
    Format a list of ambiguous candidates.
    Matches user requirement: List all (up to MAX) if multiple found.
    """
    if not candidates:
        return "ไม่พบข้อมูลที่ระบุเจาะจง"
        
    lines = ["พบข้อมูลที่ใกล้เคียงกันหลายรายการ:"]
    
    for i, c in enumerate(candidates[:max_items]):
        name = c.get("name", "Unknown")
        phones = c.get("phones", [])
        phone_str = ", ".join(phones) if phones else "ไม่มีเบอร์โทร"
        
        # Format: 1) Name (Phone)
        lines.append(f"{i+1}) {name} ({phone_str})")
        
    if len(candidates) > max_items:
        lines.append(f"... และข้อมูลอื่นๆ อีก {len(candidates) - max_items} รายการ")
        
    lines.append("\nพิมพ์หมายเลขหรือชื่อที่ต้องการได้เลยครับ")
    return "\n".join(lines)

