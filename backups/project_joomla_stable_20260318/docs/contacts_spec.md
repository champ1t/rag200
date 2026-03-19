# Contact Data Specification

This document defines the "Definition of Done" for the Contact Data Category. It serves as the single source of truth for format support, conflict resolution, and not-found policies.

## 1. Supported Phone Formats
The system MUST parse and standardize the following Thai phone number formats:

| Type | Format | Example |
|------|--------|---------|
| **Mobile** | `0xx-xxx-xxxx` | `081-234-5678` |
| **Landline (BKK)** | `02-xxx-xxxx` | `02-575-7222` |
| **Landline (Provincial)** | `0xx-xxx-xxxx` | `074-251-135` |
| **Internal / IP Phone** | Raw digits preserved (if >= 4 chars) | `575-7222`, `2104-1919` |
| **Extensions** | `... กด X`, `... ต่อ X`, `... ext X` | `02-123-4567 กด 2` |

**Validation Rules:**
- Mobile numbers MUST have 10 digits.
- Landline numbers (starting with 02, 03, 04, 05, 07) MUST have 9 digits.
- Numbers not matching these lengths are discarded as invalid/junk.

## 2. Conflict Resolution Policy
When a phone number matches multiple records (Team vs Person, or Multiple People), the system MUST:

1.  **Prioritize Person over Team**: If a Person match is found, verify if it's the specific person asked for.
2.  **Reverse Lookup (Who owns this number?)**:
    - Return **ALL** entities associated with that number.
    - **Format**:
        ```text
        [Number]
        - [Person Name 1] ([Team 1])
        - [Person Name 2] ([Team 2])
        - [Team Name]
        ```
    - **Rationale**: In organizations, one number often maps to a team or is shared by multiple staff. Showing all context is safer than guessing one.

## 3. Not Found Policy
If the routing logic determines the user is asking for a contact, but no record is found in `directory.jsonl`:

1.  **Response**:
    > "ไม่พบข้อมูลการติดต่อของ '[Query]' ในสมุดโทรศัพท์"
    > "กรุณาระบุชื่อหน่วยงาน, ชื่อบุคคล หรือคำค้นหาให้ถูกต้อง/ชัดเจนขึ้น"
2.  **Guardrail**:
    - **DO NOT** fallback to Vector Search/LLM guessing for generating a phone number.
    - **DO NOT** hallucinate a number based on similar-sounding names.
    - **EXCEPTION**: If the query implies asking for "How to contact" generally (e.g., "process to contact HR"), and not a specific number lookup, it MAY fall back to RAG for procedural answers (e.g., "Walk to building A").

## 4. Routing Logic
The system applies **Contact-First Routing**:

1.  **Is it a Phone Number?** (Digits >= 4) -> **Reverse Lookup**.
2.  **Does it contain Contact Keywords?** (`เบอร์`, `โทร`, `ติดต่อ`, `Internal`) **AND** matches a Directory Name? -> **Name Lookup**.
3.  **Strict Guardrail**: If keywords exist (`เบอร์...`) but NO Directory Match -> **STOP & REPORT NOT FOUND**. Do not pass to RAG.
