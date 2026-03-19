# Phase 174 Soft Launch Guide

This guide outlines the process for the 3-5 user soft launch phase.

## Purpose
Collect real-world user queries to build the "Gold Dataset" for Phase 175 and verify production stability.

## Monitoring Instructions

### 1. Tail Real-time Logs
Monitor incoming queries and system decisions:
```bash
tail -f api_debug.log | grep -E "Processing query|AUDIT|Synonym Rollback"
```

### 2. Capture Real Questions
Review `data/metrics.csv` daily to identify:
- Successful retrievals (answer provided).
- "Miss" coverage (user asked something we don't have).
- Edge cases for synonyms.

### 3. Reporting Issues
If a user reports an error:
1. Locate the `session_id` in `api_debug.log`.
2. Extract the full trace for debugging.

## Success Criteria for Phase 175
- System handles 100+ real queries with < 5% error rate.
- P95 latency stays under 30s for 8B model.
