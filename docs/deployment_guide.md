# RAG System Deployment Guide

## การโหลด Database ไปเครื่อง Production

### ขั้นตอนที่ 1: เตรียมข้อมูล (Local)

```bash
cd /Users/jakkapatmac/Documents/NT/RAG/rag_web

# 1. ตรวจสอบข้อมูลที่จำเป็น
ls -lh data/

# ไฟล์สำคัญที่ต้องย้าย:
# - data/bm25_index.json          (BM25 search index)
# - data/chroma_db/               (Vector database)
# - data/records/contacts.jsonl   (Contact records)
# - data/records/positions.jsonl  (Position/Directory records)
# - data/records/teams.jsonl      (Team data)
# - data/knowledge_packs.json     (Knowledge base)
# - configs/config.yaml           (Configuration)
```

---

### ขั้นตอนที่ 2: สร้าง Archive Package

```bash
# สร้าง deployment package
tar -czf rag_data_$(date +%Y%m%d).tar.gz \
  data/bm25_index.json \
  data/chroma_db/ \
  data/records/ \
  data/knowledge_packs.json \
  configs/config.yaml

# ตรวจสอบขนาดไฟล์
ls -lh rag_data_*.tar.gz
```

**หรือใช้ script อัตโนมัติ:**
```bash
./scripts/export_data.sh
```

---

### ขั้นตอนที่ 3: ย้ายไฟล์ไปเครื่อง Production

**Option A: ใช้ rsync (แนะนำ)**
```bash
# Sync ข้อมูลไปเครื่อง production
rsync -avz --progress \
  rag_data_*.tar.gz \
  user@production-server:/opt/rag_web/backups/

# หรือ sync ทั้ง directory
rsync -avz --progress --exclude='venv' --exclude='__pycache__' \
  /Users/jakkapatmac/Documents/NT/RAG/rag_web/ \
  user@production-server:/opt/rag_web/
```

**Option B: ใช้ scp**
```bash
scp rag_data_*.tar.gz user@production-server:/opt/rag_web/backups/
```

**Option C: Upload ผ่าน Cloud (Google Drive/Dropbox)**
```bash
# ถ้าเครื่อง production ไม่มี SSH direct
# 1. Upload ไปยัง cloud storage
# 2. Download จากเครื่อง production
```

---

### ขั้นตอนที่ 4: ติดตั้งบนเครื่อง Production

**SSH เข้าเครื่อง production:**
```bash
ssh user@production-server
cd /opt/rag_web
```

**Extract และ Setup:**
```bash
# Extract data
tar -xzf backups/rag_data_YYYYMMDD.tar.gz

# สร้าง virtual environment (ถ้ายังไม่มี)
python3 -m venv venv
source venv/bin/activate

# ติดตั้ง dependencies
pip install -r requirements.txt

# ตรวจสอบ config
cat configs/config.yaml
```

---

### ขั้นตอนที่ 5: Verify Data

```bash
# ตรวจสอบว่าไฟล์ครบ
ls -lh data/bm25_index.json
ls -lh data/records/
ls -lh data/chroma_db/

# ทดสอบโหลดข้อมูล
python -c "
from src.chat_engine import ChatEngine
import yaml

with open('configs/config.yaml') as f:
    cfg = yaml.safe_load(f)

engine = ChatEngine(cfg)
print('✓ Data loaded successfully')
print(f'Teams: {len(engine.directory_handler.team_index)}')
print(f'Positions: {len(engine.directory_handler.position_index)}')
"
```

---

### ขั้นตอนที่ 6: รันระบบ

```bash
# ทดสอบ interactive mode
python -m src.main chat

# หรือรันเป็น API server (ถ้ามี)
# python -m src.main serve --host 0.0.0.0 --port 8000
```

---

## Automation: Auto-Sync Script

สร้างไฟล์ `scripts/sync_to_production.sh`:

```bash
#!/bin/bash
# Auto-sync ข้อมูลไป production

PROD_HOST="user@production-server"
PROD_PATH="/opt/rag_web"
DATE=$(date +%Y%m%d_%H%M%S)

echo "=== RAG Data Sync to Production ==="
echo "Target: $PROD_HOST:$PROD_PATH"
echo "Timestamp: $DATE"
echo ""

# 1. Create backup locally
echo "[1/3] Creating local backup..."
tar -czf backups/rag_data_${DATE}.tar.gz \
  data/bm25_index.json \
  data/chroma_db/ \
  data/records/ \
  data/knowledge_packs.json

# 2. Upload to production
echo "[2/3] Uploading to production..."
rsync -avz --progress \
  backups/rag_data_${DATE}.tar.gz \
  ${PROD_HOST}:${PROD_PATH}/backups/

# 3. Extract on production
echo "[3/3] Extracting on production..."
ssh $PROD_HOST "cd ${PROD_PATH} && tar -xzf backups/rag_data_${DATE}.tar.gz"

echo ""
echo "✓ Sync complete!"
echo "Backup saved: backups/rag_data_${DATE}.tar.gz"
```

**ใช้งาน:**
```bash
chmod +x scripts/sync_to_production.sh
./scripts/sync_to_production.sh
```

---

## Incremental Update (แนะนำสำหรับการอัพเดทบ่อย)

ถ้ามีการอัพเดทข้อมูลบ่อย ใช้ rsync แบบ incremental:

```bash
# Sync เฉพาะไฟล์ที่เปลี่ยน
rsync -avz --delete --progress \
  --exclude='venv' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='.git' \
  data/ user@production-server:/opt/rag_web/data/

# บังคับให้ reload (ถ้ารันเป็น service)
ssh user@production-server "sudo systemctl restart rag-api"
```

---

## Checklist ก่อน Deployment

### ข้อมูล (Data)
- [ ] `bm25_index.json` (ตรวจสอบขนาด > 0)
- [ ] `chroma_db/` directory (มี .parquet files)
- [ ] `records/contacts.jsonl` (จำนวนบรรทัด > 0)
- [ ] `records/positions.jsonl` 
- [ ] `records/teams.jsonl`
- [ ] `knowledge_packs.json`

### การตั้งค่า (Config)
- [ ] `configs/config.yaml` (ตรวจสอบ LLM endpoint)
- [ ] API keys / credentials (ถ้ามี)
- [ ] Port settings

### Dependencies
- [ ] `requirements.txt` ครบ
- [ ] Python >= 3.9
- [ ] Ollama installed (ถ้าใช้ local LLM)

### Testing
- [ ] ทดสอบ chat mode
- [ ] ทดสอบ team lookup
- [ ] ทดสอบ contact lookup
- [ ] ทดสอบ knowledge query

---

## Rollback Plan

ถ้าเกิดปัญหา:

```bash
# Restore จาก backup ก่อนหน้า
cd /opt/rag_web
rm -rf data/
tar -xzf backups/rag_data_PREVIOUS.tar.gz

# Restart service
sudo systemctl restart rag-api
```

---

## Security Notes

1. **ข้อมูลอ่อนไหว**:
   - ตรวจสอบว่า `data/records/` ไม่มีข้อมูลส่วนตัวที่ละเอียดอ่อน
   - พิจารณาใช้ encryption สำหรับการส่งข้อมูล

2. **Access Control**:
   - ตั้งค่า file permissions: `chmod 640 data/*.json`
   - ตั้งค่า directory permissions: `chmod 750 data/`

3. **Network**:
   - ใช้ VPN หรือ SSH tunnel สำหรับการ transfer
   - ปิด direct access จาก public internet

---

## Monitoring

หลัง deploy แล้ว ติดตาม:

```bash
# ดู logs
tail -f logs/chat_telemetry.jsonl

# ตรวจสอบ latency
grep latency logs/chat_telemetry.jsonl | tail -20

# ดู error rate
grep "route.*miss" logs/chat_telemetry.jsonl | wc -l
```
