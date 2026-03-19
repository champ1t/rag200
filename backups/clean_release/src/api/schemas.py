
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class ChatRequest(BaseModel):
    query: str = Field(..., alias="message") # Alias to match Langflow 'message'
    user: str = "langflow"
    session_id: Optional[str] = None
    top_k: int = 3
    selected_choice_id: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None

    class Config:
        populate_by_name = True

class Source(BaseModel):
    title: str
    url: str
    score: float = 0.0
    snippet: Optional[str] = None

class Choice(BaseModel):
    id: str
    label: str
    payload: Optional[Dict[str, Any]] = None

class Meta(BaseModel):
    latency_ms: float = 0.0
    run_id: str = ""
    session_id: str = ""

class ChatResponse(BaseModel):
    ok: bool = True
    route: str = "answer" # answer | needs_choice | blocked | error
    answer: str
    sources: List[Source] = Field(default_factory=list)
    choices: List[Choice] = Field(default_factory=list)
    meta: Meta = Field(default_factory=Meta)
