#!/bin/bash

# Script สำหรับอัพเดทข้อมูลใหม่จากเว็บ SMC
# วิธีใช้: ./scripts/update_data.sh

echo "========================================"
echo "🔄 เริ่มต้นกระบวนการอัพเดทข้อมูล (SMC Update)"
echo "========================================"

# 1. เข้าไปที่โฟลเดอร์โปรเจค (เผื่อเรียกจากที่อื่น)
cd "$(dirname "$0")/.." || exit

# 2. Activate Virtual Environment
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "⚠️ ไม่พบ venv! พยายามรันด้วย Python หลัก..."
fi

# 3. ดึงข้อมูลใหม่ (Crawl)
echo ""
echo "[1/3] 🕷️  กำลังดึงข้อมูลจากเว็บ (Crawling)..."
python -m src.main crawl
if [ $? -ne 0 ]; then
    echo "❌ Crawl Failed!"
    exit 1
fi

# 4. สร้าง Index ใหม่ (Vector Database)
echo ""
echo "[2/3] 📚 อัพเดทสมอง AI (Indexing)..."
python -m src.main index
if [ $? -ne 0 ]; then
    echo "❌ Indexing Failed!"
    exit 1
fi

# 5. สร้างสมุดโทรศัพท์ใหม่ (Records)
echo ""
echo "[3/3] 📇 อัพเดทสมุดโทรศัพท์ (Directory Records)..."
python -m src.main records
if [ $? -ne 0 ]; then
    echo "❌ Records Build Failed!"
    exit 1
fi

echo ""
echo "========================================"
echo "✅ อัพเดทข้อมูลเสร็จสมบูรณ์!"
echo "📌 ระบบพร้อมตอบคำถามจากข้อมูลชุดใหม่แล้ว"
echo "========================================"
