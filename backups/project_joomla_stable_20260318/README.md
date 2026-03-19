# RAG Web - NT Knowledge Base System

A professional RAG (Retrieval-Augmented Generation) system for internal knowledge management.

## 🏗️ Project Structure

```
rag_web/
├── src/                         # Production code
│   ├── core/                    # Core business logic
│   │   └── chat_engine.py       # Main RAG engine (318KB)
│   ├── ai/                      # AI/LLM components
│   ├── rag/                     # RAG-specific logic
│   ├── directory/               # Contact/directory lookup
│   ├── ingest/                  # Data ingestion pipeline
│   ├── vectorstore/             # Vector DB interface
│   ├── cache/                   # Caching layer
│   ├── context/                 # Conversation context
│   ├── api/                     # API handlers
│   └── utils/                   # Utilities
│
├── tests/                       # Test suite
│   ├── integration/             # Integration tests
│   ├── e2e/                     # End-to-end tests
│   └── fixtures/                # Test fixtures
│
├── tools/                       # Development tools
│   ├── maintenance/             # Maintenance scripts
│   │   └── manual_update_knowledge.py
│   ├── benchmarks/              # Performance benchmarks
│   └── debug/                   # Debug utilities
│
├── data/                        # Data storage (gitignored)
├── docs/                        # Documentation
└── .archive/                    # Archived files (gitignored)
```

## 🚀 Quick Start

### Prerequisites
- Python 3.11.x
- Virtual environment activated

### Installation
```bash
# Activate Python 3.11 environment
source venv-py311/bin/activate

# Verify Python version
python --version  # Should show 3.11.x

# Install dependencies
pip install -r requirements.txt
```

### Running the System
```bash
# Start chat interface
python -m src.main chat

# Start API server
python -m src.api_server
```

## 📦 Key Features
- **Smart Intent Recognition** - Understands Thai queries with synonym expansion
- **Context-Aware Conversations** - Maintains conversation history
- **Fast Path Optimization** - Direct article links for exact matches
- **Semantic Caching** - Reduces LLM calls for similar queries
- **Directory Integration** - Contact/phone number lookup

## 🛠️ Development

### Running Tests
```bash
# Integration tests
pytest tests/integration/

# End-to-end tests
pytest tests/e2e/

# Specific test
python tests/integration/test_comprehensive_suite.py
```

### Updating Knowledge Base
```bash
# Manual update (requires internal network access)
python tools/maintenance/manual_update_knowledge.py
```

## 📝 System State
- **Python Version:** 3.11.14
- **Status:** Production-ready (frozen state)
- **Last Validation:** 33/34 tests passing (97.1%)

## 📚 Documentation
- [Implementation Plan](/.archive/test_results/implementation_plan.md)
- [Walkthrough](/.archive/test_results/walkthrough.md)
- [Test Results](/.archive/test_results/test_results.md)

## 🔧 Configuration
- Config files: `config/`, `configs/`
- Vector DB: ChromaDB (local)
- LLM: Ollama (local)

---

**Note:** This project follows professional Python project standards with clear separation between production code, tests, tools, and documentation.
