# RAG System Deployment via AnyDesk

## การโหลด Database ไปเครื่อง Production ผ่าน AnyDesk

### ⚡ Quick Start (5 นาที)

```
1. Export ข้อมูล → 2. Remote AnyDesk → 3. Copy ไฟล์ → 4. Extract → 5. ทดสอบ
```

---

## ขั้นตอนที่ 1: เตรียมข้อมูลบนเครื่องตัวเอง (Local)

### 1.1 Export ข้อมูลอัตโนมัติ

เปิด Terminal แล้วรัน:

```bash
cd /Users/jakkapatmac/Documents/NT/RAG/rag_web
./scripts/export_data.sh
```

**Output:**
- สร้างไฟล์: `backups/rag_data_YYYYMMDD_HHMMSS.tar.gz`
- ขนาดประมาณ: 10-50 MB (ขึ้นกับข้อมูล)

### 1.2 หรือสร้างเอง Manual

```bash
cd /Users/jakkapatmac/Documents/NT/RAG/rag_web

# สร้าง backup
tar -czf ~/Desktop/rag_backup.tar.gz \
  data/bm25_index.json \
  data/chroma_db/ \
  data/records/ \
  data/knowledge_packs.json \
  configs/config.yaml

echo "✓ สร้างไฟล์แล้ว: ~/Desktop/rag_backup.tar.gz"
open ~/Desktop  # เปิด Finder
```

**ตรวจสอบ:**
- ✅ มีไฟล์ `rag_backup.tar.gz` บน Desktop
- ✅ ขนาดไฟล์ > 1 MB (ไม่ควรเป็น 0 bytes)

---

## ขั้นตอนที่ 2: Remote เข้าเครื่อง Production ผ่าน AnyDesk

### 2.1 เชื่อมต่อ AnyDesk

1. เปิด **AnyDesk** บนเครื่องตัวเอง
2. ใส่ **AnyDesk ID** ของเครื่อง production
3. กด **Connect**
4. ใส่ **Password** (ถ้ามี)

### 2.2 เปิด File Transfer

**วิธีที่ 1: ใช้ File Transfer ใน AnyDesk**
```
1. คลิกไอคอน Files (📁) ในแถบเครื่องมือ AnyDesk
2. เลือกไฟล์ rag_backup.tar.gz จากเครื่องตัวเอง
3. Drag & Drop ไปยังโฟลเดอร์ปลายทาง (เช่น Desktop บน production)
```

**วิธีที่ 2: Copy-Paste แบบ Clipboard**
```
1. คลิกขวาที่ไฟล์ rag_backup.tar.gz → Copy
2. Remote เข้า production ผ่าน AnyDesk
3. Paste ไฟล์ลงใน Desktop หรือ /tmp
```

**เส้นทางแนะนำบน Production:**
- Windows: `C:\rag_web\backups\`
- Linux/Mac: `/opt/rag_web/backups/` หรือ `~/rag_web/backups/`

---

## ขั้นตอนที่ 3: ติดตั้งบนเครื่อง Production

### 3.1 เปิด Terminal บนเครื่อง Production

**บน Windows:**
- กด `Win + R` → พิมพ์ `cmd` หรือ `powershell`

**บน Linux/Mac:**
- เปิด Terminal

### 3.2 สร้างโฟลเดอร์และ Extract

**บน Windows:**
```powershell
# สร้างโฟลเดอร์ (ถ้ายังไม่มี)
mkdir C:\rag_web
cd C:\rag_web

# Extract (ใช้ 7-Zip หรือ tar ถ้ามี WSL)
# ถ้ามี tar:
tar -xzf C:\Users\YourName\Desktop\rag_backup.tar.gz

# ถ้าไม่มี tar ให้:
# 1. ติดตั้ง 7-Zip (https://www.7-zip.org/)
# 2. คลิกขวาไฟล์ → 7-Zip → Extract Here
```

**บน Linux/Mac:**
```bash
# ไปยังโฟลเดอร์ที่ต้องการติดตั้ง
cd /opt/rag_web
# หรือ
cd ~/rag_web

# Extract
tar -xzf ~/Desktop/rag_backup.tar.gz

# ตรวจสอบว่า extract สำเร็จ
ls -lh data/
```

### 3.3 ติดตั้ง Dependencies (ถ้ายังไม่มี)

**ครั้งแรกเท่านั้น:**

```bash
# บน Linux/Mac:
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# บน Windows PowerShell:
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

---

## ขั้นตอนที่ 4: ทดสอบระบบ

### 4.1 Verify ข้อมูล

```bash
# Activate virtual environment (ถ้ายังไม่ได้ activate)
source venv/bin/activate   # Linux/Mac
# หรือ
.\venv\Scripts\activate    # Windows

# ตรวจสอบไฟล์
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
print('✓ โหลดข้อมูลสำเร็จ')
print(f'ทีม: {len(engine.directory_handler.team_index)} ทีม')
"
```

### 4.2 รันระบบ

```bash
# ทดสอบแบบ interactive
python -m src.main chat

# ถ้าได้พร้อม "พร้อมใช้งาน" แสดงว่าสำเร็จ!
```

---

## 📋 Checklist การ Deploy

### เตรียมข้อมูล (Local)
- [ ] รัน `./scripts/export_data.sh`
- [ ] ได้ไฟล์ `.tar.gz` ออกมา
- [ ] ขนาดไฟล์ > 1 MB

### Transfer ผ่าน AnyDesk
- [ ] เชื่อมต่อ AnyDesk สำเร็จ
- [ ] Copy ไฟล์ไปเครื่อง production
- [ ] ตรวจสอบขนาดไฟล์ตรงกับต้นทาง

### ติดตั้งบน Production
- [ ] Extract ไฟล์สำเร็จ
- [ ] มีโฟลเดอร์ `data/` และ `configs/`
- [ ] ไฟล์สำคัญครบ (bm25_index.json, records/, chroma_db/)

### ทดสอบ
- [ ] Activate venv สำเร็จ
- [ ] โหลดข้อมูลได้ (ไม่มี error)
- [ ] รัน chat mode ได้
- [ ] ทดสอบถาม 2-3 คำถาม (เช่น "รายชื่อทีมทั้งหมด")

---

## 🔄 การอัพเดทข้อมูล (ครั้งต่อไป)

เมื่อมีข้อมูลใหม่ ทำแค่:

```bash
# 1. บนเครื่อง Local
cd /Users/jakkapatmac/Documents/NT/RAG/rag_web
./scripts/export_data.sh

# 2. Remote AnyDesk → Copy ไฟล์ใหม่

# 3. บนเครื่อง Production
cd /opt/rag_web  # หรือ C:\rag_web
tar -xzf ~/Desktop/rag_backup_NEW.tar.gz  # Overwrite ข้อมูลเดิม

# 4. Restart (ถ้ารันเป็น service)
# หรือ Ctrl+C แล้วรันใหม่
```

---

## 🆘 แก้ปัญหา

### ปัญหา 1: ไฟล์ใหญ่เกินไป / Transfer ช้า

**แนะนำ:**
- ใช้ Google Drive / Dropbox (เร็วกว่า)

```bash
# 1. Upload ไฟล์ .tar.gz ขึ้น Google Drive
# 2. บนเครื่อง production: Download จาก Drive
# 3. Extract ตามปกติ
```

### ปัญหา 2: Extract แล้วไฟล์หาย

**สาเหตุ:** Path ไม่ถูกต้อง

**แก้:**
```bash
# ตรวจสอบว่าอยู่ในโฟลเดอร์ที่ถูกต้อง
pwd
# ต้อง: /opt/rag_web หรือ C:\rag_web

# Extract อีกครั้ง
tar -xzf path/to/backup.tar.gz
```

### ปัญหา 3: Import Error เมื่อรัน

**สาเหตุ:** ขาด dependencies

**แก้:**
```bash
source venv/bin/activate  # ต้อง activate ก่อนทุกครั้ง
pip install -r requirements.txt
```

### ปัญหา 4: Chroma DB Error

**สาเหตุ:** Version ไม่ตรง

**แก้:**
```bash
pip install --upgrade chromadb
```

---

## 💡 เทคนิคเพิ่มเติม

### การทำงานแบบ Offline

ถ้าเครื่อง production **ไม่มี internet**:

```bash
# 1. บนเครื่อง Local (มี internet)
cd /Users/jakkapatmac/Documents/NT/RAG/rag_web
pip download -r requirements.txt -d ./offline_packages/

# 2. Copy offline_packages/ ไปด้วยผ่าน AnyDesk

# 3. บนเครื่อง Production (ไม่มี internet)
pip install --no-index --find-links=./offline_packages/ -r requirements.txt
```

### การรัน Background (ไม่ต้องเปิด Terminal ค้าง)

**บน Linux:**
```bash
nohup python -m src.main chat > logs/output.log 2>&1 &
```

**บน Windows:**
- สร้าง `run.bat`:
```batch
@echo off
cd C:\rag_web
call venv\Scripts\activate
python -m src.main chat
pause
```
- Double-click `run.bat` เพื่อรัน

---

## 📞 Support

ถ้าติดปัญหา:
1. ดู error message ใน Terminal
2. ตรวจสอบ logs: `logs/chat_telemetry.jsonl`
3. ทดสอบว่าโหลดข้อมูลได้: `python -c "from src.chat_engine import ChatEngine; ..."`
