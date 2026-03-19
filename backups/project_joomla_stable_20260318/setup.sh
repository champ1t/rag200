#!/usr/bin/env bash
# =============================================================================
# setup.sh — RAG System Quick Setup
# =============================================================================
# รันครั้งเดียวเพื่อตั้งค่าระบบทั้งหมด
#
# ข้อจำกัด:
#   1. ต้องอยู่ในเครือข่ายที่เข้าถึงเว็บ target ได้ (เช่น NT Intranet)
#   2. ต้องแก้ configs/config.yaml ก่อน (IP + API key)
#   3. Ollama ต้องถูก install แยกต่างหาก (ดำเนินการใน script นี้)
#   4. OCR (Tesseract) ต้องมี ถ้าต้องการสกัดข้อมูลจากภาพ
#
# Usage:
#   chmod +x setup.sh && ./setup.sh
#   ./setup.sh --skip-crawl    # ข้ามการ crawl ครั้งแรก (ใส่ข้อมูลเองทีหลัง)
#   ./setup.sh --no-ollama     # ข้าม Ollama (ถ้าติดตั้งแล้ว)
# =============================================================================

set -e  # หยุดทันทีถ้าเกิด error

# ── สี สำหรับ output ──────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; BOLD='\033[1m'; NC='\033[0m'

info()    { echo -e "${BLUE}[INFO]${NC}  $1"; }
success() { echo -e "${GREEN}[OK]${NC}    $1"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $1"; }
error()   { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }
header()  { echo -e "\n${BOLD}══════════════════════════════════════${NC}"; echo -e "${BOLD} $1${NC}"; echo -e "${BOLD}══════════════════════════════════════${NC}"; }

# ── Parse arguments ───────────────────────────────────────────────────────────
SKIP_CRAWL=false
NO_OLLAMA=false
for arg in "$@"; do
  case $arg in
    --skip-crawl) SKIP_CRAWL=true ;;
    --no-ollama)  NO_OLLAMA=true ;;
    --help|-h)
      echo "Usage: ./setup.sh [--skip-crawl] [--no-ollama]"
      echo "  --skip-crawl  ข้ามการ crawl/index ครั้งแรก"
      echo "  --no-ollama   ข้ามการติดตั้ง Ollama"
      exit 0 ;;
  esac
done

# ── Banner ────────────────────────────────────────────────────────────────────
echo -e "${BOLD}"
echo "  ██████╗  █████╗  ██████╗     ███████╗███████╗████████╗██╗   ██╗██████╗ "
echo "  ██╔══██╗██╔══██╗██╔════╝     ██╔════╝██╔════╝╚══██╔══╝██║   ██║██╔══██╗"
echo "  ██████╔╝███████║██║  ███╗    ███████╗█████╗     ██║   ██║   ██║██████╔╝"
echo "  ██╔══██╗██╔══██║██║   ██║    ╚════██║██╔══╝     ██║   ██║   ██║██╔═══╝ "
echo "  ██║  ██║██║  ██║╚██████╔╝    ███████║███████╗   ██║   ╚██████╔╝██║     "
echo "  ╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝     ╚══════╝╚══════╝   ╚═╝    ╚═════╝ ╚═╝     "
echo -e "${NC}"
echo "  Internal Knowledge Base — RAG System Setup"
echo ""

# ── ตรวจสอบ requirements ──────────────────────────────────────────────────────
header "ขั้นที่ 1/6 — ตรวจสอบ Requirements"

# Python
python3 --version >/dev/null 2>&1 || error "ต้องการ Python 3.9+ (ไม่พบ python3)"
PY_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
info "Python: $PY_VERSION"
[[ "${PY_VERSION}" < "3.9" ]] && error "ต้องการ Python 3.9 ขึ้นไป (ปัจจุบัน $PY_VERSION)"
success "Python $PY_VERSION ✓"

# Git
git --version >/dev/null 2>&1 || error "ต้องการ git"
success "git ✓"

# ── Virtual Environment ───────────────────────────────────────────────────────
header "ขั้นที่ 2/6 — ตั้งค่า Virtual Environment"

if [ ! -d "venv" ]; then
  info "สร้าง venv..."
  python3 -m venv venv
  success "สร้าง venv แล้ว"
else
  info "พบ venv อยู่แล้ว — ข้ามการสร้าง"
fi

source venv/bin/activate
success "Activated venv"

# ── Install Dependencies ──────────────────────────────────────────────────────
header "ขั้นที่ 3/6 — ติดตั้ง Dependencies"

# เลือก requirements ตาม OS
if [[ "$OSTYPE" == "darwin"* ]]; then
  REQ_FILE="requirements.txt"
  info "ระบบ macOS — ใช้ $REQ_FILE"
else
  REQ_FILE="requirements_linux.txt"
  info "ระบบ Linux — ใช้ $REQ_FILE"
fi

[ -f "$REQ_FILE" ] || error "ไม่พบ $REQ_FILE"

pip install --upgrade pip -q
pip install -r "$REQ_FILE" -q && success "ติดตั้ง dependencies เรียบร้อย"

# ── Config Setup ──────────────────────────────────────────────────────────────
header "ขั้นที่ 4/6 — ตั้งค่า Config"

if [ ! -f "configs/config.yaml" ]; then
  cp configs/config.example.yaml configs/config.yaml
  warn "สร้าง configs/config.yaml จาก example แล้ว"
  warn "⚠️  กรุณาแก้ไขก่อนรันระบบ:"
  warn "   - web.domain       ← IP/domain ของเว็บที่ต้องการ crawl"
  warn "   - web.start_urls   ← URL เริ่มต้น"
  warn "   - llm.model        ← ชื่อ Ollama model ที่จะใช้"
  echo ""
  read -p "เปิด config.yaml เพื่อแก้ไขตอนนี้เลยมั้ย? (y/N) " -n 1 -r
  echo
  if [[ $REPLY =~ ^[Yy]$ ]]; then
    ${EDITOR:-nano} configs/config.yaml
  fi
else
  success "configs/config.yaml มีอยู่แล้ว ✓"
fi

# ── Ollama Setup ──────────────────────────────────────────────────────────────
header "ขั้นที่ 5/6 — Ollama (Local LLM)"

if [ "$NO_OLLAMA" = true ]; then
  info "ข้าม Ollama (--no-ollama)"
elif command -v ollama &>/dev/null; then
  success "Ollama พบแล้ว ✓"
  # ดึง model ที่ config กำหนด
  MODEL=$(python3 -c "import yaml; c=yaml.safe_load(open('configs/config.yaml')); print(c.get('llm',{}).get('model','llama3.2:3b'))" 2>/dev/null || echo "llama3.2:3b")
  info "ดาวน์โหลด LLM model: $MODEL"
  ollama pull "$MODEL" && success "Model $MODEL พร้อมใช้งาน ✓"
else
  warn "ไม่พบ Ollama — กำลังติดตั้ง..."
  if [[ "$OSTYPE" == "darwin"* ]]; then
    if command -v brew &>/dev/null; then
      brew install ollama && success "ติดตั้ง Ollama ผ่าน Homebrew แล้ว"
    else
      warn "ไม่มี Homebrew — ดาวน์โหลด Ollama ด้วยตัวเองที่: https://ollama.com/download"
    fi
  else
    curl -fsSL https://ollama.com/install.sh | sh && success "ติดตั้ง Ollama แล้ว"
  fi
fi

# ── Data Setup ────────────────────────────────────────────────────────────────
header "ขั้นที่ 6/6 — เตรียมข้อมูล"

# สร้าง directory structure
mkdir -p data/records data/vectorstore data/sessions logs
success "สร้าง data directories แล้ว"

# ตรวจสอบ records
if [ ! -f "data/records/directory.jsonl" ]; then
  warn "ไม่พบ data/records/directory.jsonl"
  warn "กรุณาสร้างไฟล์ผู้ติดต่อตาม format ใน:"
  warn "  → data/records/directory.example.jsonl"
  warn "  → data/records/teams.example.jsonl"
  warn "  → data/records/positions.example.jsonl"
fi

# Initial crawl
if [ "$SKIP_CRAWL" = true ]; then
  warn "ข้าม crawl (--skip-crawl) — รันเองทีหลังด้วย: python scripts/sync_incremental.py"
else
  echo ""
  info "เริ่ม crawl เว็บและสร้าง Vector Database..."
  info "อาจใช้เวลา 5-15 นาที ขึ้นอยู่กับขนาดเว็บ"
  echo ""
  if python scripts/sync_incremental.py; then
    success "Crawl และ index เสร็จแล้ว ✓"
  else
    warn "Crawl มีข้อผิดพลาด — ตรวจสอบ config.yaml และการเชื่อมต่อเครือข่าย"
  fi
fi

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}${BOLD}══════════════════════════════════════${NC}"
echo -e "${GREEN}${BOLD}  ✅ Setup เสร็จแล้ว!${NC}"
echo -e "${GREEN}${BOLD}══════════════════════════════════════${NC}"
echo ""
echo "  รันระบบด้วยคำสั่ง:"
echo ""
echo -e "  ${BOLD}# API Server${NC}"
echo "  source venv/bin/activate"
echo "  uvicorn src.api_server:app --host 0.0.0.0 --port 8000 --reload"
echo ""
echo -e "  ${BOLD}# ทดสอบด้วย curl${NC}"
echo "  curl http://localhost:8000/health"
echo ""
echo -e "  ${BOLD}# อัปเดตข้อมูลในอนาคต${NC}"
echo "  python scripts/sync_incremental.py"
echo ""
if [ ! -f "data/records/directory.jsonl" ]; then
  echo -e "${YELLOW}  ⚠️  อย่าลืมสร้าง data/records/*.jsonl ก่อนใช้งาน!${NC}"
  echo ""
fi
