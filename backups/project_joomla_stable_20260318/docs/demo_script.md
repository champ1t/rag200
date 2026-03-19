# Demo Script (5 Minutes)

## Objective
Showcase the **Contact-First Routing** capability, proving that the system provides instant, accurate contact info without hallucination, while maintaining RAG capabilities for general knowledge.

## Scenarios

### 1. Contact Lookup (Person)
**Query**: "เบอร์คุณ เฉลิมรัตน์"
- **Expectation**:
  - **Route**: `contact_lookup`
  - **Result**: Show "คุณ เฉลิมรัตน์ อัศวทรงพล" + Phone numbers + Tags.
  - **Highlight**: Deterministic, fast (<10ms lookup).

### 2. Contact Lookup (Team)
**Query**: "เบอร์ RNOC หาดใหญ่"
- **Expectation**:
  - **Route**: `contact_lookup`
  - **Result**: Show team phone numbers.
  - **Highlight**: Correctly matches team names to numbers.

### 3. Reverse Lookup (Who is this?)
**Query**: "02-575-7222 เป็นของใคร"
**Query**: "02-104-1919" (Test extension)
- **Expectation**:
  - **Route**: `contact_lookup` (Reverse)
  - **Result**: Show Owner Name / Team.
  - **Highlight**: Extension "กด 2" is preserved and displayed.

### 4. RAG Fallback (Knowledge)
**Query**: "RAG คืออะไร" or "เน็ตเสียทำไง"
- **Expectation**:
  - **Route**: `rag`
  - **Result**: Generative answer from LLM.
  - **Highlight**: System correctly identifies this is NOT a contact request and uses the Knowledge Base.

### 5. Guardrail (Not Found)
**Query**: "เบอร์คุณ สมมติ ไม่มีจริง"
- **Expectation**:
  - **Route**: `contact_lookup`
  - **Result**: "ไม่พบข้อมูล... กรุณาระบุชื่อใหม่"
  - **Highlight**: **Does NOT guess** or make up a number.
