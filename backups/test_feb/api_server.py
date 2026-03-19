"""
FastAPI wrapper for RAG System
ใช้สำหรับ integrate กับ Langflow หรือระบบอื่นๆ

Install:
    pip install fastapi uvicorn

Run:
    uvicorn src.api_server:app --host 0.0.0.0 --port 8000
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import yaml
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from src.chat_engine import ChatEngine

app = FastAPI(
    title="RAG System API",
    description="Internal RAG system for organizational knowledge",
    version="1.0.0"
)

# CORS for Langflow
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify Langflow URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load config and initialize engine
with open("configs/config.yaml") as f:
    config = yaml.safe_load(f)

engine = ChatEngine(config)
print("[API] ChatEngine initialized")


# Request/Response models
class QueryRequest(BaseModel):
    query: str
    session_id: Optional[str] = None
    bypass_cache: Optional[bool] = False


class QueryResponse(BaseModel):
    answer: str
    route: str
    latency_ms: float
    sources: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class HealthResponse(BaseModel):
    status: str
    version: str
    teams_count: int
    positions_count: int


@app.get("/", response_model=Dict[str, str])
async def root():
    """Root endpoint"""
    return {
        "message": "RAG System API",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint for monitoring"""
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        teams_count=len(engine.directory_handler.team_index),
        positions_count=len(engine.directory_handler.position_index)
    )


@app.post("/query", response_model=QueryResponse)
async def process_query(request: QueryRequest):
    """
    Process a RAG query
    
    Example:
        POST /query
        {
            "query": "รายชื่อทีมทั้งหมด",
            "session_id": "user123",
            "bypass_cache": false
        }
    """
    try:
        # Process query
        result = engine.process(
            request.query,
            session_id=request.session_id
        )
        
        # Extract latency
        latency_ms = 0.0
        if "latencies" in result:
            total_latency = sum(result["latencies"].values())
            latency_ms = total_latency
        
        # Extract sources (if any)
        sources = []
        if "hits" in result and result["hits"]:
            sources = [
                hit.get("metadata", {}).get("url") or hit.get("metadata", {}).get("source")
                for hit in result["hits"]
                if hit.get("metadata")
            ]
            sources = [s for s in sources if s]  # Remove None
        
        return QueryResponse(
            answer=result.get("answer", "ไม่สามารถตอบได้"),
            route=result.get("route", "unknown"),
            latency_ms=latency_ms,
            sources=sources if sources else None,
            metadata={
                "intent": result.get("intent"),
                "latencies": result.get("latencies")
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/teams", response_model=Dict[str, Any])
async def list_teams():
    """List all teams in the system"""
    teams = list(engine.directory_handler.team_index.keys())
    return {
        "teams": sorted(teams),
        "count": len(teams)
    }


@app.get("/stats", response_model=Dict[str, Any])
async def get_stats():
    """Get system statistics"""
    return {
        "teams": len(engine.directory_handler.team_index),
        "positions": len(engine.directory_handler.position_index),
        "vector_store": {
            "initialized": engine.vs is not None
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
