from typing import List, Dict, Any, Optional
import json
from src.rag.ollama_client import ollama_generate

class ResponseGenerator:
    STRICT_GENERATOR_PROMPT = """
You are a strict assistant for an internal knowledge chatbot.
You must NOT hallucinate. Use only the provided facts.
If nothing matches, respond with a helpful next-step message and options.

Context:
- Query: <<<USER_QUERY>>>
- Intent: <<<INTENT>>>
- Available teams: <<<AVAILABLE_TEAMS>>>
- Available roles: <<<AVAILABLE_ROLES>>>
- Found result: <<<FOUND_RESULT_OR_EMPTY>>>

Output rules:
- If FOUND_RESULT exists: summarize in 1-5 bullet points. Include source link(s) if present.
- If empty and intent=TEAM_LOOKUP: say you can't find that team, then show up to 5 closest available teams.
- If empty and intent=POSITION_HOLDER_LOOKUP or CONTACT_LOOKUP(role-based): ask user to specify the full role (e.g., "ผส.บลตน.") and show role suggestions.
- Keep answer short and actionable. Do not mention internal implementation.

Write the final Thai response.
"""

    def __init__(self, llm_config: Dict[str, Any]):
        self.llm_config = llm_config

    def generate(self, 
                 query: str, 
                 intent: str, 
                 result: Any, 
                 available_teams: List[str] = [], 
                 available_roles: List[str] = []) -> str:
        """
        Generate a final response string based on strict context rules.
        """
        
        # Prepare Context Variables
        teams_str = ", ".join(available_teams[:20]) if available_teams else "None"
        roles_str = ", ".join(available_roles[:20]) if available_roles else "None"
        
        # Format Result
        result_str = "None"
        if result:
            if isinstance(result, (dict, list)):
                result_str = json.dumps(result, ensure_ascii=False)
            else:
                result_str = str(result)
        
        prompt = self.STRICT_GENERATOR_PROMPT
        prompt = prompt.replace("<<<USER_QUERY>>>", query)
        prompt = prompt.replace("<<<INTENT>>>", intent)
        prompt = prompt.replace("<<<AVAILABLE_TEAMS>>>", teams_str)
        prompt = prompt.replace("<<<AVAILABLE_ROLES>>>", roles_str)
        prompt = prompt.replace("<<<FOUND_RESULT_OR_EMPTY>>>", result_str)
        
        try:
            resp = ollama_generate(
                base_url=self.llm_config.get("base_url"),
                model=self.llm_config.get("model", "llama3.2:3b"),
                prompt=prompt,
                temperature=0.2 # Slight creativity for phrasing, but constrained by context
            )
            return resp.strip()
            
        except Exception as e:
            print(f"[ResponseGenerator] Error: {e}")
            return "ขออภัย ระบบเกิดข้อขัดข้องชั่วคราว (Generative Error)"
