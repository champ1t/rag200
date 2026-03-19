# คู่มือติดตั้งและใช้งาน — RAG System

> อัปเดตล่าสุด: 2026-03-04

---

## ติดตั้งครั้งแรก (เครื่องใหม่)

### ขั้นที่ 1 — Clone โปรเจกต์
```bash
git clone https://github.com/champ1t/Internal_RAG.git
cd Internal_RAG
```

### ขั้นที่ 2 — รัน Setup Script
```bash
chmod +x setup.sh
./setup.sh
```

Script จะทำให้อัตโนมัติ:
1. ตรวจสอบ Python 3.9+
2. สร้าง virtual environment (`venv/`)
3. ติดตั้ง dependencies ทั้งหมด
4. สร้าง `configs/config.yaml` จาก template
5. ติดตั้ง Ollama และ download model
6. Crawl เว็บและสร้าง Vector Database

---

## Options ของ setup.sh

```bash
./setup.sh                # ทำทุกอย่าง (แนะนำสำหรับครั้งแรก)
./setup.sh --skip-crawl   # ข้าม crawl (ทำเองทีหลัง)
./setup.sh --no-ollama    # ข้าม Ollama (ถ้าติดตั้งแล้ว)
```

---

## ⚠️ สิ่งที่ต้องทำเองก่อน setup สำเร็จ

### 1. ตั้งค่า config.yaml
Script จะถามให้แก้ บรรทัดที่ต้องแก้:
```yaml
# configs/config.yaml
web:
  domain: "10.x.x.x"              # ← IP หรือ domain ของเว็บที่ต้องการ crawl
  start_urls:
    - "http://10.x.x.x/path"      # ← URL เริ่มต้น

llm:
  model: llama3.2:3b               # ← เปลี่ยนถ้าใช้ model อื่น

api:
  api_key: "your-secret-key"       # ← ตั้งค่า API key สำหรับ /chat endpoint
```

### 2. สร้างข้อมูลผู้ติดต่อ
คัดลอกจาก example แล้วแก้เป็นข้อมูลจริง:
```bash
cp data/records/directory.example.jsonl data/records/directory.jsonl
cp data/records/teams.example.jsonl     data/records/teams.jsonl
cp data/records/positions.example.jsonl data/records/positions.jsonl
```

แก้ไขไฟล์ให้ตรงกับองค์กร (ดูโครงสร้างใน `*.example.jsonl`)

### 3. ต้องอยู่ในเครือข่ายที่เข้าถึงเว็บ target ได้
- ถ้าเว็บอยู่ใน Intranet → ต้องอยู่ในออฟฟิศหรือ VPN
- ถ้าเว็บเป็น Public URL → ใช้ได้ทั่วไป

---

## รันระบบ (หลัง setup)

```bash
source venv/bin/activate

# เปิด API Server
uvicorn src.api_server:app --host 0.0.0.0 --port 8000 --reload
```

ทดสอบ:
```bash
# Health check
curl http://localhost:8000/health

# ถามคำถาม
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-secret-key" \
  -d '{"query": "คำถามของคุณ", "session_id": "test-001"}'
```

---

## อัปเดตข้อมูล (ใช้งานประจำ)

```bash
source venv/bin/activate

# ดูว่ามีอะไรเปลี่ยนบนเว็บบ้าง (ไม่แตะ DB)
python scripts/sync_incremental.py --dry-run

# อัปเดตจริง
python scripts/sync_incremental.py

# อัปเดตแค่หน้าเดียว
python scripts/sync_incremental.py --target-url "http://..."
```

---

## Troubleshooting

| ปัญหา | แนวทางแก้ |
|---|---|
| `ModuleNotFoundError` | `source venv/bin/activate` แล้วรันใหม่ |
| `Connection refused` เวลา query | ตรวจสอบว่า uvicorn รันอยู่ |
| Ollama ไม่ตอบ | `ollama serve` แล้ว `ollama list` |
| Crawl ไม่ได้ | ตรวจสอบ IP/URL ใน `configs/config.yaml` และการเชื่อมต่อ |
| `score = 0` ทุกคำถาม | รัน `sync_incremental.py` ก่อน มีข้อมูลใน DB หรือยัง |

---

## โครงสร้างไฟล์สำคัญ

```
├── setup.sh                    ← รันครั้งเดียว ตั้งค่าทุกอย่าง
├── configs/
│   ├── config.example.yaml     ← Template (อย่าแก้ตัวนี้)
│   └── config.yaml             ← ไฟล์จริง (สร้างจาก example)
├── data/
│   ├── records/*.jsonl         ← ข้อมูลผู้ติดต่อ (สร้างเอง)
│   └── vectorstore/            ← Vector DB (สร้างอัตโนมัติ)
└── scripts/
    ├── sync_incremental.py     ← อัปเดตข้อมูลแบบ incremental
    └── swap_collection.py      ← Rebuild DB ทั้งหมด (Blue-Green)
```
