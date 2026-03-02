# Langflow Custom Components - Installation Guide

## การติดตั้ง Custom Components สำหรับใช้ RAG Database

### Component 1: Existing RAG Database
ใช้ Chroma vectorstore ที่มีอยู่แล้ว (ไม่สร้างใหม่)

### Component 2: Full RAG System
ใช้ระบบ RAG ทั้งหมด (Vector + BM25 + Handlers + Router)

---

## Installation Steps

### 1. Copy Component File

**Option A: Copy to Langflow components directory**

```bash
# หา Langflow components directory
python -c "import langflow; print(langflow.__path__[0])"

# หรือใช้ default path
mkdir -p ~/.langflow/components

# Copy component
cp langflow_components/rag_existing_db.py ~/.langflow/components/
```

**Option B: Load from custom path**

```bash
# รัน Langflow with custom components path
langflow run --components-path /opt/rag_web/langflow_components
```

---

### 2. Restart Langflow

```bash
# Stop Langflow (Ctrl+C)
# Start again
langflow run --host 0.0.0.0 --port 7860
```

---

## Component Usage

### Component 1: Existing RAG Database

**Inputs:**
- **Database Path**: `/opt/rag_web/data/vectorstore`
- **Collection Name**: `smc_web` 
- **Query**: ข้อความที่ต้องการค้นหา
- **Top K**: จำนวนผลลัพธ์ (default: 3)

**Outputs:**
- **Search Results**: รายการเอกสารที่พบ (Data[])
- **Vector Store**: Chroma object (สำหรับ chain ต่อ)

**Example Flow:**
```
[Text Input] → [Existing RAG Database] → [Text Output]
```

---

### Component 2: Full RAG System

**Inputs:**
- **RAG System Root**: `/opt/rag_web`
- **Query**: คำถาม
- **Bypass Cache**: ข้าม cache หรือไม่

**Outputs:**
- **Answer**: คำตอบจากระบบ
- **Metadata**: ข้อมูลเพิ่มเติม (route, intent, latency)

**Example Flow:**
```
[Chat Input] → [Full RAG System] → [Chat Output]
```

---

## Advanced: Modify Chroma Component

ถ้าต้องการแก้ built-in Chroma component ให้ใช้ database เดิม:

### 1. หา Chroma Component File

```bash
# หาไฟล์ component
find ~/.langflow -name "*chroma*" -type f
# หรือ
find $(python -c "import langflow; print(langflow.__path__[0])") -name "*chroma*"
```

### 2. แก้ `persist_directory` ให้ชี้ไปที่ database เดิม

เปิดไฟล์ Chroma component แล้วแก้:

```python
# ก่อน:
persist_directory = self.resolve_path(self.persist_directory)

# หลัง:
# Force use existing database
persist_directory = "/opt/rag_web/data/vectorstore"
```

**หรือ** ตั้งค่าผ่าน UI:
- **Persist Directory**: `/opt/rag_web/data/vectorstore`
- **Collection Name**: `smc_web`

---

## Complete Integration Example

### Flow: RAG + Memory + Output

```
┌─────────────┐
│ Chat Input  │
└──────┬──────┘
       │
       ↓
┌──────────────────┐
│ Full RAG System  │
│ (Custom)         │
└──────┬───────────┘
       │
       ↓
┌──────────────┐
│ Chat Memory  │
└──────┬───────┘
       │
       ↓
┌──────────────┐
│ Chat Output  │
└──────────────┘
```

**Configuration:**
1. **Chat Input**: Enable chat mode
2. **Full RAG System**: 
   - RAG Root: `/opt/rag_web`
   - Connect input from Chat Input
3. **Chat Memory**: Store conversation
4. **Chat Output**: Display answer

---

## Testing Components

### Test in Langflow Playground

1. เปิด Langflow: `http://localhost:7860`
2. สร้าง Flow ใหม่
3. ลาก "Full RAG System" component
4. ตั้งค่า inputs:
   - RAG Root: `/opt/rag_web` (หรือพาธที่ถูกต้อง)
5. ใส่ query: "รายชื่อทีมทั้งหมด"
6. กด Run (▶️)

**Expected Output:**
```
ทีมในระบบ (7 ทีม):
- HelpDesk
- FTTx
- Management SMC
...
```

---

## Troubleshooting

### Issue 1: Component ไม่ปรากฏใน Langflow

**Solution:**
```bash
# ตรวจสอบว่าไฟล์อยู่ที่ถูก
ls ~/.langflow/components/rag_existing_db.py

# Restart Langflow
pkill -f langflow
langflow run
```

---

### Issue 2: Import Error

**Error:** `ModuleNotFoundError: No module named 'src.chat_engine'`

**Solution:**
- ตรวจสอบ `RAG System Root` path ถูกต้อง
- ตรวจสอบ `sys.path` ใน component code

---

### Issue 3: Database Not Found

**Error:** `Database path not found: ...`

**Solution:**
```bash
# ตรวจสอบ path
ls -la /opt/rag_web/data/vectorstore/

# แก้ path ใน component:
Database Path: /opt/rag_web/data/vectorstore
```

---

## Production Tips

### 1. Pre-load Engine

แก้ component ให้ pre-load engine ตอน Langflow start:

```python
# ใน __init__ หรือ global scope
_GLOBAL_ENGINE = None

def _get_engine():
    global _GLOBAL_ENGINE
    if _GLOBAL_ENGINE is None:
        # Load once
        _GLOBAL_ENGINE = ChatEngine(config)
    return _GLOBAL_ENGINE
```

### 2. Enable Caching

Langflow มี built-in caching - enable ใน settings

### 3. Monitor Performance

```python
# เพิ่ม logging ใน component
import time
t_start = time.time()
result = engine.process(query)
latency = (time.time() - t_start) * 1000
self.log(f"Query processed in {latency:.2f}ms")
```

---

## Alternative: API-Only Method

ถ้าไม่ต้องการ custom component ใช้ API แทน:

### Flow with HTTP Request:
```
[Chat Input] → [HTTP Request] → [Parse JSON] → [Output]
                    ↓
            POST http://localhost:8000/query
            Body: {"query": "{input}"}
```

**ข้อดี:**
- ไม่ต้องแก้ Langflow components
- แยก concerns (RAG API vs Langflow)
- Scale ได้ง่าย

**ข้อเสีย:**
- Network latency
- ต้องรัน 2 services (API + Langflow)

---

## Summary

| Method | Pros | Cons |
|--------|------|------|
| **Custom Component** | Direct access, Fast | Must modify Langflow |
| **API Endpoint** | Clean separation | Extra latency |
| **Modify Built-in Chroma** | Use existing UI | Breaks updates |

**แนะนำ**: ใช้ **Full RAG System component** สำหรับ production
