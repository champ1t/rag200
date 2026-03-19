# RAG Web System

This repository contains the core logic for the RAG (Retrieval-Augmented Generation) system.

## ⚠️ Important Note
This codebase has been sanitized for public release. All internal IP addresses, domain names, and sensitive keywords have been replaced with placeholders.

### Placeholders Used:
- `INTERNAL_SMC_IP`: The IP address of the internal SMC server.
- `INTERNAL_NMS_IP`: The IP address of the internal NMS system.
- `COMPANY_DOMAIN`: The main company domain (e.g. example.com).
- `INTRANET_DOMAIN`: The internal intranet domain.
- `HR_DOMAIN`: The HR system domain.
- `LMS_DOMAIN`: The Learning Management System domain.
- `MAIL_DOMAIN`: The email server domain.

## Setup
1. Clone the repository.
2. Install dependencies: `pip install -r requirements.txt` (you may need to generate this).
3. Configure your environment variables or replace the placeholders in `config.yaml` and source code with your actual internal values.

## Architecture
- `src/rag/`: Logic for retrieval, article cleaning, and interpretation.
- `src/core/`: Core Chat Engine and Intent Classification.
- `src/vector_store/`: Hybrid search implementation.

## Usage
Run the main chat interface:
```bash
python3 -m src.main chat
```
