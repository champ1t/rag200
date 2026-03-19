
import sys
import yaml
import time
import logging
from pathlib import Path
from typing import Dict, Any
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

# Add project root to path
sys.path.append(str(Path.cwd()))

from src.core.chat_engine import ChatEngine
from src.api.schemas import ChatRequest, ChatResponse, Source, Choice, Meta

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("API")

# Global Engine
engine = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Load Engine
    global engine
    try:
        config_path = Path("configs/config.yaml")
        if not config_path.exists():
            logger.error("Config file not found!")
            sys.exit(1)
            
        with open(config_path) as f:
            cfg = yaml.safe_load(f)
            
        logger.info("Initializing ChatEngine...")
        engine = ChatEngine(cfg)
        logger.info("ChatEngine Ready!")
    except Exception as e:
        logger.error(f"Failed to initialize engine: {e}")
        sys.exit(1)
        
    yield
    # Shutdown (if needed)
    logger.info("Shutting down...")

app = FastAPI(lifespan=lifespan, title="RAG Backend API", version="1.0.0")

# Security Configuration
API_KEY = "nt-rag-secret" # In production, set via os.environ

def verify_api_key(request: Request):
    # Optional: Allow bypassing if API_KEY is empty
    if not API_KEY:
        return
    
    key = request.headers.get("X-API-Key")
    if key != API_KEY:
        logger.warning(f"Unauthorized access attempt from {request.client.host}")
        raise HTTPException(status_code=401, detail="Invalid API Key")

import unicodedata

def sanitize_for_json(text: str) -> str:
    """
    Phase 174: Sanitize Output for Strict JSON Parsers (Langflow)
    Removes invisible control characters while preserving formatting (\n, \t).
    """
    if not text: return ""
    # Allow newlines, tabs, returns. Strip other control characters (Cc).
    return "".join(ch for ch in text if unicodedata.category(ch) != "Cc" or ch in "\n\t\r")

def _normalize_chat_response(result: Dict[str, Any], latency_ms: float, req: ChatRequest) -> ChatResponse:
    """
    Phase 170: API Layer Normalization
    Ensures consistent structure, type safety, and defensive defaults.
    """
    # 1. Status & Route
    ok = result.get("ok", True)
    route = str(result.get("route", "answer")).strip()
    if not route or route == "unknown":
        route = "answer"

    # 2. Answer Type Safety & Sanitization (Phase 174)
    answer = result.get("answer", "")
    if not isinstance(answer, str):
        answer = str(answer)
    answer = sanitize_for_json(answer)

    # 3. Sources Normalization
    raw_sources = result.get("sources", [])
    if not isinstance(raw_sources, list):
        raw_sources = [raw_sources] if raw_sources else []
    
    sources = []
    for s in raw_sources:
        if isinstance(s, dict):
            sources.append(Source(
                title=sanitize_for_json(s.get("title") or s.get("text") or "เอกสารที่เกี่ยวข้อง"),
                url=s.get("url") or s.get("href") or "#",
                score=float(s.get("score", 0.0)),
                snippet=sanitize_for_json(s.get("snippet", ""))
            ))

    # 4. Choices Normalization & Parsing
    raw_choices = result.get("choices", [])
    if not isinstance(raw_choices, list):
        raw_choices = []
    
    choices = []
    # If engine already provided choices in dict format
    for c in raw_choices:
        if isinstance(c, dict) and (c.get("id") or c.get("label")):
            choices.append(Choice(
                id=sanitize_for_json(str(c.get("id", c.get("label", "")))),
                label=sanitize_for_json(str(c.get("label", "เลือกรายการ"))),
                payload=c.get("payload", {})
            ))
            
    # Fallback Parsing from Answer if route suggests ambiguity but choices list is empty
    if not choices and ("ambiguous" in route or "choice" in route or route == "needs_choice"):
        lines = answer.split("\n")
        for line in lines:
            line = line.strip()
            val = None
            if line.startswith(("1. ", "2. ", "3. ", "4. ", "5. ")):
                parts = line.split(". ", 1)
                if len(parts) == 2: val = parts[1].strip()
            elif line.startswith("- "):
                val = line[2:].strip()
            
            if val and len(val) > 2 and "ระบุ" not in val:
                choices.append(Choice(
                    id=val, 
                    label=val, 
                    payload={"query": val}
                ))

    # Route Logic: If choices exist, force route to needs_choice for UI consistency
    if choices and route not in ["needs_choice", "blocked", "error"]:
        route = "needs_choice"

    # 5. Meta Data
    meta = Meta(
        latency_ms=latency_ms,
        run_id=req.session_id or str(time.time()),
        session_id=req.session_id or "default"
    )

    return ChatResponse(
        ok=ok,
        route=route,
        answer=answer,
        sources=sources,
        choices=choices,
        meta=meta
    )

def _write_metrics_csv(req: ChatRequest, resp: ChatResponse, latency_ms: float, result: Dict[str, Any]):
    """
    Phase 170: Production Metrics
    Writes detailed request signals to CSV for later analytics.
    """
    try:
        metrics_file = Path("data/metrics.csv")
        # Header with enhanced signals
        header = "timestamp,session_id,query,route,latency_ms,choices_len,sources_len,ans_len,top_k,user,ok,cache_hit,prompt_mode\n"
        
        if not metrics_file.exists():
            metrics_file.parent.mkdir(parents=True, exist_ok=True)
            with open(metrics_file, "w") as f:
                f.write(header)
        
        with open(metrics_file, "a") as f:
            ts = time.strftime("%Y-%m-%d %H:%M:%S")
            # Sanitize query for CSV (no commas/newlines)
            query_safe = str(req.query).replace(",", " ").replace("\n", " ").strip()[:50]
            
            f.write(
                f"{ts},"
                f"{req.session_id or 'anon'},"
                f"{query_safe},"
                f"{resp.route},"
                f"{latency_ms:.2f},"
                f"{len(resp.choices)},"
                f"{len(resp.sources)},"
                f"{len(resp.answer)},"
                f"{req.top_k or 3},"
                f"{req.user or 'unknown'},"
                f"{resp.ok},"
                f"{result.get('cache_hit', False)},"
                f"{result.get('prompt_mode', 'unknown')}\n"
            )
    except Exception as e:
        logger.error(f"Failed to write metrics: {e}")

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest, request: Request):
    # Verify Security
    verify_api_key(request)

    global engine
    if not engine:
        raise HTTPException(status_code=503, detail="Engine not ready")
        
    try:
        # 1. Normalize top_k (Phase 171)
        try:
            req.top_k = max(1, min(int(req.top_k), 10))
        except (TypeError, ValueError):
            req.top_k = 3
        
        t_start = time.time()
        
        # 1. Determine Input Query
        input_query = req.query
        if req.selected_choice_id:
             logger.info(f"Resolving Choice ID: {req.selected_choice_id}")
             input_query = req.selected_choice_id
        
        logger.info(f"Processing query: {input_query} (Session: {req.session_id})")
        
        # 2. Call Engine
        result = engine.process(input_query, session_id=req.session_id)
        latency_ms = (time.time() - t_start) * 1000
        
        # 3. Normalize Response (Phase 170)
        response = _normalize_chat_response(result, latency_ms, req)
        
        # 4. Structured Logging & Metrics
        logger.info(
            f"AUDIT session={req.session_id} route={response.route} latency={latency_ms:.1f}ms "
            f"choices={len(response.choices)} user={req.user}"
        )
        _write_metrics_csv(req, response, latency_ms, result)

        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing query: {e}", exc_info=True)
        return ChatResponse(
            ok=False, 
            route="error", 
            answer=f"Server Error: {str(e)}"
        )

@app.get("/health")
def health():
    # Process up check
    return {"status": "ok", "process": "up"}

@app.get("/ready")
def ready():
    # Deep check: Engine loaded + VectorStore ready
    if not engine:
        raise HTTPException(status_code=503, detail="Engine initializing")
    
    # Optional: Check internal components if possible (e.g. engine.vector_db)
    # For now, engine existence implies readiness (lifespan completes)
    return {"status": "ready", "components": ["engine", "vectorstore"]}
