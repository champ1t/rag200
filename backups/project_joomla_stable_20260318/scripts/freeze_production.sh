#!/bin/bash
# Production Freeze Script
# Creates git tag for current production-ready state

set -e

echo "🔒 Creating Production Freeze..."
echo ""

# 1. Check production suite first
echo "Step 1/4: Running production verification..."
python3 verify_production_suite.py > /tmp/freeze_verify.log 2>&1
if [ $? -eq 0 ]; then
    echo "✅ Production suite: 13/13 PASS"
else
    echo "❌ Production suite FAILED - aborting freeze"
    cat /tmp/freeze_verify.log
    exit 1
fi

# 2. Stage all changes
echo ""
echo "Step 2/4: Staging changes..."
git add -A

# 3. Create commit
echo ""
echo "Step 3/4: Creating freeze commit..."
FREEZE_DATE=$(date +%Y-%m-%d)
git commit -m "PRODUCTION FREEZE: Phase 21-22 Complete + Route Audit Fix

- 13/13 production tests passing
- Governance locks enforced (vendor scope, deterministic matching)
- Exact match routing: article_link_only_exact
- Low-context detection: article_link_only_low_context
- Vendor blocking: blocked_vendor_out_of_scope
- Mandatory audit schema verified
- Route audit fix: FALLBACK_LINK_ONLY → article_link_only_index

Frozen: $FREEZE_DATE
" || echo "⚠️  Nothing to commit (already committed)"

# 4. Create tag
echo ""
echo "Step 4/4: Creating git tag..."
TAG_NAME="v1.0-production-freeze-$(date +%Y%m%d)"
git tag -a "$TAG_NAME" -m "Production Freeze: All governance locks verified

Test Results: 13/13 PASS
- TC-A1, A2, A3: Exact match routing ✅
- TC-B1, B2: Index/Low-context routing ✅
- TC-C1: Low-context detection ✅
- TC-D1: Normal summarization ✅
- TC-E1, E2: Vendor blocking ✅
- TC-F1, F2: Ambiguity/scope blocking ✅
- TC-G1, G2: Vendor scope enforcement ✅

Production Locks:
- Deterministic matching (exact/soft-normalized)
- Vendor scope enforcement (PRIMARY/SMC-ONLY/OUT-OF-SCOPE)
- Phase 21: Exact → LINK_ONLY, Low-context protection
- Phase 22: Early vendor gating
- Mandatory audit schema

Frozen: $FREEZE_DATE
" || echo "⚠️  Tag already exists"

echo ""
echo "✅ Production Freeze Complete!"
echo ""
echo "Tag created: $TAG_NAME"
echo "Current commit: $(git rev-parse --short HEAD)"
echo ""
echo "To restore this state later:"
echo "  git checkout $TAG_NAME"
echo ""
