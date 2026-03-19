# Phase 174 Code Freeze Policy

Effective immediately, the following core files are under **Code Freeze** for version `v1.0-phase174`.

## Locked Files (No-Touch)
Do NOT modify these files without a formal architectural review. They contain the production-ready retrieval, cleaning, and safety logic.

- `src/chat_engine.py` (Core RAG Orchestration & Rollback)
- `src/rag/article_cleaner.py` (Polishing & Garbage Removal)
- `src/rag/article_interpreter.py` (Fact Extraction)
- `src/rag/synonyms.py` (Synonym Engine)

## Permissible Changes
Only the following areas are eligible for post-freeze adjustments:
1. **Prompts**: Tuning LLM instructions.
2. **Configs**: Modifying `configs/config.yaml`.
3. **UI/API**: Front-end or API schema updates (not affecting core logic).
4. **Metrics/Tests**: Adding new test cases or tracking signals.

## Versioning
- **Current Tag**: `v1.0-phase174`
- **Next Dev Target**: Phase 175 (Multilingual Extension)
