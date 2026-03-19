#!/bin/bash
# Auto-sync RAG data to production server
# Usage: ./scripts/sync_to_production.sh [prod_host] [prod_path]

set -e

# Configuration (แก้ไขตามเครื่อง production จริง)
PROD_HOST="${1:-user@production-server}"
PROD_PATH="${2:-/opt/rag_web}"
DATE=$(date +%Y%m%d_%H%M%S)

echo "=== RAG Data Sync to Production ==="
echo "Target: $PROD_HOST:$PROD_PATH"
echo "Timestamp: $DATE"
echo ""

# Confirm before proceeding
read -p "Continue with sync? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 1
fi

# 1. Create backup locally
echo "[1/4] Creating local backup..."
mkdir -p backups
tar -czf backups/rag_data_${DATE}.tar.gz \
    data/bm25_index.json \
    data/chroma_db/ \
    data/records/ \
    data/knowledge_packs.json \
    configs/config.yaml \
    2>&1 | grep -v "Removing leading"

echo "✓ Backup created: backups/rag_data_${DATE}.tar.gz"

# 2. Test SSH connection
echo ""
echo "[2/4] Testing connection to production..."
if ssh -o ConnectTimeout=5 "$PROD_HOST" "echo '✓ Connection OK'"; then
    echo ""
else
    echo "✗ Cannot connect to $PROD_HOST"
    exit 1
fi

# 3. Upload to production
echo "[3/4] Uploading to production..."
rsync -avz --progress \
    backups/rag_data_${DATE}.tar.gz \
    "${PROD_HOST}:${PROD_PATH}/backups/"

# 4. Extract on production (with backup of existing data)
echo ""
echo "[4/4] Deploying on production..."
ssh "$PROD_HOST" bash <<EOF
    set -e
    cd ${PROD_PATH}
    
    # Backup existing data
    if [ -d "data" ]; then
        echo "Creating backup of existing data..."
        tar -czf backups/pre_update_${DATE}.tar.gz data/ 2>&1 | grep -v "Removing leading" || true
    fi
    
    # Extract new data
    echo "Extracting new data..."
    tar -xzf backups/rag_data_${DATE}.tar.gz 2>&1 | grep -v "Removing leading"
    
    # Verify
    echo "Verifying data..."
    ls -lh data/bm25_index.json
    ls -lh data/records/
    
    echo "✓ Deployment complete on production"
EOF

echo ""
echo "=== Sync Complete ==="
echo "Local backup: backups/rag_data_${DATE}.tar.gz"
echo "Production backup: ${PROD_PATH}/backups/pre_update_${DATE}.tar.gz"
echo ""
echo "To verify on production:"
echo "  ssh $PROD_HOST"
echo "  cd ${PROD_PATH}"
echo "  source venv/bin/activate"
echo "  python -m src.main chat"
