# RAG System Architecture (Contact-First)

## Overview
The system employs a **Hybrid Routing Architecture** to deliver deterministic answers for fact-based queries (Contacts) and semantic answers for knowledge-based queries (RAG).

## simplified Flow
```mermaid
graph TD
    User[User Query] --> Router{Is Contact Intent?}
    
    %% Contact Path
    Router -- Yes --> Extractor{Is Phone Pattern?}
    Extractor -- Yes --> Reverse[Reverse Lookup<br/>(directory.jsonl)]
    Extractor -- No --> NameLookup[Name Lookup<br/>(directory.jsonl)]
    
    Reverse --> HitCheck{Found?}
    NameLookup --> HitCheck
    
    HitCheck -- Yes --> Formatter[Standardized Format<br/>(Deterministic)]
    HitCheck -- No --> NotFound[Return 'Not Found'<br/>(Guardrail: STOP)]
    
    %% RAG Path
    Router -- No --> VectorSearch[Vector Search<br/>(ChromaDB)]
    VectorSearch --> Context[Retrieve Context]
    Context --> LLM[LLM Generation<br/>(Ollama)]
    LLM --> Answer[Generative Answer]
```

## detailed Components

### 1. Router (Guardrails)
- **Logic**: Checks for contact keywords (`เบอร์`, `โทร`) OR phone number patterns (`Digit >= 4`).
- **Goal**: Prevent LLM hallucination on static facts.

### 2. Directory Service (Structured)
- **Source**: `directory.jsonl` (built from raw web crawl).
- **Capabilities**:
  - **Person Match**: "คุณ A"
  - **Team Match**: "ทีม B"
  - **Reverse Match**: "02-123-4567"
- **Policy**: If routed here but no match found, the system **stops** and asks for clarification. It does **not** fall back to RAG to avoid guessing numbers.

### 3. RAG Pipeline (Generative)
- **Source**: Vector Store (Chunked Web Content).
- **Use Case**: Procedures, How-to, Policy explanations.
- **Model**: Llama-3 (via Ollama).
