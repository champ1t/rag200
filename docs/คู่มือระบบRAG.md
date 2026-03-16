# คู่มือระบบ RAG (Retrieval-Augmented Generation)
# ระบบผู้ช่วยค้นหาข้อมูลอัจฉริยะ — บริษัท NT

> **เวอร์ชัน:** 1.0.0 | **อัปเดตล่าสุด:** 2026-03-13
> **สถานะ:** Production Ready

---

## สารบัญ

1. [ภาพรวมระบบ](#1-ภาพรวมระบบ)
2. [สถาปัตยกรรมระบบ](#2-สถาปัตยกรรมระบบ)
3. [การติดตั้งครั้งแรก](#3-การติดตั้งครั้งแรก)
4. [การตั้งค่าระบบ](#4-การตั้งค่าระบบ)
5. [การรันระบบ](#5-การรันระบบ)
6. [การอัปเดตข้อมูล](#6-การอัปเดตข้อมูล)
7. [โครงสร้างข้อมูล](#7-โครงสร้างข้อมูล)
8. [API Reference](#8-api-reference)
9. [การเชื่อมต่อ Langflow](#9-การเชื่อมต่อ-langflow)
10. [การ Deploy ไปเครื่อง Production](#10-การ-deploy-ไปเครื่อง-production)
11. [การบำรุงรักษาและ Monitoring](#11-การบำรุงรักษาและ-monitoring)
12. [Troubleshooting](#12-troubleshooting)
13. [การปรับแต่งขั้นสูง](#13-การปรับแต่งขั้นสูง)
14. [กรณีเปลี่ยนแหล่งข้อมูล](#14-กรณีเปลี่ยนแหล่งข้อมูล)
15. [คำสั่ง Cheatsheet](#15-คำสั่ง-cheatsheet)

---

## 1. ภาพรวมระบบ

### 1.1 ระบบนี้คืออะไร?

ระบบ RAG (Retrieval-Augmented Generation) คือ **ผู้ช่วยค้นหาข้อมูลอัจฉริยะ** สำหรับองค์กร ที่สามารถ:

1. **อ่านและจดจำ** ข้อมูลจากเว็บไซต์ภายในองค์กร (SMC Intranet) ได้ทั้งหมด
2. **เข้าใจคำถามภาษาไทย** ทั้งคำถามปลายเปิดและคำศัพท์เทคนิคเฉพาะทาง
3. **ตอบคำถามอัตโนมัติ** พร้อมอ้างอิงแหล่งที่มา ไม่มั่วหรือแต่งเรื่อง

### 1.2 ความสามารถหลัก

| ประเภทคำถาม | ตัวอย่าง | วิธีตอบ |
|---|---|---|
| ค้นหาเบอร์ติดต่อ | "ขอเบอร์ OMC หาดใหญ่" | ค้นจาก Directory ตรงๆ แม่นยำ 100% |
| ค้นหาบทความเทคนิค | "Config ZTE OLT C6xx" | ส่งลิงก์ตรงไปยังบทความ |
| ค้นหาวิธีการ | "การกำหนดค่า ONU ทำยังไง" | สรุปหรือส่งลิงก์คู่มือ |
| คำถามเชิงหลักการ | "NMS ทำงานอย่างไร" | ใช้ RAG + LLM อธิบาย |
| สนทนาต่อเนื่อง | "แล้วของ RNOC หล่ะ?" | จำบริบทเดิมไว้ ตอบถูกต้อง |

### 1.3 ข้อมูลที่ระบบรู้จัก (ณ วันที่ Deploy)

- **145** หน้าเว็บจาก SMC Intranet
- **4,370** ลิงก์เชื่อมโยงภายใน
- **~197,000** คำเนื้อหาที่สกัดออกมา
- **2.1 ล้าน** ตัวอักษรรวม
- **52** ตำแหน่งงาน (positions.jsonl)
- **63** รายชื่อ directory (directory.jsonl)
- **2 ค่า** score_threshold: retrieval=0.2 / rag=0.15
- **chunk_size: 700** ตัวอักษรต่อ chunk, overlap 100

---

## 2. สถาปัตยกรรมระบบ

### 2.1 ภาพรวม Architecture

```
ผู้ใช้ (Langflow UI)
        │
        ↓ HTTP POST /query
┌─────────────────────────────┐
│       FastAPI Server         │  :8000
│       api_server.py          │
└──────────────┬──────────────┘
               │
               ↓
┌─────────────────────────────┐
│        Chat Engine           │
│     core/chat_engine.py      │
│                              │
│  1. Query Normalization      │
│  2. Intent Detection         │
│  3. Entity Bypass / Noise    │
│  4. Governance & Routing     │
│  5. Retrieval (BM25 + Vec)   │
│  6. LLM Summarization        │
│  7. Context Memory           │
└──────────────┬──────────────┘
               │
    ┌──────────┼──────────┐
    ↓          ↓          ↓
[BM25 Index] [Vector DB] [Records]
[bm25_index] [chroma_db] [contacts]
    .json                  .jsonl
```

### 2.2 Tech Stack

| Component | เทคโนโลยี | รายละเอียด |
|---|---|---|
| Backend (API) | FastAPI + Uvicorn | Python 3.11 |
| LLM (สมองกล) | Ollama llama3.2:3b | รันแบบ Local ไม่ส่งออก Internet |
| Keyword Search | BM25 | ค้นหาคำศัพท์ เฉพาะทาง |
| Semantic Search | SentenceTransformer | paraphrase-multilingual-MiniLM-L12-v2 |
| Vector DB | ChromaDB | เก็บ embedding vectors |
| UI/Frontend | Langflow | Visual flow builder |
| Web Scraper | BeautifulSoup4 | ดึงข้อมูล SMC Joomla |

### 2.3 โครงสร้างโฟลเดอร์หลัก

```
rag_web/
├── configs/
│   └── config.yaml               ← ตั้งค่าหลักทุกอย่าง (แก้ที่นี่ที่เดียว)
├── data/
│   ├── aliases.json              ← ชื่อย่อ/ชื่อเล่น อุปกรณ์
│   ├── state.json                ← บันทึก URL ที่ index แล้ว
│   ├── bm25_index.json           ← BM25 Keyword Index (auto)
│   ├── knowledge_packs.json      ← Knowledge Facts สำเร็จรูป
│   ├── metrics.csv               ← Log ทุก request
│   ├── records/                  ← ฐานข้อมูลผู้ติดต่อ (.jsonl)
│   ├── sessions/                 ← ประวัติสนทนาแต่ละ session
│   ├── processed/                ← JSON บทความที่ crawl แล้ว
│   └── vectorstore/              ← ChromaDB files
├── src/
│   ├── api_server.py             ← FastAPI endpoints
│   ├── core/chat_engine.py       ← หัวสมองหลัก (อย่าแก้ถ้าไม่จำเป็น)
│   ├── ai/                       ← LLM, Normalizer, Router
│   ├── context/                  ← Context Memory Management
│   ├── ingest/                   ← Web Crawler & Parser
│   ├── rag/                      ← RAG Logic & Article Interpreter
│   ├── vectorstore/              ← ChromaDB + BM25 Wrapper
│   └── directory/                ← ระบบค้นหาผู้ติดต่อ
├── scripts/
│   ├── sync_incremental.py       ← อัปเดตข้อมูลแบบ incremental
│   └── swap_collection.py        ← Rebuild ฐานข้อมูลใหม่ทั้งหมด
├── docs/                         ← เอกสารทั้งหมด (รวมไฟล์นี้)
├── tests/                        ← ชุดทดสอบ
├── setup.sh                      ← Script ติดตั้งครั้งแรก
└── requirements.txt              ← Python dependencies
```

---

## 3. การติดตั้งครั้งแรก

### 3.1 ความต้องการของระบบ (System Requirements)

| รายการ | ขั้นต่ำ | แนะนำ |
|---|---|---|
| OS | macOS 12+ / Ubuntu 20.04+ | macOS 14+ / Ubuntu 22.04 |
| Python | 3.9+ | 3.11.x |
| RAM | 8 GB | 16 GB |
| Storage | 10 GB ว่าง | 20 GB ว่าง |
| เครือข่าย | เชื่อม NT Intranet ได้ | VPN หรือในออฟฟิศ |

### 3.2 ขั้นตอนติดตั้ง

**ขั้นที่ 1 — Clone โปรเจกต์**
```bash
git clone https://github.com/champ1t/Internal_RAG.git
cd Internal_RAG
```

**ขั้นที่ 2 — รัน Setup Script (อัตโนมัติ)**
```bash
chmod +x setup.sh
./setup.sh
```

Script จะทำทุกอย่างให้:
1. ตรวจสอบ Python 3.9+
2. สร้าง virtual environment (`venv/`)
3. ติดตั้ง dependencies ทั้งหมด
4. สร้าง `configs/config.yaml` จาก template
5. ติดตั้ง Ollama + download model `llama3.2:3b`
6. Crawl เว็บ SMC และสร้าง Vector Database

**Options เพิ่มเติม:**
```bash
./setup.sh --skip-crawl   # ข้าม crawl (ทำเองทีหลัง)
./setup.sh --no-ollama    # ข้าม Ollama (ติดตั้งแล้ว)
```

### 3.3 สิ่งที่ต้องทำเองก่อน Setup เสร็จ

**ก. ตั้งค่า config.yaml**
```yaml
# configs/config.yaml
web:
  domain: "10.192.133.33"          # IP ของเว็บ SMC
  start_urls:
    - "http://10.192.133.33/smc"   # URL เริ่มต้น crawl

llm:
  model: llama3.2:3b               # model ที่ใช้

api:
  api_key: "your-secret-key"       # API Key สำหรับ /query endpoint
```

**ข. สร้างข้อมูลผู้ติดต่อ**
```bash
cp data/records/directory.example.jsonl data/records/directory.jsonl
cp data/records/teams.example.jsonl     data/records/teams.jsonl
cp data/records/positions.example.jsonl data/records/positions.jsonl
```
แก้ไขไฟล์ทั้ง 3 ให้มีข้อมูลจริงขององค์กร (ดูโครงสร้างในหัวข้อ 7)

### 3.4 ติดตั้งบน Linux

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements_linux.txt
playwright install
```

---

## 4. การตั้งค่าระบบ

### 4.1 ไฟล์ configs/config.yaml (ตั้งค่าหลัก)

> **หมายเหตุ:** นี่คือโครงสร้างจริงของ config.yaml — ตรวจสอบจากไฟล์จริงแล้ว

```yaml
# ตั้งค่าโปรเจกต์
project:
  name: rag_web
  env: production           # dev / production

# ความปลอดภัย
security:
  allow_credential_redirect: true
  credential_redirect_mode: "redirect_only"

# การ Crawl เว็บ
web:
  domain: "10.192.133.33"       # IP ของเว็บ SMC
  start_urls:
    - "http://10.192.133.33/smc"
  crawl_depth: 3                # ความลึก (3 = ครอบคลุมบทความส่วนใหญ่)
  rate_limit_sec: 0.3           # หน่วงเวลาระหว่างดึงหน้า
  max_pages: 300                # จำกัด crawler ไม่ให้หลงทาง
  allowed_paths:
    - "/smc"                    # เก็บเฉพาะ path นี้
  deny_extensions:              # ไม่ดึงไฟล์ประเภทเหล่านี้
    - ".pdf"
    - ".png"
    - ".jpg"
    - ".docx"
    - ".xlsx"

# การแบ่ง Text เป็น Chunk
chunk:
  chunk_size: 700               # ตัวอักษรต่อ chunk (แนะนำ 500-800)
  overlap: 100                  # ส่วนทับซ้อนระหว่าง chunk

# การค้นหา
retrieval:
  top_k: 3                     # ดึงผลลัพธ์กี่ชิ้น
  score_threshold: 0.2         # ตัดผลที่ score ต่ำกว่านี้

# RAG Logic
rag:
  latency_logging: true
  score_threshold: 0.15        # Threshold รอบที่ 2 (ต่ำกว่า retrieval)

# Vector Database (ChromaDB)
vectorstore:
  type: chroma
  persist_dir: data/vectorstore
  collection_name: smc_web
  embedding_model: sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2

# LLM (Ollama Local)
llm:
  provider: ollama
  model: "llama3.2:3b"         # เปลี่ยน model ที่นี่
  fast_model: "llama3.2:3b"
  base_url: "http://localhost:11434"
  temperature: 0.2
  max_context_chars: 2500      # จำกัดเพื่อลด latency
  timeout_sec: 300

# พฤติกรรม Chat
chat:
  show_context: false
  save_log: true
  language: th
  mode: production             # debug / production

# UX / Formatting
ux:
  enable_formatting: true
  direct_content_preview: true
  max_nav_links: 5

# Escalation (เมื่อ AI ตอบไม่ได้)
escalation:
  contact_phone: "02-XXX-XXXX"          # แก้เป็นเบอร์จริง
  contact_email: "support@example.com" # แก้เป็น email จริง
  auto_trigger_after_failures: 3

# Runtime
runtime:
  runs_dir: results/runs
  log_level: INFO

# Ingest
ingest:
  save_raw_html: true
  save_clean_text: true
```

**หลังแก้ config ต้อง Restart:**
```bash
pkill -f uvicorn
uvicorn src.api_server:app --host 0.0.0.0 --port 8000 --reload
```

### 4.2 ไฟล์ data/aliases.json (ชื่อย่ออุปกรณ์)

ใช้ให้ระบบเข้าใจว่า `ne8000` = `huawei ne8000` = `huawei netengine 8000`

```json
{
  "ne8000": ["huawei ne8000", "huawei netengine 8000", "ne 8000"],
  "olt":    ["olt c300", "olt c320", "c6xx", "zte olt"],
  "bras":   ["bras", "broadband remote access server"]
}
```

ถ้าต้องการเพิ่ม alias ใหม่:
1. เปิดไฟล์ `data/aliases.json`
2. เพิ่มบรรทัดตามรูปแบบ
3. Restart ระบบ (โหลดตอน startup)

---

## 5. การรันระบบ

### 5.1 รันทั้งระบบ (การใช้งานปกติ)

```bash
# เข้าโฟลเดอร์โปรเจกต์และเปิด Virtual Environment
cd ~/Documents/NT/RAG/rag_web
source venv/bin/activate

# เปิด API Server
uvicorn src.api_server:app --host 0.0.0.0 --port 8000 --reload

# เปิด Langflow (Terminal อีกหน้าต่าง)
export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES && langflow run
```

### 5.2 การทดสอบด้วย Terminal (Debug Mode)

```bash
python3 -m src.main chat
```
พิมพ์คำถามและกด Enter ระบบจะแสดง Debug Log ทุกขั้นตอน

### 5.3 ตรวจสอบสถานะระบบ

```bash
# Health Check
curl http://localhost:8000/health

# Ready Check (ระบบโหลดข้อมูลครบไหม)
curl http://localhost:8000/ready
```

**ผลลัพธ์ที่ถูกต้อง:**
```json
{"status": "healthy", "version": "1.0.0"}
```

---

## 6. การอัปเดตข้อมูล

> **⚠️ หมายเหตุ:** ต้องเชื่อมต่อเครือข่าย NT (ออฟฟิศหรือ VPN) ถึงจะเชื่อมเว็บ SMC ได้

### 6.1 อัปเดตเฉพาะหน้าที่เปลี่ยน (แนะนำ — ใช้บ่อย)

```bash
# ดูก่อนว่าจะมีอะไรเปลี่ยนบ้าง (ไม่แตะ DB)
python scripts/sync_incremental.py --dry-run

# รันจริง
python scripts/sync_incremental.py
```

**ผลลัพธ์:**

| ข้อความ | ความหมาย |
|---|---|
| `[UPDATED]` | หน้านี้เนื้อหาเปลี่ยน → อัปเดต DB แล้ว |
| `[SKIP]` | หน้านี้เนื้อหาเดิม → ข้ามไม่ทำอะไร |
| `[ERROR]` | เข้าหน้านั้นไม่ได้ (timeout) |

### 6.2 อัปเดตเฉพาะหน้าที่ระบุ

```bash
python scripts/sync_incremental.py \
  --target-url "http://10.192.133.33/smc/index.php?option=com_content&view=article&id=570"
```

### 6.3 Rebuild ฐานข้อมูลใหม่ทั้งหมด (เดือนละครั้ง)

Script นี้สร้างถังใหม่แยก ทดสอบ แล้วค่อยสลับ — **ระบบหลักไม่หยุด**

```bash
# ทำครบอัตโนมัติ (สร้าง → ทดสอบ → สลับ)
python scripts/swap_collection.py

# ทำทีละขั้น
python scripts/swap_collection.py --build-only   # แค่สร้างถังใหม่
python scripts/swap_collection.py --test-only    # แค่ทดสอบ
python scripts/swap_collection.py --swap-only    # แค่สลับถัง
python scripts/swap_collection.py --rollback     # คืนกลับถังเก่า
```

**Restart API หลังสลับถัง:**
```bash
pkill -f uvicorn
uvicorn src.api_server:app --host 0.0.0.0 --port 8000 --reload
```

### 6.4 บังคับ Re-index หน้าเดียว

```bash
python3 -c "
import json
state = json.load(open('data/state.json'))
url = 'http://10.192.133.33/smc/index.php?...'
state['pages'].pop(url, None)
json.dump(state, open('data/state.json','w'), ensure_ascii=False, indent=2)
print('Done')
"
python scripts/sync_incremental.py --target-url "http://..."
```

---

## 7. โครงสร้างข้อมูล

> **สำคัญ:** โครงสร้างด้านล่างคือ format จริงจากไฟล์ `*.example.jsonl` ในระบบ

### 7.1 data/records/directory.jsonl — รายชื่อบุคคลพร้อมเบอร์โทร

แต่ละ record คือข้อมูลของ **ทีม** พร้อม **สมาชิก (members array)**:
```json
{
  "team": "Network Operations Center (NOC)",
  "members": [
    {
      "name": "นายสมชาย ใจดี (ชาย)",
      "phones": ["0-7425-0685 #101", "0-7424-0089"],
      "emails": ["somchai@company.co.th"]
    },
    {
      "name": "นางสาวสมหญิง รักงาน (หญิง)",
      "phones": ["0-7425-0685 #102"],
      "emails": []
    }
  ],
  "sources": ["http://10.192.133.33/smc/index.php?option=com_content&view=article&id=59"]
}
```

### 7.2 data/records/teams.jsonl — สมาชิกทีม (รูปแบบย่อ)

รูปแบบย่อของ teams สำหรับ lookup เร็ว:
```json
{
  "team": "NOC",
  "members": [
    {"name": "นายสมชาย ใจดี (ชาย)", "phones": ["0-7425-0685 #101"], "emails": []}
  ],
  "sources": ["http://10.192.133.33/smc/..."]
}
```

### 7.3 data/records/positions.jsonl — ตำแหน่งงาน

แต่ละ record คือข้อมูลของ **ตำแหน่งหนึ่ง** พร้อมชื่อผู้ดำรงตำแหน่ง:
```json
{
  "role": "Network Supervisor",
  "name": "นายสมชาย ใจดี (ชาย)",
  "source": "http://10.192.133.33/smc/...",
  "phones": ["0-7425-0685 #101", "0-7424-0089"],
  "emails": ["somchai@company.co.th"]
}
```

**วิธีแก้ไขข้อมูลผู้ติดต่อ:**
1. เปิดไฟล์ `.jsonl` ที่ต้องการ (แต่ละบรรทัด = 1 record)
2. แก้ไขตาม format โดยเฉพาะ `phones` ต้องเป็น **array** `["เบอร์1", "เบอร์2"]`
3. **ไม่ต้อง Restart** — ระบบโหลดเมื่อมีการถาม

### 7.4 data/processed/*.json — บทความที่ประมวลผลแล้ว

```json
{
  "url": "http://10.192.133.33/smc/index.php?...",
  "title": "มาตรฐาน 5ส.",
  "text": "เนื้อหาบทความ...",
  "content_type": "general",
  "links": [{"text": "ลิงก์", "href": "http://..."}],
  "processed_at": 1740000000.0
}
```

### 7.5 data/sessions/*.json — ประวัติสนทนา

```json
{
  "session_id": "user-abc",
  "history": [
    {"role": "user", "content": "ขอเบอร์ OMC", "timestamp": "..."},
    {"role": "assistant", "content": "...", "timestamp": "..."}
  ],
  "last_intent": "CONTACT_LOOKUP"
}
```

**ล้าง session ทั้งหมด:**
```bash
rm data/sessions/*.json
```

---

## 8. API Reference

> ดู Swagger UI แบบ interactive ได้ที่: `http://localhost:8000/docs`

### 8.1 POST /query — ถามคำถาม (Endpoint หลัก)

**Request body:**
```json
{
  "query": "ขอเบอร์ OMC หาดใหญ่",
  "session_id": "user-001",
  "bypass_cache": false
}
```
- `session_id` — ถ้าไม่ส่ง ระบบใช้ session เดียวกันหมด (เสี่ยง context bleeding)
- `bypass_cache` — `true` เพื่อบังคับค้นหาใหม่ข้าม cache

**Response:**
```json
{
  "answer": "ศูนย์ OMC หาดใหญ่\n- เบอร์โทร: 074-251-135",
  "route": "contact_hit_contact_book_fuzzy",
  "latency_ms": 45.2,
  "sources": ["http://10.192.133.33/smc/..."],
  "metadata": {
    "intent": "CONTACT_LOOKUP",
    "latencies": {"routing": 5.1, "vs": 30.2, "llm": 0.0}
  }
}
```

**CURL ตัวอย่าง:**
```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "ขอเบอร์ OMC หาดใหญ่", "session_id": "user-001"}'
```

### 8.2 GET /health — ตรวจสุขภาพระบบ

```bash
curl http://localhost:8000/health
```
**Response จริง:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "teams_count": 7,
  "positions_count": 52
}
```
- `teams_count` — จำนวนทีมที่โหลดจาก teams.jsonl
- `positions_count` — จำนวนตำแหน่งที่โหลดจาก positions.jsonl

### 8.3 GET /teams — ดูรายชื่อทีมทั้งหมด

```bash
curl http://localhost:8000/teams
# → {"teams": ["FTTx", "HelpDesk", "NOC", ...], "count": 7}
```

### 8.4 GET /stats — สถิติระบบ (สำหรับ Dashboard)

```bash
curl http://localhost:8000/stats
```
คืน: จำนวนทีม, positions, สถานะ vector store, recent queries 10 รายการล่าสุด

### 8.5 GET /dashboard — หน้า Monitoring Dashboard

เปิดเบราว์เซอร์: `http://localhost:8000/dashboard`
(ให้ไฟล์ `src/api/static/dashboard.html`)

### 8.6 POST /escalate — ขอความช่วยเหลือจากคน

```bash
curl -X POST "http://localhost:8000/escalate?session_id=user-001"
```
คืน: ข้อมูลการติดต่อ support ของ NT ตามที่ตั้งใน `escalation` section ของ config.yaml

### 8.7 POST /feedback — บันทึก Feedback

```bash
curl -X POST http://localhost:8000/feedback \
  -H "Content-Type: application/json" \
  -d '{
    "query_id": "abc123",
    "session_id": "user-001",
    "query": "ขอเบอร์ OMC",
    "answer": "074-251-135",
    "rating": "like",
    "comment": ""
  }'
```
- `rating`: `"like"` หรือ `"dislike"
- บันทึกลงที่ `logs/`

### 8.8 GET /feedback/stats — สถิติ Feedback

```bash
curl http://localhost:8000/feedback/stats
# → สถิติรวม like/dislike
```

### 8.9 GET /docs — Swagger UI

เปิดเบราว์เซอร์: `http://localhost:8000/docs`

---

## 9. การเชื่อมต่อ Langflow

### 9.1 รัน Langflow

```bash
export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES && langflow run
```
เปิดเบราว์เซอร์: `http://localhost:7860`

### 9.2 สร้าง Flow เชื่อมต่อ RAG API

1. เปิด Langflow → **New Flow** → เลือก "Blank"
2. ลาก **Chat Input** → **API Request** → **Chat Output**

**ตั้งค่า API Request Component:**

| ฟิลด์ | ค่า |
|---|---|
| URL | `http://localhost:8000/query` |
| Method | `POST` |
| Headers | `{"Content-Type": "application/json"}` |
| Body | `{"query": "{input_value}", "session_id": "{session_id}"}` |
| Response Path | `answer` |

### 9.3 การส่ง session_id จาก Langflow

เพื่อป้องกัน Context Bleeding ระหว่าง conversation ต่าง session:

ใน Langflow ให้เชื่อมต่อ `Chat Input` node → `session_id` output → ไปยัง Body ของ API Request ดังนี้:
```json
{
  "query": "{input_value}",
  "session_id": "{session_id}"
}
```

---

## 10. การ Deploy ไปเครื่อง Production

### 10.1 Checklist ก่อน Deploy

**ข้อมูล (Data)**
- [ ] `data/bm25_index.json` (ขนาด > 0)
- [ ] `data/vectorstore/` (มี chroma.sqlite3)
- [ ] `data/records/directory.jsonl`
- [ ] `data/records/teams.jsonl`
- [ ] `data/records/positions.jsonl`
- [ ] `data/knowledge_packs.json`

**การตั้งค่า (Config)**
- [ ] `configs/config.yaml` (ตรวจ LLM endpoint)
- [ ] API key ตั้งค่าแล้ว
- [ ] Port settings ถูกต้อง

**Dependencies**
- [ ] Python 3.9+
- [ ] Ollama ติดตั้งแล้ว
- [ ] `ollama pull llama3.2:3b` รันแล้ว

### 10.2 สร้าง Package และย้ายไฟล์

```bash
# สร้าง deployment package
tar -czf rag_data_$(date +%Y%m%d).tar.gz \
  data/bm25_index.json \
  data/vectorstore/ \
  data/records/ \
  data/knowledge_packs.json \
  configs/config.yaml

# ส่งไปเครื่อง production
rsync -avz --progress rag_data_*.tar.gz user@production-server:/opt/rag_web/backups/
```

### 10.3 ติดตั้งบนเครื่อง Production

```bash
ssh user@production-server
cd /opt/rag_web

# Extract
tar -xzf backups/rag_data_YYYYMMDD.tar.gz

# Setup venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# ทดสอบ
python3 -m src.main chat

# รัน API
uvicorn src.api_server:app --host 0.0.0.0 --port 8000
```

### 10.4 รันเป็น systemd Service (Linux Production)

สร้างไฟล์ `/etc/systemd/system/rag-api.service`:
```ini
[Unit]
Description=RAG API Server
After=network.target

[Service]
Type=simple
User=raguser
WorkingDirectory=/opt/rag_web
Environment="PATH=/opt/rag_web/venv/bin"
ExecStart=/opt/rag_web/venv/bin/uvicorn src.api_server:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable rag-api
sudo systemctl start rag-api
sudo systemctl status rag-api
```

### 10.5 Rollback Plan

```bash
# Restore จาก backup
cd /opt/rag_web
rm -rf data/vectorstore
tar -xzf backups/rag_data_PREVIOUS.tar.gz
sudo systemctl restart rag-api
```

---

## 11. การบำรุงรักษาและ Monitoring

### 11.1 ดู Log Request

```bash
# ดู Log ล่าสุด
tail -20 data/metrics.csv

# คำถามที่ตอบช้าสุด 10 อันดับ
sort -t',' -k5 -rn data/metrics.csv | head -11

# Route ที่ใช้บ่อยสุด
cut -d',' -f4 data/metrics.csv | sort | uniq -c | sort -rn
```

### 11.2 ตรวจสอบ Vector Database

```bash
python3 -c "
import sys; sys.path.insert(0,'.')
import yaml
from src.vectorstore.chroma import ChromaVectorStore
cfg = yaml.safe_load(open('configs/config.yaml'))
vs = ChromaVectorStore(
    persist_dir='data/vectorstore',
    collection_name=cfg['vectorstore']['collection_name'],
    embedding_model=cfg['vectorstore']['embedding_model'],
    bm25_path='data/bm25_index.json'
)
print(f'Total documents: {vs.collection.count()}')
"
```

### 11.3 Backup

```bash
# Backup Vector DB
cp -r data/vectorstore data/vectorstore_backup_$(date +%Y%m%d)
cp data/state.json data/state_backup_$(date +%Y%m%d).json
cp data/bm25_index.json data/bm25_backup_$(date +%Y%m%d).json
```

### 11.4 ตรวจสอบ Ollama

```bash
# ดูว่า Ollama รันอยู่ไหม
curl http://localhost:11434/api/tags

# ดู models ที่มี
ollama list

# รัน Ollama ถ้าไม่ได้รัน
ollama serve &

# ดาวน์โหลด model ใหม่
ollama pull llama3.2:3b
```

### 11.5 ตารางการบำรุงรักษา

| งาน | ความถี่ | คำสั่ง |
|---|---|---|
| อัปเดตข้อมูล SMC | ทุกครั้งที่ SMC อัปเดต | `python scripts/sync_incremental.py` |
| Rebuild ฐานข้อมูล | เดือนละครั้ง | `python scripts/swap_collection.py` |
| Backup ข้อมูล | สัปดาห์ละครั้ง | ดูหัวข้อ 11.3 |
| ตรวจ Log ผิดปกติ | สัปดาห์ละครั้ง | `tail -50 data/metrics.csv` |
| ตรวจ Disk Space | เดือนละครั้ง | `du -sh data/` |

---

## 12. Troubleshooting

### 12.1 ตารางปัญหาและวิธีแก้

| ปัญหา | สาเหตุที่เป็นไปได้ | วิธีแก้ |
|---|---|---|
| `ModuleNotFoundError` | ยังไม่ได้ activate venv | `source venv/bin/activate` |
| `Connection refused` เวลา query | API ไม่ได้รัน | `uvicorn src.api_server:app --port 8000 --reload` |
| Ollama ไม่ตอบ | Ollama ไม่ได้รัน | `ollama serve &` |
| ระบบ crawl ไม่ได้ | ไม่ได้อยู่ใน NT Network | เชื่อม VPN หรือเข้าออฟฟิศ |
| Score = 0 ทุกคำถาม | ยังไม่มีข้อมูลใน DB | `python scripts/sync_incremental.py` |
| `Address already in use` | Port 8000 ถูกใช้อยู่ | `lsof -ti:8000 \| xargs kill -9` |
| ตอบผิดหน่วยงาน | Context Bleeding | ล้าง session: `rm data/sessions/*.json` |
| Langflow เชื่อม API ไม่ได้ | IP/Port ผิด | ตรวจสอบ URL ใน API Request component |

### 12.2 การ Rollback ด้วย Git

```bash
# ดู tags ที่มี
git tag -l

# ย้อนกลับไป tag ที่ต้องการ
git checkout freeze-2026-03-02-pre-sync-test

# กลับมา branch หลัก
git checkout public-release
```

---

## 13. การปรับแต่งขั้นสูง

### 13.1 ตาราง "อยากแก้อะไร แก้ที่ไหน"

| สิ่งที่อยากเปลี่ยน | ไฟล์ที่ต้องแก้ |
|---|---|
| เปลี่ยน LLM model | `configs/config.yaml` → `llm.model` |
| เพิ่ม alias อุปกรณ์ | `data/aliases.json` |
| เปลี่ยน score threshold | `configs/config.yaml` → `retrieval.score_threshold` |
| เพิ่มผู้ติดต่อใหม่ | `data/records/*.jsonl` |
| เพิ่มหน้าเว็บใหม่ | `python scripts/sync_incremental.py --target-url "..."` |
| แก้วิธีดึงข้อมูลจากเว็บ | `src/ingest/fetch.py` |
| แก้วิธีโชว์คำตอบ | `src/ai/response_generator.py` |
| เปลี่ยนวิธีตัดสิน intent | `src/ai/router.py` |
| เพิ่มกฎ routing | `src/core/chat_engine.py` (ระวัง — ไฟล์หลัก) |

### 13.2 เปลี่ยน LLM Model

```yaml
# configs/config.yaml
llm:
  provider: ollama
  model: llama3.2:3b      # เปลี่ยนตรงนี้
  base_url: http://localhost:11434
```

รองรับ:
- `ollama` (Local — แนะนำ)
- `openai` (ต้องมี API key)
- `azure` (Azure OpenAI)

### 13.3 ปรับ Retrieval

```yaml
# configs/config.yaml
retrieval:
  top_k: 3           # เพิ่มเป็น 5 ถ้าต้องการ context มากขึ้น
  score_threshold: 0.2  # ลดถ้าต้องการ recall สูงขึ้น
```

---

## 14. กรณีเปลี่ยนแหล่งข้อมูล

ถ้าต้องการเปลี่ยนจาก SMC (Joomla) ไปใช้เว็บอื่น:

### 14.1 สิ่งที่ต้องแก้ (3 จุด)

**จุดที่ 1: src/ingest/fetch.py — CSS Selector**
```python
# เดิม (Joomla/SMC)
content_div = soup.find("div", class_="article-content")
title = soup.find("h2", class_="article-title")

# ใหม่ (WordPress)
content_div = soup.find("div", class_="entry-content")
title = soup.find("h1", class_="entry-title")
```

**จุดที่ 2: configs/config.yaml — URL**
```yaml
web:
  domain: "new-website.com"
  start_urls:
    - "http://new-website.com/path"
```

**จุดที่ 3: src/rag/article_interpreter.py — Junk Keywords**
```python
# เพิ่ม keyword ขยะของ CMS ใหม่
if any(k in stripped for k in [
    "เขียนโดย", "Posted by", "Filed under", "Leave a Comment",
]):
    continue
```

### 14.2 สิ่งที่ไม่ต้องแก้

✅ Vector Search, BM25, RAG logic
✅ LLM, Governance Rules
✅ Chat Engine, API Server
✅ Intent Router, Entity Detector

### 14.3 ประมาณการเวลา

| งาน | เวลา |
|---|---|
| ปรับโค้ด fetch.py + Junk Filter | 1-2 วัน |
| Re-crawl + สร้าง processed cache | 1-2 วัน |
| ทดสอบและปรับ threshold | 1 วัน |
| **รวม** | **3-5 วันทำงาน** |

---

## 15. คำสั่ง Cheatsheet

### เตรียมก่อนใช้งาน (ทุกครั้ง)
```bash
cd ~/Documents/NT/RAG/rag_web
source venv/bin/activate
```

### รันระบบ
```bash
uvicorn src.api_server:app --host 0.0.0.0 --port 8000 --reload  # API Server
export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES && langflow run   # Langflow UI
python3 -m src.main chat                                          # Debug Terminal
```

### อัปเดตข้อมูล
```bash
python scripts/sync_incremental.py --dry-run   # ดูก่อน (ไม่แตะ DB)
python scripts/sync_incremental.py             # อัปเดตจริง
python scripts/swap_collection.py              # Rebuild ทั้งหมด
python scripts/swap_collection.py --rollback   # คืนถังเก่า
```

### ทดสอบ
```bash
curl http://localhost:8000/health
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -H "X-API-Key: nt-rag-secret" \
  -d '{"query": "ขอเบอร์ OMC หาดใหญ่", "session_id": "test-001"}'
python3 -m pytest tests/ -v
```

### Git
```bash
git status && git log --oneline -5
git add -A && git commit -m "message"
git push origin public-release:refs/heads/main
git tag "freeze-YYYY-MM-DD-description" && git push origin --tags
```

### Backup
```bash
cp -r data/vectorstore data/vectorstore_backup_$(date +%Y%m%d)
cp data/bm25_index.json data/bm25_backup_$(date +%Y%m%d).json
```

### Ollama
```bash
ollama list          # ดู models
ollama serve &       # รัน Ollama
ollama pull llama3.2:3b  # ดาวน์โหลด model
```

---

*คู่มือนี้จัดทำโดย: โครงการพัฒนาระบบ Internal RAG สำหรับ NT*
*เวอร์ชัน: 1.0.0 | วันที่: 2026-03-13*
