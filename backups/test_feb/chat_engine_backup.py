
from __future__ import annotations

import time
import re
import datetime
import json
import difflib
import hashlib
from pathlib import Path
from typing import Dict, Any, List

from src.utils.runlog import now_ts
from src.vectorstore import build_vectorstore
import yaml
from src.vectorstore.base import SearchResult # Step 16954: For creating boosted results
from src.directory.lookup import load_records, lookup_phones, lookup_by_phone, strip_query, norm
from src.rag.handlers.greetings_handler import GreetingsHandler # Phase 97
from src.cache.semantic import SemanticCache # Phase 23
from src.ingest.fetch import fetch_with_policy, FetchResult # Phase 130
from src.rag.synonyms import expand_synonyms # Phase 174


from src.rag.retrieval_optimizer import RetrievalOptimizer
from src.rag.controller import RAGController
from src.utils.section_filter import slice_markdown_section # Assumption: found here
from src.rag.evaluator import RAGEvaluator 
from src.rag.article_interpreter import ArticleInterpreter
from src.rag.ollama_client import ollama_generate # FIXED: Added missing import
from src.ai.planner import QueryPlanner
from src.ai.slot_filler import SlotFiller
from src.directory.format_answer import format_field_only
from src.rag.handlers.directory_handler import DirectoryHandler # Phase 43
from src.rag.handlers.web_handler import WebHandler # Phase 175: Web Knowledge
# from src.main import ProcessedCache # Removed to fix ImportError 
# Better to move ProcessedCache to utils or keep it in main and import? 
# To avoid circular imports, let's duplicate or move ProcessedCache to a util file. 
# For now, I'll redefine it here or just access data directly if possible.
# Actually, ProcessedCache is simple. Let's move it to src/utils/cache.py later? 
# For now, I will implement a simple version here to avoid modifying too many files at once.

# Phase 20: Procedural/Knowledge keywords
PROCEDURAL_KEYWORDS = {
    "วิธี", "ขั้นตอน", "ตั้งค่า", "โอนสาย", "forward", "transfer", 
    "ทำยังไง", "คู่มือ", "ปัญหา", "แก้ไข", "วิธีแก้", "how to", 
    "news", "ข่าวสาร", "config", "setup", "guide", "manual",
    "ระเบียบ", "คำสั่ง", "ประกาศ", "หนังสือเวียน"
}

# Explicit contact keywords
CONTACT_KEYWORDS = {
    "เบอร์", "โทร", "ติดต่อ", "อีเมล", "fax", "แฟกซ์", "โทรสาร", "ที่อยู่"
}

# Phase 174: Content Polish & Synonym (v1.1-dev)
# Increment this when changing summary logic or formatting to force re-evaluation.
CACHE_SCHEMA_VERSION = "v180"

class ProcessedCache:
    def __init__(self, processed_dir: str = "data/processed"):
        self.processed_dir = Path(processed_dir)
        self._url_to_text: dict[str, str] = {}
        self._url_to_images: dict[str, list] = {}  # NEW: Store images per URL
        # index: normalized_anchor_text -> list of entries {href, original_text, source_url}
        self._link_index: dict[str, list[dict[str, str]]] = {}
        self._keys: list[str] = [] # Cache keys for iteration
        self._loaded = False

    def normalize_key(self, text: str) -> str:
        # Lowercase, remove special chars (keep alphanumeric and space), collapse spaces
        text = text.lower()
        text = re.sub(r"[^a-z0-9\sก-๙]", " ", text) # Keep Thai chars too if needed
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def load(self) -> None:
        if self._loaded:
            return
        if not self.processed_dir.exists():
            self._loaded = True
            return
        
        for p in self.processed_dir.glob("*.json"):
            try:
                j = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                continue
            
            url = j.get("url", "")
            text = j.get("text", "") or ""
            
            if url and text:
                self._url_to_text[url] = text
            
            # Build link index
            links = j.get("links", [])
            for link in links:
                l_text = link.get("text", "").strip()
                l_href = link.get("href", "").strip()
                if l_text and l_href:
                    norm_text = self.normalize_key(l_text)
                    if norm_text not in self._link_index:
                        self._link_index[norm_text] = []
                    
                    self._link_index[norm_text].append({
                        "href": l_href,
                        "text": l_text,
                        "source": url
                    })
            
            # Load images (NEW)
            images = j.get("images", [])
            if url and images:
                self._url_to_images[url] = images
        
        self._keys = list(self._link_index.keys())
        self._loaded = True

    def get_text(self, url: str) -> str | None:
        if not self._loaded:
            self.load()
        return self._url_to_text.get(url)

    def find_links(self, query: str) -> list[dict[str, str]]:
        if not self._loaded:
            self.load()
        return self._link_index.get(self.normalize_key(query), [])

    def find_links_fuzzy(self, query: str, threshold: float = 0.60) -> list[dict]:
        if not self._loaded:
            self.load()
            
        norm_q = self.normalize_key(query)
        if not norm_q: return []
        
        # 1. Exact match first (fast path)
        if norm_q in self._link_index:
            return [{"score": 1.0, "items": self._link_index[norm_q]}]
            
        # 2. Fuzzy match
        results = []
        # optimization: filter keys by length? or basic containment first?
        # difflib is O(N*M), so iterating all keys might be slow if many keys.
        # But for ~1000 links it's fine.
        
        for k in self._keys:
            if not k: continue # Skip empty keys
            
            # Simple substring boost
            ratio = difflib.SequenceMatcher(None, norm_q, k).ratio()
            
            # Phase 105: Token Subset Boost (Robustness)
            # If all query tokens are in the key, likely a good match (even if extra words exist)
            q_tokens = set(norm_q.split())
            k_tokens = set(k.split())
            
            is_subset = q_tokens.issubset(k_tokens) and len(q_tokens) >= 2
            
            # Substring Boost
            # Fix Phase 106: Ensure k has significant length to avoid matching "a" or empty string
            if ((norm_q in k or (len(k) > 3 and k in norm_q)) and len(norm_q) > 8) or is_subset:
                 # Boost ratio significantly
                 ratio = max(ratio, 0.85)

            if ratio >= threshold:
                results.append({
                    "score": ratio,
                    "key": k,
                    "items": self._link_index[k]
                })
        
        # Sort by score desc
        results.sort(key=lambda x: x["score"], reverse=True)
        return results

class ChatEngine:
    def __init__(self, cfg: Dict[str, Any]):
        self.cfg = cfg
        self.llm_cfg = cfg.get("llm", {})
        self.chat_cfg = cfg.get("chat", {})
        self.rag_cfg = cfg.get("rag", {})

        # Load Routing Policy
        policy_path = Path("config/routing_policy_v1.yaml")
        if policy_path.exists():
            try:
                self.routing_policy = yaml.safe_load(policy_path.read_text(encoding="utf-8")) or {}
            except Exception as e:
                print(f"[WARN] Failed to load routing policy: {e}")
                self.routing_policy = {}
        else:
            self.routing_policy = {}
        
        self.top_k = int(cfg["retrieval"]["top_k"])
        self.show_context = bool(self.chat_cfg.get("show_context", True))
        self.save_log = bool(self.chat_cfg.get("save_log", True))
        
        # Load resources
        print("[INFO] Loading resources...")
        self.vs = build_vectorstore(cfg)
        self.processed_cache = ProcessedCache("data/processed")
        self.processed_cache.load()
        self.records = load_records("data/records/directory.jsonl")
        
        # Phase 23: Knowledge Pack
        from src.rag.knowledge_pack import KnowledgePackManager
        self.kp_manager = KnowledgePackManager()
        
        # Load positions with Optimized Index (Phase 35: Scalable Lookup)
        self.position_index = {}
        self.pos_norm_map = {}  # Normalized -> [Original Roles]
        
        pos_path = Path("data/records/positions.jsonl")
        if pos_path.exists():
            for line in pos_path.read_text(encoding="utf-8").splitlines():
                if not line.strip(): continue
                try:
                    p = json.loads(line)
                    role = p.get("role", "").strip()
                    if role:
                        if role not in self.position_index:
                            self.position_index[role] = []
                        self.position_index[role].append(p)
                except Exception:
                    pass
                    
        print(f"[INFO] Resources loaded. Position Index Size: {len(self.position_index)}")

        # Phase 69: Team Index
        self.team_index = {}
        team_path = Path("data/records/teams.jsonl")
        if team_path.exists():
            for line in team_path.read_text(encoding="utf-8").splitlines():
                if not line.strip(): continue
                try:
                    t = json.loads(line)
                    team_name = t.get("team", "").strip()
                    if team_name:
                         self.team_index[team_name] = t
                except Exception:
                     pass
        print(f"[INFO] Resources loaded. Team Index Size: {len(self.team_index)}")
        
        # Phase 43: Directory Handler (Encapsulates Person/Position Logic)
        self.directory_handler = DirectoryHandler(self.position_index, self.records, self.team_index)
        
        # Context State
        self.last_context: Dict[str, Any] | None = None
        self.proc_ctx: Dict[str, Any] | None = None  # Phase 21: Procedural Context
        
        # Clarify Session State (Phase 15: AI-First Orchestration)
        self.pending_clarify: Dict[str, Any] | None = None
        self.pending_kp_clarify: Dict[str, Any] | None = None # Phase 25: KP Clarification Memory
        self.pending_question: Dict[str, Any] | None = None   # Phase 80: Conversational Follow-up

        # Initialize Cache
        self.cache = SemanticCache() if self.rag_cfg.get("use_cache", True) else None
        
        # Initialize RAG Controller
        self.controller = RAGController(self.llm_cfg)
        
        # Initialize RAG Evaluator
        self.evaluator = RAGEvaluator(self.llm_cfg)
        
        # Initialize Retrieval Optimizer
        self.retrieval_optimizer = RetrievalOptimizer(self.llm_cfg)
        
        # Initialize AI Planner & Slot Filler (Phase 15)
        self.planner = QueryPlanner(self.llm_cfg)
        self.slot_filler = SlotFiller(self.llm_cfg)
        
        # Initialize Article Interpreter (Phase 16)
        self.article_interpreter = ArticleInterpreter(self.llm_cfg, ux_cfg=self.cfg.get("ux", {}))
        
        # Phase 34: Intent Router
        from src.ai.router import IntentRouter
        from src.ai.corrector import QueryCorrector
        
        # Optimization (Phase 127): Use fast model for Routing
        # We strip the 'model' key to force Router to use its default (llama3.2:3b)
        # unless 'router_model' is explicitly defined in config.
        router_llm_cfg = self.llm_cfg.copy()
        if "router_model" in self.cfg.get("rag", {}):
            router_llm_cfg["model"] = self.cfg["rag"]["router_model"]
        else:
             # Force default fallback (llama3.2:3b) by removing specific model dictation
             # assuming user has llama3.2 or similar light model installed.
             router_llm_cfg.pop("model", None)
             
        self.router = IntentRouter(router_llm_cfg)
        self.corrector = QueryCorrector(self.llm_cfg)
        
        # Phase 97: Pro-Level Caching
        self.greetings_handler = GreetingsHandler()
        
        # Phase R7-Fix: Initialize manager explicitly to prevent crash & enable cache globally
        from src.rag.cache_manager import CacheManager
        self.cache_manager = CacheManager(self.cache)

        # Phase 175: Web Handler
        self.web_handler = WebHandler(self.llm_cfg)

    def reset_context(self):
        """Reset conversation context associated with the current session."""
        self.pending_question = None
        self.pending_kp_clarify = None
        self.pending_clarify = None
        self.proc_ctx = None
        self.last_context = None


    # Phase 80: Conversational Follow-up Resolver
    def _resolve_pending_followup(self, q: str, latencies: Dict[str, float]) -> Dict[str, Any] | None:
        """
        Attempts to resolve a pending ambiguity question using short-term memory.
        Returns response dict if resolved/handled, else None.
        """
        pq = self.pending_question
        if not pq: return None
        
        # 1. Check TTL (60s)
        created_at = pq.get("created_at", 0)
        if time.time() - created_at > 60:
            print("[DEBUG] Pending Question Expired")
            self.pending_question = None
            return None
            
        q_clean = q.strip().lower()
        candidates = pq.get("candidates", [])
        kind = pq.get("kind", "unknown")
        
        # Keywords
        YES_WORDS = ["ใช่", "ใช่ครับ", "ใช่ค่ะ", "เอาอันนี้", "ถูก", "ok", "โอเค", "yes", "y", "ถูกต้อง", "แม่นแล้ว", "ช่าย", "แม่น", "confirm", "ยืนยัน"]
        NO_WORDS = ["ไม่", "ไม่ใช่", "ไม่เอา", "no", "n", "ยกเลิก", "cancel", "ไม่ครับ", "ไม่ค่ะ", "ไม่จ้า", "เปลี่ยน", "reject"]
        DETAIL_WORDS = ["ชื่อเต็ม", "ขอชื่อเต็ม", "ขอรายละเอียด", "รายละเอียด", "เอาแบบเต็ม", "เต็มๆ", "full", "detail", "more", "ชื่อจริง"]
        
        is_yes = any(w in q_clean for w in YES_WORDS) # Changed from equality to inclusion for robust matching? No, existing was strict eq.
        # User requirement 1: "Recognize FOLLOWUP_ACTION tokens".
        # Let's stick to containment for short phrases or equality for single words.
        # Original was: `any(w == q_clean ...)`
        # Let's expand to `w in q_clean` if q_clean is short?
        # Actually user tokens like "ขอชื่อเต็ม" might be embedded.
        is_yes = any(w in q_clean for w in YES_WORDS)
        is_no = any(w in q_clean for w in NO_WORDS)
        is_detail = any(w in q_clean for w in DETAIL_WORDS)
        
        # Logic A: NO -> Cancel
        if is_no and not is_yes: 
            self.pending_question = None
            return {
                "answer": "รับทราบครับ ยกเลิกการเลือก หากต้องการค้นหาใหม่พิมพ์ได้เลยครับ",
                "route": "followup_cancel",
                "latencies": latencies
            }
            
        # Logic B: Selection by Number
        selected_idx = -1
        nums = re.findall(r"\d+", q_clean)
        if nums:
             try:
                 idx = int(nums[0]) - 1 
                 if 0 <= idx < len(candidates):
                     selected_idx = idx
             except: pass

        # Logic C: Fuzzy Match (If no number selected)
        if selected_idx == -1:
            from difflib import SequenceMatcher
            best_score = 0.0
            best_idx = -1
            
            # Normalize for matching: remove dots, spaces
            def normalize_for_match(text):
                return text.replace(".", "").replace(" ", "").lower()
            
            q_norm = normalize_for_match(q_clean)
            
            for i, cand in enumerate(candidates):
                label = str(cand.get("label", "")).lower()
                label_norm = normalize_for_match(label)
                
                # Check containment with normalized text
                # Example: "ผส บลตน" normalized to "ผสบลตน" matches "ผส.บลตน." normalized to "ผสบลตน"
                if label_norm in q_norm or q_norm in label_norm:
                    system_prompt = (
            "You are an AI Assistant for an Internal Enterprise System (SMC).\n"
            "Your audience is authorized technical staff. You must provide accurate, technical answers based strictly on the provided context.\n"
            "Reference:\n"
            "- Correctness > Intelligence. Do not guess.\n"
            "- If the context contains credentials, IPs, or commands, display them EXACTLY as shown (do not mask). This is an internal tool.\n"
            "- Ignore irrelevant noise (visitor counters, menus) if present in context.\n"
            "- If the context discusses a procedure, extract the steps clearly.\n"
            "- Do not add generic safety warnings (e.g. 'consult admin') unless necessary. Users ARE the admins.\n"
            "- Answer in Thai (Technical terms in English).\n"
        )    
                # Also check original non-normalized for exact matches
                elif label in q_clean or q_clean in label:
                    score = 0.95
                else:
                    # SequenceMatcher on normalized text
                    score = SequenceMatcher(None, q_norm, label_norm).ratio()
                
                if score > best_score:
                    best_score = best_score
                    best_idx = i
            
            # Threshold: 0.7 for normalized fuzzy matching
            if best_score > self.cfg.get("followup_fuzzy_threshold", 0.7):
                 selected_idx = best_idx

        # Logic D: Yes/Detail Meta-Command
        if is_yes or is_detail:
             if selected_idx == -1:
                 # No specific selection found
                 if len(candidates) == 1:
                     selected_idx = 0
                 else:
                     # Ambiguous
                     msg = f"หมายถึงข้อไหนครับ? (กรุณาระบุเลข 1-{len(candidates)})"
                     if is_detail: msg = f"ต้องการข้อมูลเต็มของข้อไหนครับ? (กรุณาระบุเลข 1-{len(candidates)})"
                     
                     return {
                        "answer": msg,
                        "route": "followup_reask",
                        "latencies": latencies
                     }
        
        # If we reached here with selected_idx == -1, function returns None (Fallthrough)
        # UNLESS valid selection was made via Logic B or C (without Yes/Detail tokens)
        
        # EXECUTE RESOLUTION (Logic E)
        if selected_idx != -1:
            selection = candidates[selected_idx]
            print(f"[DEBUG] Follow-up Resolved: Choice {selected_idx+1} -> {selection['label']}")
            
            mode = pq.get("mode", "holder")
            self.pending_question = None # Clear state
            
            target_key = selection.get("key", selection.get("label"))
            target_label = selection.get("label")
            
            # Mode A: Phone Lookup (via ContactHandler)
            if mode == "phone":
                print(f"[DEBUG] resolving {target_label} in PHONE mode")
                # Construct query for ContactHandler
                phone_q = f"เบอร์โทร {target_label}"
                from src.rag.handlers.contact_handler import ContactHandler
                return ContactHandler.handle(phone_q, self.records, directory_handler=self.directory_handler)
            
            # Mode B: Standard Info Lookup
            
            if kind == "team_choice":
                return self.directory_handler.handle_team_lookup(target_key)
                
            elif kind == "role_choice" or kind == "management_choice":
                return self.directory_handler.handle_management_query(target_key)
            
        return None

        


    def warmup(self):
        print(f"[CHAT] warmup: model={self.llm_cfg.get('model')} base_url={self.llm_cfg.get('base_url')}")
        try:
            _ = ollama_generate(
                base_url=self.llm_cfg.get("base_url", "http://localhost:11434"),
                model=self.llm_cfg.get("model", "llama3.2:3b"),
                prompt="ตอบว่า: พร้อมใช้งาน",
                temperature=0.0,
            )
            print("[CHAT] LLM warmed up")
        except Exception as e:
            print(f"[CHAT] LLM warm-up skipped: {e}")

    def process(self, q: str, session_id: str = "default") -> Dict[str, Any]:
        """
        Process a query query_text and return a dictionary with:
        - answer: str
        - route: str
        - context: str (optional)
        - latency: dict (breakdown)
        - metadata: dict
        """
        t_start = time.time()

        # Phase 171: Session Isolation
        # If session_id changed, reset pending states
        if hasattr(self, "_last_session_id") and self._last_session_id != session_id:
            print(f"[DEBUG] Session Switch Detected ({self._last_session_id} -> {session_id}). Resetting context.")
            self.reset_context()
        self._last_session_id = session_id

        # Phase 174: Initialize Query Tracking
        original_q_str = q
        synonym_active = False
        applied_rule = None
        
        # Telemetry Init (Phase 25)
        
        # Telemetry Init (Phase 25)
        telemetry_data = {
            "timestamp": t_start,
            "query": q,
            "mode": "FULL", # Will be updated
            "route": "unknown",
            "clarify_asked": False,
            "synonym_rule": applied_rule,
            "synonym_rollback": False,
            "pack_hit": False
        }
        
        bypass_kp = False # Flag to skip Knowledge Pack (e.g. if explicitly falling back from HowTo)
        
        latencies = {
            "routing": 0.0,
            "embed": 0.0,
            "vector_search": 0.0,
            "bm25": 0.0,
            "fusion": 0.0,
            "controller": 0.0,
            "retrieval_opt": 0.0,
            "generator": 0.0,
            "evaluator": 0.0,
            "clarify": 0.0,
            "total": 0.0,
            "llm": 0.0  # Sum of all LLM stages
        }
        
        # 0. Answer Mode Detection (Phase 25)
        # Check for output shaping intents
        answer_mode = "FULL"
        q_lower = q.lower()
        if any(k in q_lower for k in ["ขอแค่เบอร์", "เอาแค่เบอร์", "phone only", "only phone"]):
            answer_mode = "PHONE_ONLY"
        elif any(k in q_lower for k in ["ขอแค่ ip", "เอาแค่ ip", "ip only", "only ip"]):
            answer_mode = "IP_ONLY"
        elif any(k in q_lower for k in ["ขอแค่ลิงก์", "ขอ link", "url only", "link only", "ขอลิงก์"]):
            answer_mode = "URL_ONLY"
        if any(k in q_lower for k in ["สรุปสั้นๆ", "summary", "short"]):
            answer_mode = "SUMMARY"
            
        # 0.4 Conversational Follow-up Resolver (Phase 80)
        # Check if we are pending a question answer
        bypass_cache = False
        if self.pending_question:
             print(f"[DEBUG] Attempting to resolve pending question: '{q}'")
             followup_res = self._resolve_pending_followup(q, latencies)
             if followup_res:
                 # Success! Return result bypassing cache/router
                 followup_res = self._apply_answer_mode(followup_res, answer_mode)
                 return followup_res
             
             bypass_cache = True
             print("[DEBUG] Pending Question active -> Bypassing Cache for this turn.")
             
        # Rule: Explicitly bypass cache for short follow-up words even if pending state missing (Safety)
        # Prevents "Yes" matching a cached "Yes" (unlikely but safe)
        if len(q) < 10:
            FOLLOWUP_TOKENS = ["ใช่", "ไม่", "เอา", "ข้อ", "choice", "yes", "no"]
            if any(t in q_lower for t in FOLLOWUP_TOKENS):
                bypass_cache = True
                print("[DEBUG] Short Follow-up detected -> Bypassing Cache.")

        # 0.5 Pending Clarification Resolver (Phase 26.5)
        # Intercepts input if we are waiting for a Knowledge Pack scope
        if self.pending_kp_clarify:
            print(f"[DEBUG] Resolving Pending KP Clarification: {q}")
            
            p_state = self.pending_kp_clarify
            created_ts = p_state.get("created_ts", time.time())
            turns = p_state.get("turns", 0)
            
            # 1. TTL Check (60s)
            if time.time() - created_ts > 60:
                print("[DEBUG] Clarification Expired (TTL)")
                self.pending_kp_clarify = None
                telemetry_data["clarify_expired"] = True
                # Fall through to standard processing
            else:
                # 2. Interruption Check (New Query Detection)
                # Heuristic: Match typical new query patterns vs Valid Scope Reply
                reply_raw = q.lower().strip()
                reply_clean = re.sub(r"[\[\]\(\)]", "", reply_raw).strip()
                for w in ["ขอ", "เลือก", "เอา", "ครับ", "ค่ะ"]:
                    reply_clean = reply_clean.replace(w, "").strip()
                
                # Keywords that suggest a new intent (not a scope)
                NEW_INTENT_KWS = ["ข่าว", "แจ้ง", "ตาราง", "เบอร์", "โทร", "ip", "smtp", "dns", "vlan", "config", "วิธี", "ทำยังไง", "คู่มือ", "ปัญหา", "แก้ไข", "how to"]
                
                # Check for "All" intent (Valid Scope)
                is_all = any(w in reply_clean for w in ["all", "ทั้งหมด", "ทุกรายการ"])
                
                # Check if it matches any option (Valid Scope)
                options = p_state.get("options", [])
                matched_scope = None
                if not is_all:
                    for opt in options:
                         if opt.lower() in reply_clean or reply_clean in opt.lower():
                             matched_scope = opt; break
                    
                    if not matched_scope:
                         # Aliases
                         if any(k in reply_clean for k in ["nt", "nt1", "n t 1", "bkk"]): matched_scope = "NT1"
                         elif any(k in reply_clean for k in ["region", "ภูมิภาค", "ต่างจังหวัด", "ตจว"]): matched_scope = "ภูมิภาค (Region)"
                         elif any(k in reply_clean for k in ["isp", "core"]): matched_scope = "ISP"
                
                # INTERRUPTION DECISION
                is_interruption = False
                # If input is long (> 20 chars) and NOT 'all' -> Likely a new query
                if len(reply_raw) > 20 and not is_all:
                    is_interruption = True
                # If input contains new intent keywords AND no matched scope -> Interrupt
                elif any(k in reply_raw for k in NEW_INTENT_KWS) and not matched_scope and not is_all:
                    is_interruption = True
                # Multi-phrase check (>= 3 spaces) -> Likely sentence
                elif reply_raw.count(" ") >= 3:
                    is_interruption = True
                    
                if is_interruption:
                    print(f"[DEBUG] Clarification Interrupted by new query: {q}")
                    self.pending_kp_clarify = None
                    telemetry_data["clarify_interrupted"] = True
                    # Fall through to normal processing
                
                else:
                    # Not an interruption, treat as an attempt to answer scope
                    if is_all or matched_scope:
                        # VALID RESOLUTION
                        base_q = p_state.get("original_query", "")
                        saved_mode = p_state.get("pending_answer_mode", "FULL")
                        
                        final_query = f"{base_q} {'ทั้งหมด' if is_all else matched_scope}"
                        print(f"[DEBUG] Clarification Resolved -> {final_query}")
                        
                        self.pending_kp_clarify = None
                        if is_all: telemetry_data["resolved_all"] = True
                        else: telemetry_data["resolved_scope"] = matched_scope
                        
                        if self.kp_manager:
                            kp_result = self.kp_manager.lookup(final_query)
                            if kp_result:
                                telemetry_data["clarify_resolved"] = True
                                telemetry_data["route"] = "knowledge_pack_resolved"
                                telemetry_data["pack_hit"] = True
                                self._log_telemetry(telemetry_data, latencies)
                                
                                res = {
                                     "answer": kp_result["answer"],
                                     "route": "knowledge_pack_resolved",
                                     "latencies": latencies,
                                     "hits": kp_result["hits"]
                                }
                                return self._apply_answer_mode(res, saved_mode)
                        
                        # Fallback if manager missing or empty result (rare)
                        pass 
                        
                    else:
                        # INVALID SCOPE REPLY (and not interruption)
                        # Check Max Retries
                        if turns >= 1: # Already re-asked once
                             print("[DEBUG] Clarification Failed (Max Turns)")
                             self.pending_kp_clarify = None
                             telemetry_data["clarify_failed"] = True
                             # Fall through to normal processing (treat as new query or just give up?)
                             # Requirement: "Clear pending_kp and route normally"
                        else:
                             # Re-ask
                             print("[DEBUG] Clarification Re-ask")
                             self.pending_kp_clarify["turns"] = turns + 1
                             options = p_state.get("options", [])
                             options_str = " ".join([f"[{opt}]" for opt in options])
                             return {
                                "answer": f"ขออภัยครับ กรุณาเลือกขอบเขตจาก: {options_str} หรือพิมพ์ 'ทั้งหมด'",
                                "route": "knowledge_pack_clarify_reask",
                                "latencies": latencies
                             }

        # ---------------------------------------------------------
        # INPUT SANITIZATION & PRE-FILTERS (Phase 171)
        # ---------------------------------------------------------
        
        # 1. Empty or Whitespace Only
        q_strip = q.strip()
        if not q_strip:
            return {
                "answer": "สวัสดีครับ มีอะไรให้ผมช่วยค้นหาข้อมูลหรือเบอร์โทรศัพท์ในวันนี้ครับ?",
                "route": "quick_reply",
                "latencies": latencies
            }

        # 2. Excessively Long Input (Anti-DoS / Performance)
        if len(q) > 2000:
            print(f"[DEBUG] Truncating excessively long query ({len(q)} -> 1000)")
            q = q[:1000] # Truncate for safety
            q_strip = q.strip()
            telemetry_data["query_truncated"] = True

        # 3. Numeric or Emoji Only (Deterministic Fallback)
        is_numeric = q_strip.replace(".", "", 1).isdigit()
        has_text = any(c.isalpha() or '\u0e00' <= c <= '\u0e7f' for c in q_strip)
        
        if is_numeric or not has_text:
            print(f"[DEBUG] Non-text query detected: '{q_strip}'")
            return {
                "answer": "ขออภัยครับ ผมไม่เข้าใจคำค้นหาของคุณ กรุณาพิมพ์เป็นข้อความ เช่น 'เบอร์ CSOC' หรือ 'วิธีเช็ค IP' ครับ",
                "route": "quick_reply",
                "latencies": latencies
            }

        # ---------------------------------------------------------
        # DETERMINISTIC FAST-PATHS / EARLY EXITS (Phase 170)
        # ---------------------------------------------------------
        
        # Guard A: Dispatch Mapper Handler (Province Mapping)
        try:
            from src.rag.handlers.dispatch_mapper import DispatchMapper
            if DispatchMapper.is_match(q):
                print(f"[DEBUG] DispatchMapper Intent Triggered: {q}")
                if not self.processed_cache:
                    from src.chat_engine import ProcessedCache 
                    self.processed_cache = ProcessedCache()
                    self.processed_cache.load()
                
                dispatch_res = DispatchMapper.handle(q, self.processed_cache)
                if dispatch_res and dispatch_res.get("route") != "dispatch_mapper_error":
                     return {
                         "answer": dispatch_res.get("answer"),
                         "route": dispatch_res.get("route"),
                         "latencies": latencies,
                         "debug_info": {"handler": "DispatchMapper"},
                         "context": dispatch_res.get("context")
                     }
        except Exception as e:
            print(f"[DEBUG] DispatchMapper Error: {e}")

        # Guard B: Credential / Secret Guard (Safety)
        q_sec = q.lower()
        sec_keywords = ["password", "passcode", "pwd", "รหัสผ่าน", "รหัสเข้า", "default pass", "admin pass", "root pass"]
        has_sec_kw = any(k in q_sec for k in sec_keywords)
        high_risk_targets = ["admin", "ont", "router", "cpe", "root", "super", "system", "dms", "radius", "tacacs"]
        is_target_risk = any(t in q_sec for t in high_risk_targets)
        
        if has_sec_kw or is_target_risk:
             # ONT Specific logic
             if "ont" in q_sec and "password" in q_sec:
                  sec_cfg = self.cfg.get("security", {})
                  allow_redirect = sec_cfg.get("allow_credential_redirect", False)
                  redirect_mode = sec_cfg.get("credential_redirect_mode", "block")
                  allowlist = sec_cfg.get("credential_article_allowlist", [])
                  
                  matched_link = None
                  if allow_redirect:
                      fuzzy_results = self.processed_cache.find_links_fuzzy(q) if self.processed_cache else []
                      if fuzzy_results:
                          for res in fuzzy_results:
                              for item in res.get("items", []):
                                  url_lower = item.get("href", "").lower()
                                  if any(allowed.lower() in url_lower for allowed in allowlist):
                                      matched_link = item
                                      matched_link["url"] = item.get("href")
                                      break
                              if matched_link: break
                  
                  if matched_link and redirect_mode == "redirect_only":
                      return {
                          "answer": (f"⚠️ **ข้อมูลจำกัดสิทธิ์ (Restricted Content)**\n\nระบบไม่สามารถแสดงเนื้อหารหัสผ่านได้ แต่พบเอกสารที่เกี่ยวข้อง:\n"
                                     f"🔗 **[คลิกเพื่อเปิดอ่าน (ต้องมีสิทธิ์ SMC)]({matched_link['url']})**\n\n*(กรุณาตรวจสอบสิทธิ์การเข้าถึงผ่านระบบภายใน)*"),
                          "route": "rag_credential_redirect",
                          "latencies": latencies
                      }
                  return {
                      "answer": ("🔒 **ขออภัยครับ ระบบไม่สามารถแสดงรหัสผ่าน ONT ได้เนื่องจากนโยบายความปลอดภัย**\n\n📌 **คำแนะนำ**:\n- รหัสผ่าน ONT เป็นข้อมูลเฉพาะของแต่ละพื้นที่/ชุมสาย\n- กรุณาติดต่อ **ทีม OMC ประจำเขต** หรือเปิด Ticket พร้อมระบุ **รุ่นและ Node** ที่ต้องการ"),
                      "route": "rag_security_guided",
                      "latencies": latencies
                  }
             
             # Patterns (Admin Admin)
             if "admin" in q_sec and ("admin" in q_sec.replace("admin", "", 1) or "password" in q_sec or "default" in q_sec):
                 return {
                     "answer": ("🔒 **ระงับการตอบกลับ (Security Restricted)**\n\nระบบตรวจพบแพทเทิร์นการขอรหัสผ่าน Default/Admin ซึ่งขัดต่อนโยบายความปลอดภัย (Security Policy)"),
                     "route": "rag_security_guided",
                     "latencies": latencies
                 }
             
             # General Block
             if has_sec_kw and is_target_risk:
                 return {
                     "answer": ("🔒 **ขออภัยครับ ระบบไม่สามารถแสดงรหัสผ่านได้เนื่องจากนโยบายความปลอดภัย (Security Policy)**\n\n📌 **ช่องทางดำเนินการที่แนะนำ**: ติดต่อทีม **NOC/OMC** หรือเปิด Ticket ตามระเบียบปฏิบัติ"),
                     "route": "rag_security_guided",
                     "latencies": latencies
                 }

        # Guard C: Ambiguous / Short Token Guard
        q_clean_for_guard = q.strip().lower()
        ambiguous_terms = ["sbc", "network", "omc", "bras", "access", "core", "metro", "report", "test", "wifi"]
        if (len(q_clean_for_guard.split()) == 1 and len(q_clean_for_guard) < 15 and q_clean_for_guard.isalpha() and q_clean_for_guard not in ["hi", "hello", "test", "ping"]) or q_clean_for_guard in ambiguous_terms:
             return {
                 "answer": f"คำค้นหา '{q}' กว้างเกินไปครับ กรุณาระบุให้ชัดเจน เช่น '{q} เบอร์โทร' หรือ 'วิธีแก้ปัญหา {q}'",
                 "route": "contact_ambiguous",
                 "latencies": latencies
             }

        # Guard D: Quick Replies (Chitchat)
        quick_replies = {
            "hi": "สวัสดีครับ มีอะไรให้ผมช่วยค้นหาในวันนี้ครับ?",
            "hello": "สวัสดีครับ ต้องการทราบข้อมูลด้านไหนครับ?",
            "สวัสดี": "สวัสดีครับ ผมคือผู้ช่วยค้นหาข้อมูลองค์กร มีอะไรให้ช่วยไหมครับ?",
            "test": "ระบบพร้อมใช้งานครับ (Online)",
            "ขอบคุณ": "ยินดีให้บริการครับ"
        }
        if q_clean_for_guard in quick_replies:
             return {
                 "answer": quick_replies[q_clean_for_guard],
                 "route": "quick_reply",
                 "latencies": latencies
             }


        
        # Logic C: Follow-up State (Phase 48)
        # Check if we are awaiting a province for Dispatch Mapper
        current_ctx = self.last_context.get("context") if self.last_context else None
        if current_ctx == "awaiting_province" and len(q) < 50:
            print(f"[DEBUG] Context: Awaiting Province -> '{q}'")
            # Route to DispatchMapper as Followup
            try:
                from src.rag.handlers.dispatch_mapper import DispatchMapper
                if not self.processed_cache:
                    from src.chat_engine import ProcessedCache 
                    self.processed_cache = ProcessedCache()
                    self.processed_cache.load()
                    
                dispatch_res = DispatchMapper.handle_followup(q, self.processed_cache)
                # Return immediately (clearing context happens automatically if we don't return it again?)
                # Actually we should decide if we want to clear context. 
                # If answer successful, context is cleared (by not returning it).
                # If fail, maybe keep it? DispatchMapper decides.
                return {
                     "answer": dispatch_res.get("answer"),
                     "route": dispatch_res.get("route"),
                     "latencies": latencies,
                     "context": dispatch_res.get("context") # Pass new context if any
                }
            except Exception as e:
                print(f"[DEBUG] Dispatch Followup Error: {e}")
                # Fall through

        # ---------------------------------------------------------
        # INTENT ROUTING (Phase 34)
        # ---------------------------------------------------------
        t0 = time.time()
             
        # Phase 34: Hybrid Intent Routing
        # Classify query before proceeding to specialized handlers
        
        # Phase R5: Hard Intent Override for Concepts (Moved UP for Speed)
        # Check explicit question pattern
        force_concept_kws = ["คืออะไร", "what is", "meaning", "concept", "theory", "ทฤษฎี", "หมายถึง", "definition"]
        force_concept_terms = ["rag", "ospf", "isis", "tacacs", "bgp", "vxlan", "sd-wan"] 
        sensitive_terms = ["password", "admin", "login", "user", "root", "secret", "รหัส"]
        q_lower_check = q.lower()
        is_sensitive = any(s in q_lower_check for s in sensitive_terms)
        
        override_intent = None
        if any(k in q_lower_check for k in force_concept_kws) and not is_sensitive:
             print(f"[DEBUG] Intent Override: '{q}' -> EXPLAIN (Keyword Match)")
             override_intent = "EXPLAIN"
        # Check noun-only query (e.g. "Simple OSPF")
        elif any(f" {t} " in f" {q_lower_check} " for t in force_concept_terms):
             has_action = any(k in q_lower_check for k in ["set", "config", "ตั้งค่า", "แก้", "fix", "install", "ลง"])
             if len(q.split()) <= 4 and not has_action:
                  print(f"[DEBUG] Intent Override: '{q}' -> EXPLAIN (Term Match)")
                  override_intent = "EXPLAIN"
        
        if override_intent:
             routing_res = {"intent": override_intent, "confidence": 1.0, "reason": "Keyword Override"}
        else:
             # Phase 174 Fix: Use original query for routing to avoid synonym confusion
             routing_res = self.router.route(original_q_str)
             
        intent = routing_res["intent"]
        
        # Phase 34: Auto-Correction for Fallback Intents
        # If intent is GENERAL_QA (fallback) try to correct typos (e.g. "ดบอร์โทร" -> "เบอร์โทร")
        if intent == "GENERAL_QA" and len(original_q_str) > 3:
            q_corrected = self.corrector.correct(original_q_str)
            if q_corrected and q_corrected != original_q_str:
                 print(f"[DEBUG] Corrected Query: '{original_q_str}' -> '{q_corrected}'")
                 original_q_str = q_corrected # Update original for routing retry
                 routing_res = self.router.route(original_q_str)
                 intent = routing_res["intent"]

        confidence = routing_res["confidence"]
        
        # Old Override Block Removed

        telemetry_data["intent"] = intent
        telemetry_data["intent_conf"] = confidence
        print(f"[DEBUG] Intent: {intent} ({confidence}) Reason: {routing_res.get('reason')}")

        # Phase 97: Pro-Level Greeting Handler (Deterministic & No-Cache)
        greeting_resp = self.greetings_handler.handle(q, intent)
        if greeting_resp:
            print(f"[CHAT] Greeting Handler Hit: {q}")
            latencies["total"] = (time.time() - t_start) * 1000
            greeting_resp["latencies"] = latencies
            greeting_resp["route"] = "greeting_deterministic"
            return greeting_resp

        # Phase 87/90: Override CLARIFY for Knowledge/Procedure Queries
        # Route to Article-First (HOWTO_PROCEDURE) instead of slow RAG path
        KNOWLEDGE_KEYWORDS = ["ความรู้", "คู่มือ", "manual", "แนวทาง", "วิธี", "ขั้นตอน", 
                              "howto", "config", "แก้ไข", "ตั้งค่า", "ทำอย่างไร", "how to"]
        
        q_stripped = q.lower()
        # Remove polite particles for length check
        for particle in ["ครับ", "ค่ะ", "คะ", "จ้า"]:
            q_stripped = q_stripped.replace(particle, "")
        q_stripped = q_stripped.strip()
        
        has_knowledge_kw = any(kw in q.lower() for kw in KNOWLEDGE_KEYWORDS)
        
        if intent == "CLARIFY" and has_knowledge_kw and len(q_stripped) >= 6:
            print(f"[DEBUG] Overriding CLARIFY -> HOWTO_PROCEDURE (Knowledge keyword detected: '{q}')")
            intent = "HOWTO_PROCEDURE"
            routing_res["intent"] = "HOWTO_PROCEDURE"
            routing_res["reason"] = "Knowledge keyword override (Article-First)"

        # Fix 1 (Phase 102): Knowledge Alias Trigger for Short Technical Topics
        # e.g. "sbc ip" -> HOWTO_PROCEDURE (even without "knowledge" keyword)
        
        # Check for Strong Link Match first
        link_hits = self.processed_cache.find_links_fuzzy(q_stripped, threshold=0.95)
        is_link_match = link_hits and link_hits[0]["score"] >= 0.95
        
        # Check if valid team/position (to avoid overriding valid lookups)
        is_valid_team = False
        if intent == "TEAM_LOOKUP":
             # Simple check against team index keys
             is_valid_team = any(k in q_stripped for k in self.team_index.keys())
             
        # Allow overriding CONTACT/TEAM if it's a specific link match OR a generic tech alias that isn't a verified team
        allowed_intents = ["GENERAL_QA", "CLARIFY", "CONTACT_LOOKUP", "TEAM_LOOKUP"]
        
        if intent in allowed_intents:
             q_tokens = q_stripped.split()
             # Logic: Short (<=3 words) AND Technical (English chars present)
             is_tech_pattern = len(q_tokens) <= 3 and re.search(r"[a-zA-Z]", q_stripped) and len(q_stripped) > 2
             
             # COND 1: Exact Link Match -> Force HowTo
             # COND 2: Tech Pattern AND NOT Valid Team AND NOT Contact Query -> Force HowTo
             should_override = False
             reason = ""
             
             # Check for explicit contact keywords to prevent overriding valid contact lookups
             # e.g. "เบอร์งาน FTTx" should NOT be coerced to HowTo just because it has english chars.
             has_contact_kw = any(k in q_stripped for k in ["เบอร์", "โทร", "phone", "contact", "call", "ติดต่อ"])
             
             if is_link_match:
                  should_override = True
                  reason = "Direct Link Match (Article-First)"
             elif is_tech_pattern and not is_valid_team and not has_contact_kw:
                  should_override = True
                  reason = "Tech Pattern Alias Trigger (Not a Team)"
                  
             if should_override:
                  print(f"[DEBUG] Knowledge Alias Trigger: '{q}' -> Forcing HOWTO_PROCEDURE ({reason})")
                  intent = "HOWTO_PROCEDURE"
                  routing_res["intent"] = "HOWTO_PROCEDURE" 
                  routing_res["reason"] = reason



        # ---------------------------------------------------------
        # Phase 97: Strict Cache Check (Moved UP before Handlers)
        # ---------------------------------------------------------
        if self.cache and not bypass_cache:
            # Check cache using strict intent/route context
            # Map intent to route for strict checking
            cache_route = "rag" # Default
            if intent == "CONTACT_LOOKUP": cache_route = "contact_lookup"
            elif intent == "PERSON_LOOKUP": cache_route = "person_lookup"
            elif intent == "REFERENCE_LINK": cache_route = "link_lookup"
            elif intent == "NEWS_SEARCH": cache_route = "news_search"
            elif intent == "HOWTO_PROCEDURE": cache_route = "article_answer"
            
            cached = self.cache.check(
                q, 
                intent=intent, 
                route=cache_route, 
                filter_meta={"model": self.llm_cfg.get("model", "unknown")}
            )
            
            if cached:
                # Phase 30: Cache Governance
                # If cached answer is long (likely RAG) but missing sources, ignore it to force re-generation with sources.
                ans = cached["answer"]
                has_sources = "แหล่งข้อมูลอ้างอิง:" in ans
                is_long = len(ans) > 100
                # Relax Governance for General Fallback (which naturally has no sources)
                is_general_fallback_answer = "ไม่พบเอกสารภายใน" in ans or "หลักการทั่วไป" in ans
                
                if is_long and not has_sources and not is_general_fallback_answer:
                    print(f"[DEBUG] Cache Governance: Rejected valid cache because missing evidence metadata (len={len(ans)})")
                    telemetry_data["cache_refusal_missing_refs"] = True
                else:
                    latencies["total"] = cached["latency"]
                    latencies["cache_hit"] = True
                    return {
                        "answer": cached["answer"],
                        "route": "cache_hit",
                        "latencies": latencies,
                        "score": cached["score"]
                    }


        # Phase 82: Explicit CLARIFY Handler
        # Bypass cache/RAG for ambiguous queries, delegate to DirectoryHandler to find candidates.
        if intent == "CLARIFY":
             print("[DEBUG] Handling CLARIFY intent -> Deterministic Suggestions")
             q_lower = q.lower()
             
             # 1. Mode Detection
             mode = "unknown"
             if any(k in q_lower for k in ["เบอร์", "โทร", "phone", "contact", "call", "ติดต่อ"]):
                 mode = "phone"
             elif any(k in q_lower for k in ["ใคร", "who", "ตำแหน่ง", "ผู้ดำรง", "holder", "person"]):
                 mode = "holder"
             
             # 2. Target Detection & Suggestion
             suggestions = []
             kind = "unknown"
             
             # Cleanup query for suggestion lookup
             # Remove triggers
             clean_q = q_lower
             for k in ["เบอร์", "โทร", "ติดต่อ", "ใคร", "คือ", "ตำแหน่ง", "ครับ", "ค่ะ", "what", "is", "who", "the", "of"]:
                 clean_q = clean_q.replace(k, "")
             clean_q = clean_q.strip()
             
             if not clean_q:
                  # If query was just "เบอร์โทร", "ใครครับ" -> Ask for more
                  return {
                     "answer": "ต้องการทราบข้อมูลของใครหรือหน่วยงานไหนครับ? \n(เช่น 'เบอร์ ผส.บลตน.', 'ใครคือ ผส.พพ.')",
                     "route": "clarify_empty",
                     "latencies": latencies
                  }

             # A. Team Check
             if any(k in q_lower for k in ["ทีม", "ส่วน", "ฝ่าย", "งาน", "team", "section"]):
                 kind = "team_choice"
                 suggestions = self.directory_handler.suggest_teams(clean_q)
                 
             # B. Person Check (Explicit "คุณ")
             elif "คุณ" in q_lower or len(clean_q) > 40: # Long text might be name?
                 kind = "person_choice" # No specific handler yet, treat as role/holder lookup?
                 # Actually Person Lookup is handled by find_person but we want suggestions
                 suggestions = self.directory_handler.suggest_persons(clean_q)
                 if not suggestions: # Fallback to role
                      kind = "role_choice"
                      suggestions = self.directory_handler.suggest_roles(clean_q)
             
             # C. Role Check (Default for short acronyms)
             else:
                 kind = "role_choice"
                 suggestions = self.directory_handler.suggest_roles(clean_q)
                 
             # 3. Format Response (Deterministic)
             if suggestions:
                 # Format: "1) ... 2) ..."
                 s_list = "\n".join([f"{i+1}) {s}" for i, s in enumerate(suggestions)])
                 
                 # Logic: If only 1 suggestion and good match?
                 # User Rule: "If only 1 candidate AND confidence high -> still ask confirm... when token was short."
                 # Since we are here because of Ambiguity/Clarify intent, strict confirm is safer.
                 
                 ans = f"คุณหมายถึงตำแหน่งไหนครับ?\n{s_list}\n\nพิมพ์เลข 1-{len(suggestions)} หรือพิมพ์ชื่อเต็ม"
                 
                 # Set State
                 candidates = [{"id": i+1, "label": s, "key": s} for i, s in enumerate(suggestions)]
                 self.pending_question = {
                      "kind": kind,
                      "candidates": candidates,
                      "original_query": q,
                      "created_at": time.time(),
                      "mode": mode if mode != "unknown" else "holder" # Default
                 }
                 
                 return {
                     "answer": ans,
                     "route": "clarify_ambiguous",
                     "latencies": latencies,
                     "suggestions": suggestions
                 }
             
             else:
                 # No suggestions found
                 # Fix 3 (Phase 102): Suggest Knowledge Search if Person/Team lookup failed
                 return {
                     "answer": f"ไม่พบข้อมูลบุคลากร/หน่วยงานที่ตรงกับ '{clean_q}'\n\nหากต้องการค้นหาวิธีการ/คู่มือ:\nลองพิมพ์: \"วิธี {clean_q}\" หรือ \"คู่มือ {clean_q}\"",
                     "route": "clarify_miss",
                     "latencies": latencies
                 }

        # 0.1b Symptom Follow-up Handler (Phase 21)
        # Check if we are in a procedural context and user gives a short symptom reply
        if self.proc_ctx and self.proc_ctx.get("intent") == "procedure":
            # Heuristic: Short reply (< 30 chars) or matches symptom keywords
            is_short = len(q) < 50
            symptom_kws = ["หลุด", "ช้า", "อืด", "ไม่ติด", "หมุน", "error", "เข้าไม่ได้", "wifi", "lan", "สาย", "ไร้สาย"]
            has_symptom = any(k in q_lower for k in symptom_kws)
            
            if is_short or has_symptom:
                print(f"[DEBUG] Symptom follow-up detected: {q}")
                # Update slots
                slots = self.proc_ctx.get("slots", {})
                
                # Simple slot filling rules (Deterministic)
                if "wifi" in q_lower or "ไร้สาย" in q_lower: slots["access_type"] = "wifi"
                if "lan" in q_lower or "แลน" in q_lower or "สาย" in q_lower: slots["access_type"] = "lan"
                
                if "หลุด" in q_lower: slots["symptom"] = "disconnnect"
                if "ช้า" in q_lower or "อืด" in q_lower: slots["symptom"] = "slow"
                if "ไม่ติด" in q_lower or "เข้าไม่ได้" in q_lower: slots["symptom"] = "no_connect"
                
                self.proc_ctx["slots"] = slots
                
                # Check missing slots for "internet" topic
                if self.proc_ctx.get("topic") == "internet":
                    required = ["access_type", "symptom"]
                    missing = [k for k in required if k not in slots]
                    
                    if missing:
                        # Ask next question (Deterministic)
                        next_q = ""
                        if "access_type" in missing:
                            next_q = "ใช้งานผ่าน Wi-Fi หรือสาย LAN ครับ?"
                        elif "symptom" in missing:
                            next_q = "อาการเป็นอย่างไรครับ (เช่น หลุดบ่อย, ช้า, หรือเชื่อมต่อไม่ได้)?"
                        else:
                            next_q = "ขอทราบรายละเอียดเพิ่มเติมครับ"
                            
                        return {
                            "answer": next_q,
                            "route": "rag_clarify_followup",
                            "latencies": latencies
                        }
                    else:
                        # All slots filled -> Proceed to RAG/Article
                        # Construct a better query
                        access = slots.get("access_type", "")
                        sym = slots.get("symptom", "")
                        new_q = f"วิธีแก้ไขปัญหา internet {access} อาการ {sym}"
                        print(f"[DEBUG] Auto-generating query from slots: {new_q}")
                        
                        # Clear context so we don't loop
                        self.proc_ctx = None
                        
                        # Recursive call with refined query? 
                        # Or just fall through to standard processing with modified query?
                        # Fall through is safer to use standard routing.
                        q = new_q
                        q_lower = q.lower()
                        # Fall through...

        # 1.0 STATUS_CHECK Handler (Phase 34)
        if intent == "STATUS_CHECK":
             # Implementation of strictly checking status or failing
             # User Requirement: If not found, must say "No data", NO HALLUCINATION.
             print("[DEBUG] Handling STATUS_CHECK logic (Mock)")
             # TODO: Connect to real status_logs.jsonl
             return {
                 "answer": "ไม่พบข้อมูลสถานะในระบบช่วงเวลานี้ (No Realtime Data)",
                 "route": "status_check_mock",
                 "latencies": latencies
             }
             
        # 1.0b MANAGEMENT_LOOKUP Handler (Phase 48)
        if intent == "MANAGEMENT_LOOKUP":
             print("[DEBUG] Handling MANAGEMENT_LOOKUP logic")
             result = self.directory_handler.handle_management_query(q)
             result["latencies"] = latencies
             
             # Phase 80: Capture Ambiguity
             if result.get("route") == "management_ambiguous" and result.get("candidates"):
                 self.pending_question = {
                     "kind": "management_choice",
                     "candidates": result["candidates"],
                     "original_query": result.get("original_query", q),
                     "created_at": time.time()
                 }
                 
             return result

        # 1.0c POSITION_HOLDER_LOOKUP (Phase 49)
        if intent == "POSITION_HOLDER_LOOKUP":
             print("[DEBUG] Handling POSITION_HOLDER_LOOKUP logic")
             result = self.directory_handler.handle_position_holder(q)
             result["latencies"] = latencies
             return result

        # 1.0d TEAM_LOOKUP (Phase 69)
        if intent == "TEAM_LOOKUP":
             print("[DEBUG] Handling TEAM_LOOKUP logic")
             result = self.directory_handler.handle_team_lookup(q)
             
             # Phase 80: Capture Ambiguity
             if result.get("route") == "team_ambiguous" and result.get("candidates"):
                 self.pending_question = {
                     "kind": "team_choice",
                     "candidates": result["candidates"],
                     "original_query": q,
                     "created_at": time.time()
                 }
                 
             # Phase 72: Demotion / Re-Routing
             if result.get("route") == "team_demoted":
                 print("[DEBUG] Team Lookup Demoted -> Redirecting to HOWTO_PROCEDURE")
                 # Fall through to HOWTO logic? 
                 # Or explicitly call it.
                 # Since HOWTO logic is BELOW, we can just change `intent` and FALL THROUGH?
                 # BUT HOWTO logic is at priority 1.06 (Line 706)?
                 # Wait, line 706 is AFTER this block? No, checking indices.
                 # My previous `view_file` showed HOWTO at line 706.
                 # `TEAM_LOOKUP` is at line 612.
                 # So yes, HOWTO is BELOW.
                 # So I can just set `intent = "HOWTO_PROCEDURE"` and let it fall through?
                 # BUT the `if` clauses are `if intent == ...`.
                 # They are not `elif`.
                 # Let's verify structure.
                 intent = "HOWTO_PROCEDURE"
                 # Fall through to next if block
             else:
                 result["latencies"] = latencies
                 return result

        # 1.05 NEWS_SEARCH Handler (Phase 35)
        if intent == "NEWS_SEARCH":
            print("[DEBUG] Handling NEWS_SEARCH logic")
            
            # Phase 106: Prioritize SMC Database (Link Index)
            # Check if query matches an existing Article/News Title directly
            link_hits = self.processed_cache.find_links_fuzzy(q, threshold=0.65)
            if link_hits:
                 top_link = link_hits[0]
                 if top_link.get("items"):
                      first_item = top_link["items"][0]
                      target_url = first_item.get("href")
                      print(f"[DEBUG] News/Article Link Match: '{q}' -> {target_url} (Score: {top_link['score']})")
                      return self._handle_article_route(target_url, q, latencies, start_time=t_start, match_score=top_link['score'])
            
            # Use Fusion Search but heavily dependent on BM25 match of Title
            # Or use processed_cache to scan titles?
            # VectorStore should have a way to search.
            # Assuming 'vs.retrieve' returns Documents.
            
            # Simple Strategy:
            # 1. Search Vector Store (Hybrid)
            # 2. Filter hits where source is "News" or "Announcement" OR title matches query strongly
            # 3. If hit -> Article Route
            
            # Use hybrid_query for best keyword matching on titles
            hits = self.vs.hybrid_query(q, top_k=5)
            
            # Filter for news-like content
            news_hits = []
            for h in hits:
                # h is SearchResult object
                h_meta = h.metadata
                title = h_meta.get("title", "")
                
                # Heuristic: Check if 'news', 'ประกาศ', 'ประชาสัมพันธ์' is in title or content
                is_news = any(w in title.lower() for w in ["ข่าว", "ประกาศ", "news", "announcement"])
                
                # Or query match title? (Token-based)
                # Split query only by spaces (English style). For Thai, simple split might fail.
                # But here we just want ANY overlap.
                # FIX (Phase 62): Exclude intent triggers (stopwords) from overlap check
                from src.ai.router import IntentRouter
                news_triggers = IntentRouter.INTENTS["NEWS_SEARCH"]
                
                q_toks = [t for t in q_lower.split() if len(t) > 2 and t not in news_triggers] 
                query_match = any(t in title.lower() for t in q_toks)
                
                # Relaxed: If score is very high (e.g. > 0.65), trust the vector store.
                is_strong_hit = h.score > 0.65
                
                # Logic Fix (Phase 62): 
                # Prev: is_news OR query_match OR strong_hit
                # Problem: "ข่าว garbage" finds "ข่าว Bonus" (is_news=True) -> Mismatch.
                # Fix: Must match Topic (query_match) AND be News-like (is_news), OR be very strong hit.
                
                if (is_news and query_match) or is_strong_hit:
                    news_hits.append(h)
            
            if news_hits:
                # Phase 44: Link Ranking & Filtering
                # Filter out system pages (login, register, user profile)
                NEWS_DENYLIST = [
                    "register", "login", "com_user", "reset", "remind", "cart", "checkout", "profile",
                    "forgot", "username", "password", "component/users", "download"
                ]
                # NEWS_ALLOWLIST (Optional): ["view=article", "option=com_content", "category"]
                
                valid_hits = []
                for h in news_hits:
                    url = h.metadata.get("url") or h.metadata.get("source") or ""
                    url_lower = str(url).lower()
                    if any(bad in url_lower for bad in NEWS_DENYLIST):
                        continue
                    valid_hits.append(h)

                if valid_hits:
                    # Use best valid hit
                    best_hit = valid_hits[0]
                    target_url = best_hit.metadata.get("url") or best_hit.metadata.get("source")
                    return self._handle_article_route(target_url, q, latencies, start_time=t_start, match_score=best_hit.score)
                else:
                    # Hits existed but all were system pages -> Strict Miss
                    return {
                        "answer": "ไม่พบข้อมูลในระบบปัจจุบัน (กรองลิงก์ระบบออกหมดแล้ว)",
                        "route": "news_miss_filtered",
                        "latencies": latencies
                    }

            else:
                 # Phase 35 Fallback: Strict Miss
                 # Do NOT fall through to GENERAL_QA which might hallucinate.
                 return {
                    "answer": "ไม่พบข้อมูลในระบบปัจจุบัน",
                    "route": "news_miss",
                    "latencies": latencies
                 }

        # 1.06 HOWTO_PROCEDURE Handler (Phase 45/92)
        # Goal: Article-First Strategy. If we find a strong Article match, use Full-Text Extraction.
        if intent == "HOWTO_PROCEDURE":
             print("[DEBUG] Handling HOWTO_PROCEDURE logic (Article-First)")
             
             # Phase 92: Detect explicit knowledge queries and strip keyword
             KNOWLEDGE_KEYWORDS = ["ความรู้", "knowledge"]
             is_knowledge_query = any(kw in q.lower() for kw in KNOWLEDGE_KEYWORDS)
             search_query = q
             
             if is_knowledge_query:
                 # Strip knowledge keyword for better search
                 search_query = q
                 for kw in KNOWLEDGE_KEYWORDS:
                     search_query = search_query.replace(kw, "").replace(kw.upper(), "").replace(kw.capitalize(), "")
                 search_query = search_query.strip()
                 print(f"[DEBUG] Knowledge query detected. Stripped query: '{q}' -> '{search_query}'")
             
             # 1. Search Vector Store to identify "The Article"
             hits = self.vs.hybrid_query(search_query, top_k=10)
             
             # Phase 105: Prioritize Link Lookup (Exact/Fuzzy) for HowTo
             # If the query matches a known article link (e.g. "sbc ip"), use it directly.
             link_hits = self.processed_cache.find_links_fuzzy(search_query, threshold=0.70)
             if link_hits:
                  top_link_hit = link_hits[0]
                  # Inspect items
                  if top_link_hit.get("items"):
                       # Get the first item's href
                       first_item = top_link_hit["items"][0]
                       print(f"[DEBUG] JunkFilter first_item keys: {list(first_item.keys())}, title='{first_item.get('title', 'N/A')}', text='{first_item.get('text', 'N/A')}', href='{first_item.get('href', 'N/A')}'")
                       target_url = first_item.get("href")
                       target_title = first_item.get("title") or first_item.get("text") or ""
                       
                       # JUNK FILTER (Link Match - Title Check)
                       JUNK_EXTENSIONS = [".mp4", ".avi", ".mov", ".mkv", ".mp3", ".wav", ".zip", ".rar", ".7z", ".exe", ".dmg", ".iso", ".apk", ".ipa"]
                       if target_url:
                            is_junk_url = any(target_url.lower().endswith(ext) for ext in JUNK_EXTENSIONS)
                            is_junk_title = any(target_title.lower().endswith(ext) for ext in JUNK_EXTENSIONS)
                            
                            # Google Drive Special: Strict Filter for /file/d/ (Binaries)
                            if "drive.google.com" in target_url.lower():
                                 if "/file/d/" in target_url.lower():
                                      print(f"[ChatEngine] Detected Google Drive File URL (High Risk of Binary): {target_url}")
                                      is_junk_url = True 
                                 elif any(ext in target_title.lower() for ext in JUNK_EXTENSIONS):
                                      is_junk_title = True

                            if is_junk_url or is_junk_title:
                                print(f"[ChatEngine] Filtered Junk Link (Title/URL): {target_title} | {target_url}")
                            else:
                                print(f"[DEBUG] HowTo Link Match: '{search_query}' -> {target_url} (Score: {top_link_hit['score']})")
                                return self._handle_article_route(target_url, q, latencies, start_time=t_start, match_score=top_link_hit.get('score', 0.0))
             
             # 2. Check overlap logic or Score
             # Phase 92: Use lower threshold (0.45) for explicit knowledge queries
             threshold = 0.45 if is_knowledge_query else 0.6
             
             candidate = None
             if hits:
                 for h in hits:
                     meta = h.metadata or {}
                     url = meta.get("url", "").lower()
                     c_type = meta.get("content_type", "")
                     
                     # Phase 98: Category Exclusion
                     if "view=category" in url: continue
                     if "view=section" in url: continue
                     if c_type == "category": continue
                     
                     print(f"[DEBUG] HowTo Candidate: {meta.get('title')} (Score: {h.score:.4f}, Threshold: {threshold})")
                     
                     if h.score > 0.6: # Phase 116: Reverted to 0.6 for STRICTNESS. "Correctness > Recall"
                         # Check if it behaves like an Article (Has URL)
                         if meta.get("url") or meta.get("source"):
                             # JUNK FILTER ADAPTER
                             _url = (meta.get("url") or meta.get("source") or "").lower()
                             _title = (meta.get("title") or "").lower()
                             JUNK_EXTENSIONS = [".mp4", ".avi", ".mov", ".mkv", ".mp3", ".wav", ".zip", ".rar", ".7z", ".exe", ".dmg", ".iso", ".apk", ".ipa"]
                             
                             if any(_url.endswith(ext) for ext in JUNK_EXTENSIONS) or any(_title.endswith(ext) for ext in JUNK_EXTENSIONS):
                                 print(f"[ChatEngine] Filtered Junk Candidate: {_title}")
                                 continue

                             candidate = h
                             break # Found best valid hit
             
             if candidate:
                 # Route to Article Interpreter (Full Text)
                 # This bypasses chunked RAG, letting us read the WHOLE guide (up to limit)
                 # and allowing Image logic to run.
                 target_url = candidate.metadata.get("url") or candidate.metadata.get("source")
                 return self._handle_article_route(target_url, q, latencies, start_time=t_start, match_score=candidate.score)
             
             # Else: Fallback to General RAG (Chunk-based)
             print("[DEBUG] No single strong article found for HowTo. Falling back to RAG.")
             intent = "GENERAL_QA" # Fall through
             bypass_kp = True # Skip KP lookup since we want to find document chunks, not short facts

        # Phase 175: Web Knowledge Handler
        if intent == "WEB_KNOWLEDGE":
            # Safety Check: Prevent Web Hijack of Internal Topics
            # Policy: web_knowledge.internal_override_threshold
            policy_threshold = self.routing_policy.get("web_knowledge", {}).get("internal_override_threshold", 0.65)
            
            print(f"[DEBUG] Web Knowledge Safety Check for: '{q}' (Threshold: {policy_threshold})")
            try:
                safety_hits = self.vs.hybrid_query(q, top_k=1)
                
                if safety_hits and safety_hits[0].score > policy_threshold:
                    matched_score = safety_hits[0].score
                    print(f"[DEBUG] Safety Check: Found internal match (score={matched_score:.2f}) -> Override to SMC")
                    
                    # Point 4: Structured Logging for Regression Guard
                    print(f"[DEBUG] SAFETY_OVERRIDE\nquery=\"{q}\"\ninternal_score={matched_score:.4f}\noriginal_intent=WEB_KNOWLEDGE\nfinal_intent=GENERAL_QA")
                    
                    intent = "GENERAL_QA" # Fall through to Internal RAG
                    # Do NOT return here. Let it fall through.
                else:
                    print(f"[DEBUG] Routing to WebHandler: {q}")
                    return self.web_handler.handle(q)
            except Exception as e:
                print(f"[DEBUG] Safety Check Error: {e} -> Defaulting to Web")
                return self.web_handler.handle(q)



        # 0.2 Context-Aware Follow-up (Robust)
        if self.last_context:
            ctx = self.last_context
            ctx_data = ctx.get("data")
            ctx_type = ctx.get("type")
            
            # Normalization Layer
            normalized_q = q_lower
            # Remove polite words and common fillers
            for w in ["ครับ", "ค่ะ", "หน่อย", "ด้วย", "นะ", "จ๊ะ", "รบกวน", "ช่วย", "ขอ", "อยากได้", "ทราบ"]:
                normalized_q = normalized_q.replace(w, "")
            normalized_q = re.sub(r"[^\wก-๙]", "", normalized_q) # Remove spaces/punct
            
            # Intent Keywords (Expanded)
            kws_phone = ["เบอร์", "เบอ", "โทร", "phon", "call", "contact"]
            kws_email = ["เมล", "mail", "อีเมล", "e-mail"]
            kws_fax = ["fax", "แฟกซ์", "โทรสาร"]
            kws_link = ["link", "url", "เว็บไซต์", "เว็บ", "web", "page", "ลิงก์", "ลิ้ง", "เข้า"]
            kws_detail = ["รายละเอียด", "detail", "info", "คืออะไร", "what"]
            
            req_fax = any(k in normalized_q for k in kws_fax)
            req_phone = any(k in normalized_q for k in kws_phone) and not req_fax
            req_email = any(k in normalized_q for k in kws_email)
            req_link = any(k in normalized_q for k in kws_link)
            req_detail = any(k in normalized_q for k in kws_detail)
            
            # Heuristic: Is this a generic query? (No new entity)
            # Remove intent keywords to see if a name/role remains
            clean_q = normalized_q
            all_intents = kws_phone + kws_email + kws_fax + kws_link + kws_detail + ["ครับ", "ค่ะ", "ขอ", "ช่วย", "หน่อย"]
            for k in all_intents:
                clean_q = clean_q.replace(k, "")
            
            # Apply role alias expansion BEFORE entity check
            # This ensures "ขอเบอร์ผจ" expands to "ผจ.สบลตน." which is recognized as entity
            ROLE_ALIASES = {
                "ผจ": "ผจ.สบลตน.",
                "ผส": "ผส.บลตน.",
                "ผอ": "ผอ.",
                "รอง": "รองผอ."
            }
            for alias, full_role in ROLE_ALIASES.items():
                if alias in clean_q:
                    clean_q = clean_q.replace(alias, full_role)
            
            # Check if entity remains after cleanup
            # Method 1: Length check (significant text remaining)
            has_entity_by_length = len(clean_q) > 3
            
            # Method 2: Check against known roles in position_index
            has_entity_by_role = any(role in clean_q for role in self.position_index.keys())
            
            # Method 3: Check against common entity patterns (names, departments)
            # For now, we rely on length + role matching
            has_entity = has_entity_by_length or has_entity_by_role
            
            # Only trigger follow-up if NO entity detected
            is_generic_request = (not has_entity) or req_detail  # Detail requests can use context

            if is_generic_request:
                # Fax Request
                if req_fax:
                    faxes = []
                    if isinstance(ctx_data, list):
                        for r in ctx_data:
                            if "faxes" in r: faxes.extend(r["faxes"])
                    elif isinstance(ctx_data, dict):
                         if "faxes" in ctx_data: faxes.extend(ctx_data["faxes"])
                    
                    if faxes:
                        faxes = list(set(faxes))
                        return {
                            "answer": f"โทรสาร (Fax) ของ {ctx.get('ref_name')}:\n" + "\n".join(f"- {f}" for f in faxes),
                            "route": "context_followup",
                            "latencies": latencies
                        }
                    else:
                        return {
                            "answer": f"ไม่พบข้อมูลโทรสารของ {ctx.get('ref_name')} ในระบบ",
                            "route": "context_followup_miss",
                            "latencies": latencies
                        }

                # Phone Request
                if req_phone:
                    phones = []
                    if isinstance(ctx_data, list):
                        for r in ctx_data:
                            if "phones" in r: phones.extend(r["phones"])
                    elif isinstance(ctx_data, dict):
                         if "phones" in ctx_data: phones.extend(ctx_data["phones"])
                    
                    # Fallback lookup if missing
                    if not phones:
                         target_name = None
                         if isinstance(ctx_data, dict): target_name = ctx_data.get("name")
                         elif isinstance(ctx_data, list) and ctx_data: target_name = ctx_data[0].get("name")
                         if target_name:
                             hits = lookup_phones(target_name, self.records)
                             for h in hits:
                                 if "phones" in h: phones.extend(h["phones"])

                    if phones:
                        phones = list(set(phones))
                        return {
                            "answer": f"เบอร์โทรศัพท์ของ {ctx.get('ref_name')}:\n" + "\n".join(f"- {p}" for p in phones),
                            "route": "context_followup",
                            "latencies": latencies
                        }
                    else:
                        return {
                            "answer": f"ไม่พบข้อมูลเบอร์โทรศัพท์ของ {ctx.get('ref_name')} ในระบบ",
                            "route": "context_followup_miss",
                            "latencies": latencies
                        }
                
                # Email Request
                if req_email:
                     emails = []
                     if isinstance(ctx_data, list):
                         for r in ctx_data:
                             if "emails" in r: emails.extend(r["emails"])
                     elif isinstance(ctx_data, dict):
                         if "emails" in ctx_data: emails.extend(ctx_data["emails"])

                     if emails:
                         emails = list(set(emails))
                         return {
                             "answer": f"อีเมลของ {ctx.get('ref_name')}:\n" + "\n".join([f"- {e}" for e in emails]),
                             "route": "context_followup",
                             "latencies": latencies
                         }
                     else:
                         return {
                             "answer": f"ไม่พบข้อมูลอีเมลของ {ctx.get('ref_name')} ในระบบ",
                             "route": "context_followup_miss",
                             "latencies": latencies
                         }

                # Link Request
                if req_link:
                    url = None
                    if ctx_type == "link": url = ctx_data.get("href")
                    elif ctx_type == "position":
                        if isinstance(ctx_data, list) and ctx_data: url = ctx_data[0].get("source")
                        elif isinstance(ctx_data, dict): url = ctx_data.get("source")
                    elif ctx_type == "contact": url = ctx_data.get("source")
                    
                    if url:
                         return {
                            "answer": f"ลิงก์ข้อมูลสำหรับ {ctx.get('ref_name')}:\nURL: {url}",
                            "route": "context_followup",
                            "latencies": latencies
                        }
                    else:
                         return {
                            "answer": f"ไม่พบข้อมูลลิงก์สำหรับ {ctx.get('ref_name')}",
                            "route": "context_followup_miss",
                            "latencies": latencies
                        }

                # Detail Request (Generic)
                if req_detail and ctx_type == "link":
                    return {
                         "answer": f"รายละเอียด {ctx.get('ref_name')}:\nURL: {ctx_data.get('href')}\nAccess: {ctx_data.get('access', 'Unknown')}",
                         "route": "context_followup",
                         "latencies": latencies
                    }
        
        # ---------------------------------------------------------
        # Phase 23/25: Knowledge Pack Lookup (PRIORITY)
        # ---------------------------------------------------------
        # Moved up to prioritize verified facts over heuristics

        # B. Direct KP Lookup (High Confidence Entities)
        # Check if query matches high-value facts (DNS/SMTP/BRAS etc)
        # We perform this BEFORE Position/Contact lookup to catch "Bras IP", "DNS" etc.
        kp_result = None
        # Phase 98: Contact/Person Intent Guard
        # If intent is explicitly looking for people/contacts, skip high-level KP lookup 
        # to ensure it goes to the specialized `ContactHandler` downstream.
        if self.kp_manager and not bypass_kp and intent not in ["CONTACT_LOOKUP", "PERSON_LOOKUP", "TEAM_LOOKUP", "MANAGEMENT_LOOKUP", "POSITION_HOLDER_LOOKUP", "HOWTO_PROCEDURE"]:
            # Phase 31: Multi-Key Aggregation
            # Detect combination of key entities
            q_lower = q.lower()
            keys_found = []
            if "dns" in q_lower: keys_found.append("DNS")
            if "smtp" in q_lower or "mail" in q_lower: keys_found.append("SMTP")
            if "bras" in q_lower: keys_found.append("BRAS")
            
            if len(keys_found) > 1:
                print(f"[DEBUG] Multi-Key KP Query: {keys_found}")
                telemetry_data["kp_multi_key"] = True
                telemetry_data["kp_keys"] = keys_found
                
                # Extract Scope to preserve
                scope_hint = ""
                if "nt1" in q_lower or "bkk" in q_lower: scope_hint = "NT1"
                elif "isp" in q_lower: scope_hint = "ISP"
                elif "region" in q_lower or "ภูมิภาค" in q_lower: scope_hint = "Region"
                
                aggregated_ans = []
                aggregated_hits = []
                all_options = set()
                
                for key in keys_found:
                    sub_q = f"{key} {scope_hint}".strip()
                    sub_res = self.kp_manager.lookup(sub_q)
                    if sub_res:
                        # If signal is CLARIFY, collect options but don't fail
                        if sub_res.get("signal") == "CLARIFY_SCOPE":
                            for opt in sub_res.get("options", []): all_options.add(opt)
                        else:
                            # Clean answer: Remove "Found X items" header for sub-sections to be cleaner
                            raw_ans = sub_res["answer"]
                            # Remove first line if it looks like a header count
                            if raw_ans.startswith("พบข้อมูล") or raw_ans.startswith("ไม่พบข้อมูล"):
                                lines = raw_ans.split('\n')
                                if len(lines) > 1: raw_ans = "\n".join(lines[1:])
                            
                            
                            aggregated_ans.append(f"=== {key} ===\n{raw_ans}")
                            # Deduplicate hits by key+value
                            for h in sub_res.get("hits", []):
                                h_id = f"{h.get('key')}_{h.get('value')}"
                                if h_id not in [f"{x.get('key')}_{x.get('value')}" for x in aggregated_hits]:
                                     aggregated_hits.append(h)
                
                if aggregated_ans:
                    kp_result = {
                        "answer": "\n\n".join(aggregated_ans),
                        "hits": aggregated_hits,
                        "signal": "AGGREGATED"
                    }
                elif all_options:
                     # If all sub-lookups asked for clarification
                     sorted_opts = sorted(list(all_options))
                     kp_result = {
                         "answer": f"กรุณาเลือกขอบเขตสำหรับ {', '.join(keys_found)}: {', '.join(sorted_opts)}",
                         "signal": "CLARIFY_SCOPE",
                         "options": sorted_opts
                     }
            
            # Fallback to Single Lookup if not multi-key or aggregation failed
            if not kp_result:
                kp_result = self.kp_manager.lookup(q)
        if kp_result:
             if kp_result.get("signal") == "CLARIFY_SCOPE":
                  self.pending_kp_clarify = {
                      "original_query": q,
                      "options": kp_result.get("options", []),
                      "timestamp": time.time(),
                      "pending_answer_mode": answer_mode # Persist mode
                  }
                  latencies["total"] = (time.time() - t_start) * 1000
                  telemetry_data["route"] = "knowledge_pack_clarify"
                  telemetry_data["clarify_asked"] = True
                  telemetry_data["pack_hit"] = True
                  self._log_telemetry(telemetry_data, latencies)
                  
                  return {
                      "answer": kp_result["answer"],
                      "route": "knowledge_pack_clarify",
                      "latencies": latencies,
                      "hits": []
                  }
             
             latencies["total"] = (time.time() - t_start) * 1000
             res = {
                 "answer": kp_result["answer"],
                 "route": "knowledge_pack",
                 "latencies": latencies,
                 "hits": kp_result["hits"]
             }
             telemetry_data["route"] = "knowledge_pack"
             telemetry_data["pack_hit"] = True
             self._log_telemetry(telemetry_data, latencies)
             return self._apply_answer_mode(res, answer_mode)

             return self._apply_answer_mode(res, answer_mode)

        # ---------------------------------------------------------
        # Phase 34: Strict Intent-Based Routing (Refactored)
        # ---------------------------------------------------------
        
        # 1.1 CONTACT_LOOKUP
        # 1.1 CONTACT_LOOKUP
        if intent == "CONTACT_LOOKUP":
            print("[DEBUG] Route: CONTACT_LOOKUP (via Handler)")
            from src.rag.handlers.contact_handler import ContactHandler
            
            res = ContactHandler.handle(q, self.records, directory_handler=self.directory_handler)
            
            # If hit, update context
            if res.get("hits"):
                hits = res["hits"]
                self.last_context = {"type": "contact", "data": hits[0], "ref_name": hits[0]["name"]}
            
            # Fallback to RAG if Contact Handler misses (e.g. support phone in an article)
            if res.get("route") == "contact_miss":
                # Policy: contact_lookup.no_kill_switch
                # If true, allow RAG fallback? Original code Logic says "Strict Kill-Switch (No RAG)".
                # Let's check the policy.
                # User config: guided_fallback_on_miss: true, no_kill_switch: true
                # If no_kill_switch is TRUE, we SHOULD fall through or try something else?
                # User Point 2 for Contact says "no_kill_switch: true" in sample,
                # BUT "strict kill-switch" logic was requested in previous phase (135).
                # Wait, Point 2 sample says: "ขอเบอร์ทั้งหมดของหาดใหญ่ → ต้อง guided fallback (ไม่ MISS)"
                # My `contact_lookup` policy in file says:
                # contact_lookup:
                #   guided_fallback_on_miss: true
                #   no_kill_switch: true
                
                # So if no_kill_switch is True, we should NOT return contact_miss_strict IMMEDIATELY?
                # However, the user request says "Phase 135: Kill-Switch (No RAG Fallback)".
                # The "Bridge Port", "North Flood" cases imply we WANT strict behavior for numbers.
                # BUT "Bridge Port" (config) -> Article.
                # "Hat Yai" -> Guided Fallback.
                
                # Let's implement Guided Fallback here as per Policy.
                no_kill = self.routing_policy.get("contact_lookup", {}).get("no_kill_switch", False)
                guided = self.routing_policy.get("contact_lookup", {}).get("guided_fallback_on_miss", False)

                if guided:
                     print("[DEBUG] Contact Miss -> Attempting Guided Fallback (Policy)")
                     # Try to suggest teams in that area?
                     # For now, return a helpful message instead of generic miss
                     # Or stick to strict miss but with better message?
                     return {
                         "answer": "ไม่พบข้อมูลเบอร์โทรศัพท์ที่ระบุโดยตรง\n\nคำแนะนำ:\n- ระบุชื่อหน่วยงานให้ชัดเจน (เช่น 'ส่วนงาน...')\n- ระบุชื่อบุคคล (เช่น 'คุณสมชาย')",
                         "route": "contact_miss_guided",
                         "latencies": latencies,
                         "hits": []
                     }

                print("[DEBUG] Contact Handler Miss -> Strict Kill-Switch (No RAG).")
                return {
                     "answer": "ไม่พบข้อมูลเบอร์โทรศัพท์/หน่วยงานที่ระบุในระบบสมุดโทรศัพท์ (กรุณาระบุชื่อหน่วยงาน/พื้นที่ให้ชัดเจน)",
                     "route": "contact_miss_strict",
                     "latencies": latencies,
                     "hits": []
                }
            else:
                return {
                    "answer": res.get("answer"),
                    "route": res.get("route"),
                    "latencies": latencies,
                    "hits": res.get("hits")
                }

        # 1.2 PERSON_LOOKUP (Roles/WhoIs)
        # 1.2 PERSON_LOOKUP (Roles/WhoIs)
        elif intent == "PERSON_LOOKUP" or intent == "CONTACT_LOOKUP" or intent == "TEAM_LOOKUP":
             print(f"[DEBUG] Route: {intent}")
             t_start = time.time()
             # Use original query for directory to ensure Thai keyword matching
             return self.directory_handler.handle(original_q_str)

        elif intent == "REFERENCE_LINK":
             print("[DEBUG] Route: REFERENCE_LINK")
             # Clean query for link search
             clean_q = q.lower().replace("ขอลิงก์", "").replace("link", "").strip()
             fuzzy_results = self.processed_cache.find_links_fuzzy(clean_q, threshold=0.60)
             
             if fuzzy_results:
                 top_links = []
                 seen_urls = set()
                 for res in fuzzy_results[:5]:
                     for item in res["items"]:
                         if item["href"] not in seen_urls:
                             top_links.append(item)
                             seen_urls.add(item["href"])
                 
                 if self.cfg.get("ux", {}).get("enable_formatting", True):
                     ans_parts = []
                     for item in top_links[:4]:
                         title = item['text'].replace('\n', ' ').strip()
                         ans_parts.append(f"• **{title}**\n  🔗 {item['href']}")
                     
                     latencies["total"] = (time.time() - t_start) * 1000
                     return {
                         "answer": "พบลิงก์ที่เกี่ยวข้องดังนี้ครับ:\n\n" + "\n\n".join(ans_parts),
                         "route": "link_lookup",
                         "latencies": latencies
                     }
                 else:
                     simple_ans = "\n".join([f"- {item['text']}: {item['href']}" for item in top_links[:4]])
                     latencies["total"] = (time.time() - t_start) * 1000
                     return {
                         "answer": simple_ans,
                         "route": "link_lookup",
                         "latencies": latencies
                     }
            # Fallthrough if no link found -> RAG (maybe it's in a document content)

        # 1.4 HOWTO_PROCEDURE / GENERAL / STATUS_CHECK (Mock) -> Fall through to RAG
        # STATUS_CHECK was handled early (line 496), but if it wasn't, ensure we don't do Position Lookup.
        
        # Phase 106: Prioritize SMC Database (Link Index) for General Queries (Fallthrough)
        # Even if intent wasn't HOWTO or NEWS, if it strongly matches a known Article, USE IT.
        # This catches "SMC Policy" or "Manual X" that slipped through Router.
        
        # Phase R6: Bypass Link Match for "What is X" (Concept) queries
        # User Feedback: "What is RAG" shouldn't match "RAG WAN Document". It should use General Fallback.
        is_what_is = any(k in q.lower() for k in ["คืออะไร", "what is", "concept"])
        
        if not is_what_is:
            link_hits = self.processed_cache.find_links_fuzzy(q, threshold=0.75) # Strict threshold for implicit intent
            if link_hits:
                 top_link = link_hits[0]
                 # Double check: match must be robust (length > 4) and score high
                 if len(q) > 4 and top_link.get("items"):
                      first_item = top_link["items"][0]
                      target_url = first_item.get("href")
                      print(f"[DEBUG] General/Fallthrough Link Match: '{q}' -> {target_url} (Score: {top_link['score']})")
                      return self._handle_article_route(target_url, q, latencies, start_time=t_start, match_score=top_link['score'])

        # Fallthrough to RAG Vector Search (Step 2)
        # This handles:
        # - HOWTO_PROCEDURE (Vector Search + Article)
        # - GENERAL_QA
        # - Missed Lookups (optional fallback but we returned early for misses above?)



        # 1.6 Heuristic Clarification (Pre-RAG Fast Path)
        # Check BEFORE vector search to avoid wasting time on embedding/retrieval
        # Pattern 1: Generic trouble queries (internet/wifi issues)
        is_internet_issue = any(k in q.lower() for k in ["internet", "wifi", "network", "เน็ต", "ไวไฟ", "lan"]) and \
                            any(k in q.lower() for k in ["ใช้ไม่ได้", "ใช้งานไม่ได้", "หลุด", "ช้า", "อืด", "เสีย", "พัง", "problem", "issue", "error", "connect", "ต่อไม่ติด", "เข้าไม่ได้", "ล่ม"])
        
        # Pattern 2: Procedure queries without specific context
        is_procedure_query = any(k in q.lower() for k in ["ขั้นตอน", "วิธี", "อย่างไร", "ทำไง", "how to", "procedure", "steps"]) and \
                            any(k in q.lower() for k in ["แจ้ง", "รายงาน", "report", "ขัดข้อง", "เสีย", "พัง", "ปัญหา"])
        
        if is_internet_issue:
            latencies["total"] = (time.time() - t_start) * 1000
            
            # Initialize Procedural Context
            self.proc_ctx = {
                "intent": "procedure",
                "topic": "internet",
                "slots": {},
                "timestamp": time.time()
            }
            
            return {
                "answer": "ใช้งานไม่ได้แบบไหน (ต่อไม่ติด/ช้า/หลุดบ่อย/ขึ้น error) และใช้งานผ่าน Wi-Fi หรือสาย LAN ครับ?",
                "route": "rag_clarify",
                "latencies": latencies
            }
        
        if is_procedure_query:
            latencies["total"] = (time.time() - t_start) * 1000
            return {
                "answer": "ต้องการแจ้งเรื่องอะไร (อินเทอร์เน็ต/ONU/โทรศัพท์/อุปกรณ์) และเป็นพื้นที่/หน่วยงานไหนครับ?",
                "route": "rag_clarify",
                "latencies": latencies
            }


        # ---------------------------------------------------------
        # Phase R3: Multi-Level Caching & Safety Guard
        # ---------------------------------------------------------
        from src.rag.cache_manager import CacheManager
        from src.rag.safety_guard import SafetyGuard
        
        # Initialize Cache Manager
        if not hasattr(self, "cache_manager") or not self.cache_manager:
             # Reuse existing semantic cache if available
             sem_cache = self.cache if hasattr(self, "cache") else None
             self.cache_manager = CacheManager(sem_cache)

        # Step 1: L1 Retrieval Cache Check (Exact Query + Strategy)
        # Note: We need 'intent' and 'strategy' defined before this?
        # Intent is defined above. Strategy is defined in R1 block.
        # Ideally, we move Strategy definition up or just use 'intent' as proxy for mode.
        # Let's use 'intent' for L1 key for now as it maps to strategy.
        
        l1_hits = self.cache_manager.get_retrieval_cache(q, intent)
        if l1_hits:
            print(f"[DEBUG] L1 Retrieval Cache HIT")
            valid_results = l1_hits
            latencies["vector_search"] = 0.0 # From cache
            is_l1_hit = True
            telemetry_data["cache_hit_l1"] = True
        else:
            is_l1_hit = False
            telemetry_data["cache_hit_l1"] = False
            # ... Perform Retrieval (R1 Logic) ...
            
            # (R1 Logic Block insert here - reuse existing code flow, just wrap?)
            # Since I cannot easily wrap the existing block without huge diff, 
            # I will insert the L1 check BEFORE the R1 block, and if HIT, skip retrieval.
            # But the R1 block is messy.
            # Let's assume the user wants me to EDIT the retrieval block.
            pass

        # Wait, I need to REPLACE the retrieval block effectively.
        # Or I can use 'if not is_l1_hit:' around the entire retrieval section.
        
        # Let's locate the start of R1 Retrieval Strategy and wrap it.
        # ...
        
        # For this tool call, I will add the imports and initialization at the top of RAG block,
        # and implement the Logic flow.

        # 2. RAG
        t_vs = time.time()
        is_general_fallback = False # Initialize for safety scope
        is_conceptual = False       # Initialize for score filtering scope

        # Location Context (Early Extraction for Cache)
        # We need this for both L1 and L2 cache keys/fingerprints effectively
        # (Though L1 currently doesn't use it, L2 should strict filter)
        from src.utils.section_filter import extract_location_intent
        req_locations = extract_location_intent(q)
        if req_locations:
             loc_fingerprint = "|".join(sorted(req_locations))
        else:
             loc_fingerprint = "none"

        # Initialize Cache
        if not hasattr(self, "cache_manager") or not self.cache_manager:
             sem_cache = self.cache if hasattr(self, "cache") else None
             self.cache_manager = CacheManager(sem_cache)
             
        # Step 1: L1 Cache Check
        l1_hits = self.cache_manager.get_retrieval_cache(q, intent)
        
        if l1_hits:
             print(f"[DEBUG] L1 Retrieval Cache HIT")
             results = l1_hits # Skip retrieval
             latencies["vector_search"] = 0
             # Skip optimization? Maybe ran before caching.
             # Assume cached hits are already optimized/ranked.
             valid_results = results # Directly valid
             
             # Phase R6: Re-evaluate General Fallback for Cached Results
             # If we hit cache, we must check if this result SHOULD trigger a General Knowledge Fallback
             # (i.e. if the cached result has low score for a concept query, we must allow it to pass safety)
             
             top_score = getattr(valid_results[0], "score", 0.0) if valid_results else 0.0
             
             # Re-use simplified Concept Logic (Phase 133/R5)
             # Note: 'intent' is already available.
             concept_kws = ["คืออะไร", "what is", "concept", "explain", "meaning", "definition"]
             is_conceptual = (intent == "EXPLAIN") or any(k in q.lower() for k in concept_kws)
             
             # If Concept + Low Score (but not zero) -> Enable Fallback
             if is_conceptual and 0.05 < top_score < 0.35:
                  print(f"[DEBUG] L1 Cache Hit -> General Fallback Triggered (Score {top_score:.4f})")
                  is_general_fallback = True
             
        else:
             # --- ORIGINAL RETRIEVAL LOGIC (R1) ---
             start_vs = time.time()
             where = None
             
             # Phase 174: Deferred Synonym Expansion (Applied only to RAG retrieval)
             q, applied_rule = expand_synonyms(original_q_str)
             if q != original_q_str:
                  synonym_active = True
                  print(f"[METRIC] Synonym Applied for Retrieval: {applied_rule} (Query: '{original_q_str}' -> '{q}')")
                  telemetry_data["synonym_rule"] = applied_rule

             # Phase 133: Define Conceptual Intent Early
             conceptual_kws = ["สรุป", "แนวทาง", "อธิบาย", "คืออะไร", "concept", "explain", "overview", "what is", "introduction", "ความหมาย", "ทำความรู้จัก"]
             is_conceptual = any(k in original_q_str.lower() for k in conceptual_kws)
            
             if hasattr(self.vs, "hybrid_query"):
                 # Phase R1: Dynamic Retrieval Strategy
                 from src.rag.retrieval_strategy import StrategyFactory
                 strategy = StrategyFactory.get_strategy(intent)
                 # ... (Existing retrieval) ...
                 print(f"[DEBUG] Retrieval Strategy: {strategy.mode} (alpha={strategy.alpha}, top_k={strategy.top_k})")
                 results = self.vs.hybrid_query(q, top_k=strategy.top_k + 25, alpha=strategy.alpha, where=where)
             else:
                 results = self.vs.query(q, top_k=self.top_k + 20, where=where)
             
             # Phase 174 Extension: Synonym Rollback Safety
             if synonym_active and results:
                  top_score = results[0].score
                  if top_score < 0.35:
                       print(f"[METRIC] Synonym Rollback Triggered: Score {top_score:.2f} < 0.35. Reverting to '{original_q_str}'")
                       telemetry_data["synonym_rollback"] = True
                       
                       # Re-run retrieval with original query
                       backoff_q = original_q_str
                       try:
                           if hasattr(self.vs, "hybrid_query"):
                                # If strategy was defined locally
                                tk = strategy.top_k + 25 if 'strategy' in locals() else self.top_k + 25
                                alp = strategy.alpha if 'strategy' in locals() else 0.5
                                fallback_results = self.vs.hybrid_query(backoff_q, top_k=tk, alpha=alp, where=where)
                           else:
                                fallback_results = self.vs.query(backoff_q, top_k=self.top_k + 20, where=where)
                                
                           fb_score = fallback_results[0].score if fallback_results else 0.0
                           if fb_score > top_score:
                                print(f"[METRIC] Rollback Successful: Score improved ({top_score:.2f} -> {fb_score:.2f})")
                                results = fallback_results
                                q = backoff_q # Update context query
                           else:
                                print(f"[METRIC] Rollback Aborted: Original was worse ({fb_score:.2f} < {top_score:.2f})")
                       except Exception as e:
                           print(f"[ERROR] Rollback Failed: {e}")
                 
             # ... (Ranking/Filtering) ...
             # Phase 98: Category Exclusion & System Page Filter
             filtered_results = []
             for r in results:
                 meta = r.metadata or {}
                 url = meta.get("url", "").lower()
                 c_type = meta.get("content_type", "")
                 if "view=category" in url: continue
                 if "view=section" in url: continue
                 if c_type == "category": continue
                 filtered_results.append(r)
             
             # Phase R1: Anti-Ranking Inversion
             if self.retrieval_optimizer:
                  filtered_results = self.retrieval_optimizer.re_rank(filtered_results, q)
             
             # Trim
             top_k_final = strategy.top_k if 'strategy' in locals() else self.top_k
             results = filtered_results[:top_k_final]
             
             latencies["vector_search"] = (time.time() - start_vs) * 1000
             
             # Verify Coverage (R1)
             if self.evaluator:
                  # Phase R5: Pass Intent and Query for Dynamic Thresholds
                  coverage = self.evaluator.check_coverage(results, query=q, intent=intent)
                  print(f"[DEBUG] Evidence Coverage: {coverage['status']} ({coverage.get('reason', 'OK')})")
                  
                  if coverage["status"] == "MISS":
                       # Phase R5: General Knowledge Tier
                       # If it's a CONCEPT question, allow a Safe Fallback instead of strict MISS
                       if intent in ["EXPLAIN", "CONCEPT", "SUMMARY", "WHAT_IS"]:
                            print(f"[DEBUG] General Tier Active for Concept Miss")
                            is_general_fallback = True
                            # We proceed with whatever weak results we have OR empty?
                            # If we use strict generator, it might still refuse.
                            # We will rely on prompt engineering in Generator to handle "Low Evidence but General Concept".
                            # For now, let's keep the results (even if low score) so the LLM has *something* 
                            # context, but we flag it.
                       else:    
                           latencies["total"] = (time.time() - t_start) * 1000
                           return {
                               "answer": "ไม่พบข้อมูลที่เกี่ยวข้องในระบบ (Coverage Check FAILED)",
                               "route": "rag_miss_coverage",
                               "latencies": latencies,
                               "debug_info": {"reason": coverage.get("reason")}
                           }
                  elif coverage["status"] == "LOW_CONFIDENCE":
                       telemetry_data["low_confidence"] = True
             
             # Step 2: Set L1 Cache
             self.cache_manager.set_retrieval_cache(q, intent, results)
             valid_results = results

        # Step 3: Kill-Switch (Safety Guard)
        from src.rag.safety_guard import SafetyGuard
        
        # Phase R6: Bypass Kill-Switch for General Fallback (Concept Tier)
        # If we explicitly allowed low confidence fallback earlier (Concept Tier), we skip strict score check.
        # But we still check for Navigation/Boilerplate (Safety).
        
        # Note: 'is_general_fallback' local variable from Coverage Check block
        allow_low_score = 'is_general_fallback' in locals() and is_general_fallback
        
        if allow_low_score:
             print(f"[SafetyGuard] General Fallback Active -> Bypassing Low Score Check")
             # Let's trust that 'Concept' intent implies we want an explanation.
             safety = {"safe": True, "reason": "General Fallback Override"}
        else:
             safety = SafetyGuard.check_retrieval_safety(valid_results)

        if not safety["safe"]:
             print(f"[SafetyGuard] KILL-SWITCH ACTIVATED: {safety['reason']}")
             return {
                 "answer": f"ไม่สามารถตอบคำถามได้เนื่องจากข้อมูลไม่เพียงพอหรือไม่มีคุณภาพ ({safety['reason']})",
                 "route": "rag_kill_switch",
                 "latencies": latencies
             }
             
        # Step 4: L2 Answer Cache Check (Using Fingerprint)
        fingerprint = self.cache_manager.compute_fingerprint(valid_results)
        l2_hit = self.cache_manager.get_answer_cache(q, intent, fingerprint)
        
        if l2_hit:
             print(f"[DEBUG] L2 Answer Cache HIT (Score: {l2_hit.get('score', 0):.2f})")
             latencies["cache"] = l2_hit.get("latency", 0)
             latencies["total"] = (time.time() - t_start) * 1000
             return {
                 "answer": l2_hit["answer"],
                 "route": "rag_cache_l2",
                 "latencies": latencies,
                 "score": l2_hit.get("score"),
                 "cache_hit": True,
                 "prompt_mode": l2_hit.get("prompt_mode", "cached")
             }

        # Proceed to Generation (R2 Logic)
        # ...

        
        if not results:
            latencies["total"] = (time.time() - t_start) * 1000
            return {
                "answer": "No information found in the system.",
                "route": "rag_no_docs",
                "latencies": latencies
            }

        # Filter by Score
        # Phase 133: If Concept, ignore global threshold (use gate below)
        score_threshold = float(self.rag_cfg.get("score_threshold", 0.0))
        if is_conceptual:
             valid_results = results # Keep all
        else:
             valid_results = [r for r in results if r.score >= score_threshold]
        
        if valid_results and valid_results[0].score >= 0.85:
            # print(f"[DEBUG] High confidence match ({valid_results[0].score:.2f}). Reducing Top-K to 1.")
            valid_results = [valid_results[0]]

        # Phase 116: Strict RAG Score Gate (Anti-Hallucination) - UPSTREAMED
        # Phase 133: Dynamic Threshold for Conceptual Queries (Broad/Summary)
        
        # Phase 133: Aggressive Retrieval for Conceptual Queries
        # If user wants "Summary", we trust the Ranking (Top 1) even if score is low.
        min_gate_score = 0.0 if is_conceptual else 0.65
        
        # If even the best result is weak (< min_gate_score), DO NOT Answer or Engage Controller.
        if not valid_results or valid_results[0].score < min_gate_score:
             best_s = valid_results[0].score if valid_results else 0
             print(f"[DEBUG] RAG Score Gate: Best score {best_s:.4f} < {min_gate_score} (Conceptual={is_conceptual}). REJECTING EARLY.")
             latencies["total"] = (time.time() - t_start) * 1000
             return {
                 "answer": "ไม่พบข้อมูลในระบบปัจจุบัน (Low Confidence Match)",
                 "route": "rag_low_score_gate",
                 "latencies": latencies,
                 "docs": [r.text[:100] for r in valid_results] if valid_results else [],
                 "reason": "Universal Low Score Gate (< 0.65)"
             }
        else:
             print(f"[DEBUG] RAG Score Gate Passed: Best score {valid_results[0].score:.4f} (Doc: {valid_results[0].text[:50]}...)")
            
        # 2.5 Retrieval Optimization (Dynamic Top-K)
        # Only run if we have multiple candidates and logic is enabled
        # This helps reduce noise for the LLM
        if len(valid_results) > 1 and self.retrieval_optimizer:
             t_opt = time.time()
             # We pass all valid results to the optimizer
             optimized_results = self.retrieval_optimizer.optimize(q, valid_results)
             latencies["retrieval_opt"] = (time.time() - t_opt) * 1000
             
             # If optimizer actually reduced the count or reordered?
             if optimized_results:
                  valid_results = optimized_results
        
        # 3. RAG Controller Strategy (LLM Judge)
        # Replaces simple thresholding. Run ONCE.
        candidates = valid_results if valid_results else results
        style = "GENERAL" # Default
        
        # 3.2 Dynamic Controller (The Brain)
        if candidates and self.controller:
             t_ctrl = time.time()
             # Optimize: Truncate context for Controller to reduce latency
             context_docs = [r.text for r in candidates] # Full docs for context
             # Limit to 500 chars per doc for decision to speed up.
             ctrl_context = [d[:500] for d in context_docs]
             
             strategy_res = self.controller.decide(q, ctrl_context)
             latencies["controller"] = (time.time() - t_ctrl) * 1000
             
             strategy = strategy_res.get("strategy")
             style = strategy_res.get("style", "GENERAL")
             
             # Dispatch Strategy
             # Phase 133: Conceptual Override (Force Answer)
             if is_conceptual and strategy == "NO_ANSWER":
                 print(f"[DEBUG] Controller Rejected but Conceptual Override prevents it. Forcing RAG_ANSWER.")
                 strategy = "RAG_ANSWER"
                 
             if strategy == "NO_ANSWER":
                 latencies["total"] = (time.time() - t_start) * 1000
                 latencies["llm"] = latencies.get("controller", 0) + latencies.get("retrieval_opt", 0)
                 return {
                     "answer": "ไม่พบข้อมูลในระบบปัจจุบัน",
                     "route": "rag_controller_rejected",
                     "latencies": latencies,
                     "docs": context_docs,
                     "reason": strategy_res.get("reason"),
                     "retrieved_context": [{"text": r.text, "score": r.score, "metadata": r.metadata} for r in candidates]
                 }
             elif strategy == "DIRECT_LOOKUP":
                 pass 
             elif strategy == "ASK_FOR_CLARIFICATION" or strategy == "CLARIFY":
                 latencies["total"] = (time.time() - t_start) * 1000
                 latencies["llm"] = latencies.get("controller", 0) + latencies.get("retrieval_opt", 0)
                 # Remove prefix, just return the question
                 return {
                     "answer": strategy_res.get("reason"), 
                     "route": "rag_clarify",
                     "latencies": latencies
                 }
             
             # Evidence Gate: If RAG_ANSWER but confidence is low, reject early
             # Limit wasteful generation
             conf = strategy_res.get("confidence", 0.0)
             if strategy == "RAG_ANSWER" and conf < 0.6:
                  latencies["total"] = (time.time() - t_start) * 1000
                  latencies["llm"] = latencies.get("controller", 0) + latencies.get("retrieval_opt", 0)
                  return {
                      "answer": "ไม่พบข้อมูลในระบบปัจจุบัน (Low Confidence)",
                      "route": "rag_controller_rejected",
                      "latencies": latencies,
                     "docs": context_docs,
                     "reason": f"Controller Confidence Low ({conf:.2f} < 0.6)",
                     "retrieved_context": [{"text": r.text, "score": r.score, "metadata": r.metadata} for r in candidates]
                  }

             # If RAG_ANSWER or DIRECT_LOOKUP, we proceed. 
             # Also update valid_results to be candidates if they were originally empty (Rescue)
             if not valid_results and (strategy == "RAG_ANSWER" or strategy == "DIRECT_LOOKUP"):
                 valid_results = candidates
        
        if not valid_results:
            latencies["total"] = (time.time() - t_start) * 1000
            # Consolidate generic message
            return {
                "answer": "ไม่พบข้อมูลในระบบปัจจุบัน",
                "route": "rag_low_score",
                "latencies": latencies,
                "docs": [f"{r.text[:50]}... ({r.score:.4f})" for r in results],
                "retrieved_context": [{"text": r.text, "score": r.score, "metadata": r.metadata} for r in results]
            }

        # Build Context
        context_text = ""
        for i, res in enumerate(valid_results):
            context_text += f"\n[Document {i+1}]:\n{res.text}\n"

        # NEW: Extract and filter images from retrieved documents
        from src.rag.image_filter import detect_image_intent, filter_and_rank_images
        
        show_images = detect_image_intent(q)
        all_images = []
        
        if show_images:  # Only extract images if user requests them
            seen_urls = set()
            for res in valid_results:
                doc_url = res.metadata.get("url", "")
                if doc_url and doc_url in self.processed_cache._url_to_images:
                    doc_images = self.processed_cache._url_to_images[doc_url]
                    for img in doc_images:
                        img_url = img.get("url", "")
                        if img_url and img_url not in seen_urls:
                            all_images.append(img)
                            seen_urls.add(img_url)
            
            # Filter and rank images
            all_images = filter_and_rank_images(all_images, q, max_images=3)
        
        # Add images to context if available
        image_context = ""
        if all_images:
            image_context = "\n\nIMAGES AVAILABLE:\n"
            for idx, img in enumerate(all_images, 1):
                image_context += f"{idx}. URL: {img.get('url', '')}\n"
                if img.get('alt'):
                    image_context += f"   Alt: {img.get('alt', '')}\n"
                if img.get('caption'):
                    image_context += f"   Caption: {img.get('caption', '')}\n"

        # LLM Generation
        t_gen = time.time()
        
        # ---------------------------------------------------------
        # Phase R2: Answer Governance (RAGGenerator)
        # ---------------------------------------------------------
        # Use centralized generator for Strict Templates & Token Budgeting
        from src.rag.generator import RAGGenerator
        
        if not hasattr(self, "generator") or not self.generator:
             self.generator = RAGGenerator(self.llm_cfg)
             
        # Prepare Context Objects (Standardize)
        # valid_results already contains SearchResult objects
        
        # Determine Intent for Template Selection (Mapped from style or raw intent)
        # If Controller set style, map it.
        gen_intent = intent # Default to router intent
        if style == "PROCEDURE": gen_intent = "HOWTO_PROCEDURE"
        elif style == "DEFINITION": gen_intent = "EXPLAIN"
        
        # Override for Image/Conceptual
        if is_conceptual: gen_intent = "EXPLAIN"
        
        # Phase R5: General Fallback Override
        # If coverage was missing but we allow general answer (Concept Tier)
        if 'is_general_fallback' in locals() and is_general_fallback:
             gen_intent = "GENERAL_FALLBACK"
             print(f"[Thinking...] Using Intent Template: GENERAL_FALLBACK (Concept Fallback)")
        else:
             print(f"[Thinking...] Using Intent Template: {gen_intent}")
        
        gen_res = self.generator.generate(
            query=q,
            context_docs=valid_results,
            intent=gen_intent
        )
        
        ans = gen_res.get("answer", "")
        latencies["generator"] = gen_res.get("latency", 0)
        
        # Temporary: Append Image Context manually if it exists?
        # RAGGenerator handles text context. Images are separate.
        # If we have images, we might need to append them to the answer directly 
        # OR pass them to generator (future).
        # For now, let's append the Image Section manually if RAGGenerator didn't.
        # (Our current RAGGenerator prompt doesn't handle image_context arg yet, 
        #  so we append it to the FINAL string if not empty).
        
        if image_context and ans:
             # Basic append if not present
             if "รูปภาพประกอบ" not in ans:
                 ans += f"\n\n{image_context}"

        t_gen = time.time() # Just for compat with old vars if needed below
        # (latencies['generator'] is already set from gen_res)
        
        # Step 5: Reviewer Agent (Phase R4)
        # Check grounding (Only if we have an answer and it's not a "not found" boilerplate)
        if ans and "ไม่พบข้อมูล" not in ans and len(ans) > 20: 
             from src.rag.reviewer import RAGReviewer
             if not hasattr(self, "reviewer"):
                 self.reviewer = RAGReviewer(self.llm_cfg)
                 
             # Only review if strictly needed (e.g. not procedural/fact check which is usually safe?)
             # For R4, let's review everything to be safe.
             
             review_res = self.reviewer.review(q, ans, valid_results)
             print(f"[Reviewer] Verdict: {review_res.get('verdict')} ({review_res.get('reason')})")
             
             if review_res.get("verdict") in ["FAIL", "HARD_FAIL"] and review_res.get("safe_response"):
                  # Swap answer!
                  ans = review_res.get("safe_response")
                  latencies["reviewer"] = 999 # Placeholder for tracking
                  # Mark route
                  # We can't easily change route variable here as it's implied RAG.
                  # But we can log it.
                  telemetry_data["reviewer_fail"] = True
                  telemetry_data["reviewer_reason"] = review_res.get("reason")
        
        # Step 6: Update L2 Answer Cache (Strict)
        # Only cache if Reviewer PASSED (or we swapped to a safe response?)
        # Fix: Force Save if 'is_general_fallback' because we want to cache the "Not Found/General Knowledge" answer
        should_cache = (ans and "ไม่พบข้อมูล" not in ans and len(ans) > 20) or (is_general_fallback and ans)
        if should_cache:
             # Save with Fingerprint
             print(f"[DEBUG] Saving to L2 Cache (Fingerprint: {fingerprint[:10]}...)")
             meta = {
                 "route": "rag",
                 "model": self.llm_cfg.get("model", "unknown"),
                 "locations": loc_fingerprint
             }
             self.cache_manager.set_answer_cache(q, ans, intent, fingerprint, meta)

        
        # 4. RAG Evaluator (Post-Gen Guard)
        # Check both English and Thai refusal strings for Evaluator
        refusal_phrases = ["No information", "ไม่พบข้อมูลในระบบปัจจุบัน", "ไม่พบข้อมูลที่ยืนยัน", "ไม่พบข้อมูล"]
        is_refusal = any(phrase in ans for phrase in refusal_phrases)
        
        # Phase R6: Bypass Verification for General Fallback
        # If we already decided to show a "General Knowledge" answer (Concept Tier), 
        # we don't want the strict Verifier to reject it because it lacks internal evidence.
        if self.evaluator and ans and not is_refusal and not is_general_fallback:
             t_eval = time.time()
             eval_res = self.evaluator.verify(q, [r.text for r in valid_results], ans)
             latencies["evaluator"] = (time.time() - t_eval) * 1000
             
             if eval_res.get("verdict") == "REJECT":
                 latencies["total"] = (time.time() - t_start) * 1000
                 latencies["llm"] = (latencies.get("controller", 0) + 
                                     latencies.get("retrieval_opt", 0) + 
                                     latencies.get("generator", 0) + 
                                     latencies.get("evaluator", 0))
                 return {
                     "answer": "ไม่พบข้อมูลในระบบปัจจุบัน (Verification Failed)",
                     "route": "rag_evaluator_rejected",
                     "latencies": latencies,
                     "docs": [r.text for r in valid_results],
                     "reason": eval_res.get("missing_evidence")
                 }
             elif eval_res.get("verdict") == "TIMEOUT":
                 # Graceful Degradation: Warn but allow answer
                 print(f"[DEBUG] Verification Timed Out. Proceeding with warning.")
                 ans += "\n\n[System Warning: Verification skipped due to high load]"

        latencies["total"] = (time.time() - t_start) * 1000
        
        # Sum LLM Components
        latencies["llm"] = (latencies.get("controller", 0) + 
                            latencies.get("retrieval_opt", 0) + 
                            latencies.get("generator", 0) + 
                            latencies.get("evaluator", 0))
        # 5. Source Attachment (Phase 28)
        # If answer is valid and not a refusal, attach references
        if ans and not is_refusal and valid_results:
             unique_sources = {} # url -> title
             for r in valid_results:
                 if not r.metadata: continue
                 url = r.metadata.get("source") or r.metadata.get("url")
                 title = r.metadata.get("title") or "Document"
                 if url and url not in unique_sources:
                     unique_sources[url] = title
                     
             if unique_sources:
                 ans += "\n\nแหล่งข้อมูลอ้างอิง:"
                 for i, (url, title) in enumerate(list(unique_sources.items())[:3]):
                      ans += f"\n{i+1}. {title} ({url})"
        
        # Location Intent (Phase 36)
        # Already extracted early as 'req_locations' and 'loc_fingerprint'

        # 2. Check Semantic Cache
        if self.cache:
            # Add location strictness to filter
            # This ensures "songkhla" query NEVER hits "surat" cache
            filter_meta = {
                "route": "rag",
                "model": self.llm_cfg.get("model", "unknown"),
                "locations": loc_fingerprint 
            }
            
            t_cache = time.time()
            # Phase 97: Strict Intent Check
            best_hit = self.cache.check(
                q, 
                intent=intent, 
                route="rag", 
                filter_meta=filter_meta
            )
            
            if best_hit:
                score = best_hit.get("score", 0.0)
                if score > self.cache_threshold:
                    print(f"[DEBUG] Semantic Cache HIT (score={score:.4f})")
                    latencies["cache"] = (time.time() - t_cache) * 1000
                    latencies["total"] = (time.time() - t_start) * 1000
                    
                    return {
                        "answer": best_hit["answer"],
                        "route": "rag_cache",
                        "latencies": latencies,
                        "score": score
                    }

        # 6. Store in Cache (Pro-Level Metadata)
        if self.cache and ans and not is_refusal and len(ans) > 20: 
             # Phase 97: Strict Metadata for Hygiene
             store_meta = {
                 "route": "rag",
                 "intent": intent, # Strict Key
                 "model": self.llm_cfg.get("model", "unknown"),
                 "timestamp": time.time(),
                 "locations": loc_fingerprint
             }
             self.cache.store(q, ans, meta=store_meta)
             
        # Phase 33: Populate hits for Article URL_ONLY mode
        # If no KP matches, we treat the retrieved docs as "hits" for URL filtering
        doc_matches = []
        for r in valid_results:
            if r.metadata.get("url"):
                doc_matches.append({
                    "key": "Article",
                    "value": r.metadata.get("title", "Link"),
                    "source_url": r.metadata.get("url")
                })
        
        # Merge doc matches into results if not present (or append for hybrid)
        # Check if we should use doc_matches as primary hits for RAG route
        if not kp_result:
             matches = doc_matches
        else:
             matches = kp_result.get("hits", []) + doc_matches

        # Location Slicing (Phase 36)
        # Apply strict location filtering if user requested specific province
        
        # req_locations = extract_location_intent(q) # Moved up for cache
        if req_locations and ans:
            print(f"[DEBUG] Location Intent Detected: {req_locations}. Slicing answer...")
            sliced_ans = slice_markdown_section(ans, req_locations)
            # Only use sliced if it's not empty and significantly different
            if sliced_ans and len(sliced_ans) < len(ans):
                ans = sliced_ans + f"\n\n(คัดกรองเฉพาะข้อมูล: {', '.join(req_locations)})"

        return {
            "answer": ans,
            "route": "rag",
            "context": context_text if self.show_context else None,
            "latencies": latencies,
            "docs": [r.text for r in valid_results],
            "hits": matches,
            "debug_info": {
                "generated_at": time.time(),
                "model": self.llm_cfg.get("model")
            }
        }

    def _handle_article_route(self, url: str, query: str, latencies: Dict[str, float], start_time: float, match_score: float = 0.0) -> Dict[str, Any]:
        """
        Helper to invoke Article Interpreter for a specific URL.
        """
        if not url:
            return {
                "answer": "ไม่พบลิงก์บทความที่เกี่ยวข้อง",
                "route": "article_miss",
                "latencies": latencies
            }
        
        # Invoke Article Interpreter (Phase 16)
        print(f"[DEBUG] News/Article Route -> {url}")
        
        # Must ensure interpreter is loaded
        if not hasattr(self, "article_interpreter") or not self.article_interpreter:
            from src.rag.article_interpreter import ArticleInterpreter
            self.article_interpreter = ArticleInterpreter(self.llm_cfg)
            
        t_art = time.time()
        
        # Check Cache FIRST (Phase R6)
        # We cache the RESULT of interpretation (the summary)
        # Fix: Safe access to prevention crash if not initialized
        cm = getattr(self, "cache_manager", None)
        if cm:
            ux_formatting = self.cfg.get("ux", {}).get("enable_formatting", True)
            ux_preview = self.cfg.get("ux", {}).get("direct_content_preview", True)
            cache_key_str = f"article_summary|{url}|{query}|{CACHE_SCHEMA_VERSION}|fmt:{ux_formatting}|pre:{ux_preview}" 
            fingerprint = hashlib.md5(cache_key_str.encode()).hexdigest()
            
            # Use 'ARTICLE_SUMMARY' as intent
            l2_hit = self.cache_manager.get_answer_cache(query, "ARTICLE_SUMMARY", fingerprint)
            if l2_hit:
                 print(f"[DEBUG] Article Summary Cache HIT (Score: {l2_hit.get('score', 0):.2f})")
                 latencies["cache"] = l2_hit.get("latency", 0)
                 latencies["total"] = (time.time() - start_time) * 1000
                 
                 return {
                     "answer": l2_hit["answer"],
                     "route": "article_answer", # or article_cache
                     "latencies": latencies,
                     "hits": [{"key": "Source", "value": "News", "source_url": url}]
                 }

        # Fetch content (Cache or Web)
        # Note: Interpreter expects context or url? 
        # Checking ArticleInterpreter.interpret signature...
        # interpret(user_query, article_title, article_url, article_content, ...)
        
        article_content = self.processed_cache._url_to_text.get(url)
        if not article_content:
            # Phase 130: Smart Fetch with Timeout & Policy
            print(f"[DEBUG] Cache Miss for {url} -> Attempting Fetch (Strict Timeout)...")
            fetch_res = fetch_with_policy(url)
            
            if fetch_res.status_code == 200 and fetch_res.html:
                # Success: Parse and use
                print(f"[DEBUG] Fetch Success: {len(fetch_res.html)} chars")
                # Clean html to text immediately for use
                from src.ingest.clean import clean_html_to_text
                clean_res = clean_html_to_text(fetch_res.html)
                article_content = clean_res.text
                
                # Optional: Update memory cache (TTL not implemented in memory dict yet, but good for session)
                self.processed_cache._url_to_text[url] = article_content
            
            else:
                # Failure (Timeout / Blocked / 404)
                reason = fetch_res.error or f"Status {fetch_res.status_code}"
                print(f"[DEBUG] Fetch Failed: {reason}")
                
                # Graceful Degradation Message
                msg = f"สรุปไม่ได้เนื่องจากดึงข้อมูลต้นทางไม่สำเร็จ ({reason})"
                if "timeout" in reason:
                     msg = "สรุปไม่ได้เนื่องจากใช้เวลาดึงข้อมูลนานเกินกำหนด (Timeout)"
                elif "blocked" in reason:
                     msg = "ไม่สามารถเข้าถึงแหล่งข้อมูลภายนอกนี้ได้ (Domain Policy Restricted)"
                     
                return {
                    "answer": f"{msg}\nกรุณาเปิดลิงก์โดยตรง: {url}",
                    "route": "article_miss",
                    "latencies": latencies
                }
        
        # Check cache for images
        images = self.processed_cache._url_to_images.get(url, [])
        
        print(f"[DEBUG] article_content type: {type(article_content)}")
        
        # Pass correct arguments
        ans_data = self.article_interpreter.interpret(
            user_query=query,
            article_title="News Article", 
            article_url=url,
            article_content=article_content,
            images=images,  # Pass images
            show_images=False,
            match_score=match_score
        )
        
        latencies["article_gen"] = (time.time() - t_art) * 1000
        latencies["total"] = (time.time() - start_time) * 1000
        
        # Save to Cache (Phase R6)
        if self.cache_manager and isinstance(ans_data, str) and len(ans_data) > 50:
             # Re-compute fingerprint to be safe (though same as above)
             if 'fingerprint' in locals():
                 meta = {
                     "route": "article_answer",
                     "model": self.llm_cfg.get("model", "unknown"),
                     "url": url
                 }
                 self.cache_manager.set_answer_cache(query, ans_data, "ARTICLE_SUMMARY", fingerprint, meta)
        
        return {
            "answer": ans_data, # interpret returns str, not dict
            "route": "article_answer",
            "latencies": latencies,
            "hits": [{"key": "Source", "value": "News", "source_url": url}]
        }

    def _apply_answer_mode(self, result: Dict[str, Any], mode: str) -> Dict[str, Any]:
        """
        Phase 25/26: Filter answer/hits based on mode.
        """
        if mode == "FULL":
            return result
            
        hits = result.get("hits", [])
        filtered_hits = []
        fallback_msg = ""
        
        if mode == "PHONE_ONLY":
            fallback_msg = "ไม่พบหมายเลขโทรศัพท์ในข้อมูลนี้"
            for h in hits:
                val = str(h.get("value", ""))
                # Strict phone check: Must have digits, but NOT look like an IP (x.x.x.x)
                is_ip = re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", val.strip())
                if any(c.isdigit() for c in val) and not is_ip: 
                    filtered_hits.append(h)
                    
        elif mode == "IP_ONLY":
            fallback_msg = "ไม่พบข้อมูล IP Address ในส่วนนี้"
            for h in hits:
                val = str(h.get("value", ""))
                if "IP" in h.get("key", "") or any(x in val for x in [".", ":"]): 
                     filtered_hits.append(h)
                     
        elif mode == "URL_ONLY":
             fallback_msg = "ไม่พบลิงก์เว็บไซต์ในข้อมูลนี้"
             for h in hits:
                 val = str(h.get("value", ""))
                 src = str(h.get("source_url", ""))
                 if "http" in val or "http" in src:
                     filtered_hits.append(h)
                     
        elif mode == "NAME_ONLY":
             fallback_msg = "ไม่พบรายชื่อบุคคลในข้อมูลนี้"
             for h in hits:
                 val = str(h.get("value", ""))
                 # Regex match Thai Title at start
                 if re.match(r"(?:นาย|นาง|น\.ส\.|คุณ|ดร\.|พล\.)", val.strip()):
                     filtered_hits.append(h)

        elif mode == "SUMMARY":
            return result

        if not filtered_hits and mode != "SUMMARY":
            return {
                "answer": fallback_msg,
                "hits": [],
                "route": result["route"],
                "latencies": result.get("latencies", {})
            }

        elif mode == "NAME_ONLY":
             lines = []
             seen_names = set()
             for i, h in enumerate(filtered_hits):
                 val = str(h.get("value", ""))
                 # Clean value: matches "Title Name Surname"
                 match = re.search(r"((?:นาย|นาง|น\.ส\.|คุณ|ดร\.|พล\.)\s*[\u0E00-\u0E7F]+\s+[\u0E00-\u0E7F]+)", val)
                 if match:
                     name = match.group(1)
                     if name not in seen_names:
                         lines.append(f"{len(lines)+1}. {name}")
                         seen_names.add(name)
             return {
                 "answer": "\n".join(lines) if lines else fallback_msg,
                 "hits": filtered_hits,
                 "route": result["route"],
                 "latencies": result.get("latencies", {})
             }
        elif mode == "URL_ONLY":
             # Dedup URLs
             seen_urls = set()
             lines = []
             for h in filtered_hits:
                 val = str(h.get("value", ""))
                 src = str(h.get("source_url", ""))
                 # Use value if it's a link, else source
                 link = val if "http" in val else src
                 
                 # Clean link
                 link = link.strip()
                 if not link or link in seen_urls: continue
                 
                 # Strip markdown link syntax if present [x](url)
                 m = re.search(r'\((http[s]?://[^)]+)\)', link)
                 if m: link = m.group(1)
                 
                 seen_urls.add(link)
                 
                 # Optional: Show Title?
                 # If value was NOT the link, use value as title
                 if val != link and len(val) < 100:
                     title = val
                 else:
                     title = h.get("source_title", h.get("key"))
                 # Simply list URL if title irrelevant, or 'Title: URL'
                 lines.append(f"- {title}: {link}")
                 
                 if len(lines) >= 5: break # Limit
                 
             new_ans = "\n".join(lines)
        else:
             # Dedup Values for FULL Mode
             seen_vals = set()
             lines = []
             
             # Sort hits: prioritize detections? 
             # Hits usually pre-sorted by Score/Date in KP Manager
             
             for h in filtered_hits:
                 val = str(h.get("value", "")).strip()
                 key = h.get("key", "")
                 composite = f"{key}:{val}"
                 
                 if composite in seen_vals: continue
                 seen_vals.add(composite)
                 
                 lines.append(f"- {key}: {val}")
                 
             if warning_msg := result.get("answer", "").split("\n\n")[0]:
                 if "ไม่พบข้อมูลในขอบเขต" in warning_msg:
                      lines.insert(0, warning_msg + "\n")
             
             new_ans = "\n".join(lines)
        
        return {
            "answer": new_ans,
            "hits": filtered_hits,
            "route": result["route"],
            "latencies": result.get("latencies", {})
        }

    def _log_telemetry(self, data: Dict[str, Any], latencies: Dict[str, float]):
        """
        Phase 25: Log telemetry to JSONL
        """
        if not self.save_log:
            return
            
        try:
            log_path = Path("data/logs/chat_telemetry.jsonl")
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Enrich with latencies
            data["latencies"] = latencies
            # Ensure timestamp is float
            ts = data.get("timestamp", time.time())
            data["timestamp_iso"] = datetime.datetime.fromtimestamp(ts).isoformat()
            
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(data, ensure_ascii=False) + "\n")
        except Exception as e:
            print(f"[Telemetry] Error: {e}")
