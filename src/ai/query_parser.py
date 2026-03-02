"""
Structured Query Parser
Extracts structured information from natural language queries WITHOUT rewriting them.

IMPORTANT: This is extraction-only. NO query rewriting, NO answer generation.
"""

import json
from typing import Dict, Any, Optional
from src.rag.ollama_client import ollama_generate


PROMPT_QUERY_PARSER = """Extract structured information from the user query. Return ONLY valid JSON with these exact fields:

{{
  "vendor": "ZTE|Cisco|Huawei|Nokia|Alcatel|null",
  "device": "OLT|ONU|Switch|Router|Gateway|null", 
  "command_keyword": "main technical keyword or null",
  "intent": "COMMAND|DEFINE|LOOKUP|TROUBLESHOOT|null"
}}

Rules:
- vendor: Extract ONLY if explicitly mentioned (ZTE, Cisco, ฮัวเว่ย, etc.)
- device: Extract device type if mentioned (OLT, ONU, Switch, สวิตช์, etc.)
- command_keyword: Main technical term (vlan, config, show, add, etc.)
- intent: COMMAND for command/config requests, DEFINE for "คืออะไร", LOOKUP for general info
- Use "null" (not None, not empty string) if field not detected
- Return ONLY the JSON object, no explanation

User Query: {query}

JSON:"""


class QueryParser:
    """
    Parses natural language queries to extract structured information.
    Does NOT rewrite queries or generate answers.
    """
    
    def __init__(self, llm_cfg: Dict[str, Any]):
        self.llm_cfg = llm_cfg
        self.model = llm_cfg.get("fast_model", "llama3.2:3b")
        self.base_url = llm_cfg.get("base_url", "http://localhost:11434")
    
    def parse(self, query: str) -> Dict[str, Optional[str]]:
        """
        Parse query to extract structured information.
        
        Args:
            query: Natural language query
            
        Returns:
            {
                "vendor": str or None,
                "device": str or None,
                "command_keyword": str or None,
                "intent": str or None
            }
        """
        
        # Fast path: Don't parse very short queries
        if len(query.strip()) < 3:
            return self._empty_result()
        
        # Build prompt
        prompt = PROMPT_QUERY_PARSER.format(query=query)
        
        try:
            # Call LLM with strict deterministic mode
            response = ollama_generate(
                base_url=self.base_url,
                model=self.model,
                prompt=prompt,
                temperature=0.0,  # Deterministic
                num_predict=128,  # Short output
                num_ctx=1024,     # Small context
                stream=False
            )
            
            # Parse JSON response
            response_clean = response.strip()
            
            # Handle markdown code blocks if present
            if response_clean.startswith("```"):
                # Extract JSON from code block
                lines = response_clean.split("\n")
                json_lines = [l for l in lines if l and not l.startswith("```")]
                response_clean = "\n".join(json_lines)
            
            parsed = json.loads(response_clean)
            
            # Normalize null values
            result = {
                "vendor": self._normalize_value(parsed.get("vendor")),
                "device": self._normalize_value(parsed.get("device")),
                "command_keyword": self._normalize_value(parsed.get("command_keyword")),
                "intent": self._normalize_value(parsed.get("intent"))
            }
            
            print(f"[QueryParser] '{query[:50]}...' → vendor={result['vendor']}, intent={result['intent']}, keyword={result['command_keyword']}")
            
            return result
            
        except json.JSONDecodeError as e:
            print(f"[QueryParser] JSON parse error: {e}, response: {response[:100]}")
            return self._empty_result()
        except Exception as e:
            print(f"[QueryParser] Error: {e}")
            return self._empty_result()
    
    def _normalize_value(self, value: Any) -> Optional[str]:
        """Normalize value to None if null/empty."""
        if value is None or value == "null" or value == "" or value == "None":
            return None
        return str(value).strip()
    
    def _empty_result(self) -> Dict[str, None]:
        """Return empty result structure."""
        return {
            "vendor": None,
            "device": None,
            "command_keyword": None,
            "intent": None
        }


# Global singleton
_parser_instance = None


def get_parser(llm_cfg: Dict[str, Any]) -> QueryParser:
    """Get singleton parser instance."""
    global _parser_instance
    if _parser_instance is None:
        _parser_instance = QueryParser(llm_cfg)
    return _parser_instance


def parse_query_structure(query: str, llm_cfg: Dict[str, Any]) -> Dict[str, Optional[str]]:
    """
    Convenience function to parse query structure.
    
    Args:
        query: Natural language query
        llm_cfg: LLM configuration
        
    Returns:
        Parsed structure dict
    """
    parser = get_parser(llm_cfg)
    return parser.parse(query)
