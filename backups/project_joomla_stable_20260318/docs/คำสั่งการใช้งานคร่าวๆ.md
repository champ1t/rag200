# คำสั่งที่ใช้บ่อย — RAG System Cheatsheet

> อัปเดตล่าสุด: 2026-03-04  
> สำหรับผู้ดูแลระบบและนักพัฒนาที่จะพัฒนาต่อในอนาคต

---

## 0. เตรียมความพร้อม (ทำทุกครั้งก่อนรัน)

```bash
cd ~/Documents/NT/RAG/rag_web
source venv/bin/activate
```

---

## 1. รันระบบ

### เปิด Chat แบบ Terminal (สำหรับ debug)
```bash
python3 -m src.main chat
```

### เปิด API Server (FastAPI + uvicorn)
```bash
uvicorn src.api_server:app --host 0.0.0.0 --port 8000 --reload
```

### เปิด Langflow (สำหรับต่อ UI กับ API)
```bash
export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES && langflow run
```

### เปิดทั้งหมดพร้อมกัน (background)
```bash
uvicorn src.api_server:app --host 0.0.0.0 --port 8000 --reload &
export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES && langflow run &
python3 -m src.main chat
```

---

## 2. อัปเดตข้อมูล (Data Sync)

### ดูก่อนว่าจะมีอะไรเปลี่ยน (ไม่แตะ DB)
```bash
python scripts/sync_incremental.py --dry-run
```

### อัปเดตจริง (เฉพาะหน้าที่เปลี่ยน)
```bash
python scripts/sync_incremental.py
```

### อัปเดตเฉพาะหน้าที่ระบุ
```bash
python scripts/sync_incremental.py \
  --target-url "http://10.192.133.33/smc/index.php?option=com_content&view=article&id=570"
```

### Rebuild ฐานข้อมูลใหม่ทั้งหมด (Blue-Green)
```bash
python scripts/swap_collection.py          # ทำครบ: สร้าง → ทดสอบ → สลับ
python scripts/swap_collection.py --build-only   # แค่สร้างถังใหม่
python scripts/swap_collection.py --test-only    # แค่ทดสอบ
python scripts/swap_collection.py --swap-only    # แค่สลับถัง
python scripts/swap_collection.py --rollback     # คืนกลับถังเก่า
```

---

## 3. Git (Version Control)

### ดู status และ commit
```bash
git status
git log --oneline -5
git diff
```

### Commit และ push
```bash
git add -A
git commit -m "your message here"
git push origin public-release:refs/heads/main
```

### Freeze (บันทึกจุดที่ระบบดีอยู่)
```bash
git tag "freeze-YYYY-MM-DD-description"
git push origin --tags
```

### ดู tags ที่มี
```bash
git tag -l
```

### ย้อนกลับไป tag ที่ต้องการ
```bash
git checkout freeze-2026-03-02-pre-sync-test
```

### ย้อนกลับไป branch หลัก
```bash
git checkout public-release
```

---

## 4. ChromaDB / Vector Database

### ดูจำนวน documents ใน collection
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
print(f'Collection: {cfg[\"vectorstore\"][\"collection_name\"]}')
print(f'Documents: {vs.collection.count()}')
"
```

### ทดสอบ query
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
results = vs.query('5S network', top_k=3)
for r in results:
    print(f'score={r.score:.3f}  url={r.metadata.get(\"url\",\"?\")}')
"
```

### Backup Vector DB
```bash
cp -r data/vectorstore data/vectorstore_backup_$(date +%Y%m%d)
cp data/state.json data/state_backup_$(date +%Y%m%d).json
```

### Restore Vector DB จาก backup
```bash
rm -rf data/vectorstore
cp -r data/vectorstore_backup_YYYYMMDD data/vectorstore
```

---

## 5. ทดสอบระบบ

### รัน test ทั้งหมด
```bash
python3 -m pytest tests/ -v
```

### รัน test file เดียว
```bash
python3 -m pytest tests/manual/test_normalizer_e2e.py -v
```

### ดู API health check
```bash
curl http://localhost:8000/health
curl http://localhost:8000/ready
```

### ทดสอบ /chat endpoint
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: nt-rag-secret" \
  -d '{"query": "5S คืออะไร", "session_id": "test-001"}'
```

---

## 6. Debug และ Logs

### ดู Metrics (คำถามที่ผ่านระบบ)
```bash
tail -20 data/metrics.csv
cat data/metrics.csv | sort -t',' -k5 -rn | head -10   # เรียงตาม latency
```

### ดู state.json (URLs ที่ track อยู่)
```bash
python3 -c "
import json
d = json.load(open('data/state.json'))
print(f'Total URLs: {len(d.get(\"pages\",{}))}')
"
```

---

## 7. Dependencies

### Install ครั้งแรก (Mac / Apple Silicon)
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Install บน Linux / เครื่อง Local
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements_linux.txt
playwright install
```

### อัปเดต requirements.txt (หลัง pip install package ใหม่)
```bash
pip freeze > requirements.txt
grep -Ev "^(mlx|mlx-audio|mlx-lm|mlx-metal|mlx-vlm)" requirements.txt > requirements_linux.txt
```

---

## 8. Config สำคัญ

| ไฟล์ | หน้าที่ |
|---|---|
| `configs/config.yaml` | ตั้งค่าหลัก (LLM, Vector DB, Crawl) |
| `configs/config.yaml.bak` | Backup config (สร้างอัตโนมัติตอน swap) |
| `data/state.json` | บันทึก hash ของ URLs ที่ index แล้ว |
| `data/vectorstore/` | ChromaDB files |
| `data/bm25_index.json` | BM25 keyword index |
| `data/metrics.csv` | Log ทุก request |

### เปลี่ยน Collection ที่ใช้งาน (ใน config.yaml)
```yaml
vectorstore:
  collection_name: smc_web        # ← แก้ตรงนี้
```

---

## 9. Ollama (LLM Local)

### เช็คว่า Ollama รันอยู่มั้ย
```bash
curl http://localhost:11434/api/tags
```

### ดู models ที่มี
```bash
ollama list
```

### รัน Ollama ถ้าไม่ได้รัน
```bash
ollama serve &
```

### ดึง model ใหม่
```bash
ollama pull llama3.2:3b
```
