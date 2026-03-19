# Alignment of ONT/ONU Access & Ambiguity Logic

The user discovered a discrepancy where a "typo" (ONT) worked better than a "correct" term (OLT). This is because OLT is a broad term in the corpus, triggering a safety ambiguity guard, while ONT was unknown and used a smarter fallback.

## Proposed Changes

### [Corpus] aliases.json
- [MODIFY] [aliases.json](file:///Users/jakkapatmac/Documents/NT/RAG/rag_web/data/aliases.json)
    - Add "ONT" as an alias for "OLT/ONU" articles to ensure technical alignment.
    - Map "กำหนดค่าบน ONT" and "ตั้งค่า ONT" to the correct article.

## Verification Plan

### Automated Tests
- Run `python3 /tmp/diag_match.py` after changes to verify scores.
- Test query: "ผมจะกำหนดค่าบน ONT" should now show a high score match (0.9 or 1.0 depending on rule).
- Test query: "ผมจะกำหนดค่าบน OLT" should still be ambiguous (this is technically correct for OLT).
