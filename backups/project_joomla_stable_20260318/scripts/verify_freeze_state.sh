#!/bin/bash
# Verify Current State Matches Production Freeze
# Quick check to ensure no production locks have been violated

set -e

echo "🔍 Verifying Production Freeze State..."
echo ""

# 1. Run production suite
echo "1/3: Running production test suite..."
python3 verify_production_suite.py > /tmp/verify_output.log 2>&1
SUITE_RESULT=$?

if [ $SUITE_RESULT -eq 0 ]; then
    PASS_COUNT=$(grep "SUMMARY:" /tmp/verify_output.log | grep -oE "[0-9]+/[0-9]+" | head -1)
    echo "✅ Production Suite: $PASS_COUNT"
else
    echo "❌ Production Suite FAILED"
    tail -20 /tmp/verify_output.log
    echo ""
    echo "Run 'python3 verify_production_suite.py' for details"
    exit 1
fi

# 2. Check audit schema compliance
echo ""
echo "2/3: Verifying audit schema..."
python3 -c "
import sys, os
sys.path.append('.')
import yaml
from src.chat_engine import ChatEngine

config = yaml.safe_load(open('configs/config.yaml'))
engine = ChatEngine(config)

# Test audit fields
test_queries = [
    'ZTE-SW Command',
    'zte sw command',
    'Cisco OLT new command'
]

required_fields = ['normalized_query', 'matched_article_title', 'confidence_mode', 'decision_reason']
all_ok = True

for q in test_queries:
    res = engine.process(q)
    audit = res.get('audit', {})
    missing = [f for f in required_fields if f not in audit or audit[f] is None]
    if missing:
        print(f'❌ {q}: Missing {missing}')
        all_ok = False

if all_ok:
    print('✅ All audit fields present')
    sys.exit(0)
else:
    sys.exit(1)
" 2>&1

AUDIT_RESULT=$?
if [ $AUDIT_RESULT -ne 0 ]; then
    exit 1
fi

# 3. Check key governance markers
echo ""
echo "3/3: Checking governance markers..."
GOVERNANCE_OK=true

# Check Phase 21 markers
if ! grep -q "Phase 21.*PRODUCTION LOCK" src/chat_engine.py; then
    echo "⚠️  Phase 21 marker not found"
    GOVERNANCE_OK=false
fi

# Check Phase 22 markers
if ! grep -q "Phase 22.*SMC-Only Vendor Block" src/chat_engine.py; then
    echo "⚠️  Phase 22 marker not found"
    GOVERNANCE_OK=false
fi

# Check DETERMINISTIC_MATCH routing
if ! grep -q 'intent == "DETERMINISTIC_MATCH".*article_link_only_exact' src/chat_engine.py; then
    echo "⚠️  DETERMINISTIC_MATCH routing marker not found"
    GOVERNANCE_OK=false
fi

if [ "$GOVERNANCE_OK" = true ]; then
    echo "✅ Governance markers intact"
else
    echo "❌ Governance markers missing or modified"
    exit 1
fi

echo ""
echo "═══════════════════════════════════════════"
echo "✅ PRODUCTION FREEZE STATE VERIFIED"
echo "═══════════════════════════════════════════"
echo ""
echo "All locks intact:"
echo "  • Deterministic matching ✅"
echo "  • Vendor scope enforcement ✅"
echo "  • Phase 21 exact match routing ✅"
echo "  • Phase 22 vendor blocking ✅"
echo "  • Mandatory audit schema ✅"
echo ""
