# Phase 23 Test Results

| Label | Query | Route | Status | Decision Reason |
| :--- | :--- | :--- | :--- | :--- |
| Regression: Exact Match | `zte sw command` | `article_link_only_exact` | PASS | Soft-normalized exact match |
| Regression: Soft-norm Match | `ZTE--SW--Command` | `article_link_only_exact` | PASS | Soft-normalized exact match |
| Regression: Normal Article (Summary) | `GPON Overview` | `article_link_only` | FAIL | Processing complete |
| Regression: Primary Vendor Sanity | `Huawei manual` | `article_link_only` | PASS | Processing complete |
| Boundary: Ambiguity (Short) | `zte sw` | `article_link_only_exact` | FAIL | Precise Tech Match → Link Only |
| Boundary: Ambiguity (Mixed) | `command zte sw overview` | `article_link_only_exact` | FAIL | Precise Tech Match → Link Only |
| Boundary: Comparison (Cross-vendor) | `ZTE OLT vs Huawei OLT` | `blocked_scope` | PASS | Processing complete |
| Boundary: Cisco (Adversarial) | `Cisco command like ZTE` | `web_error` | FAIL | Processing complete |
| Thai Stress: Mixed Lang | `ขอ command zte sw ที่ใช้ config vlan หน่อย` | `blocked_intent` | FAIL | Intent mismatch: Query(COMMAND) vs Article(MIGRATION_CONVERSION) |
| Thai Stress: Spacing Error | `zte  sw    command` | `article_link_only_exact` | PASS | Soft-normalized exact match |
| Thai Stress: Long Query/Short Intent | `ขอ command zte sw ที่ใช้ config vlan หน่อย แบบที่อยู่ใน manual` | `blocked_intent` | FAIL | Intent mismatch: Query(COMMAND) vs Article(MIGRATION_CONVERSION) |
