#!/bin/bash
# Script สำหรับตั้งเวลาอัพเดทข้อมูลอัตโนมัติ (ทุกเที่ยงคืน)
# วิธีใช้: ./scripts/install_cron_job.sh

# 1. หาตำแหน่งปัจจุบันของโฟลเดอร์โปรเจค
# (ต้องรันจาก root ของโปรเจค เช่น /opt/rag_web)
CURRENT_DIR=$(pwd)
SCRIPT_PATH="$CURRENT_DIR/scripts/update_data.sh"
LOG_PATH="$CURRENT_DIR/logs/cron_update.log"

echo "========================================"
echo "⏰ ตั้งเวลาอัพเดทข้อมูลอัตโนมัติ (Auto-Scheduler)"
echo "========================================"
echo "📂 Working Directory: $CURRENT_DIR"

# 2. สร้างโฟลเดอร์ Logs ถ้ายังไม่มี
mkdir -p "$CURRENT_DIR/logs"

# 3. ทำให้ Script ตัวอัพเดทรันได้ (Executable)
chmod +x "$SCRIPT_PATH"

# 4. เตรียมคำสั่ง Cron (รันทุกวัน เวลา 00:00 น.)
# Format: นาที ชั่วโมง วัน เดือน วันในสัปดาห์ คำสั่ง
CRON_JOB="0 0 * * * $SCRIPT_PATH >> $LOG_PATH 2>&1"

# 5. ตรวจสอบว่ามีอยู่แล้วไหม (กันซ้ำ)
if crontab -l 2>/dev/null | grep -Fq "$SCRIPT_PATH"; then
    echo "⚠️  มีการตั้งเวลาไว้อยู่แล้ว (Skipping...)"
else
    # เพิ่ม Job ใหม่เข้าไป
    (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
    echo "✅ ติดตั้งสำเร็จ! ระบบจะอัพเดทตัวเองทุกเที่ยงคืน"
fi

echo ""
echo "📝 รายการ Schedule ทั้งหมด:"
crontab -l
echo "========================================"
