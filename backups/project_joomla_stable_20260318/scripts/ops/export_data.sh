#!/bin/bash
# RAG Data Export Script (Updated: สำหรับระบบจริง)
# Usage: ./scripts/export_data.sh [output_dir]

set -e  # Exit on error

# Configuration
OUTPUT_DIR="${1:-./backups}"
DATE=$(date +%Y%m%d_%H%M%S)
ARCHIVE_NAME="rag_data_${DATE}.tar.gz"

echo "=== RAG Data Export ==="
echo "Date: $DATE"
echo "Output: $OUTPUT_DIR/$ARCHIVE_NAME"
echo ""

# Create output directory
mkdir -p "$OUTPUT_DIR"

# List of REQUIRED files
echo "[1/5] Checking required files..."
REQUIRED_FILES=(
    "data/bm25_index.json"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [ ! -f "$file" ]; then
        echo "✗ Missing: $file"
        exit 1
    fi
    echo "✓ Found: $file ($(du -h $file | cut -f1))"
done

# Check REQUIRED directories
REQUIRED_DIRS=(
    "data/records"
)

for dir in "${REQUIRED_DIRS[@]}"; do
    if [ ! -d "$dir" ]; then
        echo "✗ Missing directory: $dir"
        exit 1
    fi
    echo "✓ Found: $dir ($(du -sh $dir | cut -f1))"
done

# Optional files (ไม่บังคับ)
echo ""
echo "[2/5] Checking optional files..."
OPTIONAL_FILES=(
    "data/knowledge_packs.json"
    "data/state.json"
)

for file in "${OPTIONAL_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "✓ Found: $file ($(du -h $file | cut -f1))"
    else
        echo "⚠ Skipping: $file (not found)"
    fi
done

# Optional directories
OPTIONAL_DIRS=(
    "data/chroma_db"
    "data/vectorstore"
)

for dir in "${OPTIONAL_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        echo "✓ Found: $dir ($(du -sh $dir | cut -f1))"
    else
        echo "⚠ Skipping: $dir (not found)"
    fi
done

# Build file list dynamically
echo ""
echo "[3/5] Building archive list..."
TAR_FILES=(
    "data/bm25_index.json"
    "data/records/"
    "configs/config.yaml"
)

# Add optional files if they exist
[ -f "data/knowledge_packs.json" ] && TAR_FILES+=("data/knowledge_packs.json")
[ -f "data/state.json" ] && TAR_FILES+=("data/state.json")
[ -d "data/chroma_db" ] && TAR_FILES+=("data/chroma_db/")
[ -d "data/vectorstore" ] && TAR_FILES+=("data/vectorstore/")

echo "Files to archive: ${#TAR_FILES[@]}"

# Create archive
echo ""
echo "[4/5] Creating archive..."
tar -czf "$OUTPUT_DIR/$ARCHIVE_NAME" "${TAR_FILES[@]}" 2>&1 | grep -v "Removing leading" || true

# Verify archive
echo ""
echo "[5/5] Verifying archive..."
if tar -tzf "$OUTPUT_DIR/$ARCHIVE_NAME" > /dev/null 2>&1; then
    echo "✓ Archive is valid"
else
    echo "✗ Archive verification failed"
    exit 1
fi

# Summary
echo ""
echo "====================================="
echo "✓ Export complete!"
echo "====================================="
echo ""
echo "Archive: $OUTPUT_DIR/$ARCHIVE_NAME"
echo "Size: $(du -h $OUTPUT_DIR/$ARCHIVE_NAME | cut -f1)"
echo "Files: $(tar -tzf $OUTPUT_DIR/$ARCHIVE_NAME | wc -l | tr -d ' ')"
echo ""
echo "📦 Contents:"
tar -tzf "$OUTPUT_DIR/$ARCHIVE_NAME" | head -20
echo ""
echo "Next steps:"
echo "1. Transfer to production via AnyDesk:"
echo "   - Open AnyDesk File Transfer (📁)"
echo "   - Drag '$OUTPUT_DIR/$ARCHIVE_NAME' to production Desktop"
echo ""
echo "2. On production server:"
echo "   cd /opt/rag_web  # or C:\\rag_web"
echo "   tar -xzf ~/Desktop/$ARCHIVE_NAME"
echo "   python -m src.main chat  # Test"
echo ""
