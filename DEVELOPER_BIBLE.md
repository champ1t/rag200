# คู่มือนักพัฒนา (Developer Bible) 💻
**เอกสารเทคนิคและแนวทางการดูแลรักษาระบบ RAG**

---

## 1. สถาปัตยกรรมระบบ (System Architecture) 🏗️

### ภาพรวม (Overview)
โปรเจคนี้คือระบบ **Retrieval-Augmented Generation (RAG)** ที่เน้นความปลอดภัยของข้อมูลโดยประมวลผลภายในองค์กร (Local-first) ประกอบด้วย:
- **ภาษาที่ใช้:** Python 3.11+
- **ฐานข้อมูล (Vector DB):** ChromaDB (ฝังมากับโปรเจค ไม่ต้องรัน Server แยก)
- **สมองกล (LLM):** Ollama (รัน Local) หรือ OpenAI API (ปรับแก้ได้ใน Config)
- **ตัวควบคุมหลัก:** `ChatEngine` (Custom Class ที่เขียนเอง)
- **Frontend/API:** รันผ่าน CLI หรือ API ด้วย FastAPI

### โครงสร้างโฟลเดอร์ (Directory Structure)
```bash
rag_web/
├── src/
│   ├── core/           # หัวใจหลัก
│   │   └── chat_engine.py  # BRAIN: ตัวคุม Flow การทำงานทั้งหมด
│   ├── ingest/         # ท่อส่งข้อมูล (Data Pipeline)
│   │   ├── fetch.py        # ตัวดูดเว็บ (Crawler + Retry logic)
│   │   └── process_one.py  # ตัวล้าง HTML (Important!)
│   ├── vectorstore/    # ตัวติดต่อ Database
│   │   └── chroma.py       # Wrapper สำหรับ ChromaDB
│   ├── directory/      # สมุดโทรศัพท์ (Phone Directory)
│   ├── ai/             # ตัวติดต่อ LLM & Prompts
│   └── api/            # API Server (FastAPI)
├── tests/              # ชุดทดสอบ (Pytest)
├── tools/              # สคริปต์ซ่อมบำรุง
├── data/               # ที่เก็บข้อมูล
│   ├── raw/            # HTML ต้นฉบับ (เก็บไว้ debug)
│   ├── processed/      # JSON ที่ผ่านการล้างแล้ว
│   └── chroma_db/      # ไฟล์ฐานข้อมูล Vector
└── config/             # ไฟล์ตั้งค่า (Config YAMLs)
```

---

## 2. เจาะลึกส่วนประกอบสำคัญ (Key Components) 🧩

### A. สมองของระบบ: `ChatEngine` (`src/core/chat_engine.py`)
คลาสนี้คือ "ผู้จัดการ" ที่คอยสั่งการทุกอย่าง:
1. **แยกแยะเจตนา (Intent):** ดูว่า user ถามเรื่องทั่วไป (`GENERAL`), ถามเบอร์ (`CONTACT`), หรือถามเทคนิค (`TECHNICAL`)
2. **จัดการความจำ (Context):** จำประวัติการคุย 5 ประโยคล่าสุด เพื่อให้คุยต่อเนื่องได้ (เช่น "ขอเบอร์หน่อย"... "แล้วมือถือล่ะ")
3. **แผนการค้นหา (Retrieval):**
   - **Vector Search:** สำหรับเนื้อหาความรู้ (`src/rag/retriever.py`)
   - **Directory Lookup:** สำหรับเบอร์โทรศัพท์ (`src/directory/lookup.py`)
4. **สร้างคำตอบ (Generation):** เอาข้อมูลที่เจอ + คำถาม ส่งให้ LLM เรียบเรียงคำตอบ

### B. ท่อส่งข้อมูล (`src/ingest/`)
**ขั้นตอนการทำงาน:** `Crawl` -> `Save Raw` -> `Process` -> `Vectorize` -> `Store`
- **`fetch.py`:** ทำหน้าที่ดึงหน้าเว็บ (มีระบบเปลี่ยน User-Agent และลองใหม่เมื่อเน็ตหลุด)
- **`process_one.py`:** **สำคัญมาก!** ทำหน้าที่ล้างขยะออกจาก HTML
  - ตัดเมนู (`<nav>`), ฟุตเตอร์, โฆษณา, แถบข้าง
  - **💡 ทริค:** ถ้า Crawler ดูดข้อความขยะมา ให้มาแก้ CSS Selector ในไฟล์นี้

### C. สมุดโทรศัพท์ (`src/directory/`)
**ทำไมต้องแยกออกมา?** เพราะ LLM มักจะจำตัวเลขผิดๆ ถูกๆ เราจึงใช้ **ระบบกฎ (Rules)** แทน:
1. ใช้ Regex ดึงเบอร์โทรจากตาราง HTML ตอนดูดข้อมูล
2. เก็บลงไฟล์ JSON/SQLite แยกต่างหาก
3. เวลาค้นหา จะใช้การเทียบคำ (Keyword Match) แบบเป๊ะๆ (เช่น "RNOC", "Songkhla")
**ผลลัพธ์:** เบอร์โทรแม่นยำ 100% ไม่มีการมั่ว (No Hallucination)

---

## 3. การไหลของข้อมูล & ฐานข้อมูล 💾

### ฐานข้อมูล Vector (ChromaDB)
- **ชื่อ Collection:** ตั้งค่าได้ใน `config.yaml`
- **โครงสร้าง (Schema):**
  - `id`: รหัสก้อนข้อมูล (เช่น `url_hash#ลำดับที่`)
  - `embedding`: ตัวเลขเวกเตอร์ 768 หรือ 1536 มิติ
  - `document`: เนื้อหาข้อความ (Chunk)
  - `metadata`: ข้อมูลกำกับ
    - `url`: ลิงก์ต้นทาง
    - `title`: ชื่อหน้าเว็บ
    - `category`: หมวดหมู่ (ดึงจาก Breadcrumb)

### ที่เก็บไฟล์ (`data/`)
- `data/raw/*.html`: ไฟล์ HTML ดิบ (มีไว้ตรวจสอบว่า Crawler เห็นหน้าเว็บยังไง)
- `data/processed/*.json`: ไฟล์ JSON ที่ล้างสะอาดแล้ว (พร้อมทำ Vector)

---

## 4. คำสั่งที่ใช้บ่อย (Operational Commands) 🛠️

### เริ่มต้นใช้งาน (Quick Start)
```bash
# 1. เข้า Environment
source venv-py311/bin/activate

# 2. รันหน้าแชท (CLI)
python -m src.main chat

# 3. รัน API Server (สำหรับต่อกับหน้าเว็บอื่น/Langflow)
python -m src.api_server
```

### งานซ่อมบำรุง (Maintenance)
**อัปเดตข้อมูลความรู้ (สั่งด้วยมือ):**
```bash
# รันสคริปต์ดูดข้อมูลใหม่
python tools/maintenance/manual_update_knowledge.py
```

**รันชุดทดสอบ (ก่อนแก้โค้ด):**
```bash
# เทสระบบรวม (Integration Tests)
pytest tests/integration/

# เทสจำลองการใช้งานจริง (E2E)
pytest tests/e2e/
```

---

## 5. คู่มือการต่อยอด (Extension Guide) 🚀

### กรณีที่ 1: ต้องการเพิ่มแหล่งข้อมูลใหม่ (เช่น PDF)
1. สร้างไฟล์สคริปต์ใน `src/ingest/pdf_loader.py`
2. ใช้ library `pypdf` หรือ `langchain` ดึงข้อความออกมา
3. จัดรูปแบบให้เป็น JSON เหมือนใน `process_one.py`
4. ใช้คำสั่ง `vectorstore.add_documents()` เพื่อยัดเข้า ChromaDB

### กรณีที่ 2: ต้องการเปลี่ยนโมเดล LLM
แก้ที่ไฟล์ `config/config.yaml`:
```yaml
llm:
  provider: "ollama"  # หรือตัั้งเป็น "openai"
  model: "llama3"     # หรือ "gpt-4-turbo"
  base_url: "http://localhost:11434"
  temperature: 0.3
```

### กรณีที่ 3: ต้องการให้ค้นหาแม่นขึ้น
1. **ปรับขนาด Chunk:** ใน `config.yaml` ลองปรับให้เล็กลง (เช่น 300 ตัวอักษร) สำหรับคำถามที่เจาะจง หรือใหญ่ขึ้น (1000+) สำหรับคำถามสรุปความ
   ```yaml
   chunk:
     size: 500
     overlap: 50
   ```
2. **ค้นหาแบบผสม (Hybrid Search):** แก้ไฟล์ `src/rag/retriever.py` ให้ค้นหาด้วย Keyword (BM25) ร่วมกับ Vector

---

## 6. ปัญหาที่พบบ่อย (Troubleshooting) 🐞

| ปัญหา | สาเหตุ | วิธีแก้ |
|-------|--------|---------|
| **ตอบมั่ว (Hallucination)** | หาข้อมูลไม่เจอ หรือตั้งค่าความมั่นใจต่ำไป | เช็ค `retriever.py` ปรับค่า threshold ให้สูงขึ้น |
| **ดูดข้อมูลไม่เข้า** | หน้าเว็บเปลี่ยนโครงสร้าง | แก้ selector ใน `process_one.py` และเช็ค header ใน `fetch.py` |
| **ตอบช้า** | โมเดล Embedding ใหญ่เกินไป | ลองเปลี่ยนใช้ model ที่เล็กลง หรือปรับ batch size ของ ChromaDB |
| **API Error 500** | ปัญหา Path หรือ Import | เช็ค `sys.path` ใน `api_server.py` หรือเช็ค Environment Variable |

---

**จัดทำโดย:** [ทีมพัฒนา RAG]
**อัปเดตล่าสุด:** กุมภาพันธ์ 2026
