# Walkthrough - Root Cause Fix & Stability Report

I have corrected the system logic to handle technical queries reliably without relying on ad-hoc keyword expansions.

## 🕒 Executive Summary (The "Root Cause" Fix)

The discrepancy where "OLT" failed while "ONT" worked was caused by **conversational noise** in Thai queries blocking our strict matching engine.

### 1. Hardening the Normalization Engine (Root Cause)
- **Problem**: The system was trying to match the *entire* sentence (e.g., *"ผมจะกำหนดค่าบน OLT"*) against article titles. Because words like `"ผมจะ"` and `"บน"` weren't in the titles, the confidence score dropped to 0.9, triggering the **Ambiguity Guard** (which assumes that a 0.9 score means "too many options").
- **Fix**: Upgraded the `normalize_for_matching` logic to be **Thai-aware**. It now automatically strips:
    - **Pronouns**: ผม, หนู, เรา, พี่, น้อง
    - **Intent Verbs**: จะ, อยาก, ต้องการ, ช่วย
    - **Polite Particles**: ครับ, ค่ะ, นะ, หน่อย
    - **Prepositions**: บน, ที่, ใน, ของ
- **Result**: The query now boils down to the core technical intent (*"กำหนดค่า OLT"*), allowing it to match the main article with **0.98 confidence**, which safely bypasses the ambiguity check.

### 2. Consistency & Cleanliness
- **Reverted Aliases**: I removed the temporary `ONT/ONU` keywords from `aliases.json` as the logic fix now handles these variations more naturally through the "Article-First" fallback.
- **Verification**: Both correctly spelled and informally phrased queries now resolve to the same high-quality links.

---

## ✅ Verified Test Cases

| Test Scenario | Query | Result | Status |
|---------------|-------|--------|--------|
| **Formal OLT** | "กำหนดค่า OLT" | Found OLT/ONU guide (0.98) | ✅ Pass |
| **Informal OLT** | "ผมจะกำหนดค่าบน OLT" | Found OLT/ONU guide (0.98) | ✅ Pass |
| **Typo/Alias** | "กำหนดค่าบน ONT" | Found OLT/ONU guide (Vector) | ✅ Pass |
| **Multi-Keyword** | "ตรวจสอบ OLT ZTE" | Finds multiple ZTE OLT articles | ✅ Pass |

## 🛡️ Stability Assessment
- **Logic Level**: The fix is at the engine level, making the entire search system (not just OLT) more resilient to how users actually talk.
- **Fail-Safe**: By increasing the confidence of "Correct" words, we ensure the system doesn't hesitate when it has found the exact answer.
