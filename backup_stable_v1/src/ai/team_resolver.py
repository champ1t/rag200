from typing import List, Dict, Any, Optional
import json
from src.rag.ollama_client import ollama_generate

class TeamResolver:
    STRICT_RESOLVER_PROMPT = """
You are a strict team-name resolver for an internal directory.
Task: map the user's team text to ONE existing canonical team key from the provided list.
Rules:
- Do NOT invent a new team key.
- If no clear match, return "ambiguous" with top 3 closest candidates.
- Use normalization: remove words like "งาน", "ทีม", "ฝ่าย", "แผนก", "บุคลากร", "สมาชิก", and polite particles.
- Prefer exact / substring match after normalization, then semantic similarity.

Return JSON only:
{
  "status": "match|ambiguous|no_match",
  "canonical_team": null|string,
  "candidates": [string],
  "why": "short reason"
}

Canonical team keys:
<<<CANONICAL_TEAM_KEYS>>>

User team text:
<<<TEAM_TEXT>>>
"""

    def __init__(self, llm_config: Dict[str, Any]):
        self.llm_config = llm_config

    def resolve(self, team_text: str, candidates: List[str]) -> Dict[str, Any]:
        """
        Resolve team_text to a canonical key from candidates using LLM.
        """
        # Optimization: Pre-filter candidates if too many (> 50) to fit context?
        # For now, pass all assuming < 100 keys.
        
        # Format keys as bullet list
        keys_str = "\n".join([f"- {k}" for k in candidates])
        
        prompt = self.STRICT_RESOLVER_PROMPT.replace("<<<CANONICAL_TEAM_KEYS>>>", keys_str)
        prompt = prompt.replace("<<<TEAM_TEXT>>>", team_text)
        
        try:
            resp = ollama_generate(
                base_url=self.llm_config.get("base_url"),
                model=self.llm_config.get("model", "llama3.2:3b"),
                prompt=prompt,
                temperature=0.0
            )
            
            clean_resp = resp.replace("```json", "").replace("```", "").strip()
            return json.loads(clean_resp)
            
        except Exception as e:
            print(f"[TeamResolver] Error: {e}")
            return {
                "status": "error",
                "canonical_team": None,
                "candidates": [],
                "why": f"LLM Error: {e}"
            }
