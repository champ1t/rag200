# RAG Project Master Guide 📘
**คู่มือฉบับสมบูรณ์: ระบบค้นหาข้อมูลองค์กรอัจฉริยะ (Enterprise RAG System)**

---

## ส่วนที่ 1: สำหรับผู้บริหารและคนทั่วไป (Non-Technical) 👔
*อธิบายหลักการทำงานแบบเข้าใจง่าย ไม่ลงลึกเรื่องโค้ด*

### 1.1 ภาพรวม: ระบบนี้คืออะไร?
ลองจินตนาการว่าเรามี **"บรรณารักษ์อัจฉริยะ"** ประจำองค์กร ที่:
1. **อ่านหนังสือทุกเล่ม** ในห้องสมุด (เว็บ Knowledge Base, คู่มือ PDF, ข้อมูลเบอร์โทร) จนจำได้ทุกตัวอักษร
2. **เข้าใจภาษาคน** ไม่ใช่แค่หาคำเหมือน (Keyword) แต่เข้าใจ "ความหมาย" (Semantic)
3. **ตอบคำถามได้ทันที** พร้อมบอกด้วยว่าเอาข้อมูลมาจากหน้าไหน

ระบบ RAG (Retrieval-Augmented Generation) คือการสร้างบรรณารักษ์คนนี้ขึ้นมาด้วย AI ครับ

### 1.2 การทำงาน 4 ขั้นตอน (The 4-Step Process)

#### ขั้นตอนที่ 1: การเก็บรวบรวมข้อมูล (Ingestion) 📥
*เปรียบเหมือน: บรรณารักษ์เดินเก็บหนังสือเข้าชั้น*
- **สิ่งที่ทำ:** ระบบจะส่ง "หุ่นยนต์เล็กๆ" (Crawler) วิ่งไปตามหน้าเว็บภายในองค์กร (Intranet)
- **เก็บอะไร:** เก็บข้อความ (Text), รูปภาพ, ตาราง, และเบอร์โทรศัพท์
- **ความฉลาด:**
  - แยกแยะได้ว่าอันไหนเป็น "เนื้อหา" อันไหนเป็น "เมนูขยะ"
  - ถ้าเจอ "ตารางเบอร์โทร" จะรู้วิธีแปลงให้ค้นหาได้ง่าย (เช่น "เบอร์พี่เอ แผนก IT")

#### ขั้นตอนที่ 2: การจดจำและจัดระเบียบ (Indexing) 🧠
*เปรียบเหมือน: การทำดัชนีและย่อความ*
- **ย่อยข้อมูล:** ข้อมูลยาวๆ จะถูกหั่นเป็นชิ้นย่อยๆ (Chunks) เพื่อให้จำแม่น
- **แปลงเป็นคณิตศาสตร์ (Embedding):** แปลงข้อความให้เป็น "รหัสตัวเลข" (Vector)
  - *เช่น:* คำว่า "เน็ตหลุด" กับ "Internet Down" จะถูกแปลงเป็นรหัสที่ **ใกล้เคียงกัน** (เพราะความหมายเดียวกัน)
- **เก็บเข้าสมอง (Vector DB):** บันทึกรหัสทั้งหมดลงฐานข้อมูลพิเศษ เพื่อให้ค้นหาได้ในเสี้ยววินาที

#### ขั้นตอนที่ 3: การค้นหาคำตอบ (Retrieval) 🔍
*เปรียบเหมือน: เมื่อมีคนเดินมาถาม*
- **User ถาม:** "เน็ตที่หาดใหญ่ใช้ไม่ได้ ต้องโทรหาใคร?"
- **ระบบคิด:** แปลงคำถามเป็นรหัสตัวเลข แล้ววิ่งไปเทียบกับรหัสในสมอง
- **ผลลัพธ์:** ดึงข้อมูลที่เกี่ยวข้องที่สุด 5-10 อันออกมา (เช่น เบอร์ติดต่อทีมหาดใหญ่, วิธีแก้เบื้องต้น)

#### ขั้นตอนที่ 4: การเรียบเรียงคำตอบ (Generation) 💬
*เปรียบเหมือน: การพูดตอบกลับ*
- **AI ประมวลผล:** ส่งข้อมูลที่เจอ + คำถาม ให้ AI (LLM - Large Language Model)
- **คำสั่งกำกับ:** "จงตอบคำถามนี้ โดยใช้ข้อมูลที่หามาได้เท่านั้น ห้ามมั่ว และแนบลิงก์ที่มาด้วย"
- **User ได้รับ:** "หากอินเทอร์เน็ตที่หาดใหญ่ขัดข้อง สามารถติดต่อศูนย์ RNOC หาดใหญ่ ได้ที่เบอร์ 074-xxxxxx ครับ (อ้างอิง: [สมุดโทรศัพท์ภาคใต้])"

---

## ส่วนที่ 2: สำหรับนักพัฒนา (Developer Guide) 💻
*คู่มือเชิงลึกสำหรับ Dev ที่จะมารับงานต่อ*

### 2.1 สถาปัตยกรรมระบบ (System Architecture)
Project Structure ถูกจัดระเบียบตามมาตรฐาน (Clean Architecture) ดังนี้:

```
rag_web/
├── src/
│   ├── core/           # หัวใจหลัก (ChatEngine) ควบคุม Flow ทั้งหมด
│   ├── ingest/         # Crawler & Parser (BeautifulSoup, Logic ตัด noise)
│   ├── vectorstore/    # ChromaDB integration (เก็บ Vectors)
│   ├── ai/             # Logic ฝั่ง AI (LLM Client, Prompt Templates)
│   ├── rag/            # RAG Logic (Retriever, Re-ranker)
│   └── directory/      # ระบบสมุดโทรศัพท์ (Phone Directory Logic)
├── tests/              # ชุดทดสอบ (Integration, E2E)
├── tools/              # Scripts สำหรับ Maintain ระบบ
└── data/               # ที่เก็บไฟล์ Raw HTML และ Vector DB (Local)
```

### 2.2 Tech Stack 🛠️
- **Language:** Python 3.11.14 (Stable Version)
- **LLM:** Ollama (Local LLM) หรือ OpenAI API (Configurable)
- **Vector DB:** ChromaDB (ฝังในโปรเจค ไม่ต้องรัน Server แยก)
- **Web App:** HTML/CSS (Jinja2 Templates) หรือ Integrate ผ่าน API (FastAPI)

### 2.3 จุดที่ Dev ต้องรู้ (Key Components)

#### A. ระบบดูดข้อมูล (Ingestion Pipeline)
- **Code:** `src/ingest/`
- **Logic:**
  - `fetch.py`: ดึง HTML (รองรับ Retry, Timeout)
  - `process_one.py`: ตัด Header/Footer/Sidebar ออก (ใช้ Heuristic Rules)
  - **การแก้ไข:** ถ้าเว็บต้นทางเปลี่ยนหน้าตา ให้แก้ Selector ในไฟล์นี้

#### B. ระบบสมองกล (Chat Engine)
- **Code:** `src/core/chat_engine.py` (Class `ChatEngine`)
- **หน้าที่:** เป็น Orchestrator รับ Input -> เรียก Retriever -> เรียก LLM -> ส่ง Output
- **Flow สำคัญ:**
  1. **User Intent:** เช็คเจตนา (ถามเบอร์? ถามวิธี? ทักทาย?)
  2. **Retrieve:** ค้น ChromaDB
  3. **Context Check:** เช็คประวัติการคุย (เช่น ถ้าถามต่อว่า "แล้วเบอร์มือถือละ")
  4. **Generate:** ส่ง Prompt ให้ LLM ตอบ

#### C. การจัดการเบอร์โทร (Directory System)
- **Code:** `src/directory/`
- **ความพิเศษ:** เบอร์โทรเป็นข้อมูล structured ที่ต้องแม่นยำ 100% (ห้าม Hallucinate)
- **Logic:** เราไม่ใช้ Vector Search กับเบอร์โทร แต่ใช้ **Regex & Key-Value Lookup** เพื่อความชัวร์

### 2.4 แนวทางการพัฒนาต่อ (Future Roadmap) 🚀

#### 1. การเพิ่มแหล่งข้อมูลใหม่ (Add New Source)
- **วิธีทำ:** เขียน Script ใน `tools/` เพื่อดึงข้อมูล API หรือ Scrape เว็บใหม่
- **Format:** แปลงข้อมูลให้อยู่ในรูป `Document(text, metadata)` แล้วโยนเข้า `ingest` pipeline เดิมได้เลย

#### 2. การเปลี่ยนโมเดล AI (Swap LLM)
- **วิธีทำ:** แก้ config ใน `config.yaml`
- **จุดแก้:** เปลี่ยน `base_url` และ `model_name` (รองรับ Ollama, OpenAI, Azure)

#### 3. การจูนความแม่นยำ (Fine-tuning Retrieval)
- **วิธีทำ:** ปรับค่า `chunk_size` และ `overlap` ใน `config.yaml`
- **Advance:** แก้ logic ใน `src/rag/retriever.py` เพื่อเพิ่ม algorithm เช่น Hybrid Search (Keyword + Vector)

#### 4. การ Scale ระบบ (Scaling Up)
- **ปัจจุบัน:** Run Local (SQLite base)
- **อนาคต:** ย้าย ChromaDB ไปเป็น Server Mode หรือใช้ Pinecone/Weaviate รองรับข้อมูลระดับล้าน records
- **Deployment:** จับใส่ Docker Container (มี `Dockerfile` เตรียมไว้ให้แล้ว หรือเขียนเพิ่มได้ง่ายมาก)

---

### 📥 คำแนะนำสุดท้ายสำหรับ Dev ใหม่
1. **เริ่มที่ Tests:** ลองรัน `pytest tests/integration/` เพื่อดูว่าระบบทำงานถูกต้องไหมก่อนแก้โค้ด
2. **อย่ากลัว Log:** ระบบนี้ Log ละเอียดมากอยู่ที่ `.archive/validation_logs/` ใช้ debug ได้ทุก step
3. **โครงสร้างสำคัญ:** `src/core/chat_engine.py` คือไฟล์ที่สำคัญที่สุด ศึกษา flow ของมันให้ดี

หวังว่าคู่มือนี้จะเป็นแผนที่นำทางให้ทั้งผู้ใช้งานและนักพัฒนา ต่อยอดระบบนี้ให้ดียิ่งขึ้นไปอีกครับ! ✨
