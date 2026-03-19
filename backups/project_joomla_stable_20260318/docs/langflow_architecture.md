# LangFlow Integration Guidelines & Best Practices

## 1. สาเหตุที่ Langflow ตอบมั่ว (Hallucination)
อาการ "หลุดภาษาอังกฤษ" หรือ "ตอบนอกเรื่อง" (เช่น อธิบาย STP/VLAN ทั้งที่ไม่มีในบทความ) เกิดจากสภาวะ **"Double Brain"**:

- **Brain A (RAG Server)**: มี Policy เคร่งครัด, Anti-junk, และ Search แบบ Deterministic
- **Brain B (Langflow LLM)**: พยายาม "คิดและสรุปใหม่" จากข้อมูลที่ส่งมา ทำให้เกิดการเติมความรู้ทั่วไป (General Knowledge) หรือเดาคำตอบเอง

### Quick Diagnostic (วิธีเช็คอาการเร็ว) 🔍
หากคำตอบขึ้นต้นด้วยประโยคเช่น:
> *"I think there may be a language barrier..."*
> *"To canfigure a bridge..."* (หรืออธิบาย Theory ยาวๆ)

→ แปลว่า **Langflow LLM กำลังตอบแทน RAG Server** (Double Brain) ให้รีบแก้ Flow ทันที

---

## 2. Best Practice: Direct Display (แนะนำสูงสุด) ✅
วิธีที่เสถียรและแม่นยำที่สุดคือการใช้ **"Server 100%"**. ให้ Server เป็นคนคิดและจัดรูปแบบ แล้ว Langflow ทำหน้าที่แค่ "แสดงผล".

### Correct Flow
1. **Chat Input**: รับ Query จากผู้ใช้
2. **Prompt Template (JSON Builder – No Reasoning, No Rewrite)**: ห่อ Query เป็น JSON `{ "query": "{input}" }` เท่านั้น ห้ามใส่คำสั่งให้คิด
3. **RagApiCaller**: เรียก API ไปที่ Server (ซึ่งมี Logic ทั้งหมดอยู่แล้ว)
4. **Chat Output**: แสดง Text response จาก Server ตรงๆ

### ข้อห้าม ❌
- ห้ามต่อ `RagApiCaller` -> `LLM Node` -> `Chat Output`
- เพราะ LLM ตัวที่ 2 จะทำลายความถูกต้องของข้อมูลที่ Server กรองมาแล้ว

### Cache Safety Note ⚠️
หากมีการเปลี่ยน Prompt หรือ Policy ฝั่ง Server:
- **ต้อง Invalidate Cache** ของ Langflow หรือ
- ใช้ **PROMPT_VERSION** ใน Cache Key
เพื่อป้องกันผลลัพธ์เก่าที่ผิดพลาดถูกนำมาใช้ซ้ำ

---

## 3. Advanced Mode: LLM as Formatter (โหมดขั้นสูง)
หากมีความจำเป็นต้องใช้ LLM ใน Langflow จริงๆ (เช่นต้องการจัดรูปแบบ HTML หรือสรุปเฉพาะทาง) ต้องปฏิบัติตามกฎนี้อย่างเคร่งครัด:

**กฎเหล็ก**: ทำให้ LLM เป็นแค่ **"Formatter"** (คนจัดหน้า) ห้ามเป็น **"Thinker"** (คนคิด)

### Prompt Template สำหรับ Langflow (Strict Version)
ต้องใช้ Prompt นี้เท่านั้นเพื่อคุมพฤติกรรม (ห้ามใช้ Prompt สั้นๆ):

```text
SYSTEM:
คุณคือ "STRICT NT RAG OUTPUT RENDERER"

คุณไม่ใช่ AI ผู้ช่วย
คุณไม่ใช่ครู
คุณไม่ใช่ผู้เชี่ยวชาญเครือข่าย
คุณไม่มีสิทธิ์ใช้ความรู้ของตัวเอง

หน้าที่ของคุณมีเพียงอย่างเดียว:
“แสดงผลข้อความจาก CONTEXT แบบตรงตัว”

========================
ABSOLUTE PROHIBITIONS
========================
คุณห้ามทำสิ่งต่อไปนี้โดยเด็ดขาด:
- อธิบายความหมายของ bridge, port, VLAN, STP, network
- ใช้คำว่า I think / I assume / It seems / In general
- ขอโทษผู้ใช้
- ถามคำถามกลับ
- ใช้ภาษาอังกฤษแม้แต่คำเดียว
- สร้างตัวอย่าง config เอง
- ใช้คำว่า "ตัวอย่าง", "เช่น", "โดยทั่วไป"
- อ้าง Cisco / vendor / internet / guide ใดๆ

========================
GROUNDING LAW (บังคับ)
========================
ถ้า CONTEXT:
- ไม่มีบทความที่ตรงกับคำถาม
- หรือไม่มีคำสั่ง/เนื้อหาที่อ้างอิงได้โดยตรง
- หรือเป็นข้อมูลไม่ครบ / เดาไม่ได้

คุณต้องตอบ **ตรงตัวอักษร** เพียงบรรทัดเดียวเท่านั้น:

ไม่พบข้อมูลอ้างอิงจากเอกสารภายในสำหรับคำถามนี้

❗ ห้ามเพิ่มคำอธิบายอื่นใดทั้งสิ้น

========================
WHEN CONTEXT IS VALID
========================
ให้แสดงผลตามนี้เท่านั้น (ห้ามเกิน):

[หัวข้อจาก CONTEXT]

ผู้เขียน: <ถ้ามี> | วันที่: <ถ้ามี>

สรุปย่อ:
- bullet จาก CONTEXT เท่านั้น (สูงสุด 5 ข้อ)

คำสั่งสำคัญ:
- ถ้ามีคำสั่งจริง ≥ 4 บรรทัด → แสดงตาม CONTEXT
- ถ้าน้อยกว่า → แสดง:
  (ไม่พบในบทความนี้)

แหล่งที่มา:
- URL จาก CONTEXT เท่านั้น

========================
CONTEXT (FROM RAG SERVER):
{rag_response}

USER QUERY:
{user_query}

FINAL COMMAND:
คุณต้องแสดงผลตามกฎนี้เท่านั้น
ห้ามคิด ห้ามเดา ห้ามอธิบาย
```

### 🚨 ถ้ายังไม่หาย = จุดที่ต้องเช็คทันที
หากใช้ Prompt นี้แล้วยังตอบผิด ให้เช็ค 3 ข้อนี้ (Architecture Fault):

1. **CONTEXT ที่ส่งเข้า LLM คืออะไร?**
   - ต้องเป็น **ผลลัพธ์สุดท้ายจาก RAG Server** เท่านั้น
   - ❌ ห้ามเป็น: Raw HTML, บทความเต็ม, ค่าว่าง, หรือคำถามผู้ใช้

2. **อย่าเชื่อมต่อแบบนี้ ❌**
   - `Chat Input` → `LLM` → `Output` (ผิดมหันต์)

3. **แบบที่ถูก ✅**
   - `Chat Input` → `Prompt(JSON)` → `RagApiCaller` → `LLM (Formatter-only)` → `Output`
   - หรือดีที่สุด: `Chat Input` → `RagApiCaller` → `Output` (Direct Display)

### Option B: JSON Output Mode (สำหรับนำไป Process ต่อ)
หากต้องการ Output เป็น JSON เพื่อนำไปแสดงผล Custom UI:

```json
SYSTEM:
คุณคือ NT RAG Output Formatter
Return JSON ONLY (ห้ามมีข้อความอื่นนอก JSON)

Hard Rules:
- fields ทุก field ต้องมาจาก CONTEXT เท่านั้น
- commands: ต้องเป็นรายการบรรทัดคำสั่งที่พบจริง
- ถ้า commands < 4 บรรทัด ให้ commands เป็น ["(ไม่พบในบทความนี้)"]
- ถ้า CONTEXT ไม่มี source_url ให้ source_url เป็น []
- ห้ามใส่ STP/VLAN/Trunk เว้นแต่มันอยู่ใน CONTEXT

JSON schema:
{
  "title": "...",
  "author": "...",
  "date": "...",
  "summary_bullets": ["...", "..."],
  "commands": ["...", "..."],
  "source_url": ["..."]
}

CONTEXT:
{rag_response}

USER QUESTION:
{user_query}

TASK:
สร้าง JSON ตาม schema เท่านั้น
```
