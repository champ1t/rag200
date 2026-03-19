# Production Freeze Recovery Guide

## 🔒 Current Freeze Status

**Frozen Version**: `v1.0-production-freeze-20260211`  
**Commit**: `5ccfd34`  
**Test Results**: 13/13 PASS  
**Date**: 2026-02-11

---

## 📋 Quick Commands

### Check if Still in Frozen State
```bash
./scripts/verify_freeze_state.sh
```

### Restore to Frozen State
```bash
./scripts/restore_freeze.sh
```

### View Freeze Tags
```bash
git tag -l "v1.0-production-freeze-*"
```

---

## 🔄 Restore Methods

### Method 1: Using Restore Script (Recommended)
```bash
cd /Users/jakkapatmac/Documents/NT/RAG/rag_web
./scripts/restore_freeze.sh
```

### Method 2: Direct Git Checkout
```bash
git checkout v1.0-production-freeze-20260211
```

### Method 3: View Freeze Commit Details
```bash
git show v1.0-production-freeze-20260211
```

---

## ✅ Verification After Restore

After restoring, verify the state:

```bash
# 1. Run production suite
python3 verify_production_suite.py
# Expected: 13/13 Passed

# 2. Verify freeze state
./scripts/verify_freeze_state.sh

# 3. Quick audit check
python3 -c "
import yaml
from src.chat_engine import ChatEngine
config = yaml.safe_load(open('configs/config.yaml'))
engine = ChatEngine(config)
res = engine.process('ZTE-SW Command')
print(f\"Route: {res['route']}\")
print(f\"Audit: {res.get('audit', {}).keys()}\")
"
```

---

## 🔍 What's Frozen

### Production Locks
- ✅ Deterministic matching (exact/soft-normalized)
- ✅ Vendor scope enforcement (PRIMARY/SMC-ONLY/OUT-OF-SCOPE)
- ✅ Phase 21: Exact → LINK_ONLY, Low-context protection
- ✅ Phase 22: Early vendor gating
- ✅ Mandatory audit schema

### Test Coverage (13/13)
- TC-A1, A2, A3: Exact match routing
- TC-B1, B2: Index/Low-context routing
- TC-C1: Low-context detection
- TC-D1: Normal summarization
- TC-E1, E2: Vendor blocking
- TC-F1, F2: Ambiguity/scope blocking
- TC-G1, G2: Vendor scope enforcement

### Key Files
- `src/chat_engine.py` - Core engine with all locks
- `verify_production_suite.py` - 13-test verification suite
- `production_locks.md` - Documentation
- `walkthrough.md` - Implementation history

---

## 🚨 Troubleshooting

### If Verification Fails

1. **Check git status**:
   ```bash
   git status
   git log --oneline -5
   ```

2. **Force restore**:
   ```bash
   git reset --hard v1.0-production-freeze-20260211
   ```

3. **Verify again**:
   ```bash
   ./scripts/verify_freeze_state.sh
   ```

### If Production Tests Fail

Run detailed verification:
```bash
python3 verify_production_suite.py 2>&1 | tee freeze_verify.log
```

Check specific test:
```bash
python3 -c "
import yaml
from src.chat_engine import ChatEngine
config = yaml.safe_load(open('configs/config.yaml'))
engine = ChatEngine(config)

# Test exact match
res = engine.process('ZTE-SW Command')
print(f\"Route: {res['route']} (Expected: article_link_only_exact)\")
print(f\"Reason: {res.get('audit', {}).get('decision_reason')}\")
"
```

---

## 📝 Notes

- **NEVER modify** files in frozen state - always create new branch
- **Always verify** before deploying
- **Keep freeze tag** for rollback purposes
- **Document changes** if creating new features on top of freeze

---

## 🔗 Related Files

- `scripts/freeze_production.sh` - Creates new freeze
- `scripts/restore_freeze.sh` - Restores to freeze
- `scripts/verify_freeze_state.sh` - Verifies current state
- `verify_production_suite.py` - Full test suite
- `production_locks.md` - Lock documentation
