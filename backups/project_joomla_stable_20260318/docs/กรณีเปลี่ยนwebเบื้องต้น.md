# แนวทางเปลี่ยน Website สำหรับระบบ RAG (เบื้องต้น)

## สรุปส่วนที่ต้องปรับ

| ส่วน | ไฟล์ | ระดับความยาก |
|---|---|---|
| Scraper/Fetcher | `src/ingest/fetch.py` | ปานกลาง — เปลี่ยน CSS selector และ URL pattern |
| ProcessedCache | `data/processed/*.json` | ต้อง re-crawl เว็บใหม่ทั้งหมด |
| Junk Filter | `src/rag/article_interpreter.py` | เล็กน้อย — เพิ่ม keyword ของ CMS ใหม่ |

---

## 1. Scraper/Fetcher — `src/ingest/fetch.py`

ปัจจุบันเขียนมาดึง HTML ของ Joomla/SMC โดยเฉพาะ

**โค้ดเดิม (Joomla/SMC):**
```python
content_div = soup.find("div", class_="article-content")  # Joomla article body
title = soup.find("h2", class_="article-title")
pagination = soup.find("div", id="system-message")
```

**ถ้าย้ายไปเว็บใหม่ที่เป็น WordPress:**
```python
content_div = soup.find("div", class_="entry-content")    # WordPress article body
title = soup.find("h1", class_="entry-title")             # WordPress title
pagination = soup.find("nav", class_="post-navigation")   # WordPress nav
```

**URL pattern ที่เปลี่ยน:**
```
SMC:       /smc/index.php?option=com_content&view=article&id=665
WordPress: /knowledge/bras-for-fixip/   ← slug-based
```

---

## 2. ProcessedCache — `data/processed/*.json`

ไฟล์เหล่านี้คือ "ฐานข้อมูลที่ crawl ไว้แล้ว" ตัวอย่าง 1 record:

```json
{
  "title": "Bras for fixip",
  "url": "http://10.192.133.33/smc/index.php?id=665",
  "text": "ลูกค้า Fixip จะต้องใช้งานกับ Bras Nokia01...",
  "article_type": "OVERVIEW",
  "links": []
}
```

ถ้าเว็บใหม่มี URL base ต่างกัน ต้องสร้าง processed cache ทั้งหมดใหม่ ด้วยคำสั่ง:
```bash
python3 scripts/sync_incremental.py --source https://new-website.com
```

---

## 3. Junk Filter — `src/rag/article_interpreter.py`

โค้ดปัจจุบันกรองขยะที่ Joomla สร้าง:

**โค้ดเดิม (Joomla/SMC):**
```python
if any(k in stripped for k in [
    "เขียนโดย",       # Joomla author label
    "แก้ไขล่าสุด",    # Joomla last modified
    "วันพฤหัสบดี",    # Thai date from Joomla
]):
    continue
```

**ถ้าเว็บใหม่เป็น WordPress** — เพิ่ม keyword:
```python
if any(k in stripped for k in [
    "เขียนโดย",
    "แก้ไขล่าสุด",
    "Posted by",        # WordPress author
    "Filed under",      # WordPress category
    "Leave a Comment",  # WordPress comment section
]):
    continue
```

---

## ภาพรวมส่วนที่ต้องแก้ vs ไม่ต้องแก้

```
เว็บเดิม (SMC/Joomla)             เว็บใหม่
──────────────────────────────────────────────────────
fetch.py     → ดึง Joomla CSS  → ดึง CSS ใหม่    (~20-30 บรรทัด)
data/processed → 145 ไฟล์      → crawl ใหม่ทั้งหมด
Junk Filter  → Joomla keywords → เพิ่ม CMS ใหม่  (~5-10 บรรทัด)

ส่วนที่ไม่ต้องแตะเลย:
✅ Vector Search, BM25, RAG logic
✅ LLM (Ollama), Governance Rules, Phase 21
✅ Chat Engine, API Server
✅ Intent Router, Entity Detector
```

---

## ประมาณการเวลา

| งาน | เวลา |
|---|---|
| ปรับโค้ด fetch.py + Junk Filter | 1-2 วัน |
| Re-crawl + สร้าง processed cache | 1-2 วัน |
| ทดสอบและ fine-tune threshold | 1 วัน |
| **รวม** | **3-5 วันทำงาน** |
