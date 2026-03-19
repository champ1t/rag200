# SMC RAG – STRICT TEST SUITE (Phase 20+)
## ผลการทดสอบและคำแนะนำ

### สถานะ: ⚠️ ต้องการการทดสอบด้วยตนเอง

## ปัญหาที่พบ
ไม่สามารถเชื่อมต่อกับ RAG API Server ที่ port 8999 ได้ในขณะนี้ 

เซิร์ฟเวอร์ที่ running อยู่อาจเป็นโหมด CLI ไม่ใช่ API mode

## วิธีแก้ไข: เริ่ม Server ใหม่ในโหมด API

```bash
# 1. หยุดเซิร์ฟเวอร์เก่าทั้งหมด
pkill -f "python3 -m src.main"

# 2. รอสักครู่
sleep 3

# 3. เริ่มเซิร์ฟเวอร์ใหม่ในโหมด API
cd /Users/jakkapatmac/Documents/NT/RAG/rag_web
python3 -m src.main api

# หรือรันใน background
# nohup python3 -m src.main api > /tmp/rag_api.log 2>&1 &

# 4. รอให้เซิร์ฟเวอร์เริ่มทำงาน (ประมาณ 15-20 วินาที)
sleep 20

# 5. ทดสอบว่าเซิร์ฟเวอร์พร้อมทำงาน
curl http://localhost:8999/health
```

## วิธีรันการทดสอบ

เมื่อเซิร์ฟเวอร์พร้อมแล้ว ให้รันสคริปต์ทดสอบ:

```bash
cd /Users/jakkapatmac/Documents/NT/RAG/rag_web
python3 test_phase20_strict.py
```

## รายการทดสอบทั้งหมด (15 Test Cases)

### 1️⃣ DETERMINISTIC MATCH – SOFT NORMALIZE (5 tests)
- **TC-D1**: `ZTE-SW Command` → ต้องได้ LINK_ONLY
- **TC-D2**: `zte-sw command` → Case insensitive
- **TC-D3**: `zte sw command` → Space normalize
- **TC-D4**: `ZTE__SW__Command` → Underscore normalize
- **TC-D5**: `   ZTE   SW    Command   ` → Trim & collapse

**เป้าหมาย**: ทุก variation ต้องให้ผลเหมือนกัน = EXACT_MATCH + LINK_ONLY

### 2️⃣ OVERVIEW / INDEX RULE (2 tests)
- **TC-O1**: `ONU Command` → LINK_ONLY (Overview Index)
- **TC-O2**: `คำสั่ง ONU` → LINK_ONLY (Ignore intent)

**เป้าหมาย**: Overview articles ห้าม summarize

### 3️⃣ LOW CONTEXT GUARD (3 tests)
- **TC-L1**: `show power DE` → Short article → LINK_ONLY
- **TC-L2**: `คำสั่ง ASR920-12GE` → Long article → Summary อนุญาต
- **TC-L3**: `NCS Command` → Low bullets → LINK_ONLY

**เป้าหมาย**: บทความสั้นหรือมี bullet น้อย ต้อง LINK_ONLY

### 4️⃣ SINGLE CANONICAL LINK (2 tests)
- **TC-S1**: `zte telnet to onu` → มีลิงก์เดียว
- **TC-S2**: `Command NCS` → เลือก best match เดียว

**เป้าหมาย**: ห้ามมีลิงก์ซ้ำ, ห้าม link spam

### 5️⃣ GOVERNANCE / BLOCKING (2 tests)
- **TC-G1**: `Cisco OLT new command 2024` → BLOCKED (ไม่มีใน SMC)
- **TC-G2**: `ZTE Switch Commands` → ไม่ใช่ exact match

**เป้าหมาย**: Fail-closed เสมอเมื่อไม่มั่นใจ

### 6️⃣ AUDIT LOG TRACEABILITY (1 test)
- **TC-A1**: ตรวจสอบ audit fields ครบ:
  - `normalized_query`
  - `matched_article_title`
  - `confidence_mode`
  - `decision_reason`

**เป้าหมาย**: อธิบายทุกการตัดสินใจได้

## การทดสอบด้วยตนเอง (ถ้าสคริปต์ไม่ทำงาน)

ถ้ารันสคริปต์ไม่ได้ สามารถทดสอบด้วย `curl` ได้:

```bash
# ทดสอบ TC-D1: Exact Match
curl -X POST http://localhost:8999/chat \
  -H "Content-Type: application/json" \
  -d '{"query":"ZTE-SW Command"}' | jq '.'

# ตรวจสอบ:
# - route ต้องเป็น "article_link_only_exact" หรือ "article_link_only"
# - answer ต้องมี 🔗
# - audit ต้องมี normalized_query, matched_article_title, confidence_mode, decision_reason
```

```bash
# ทดสอบ TC-L1: Low Context
curl -X POST http://localhost:8999/chat \
  -H "Content-Type: application/json" \
  -d '{"query":"show power DE"}' | jq '.'

# ตรวจสอบ:
# - route ต้องเป็น "article_link_only_low_context" หรือ "blocked" หรือ "miss"
# - ห้าม summarize บทความสั้น
```

```bash
# ทดสอบ TC-G1: No Match (Blocking)
curl -X POST http://localhost:8999/chat \
  -H "Content-Type: application/json" \
  -d '{"query":"Cisco OLT new command 2024"}' | jq '.'

# ตรวจสอบ:
# - route ต้องเป็น "blocked" หรือ "miss"
# - ห้ามแสดงข้อมูลที่ไม่มีใน SMC
```

## Expected Success Criteria

✅ **Pass Rate: 100% (15/15 tests)**

**Critical Tests (ห้ามตก):**
- TC-D1, TC-D2, TC-D3: Deterministic matching ทุก variation
- TC-A1: Audit log completeness
- TC-G1: Blocking non-SMC queries

**Important Tests:**
- TC-L1: Low-context protection
- TC-S1: Single link enforcement
- TC-O1: Overview index handling

## ผลการทดสอบก่อนหน้า (จาก verify_phase_21.py)

✅ **Passed:** Low-context detection, Exact-match link-only
✅ **Passed:** Audit field injection  
✅ **Passed:** Normal article summary

## สิ่งที่ต้องตรวจสอบเพิ่มเติม

1. **Production Server Status**: ตรวจสอบว่าเซิร์ฟเวอร์ที่ user รันอยู่เป็น API mode หรือ CLI mode
2. **Port Configuration**: ตรวจสอบว่า API server ใช้ port อะไร (8999, 9000, หรืออื่นๆ)
3. **Manual Testing**: ถ้าสคริปต์อัตโนมัติไม่ทำงาน ให้ทดสอบด้วย curl แทน

## สรุป

ระบบ Phase 21 ได้รับการ harden แล้วทั้งหมด:
- ✅ Low-context detection (< 3 paras, < 2 bullets)
- ✅ Exact-match Link-Only enforcement
- ✅ Mandatory audit logs
- ✅ Fail-closed governance

**แต่ต้องการ User ช่วยรันการทดสอบเต็มรูปแบบ เพราะ API server ยังไม่พร้อมใช้งาน**
