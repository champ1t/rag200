from langflow.custom import CustomComponent
from langflow.field_typing import Text
from typing import Optional
import sys
import os
import yaml

# Global cache for the singleton instance
_cached_engine = None

class NTRAGEngineComponent(CustomComponent):
    display_name = "NT RAG Engine"
    description = "Wraps the custom NT RAG ChatEngine (Phases 221-230)."
    documentation = "Requires 'project_root' to point to the folder containing src/ and data/."

    def build_config(self):
        return {
            "query": {
                "display_name": "Input Query",
                "multiline": True,
            },
            "project_root": {
                "display_name": "Project Root Path",
                "info": "Absolute path to the project root (where src/ and configs/ are).",
                # Default to current directory if not specified, but usually needs explicit path in Docker
                "value": "/app" 
            },
            "config_rel_path": {
                "display_name": "Config File (Relative)",
                "value": "configs/config.yaml"
            },
            "session_id": {
                "display_name": "Session ID",
                "value": "langflow_session"
            },
            "force_reload": {
                "display_name": "Force Reload Engine",
                "field_type": "bool",
                "value": False,
                "info": "Set to True to force reload code/prompts. Set back to False after."
            }
        }

    def build(
        self, 
        query: str, 
        project_root: str, 
        config_rel_path: str = "configs/config.yaml",
        session_id: str = "langflow_session",
        force_reload: bool = False
    ) -> Text:
        global _cached_engine
        
        # 0. Handle Force Reload
        if force_reload:
            print("[Wrapper] Force Reload triggered. Clearing cached engine.")
            _cached_engine = None
        
        # 1. Path Setup
        if project_root and project_root not in sys.path:
            sys.path.append(project_root)
            print(f"[Wrapper] Added {project_root} to sys.path")

        # 2. Change CWD (Critical for relative data paths in ChatEngine)
        # Store original cwd to restore later if needed? 
        # For LangFlow, changing process CWD might affect other components if they rely on it.
        # But ChatEngine relies on `open("data/...")`.
        try:
            if os.getcwd() != project_root:
                os.chdir(project_root)
                print(f"[Wrapper] Changed CWD to {project_root}")
        except FileNotFoundError:
            return f"Error: Project root '{project_root}' not found."

        # 3. Lazy Load Engine
        if _cached_engine is None:
            try:
                # Late import to ensure sys.path is ready
                from src.core.chat_engine import ChatEngine
                
                cfg_path = os.path.join(project_root, config_rel_path)
                if not os.path.exists(cfg_path):
                    return f"Error: Config file not found at {cfg_path}"
                    
                print(f"[Wrapper] Loading config from {cfg_path}...")
                with open(cfg_path, 'r') as f:
                    cfg = yaml.safe_load(f)
                
                print("[Wrapper] Initializing ChatEngine (this may take time)...")
                _cached_engine = ChatEngine(cfg)
                print("[Wrapper] ChatEngine loaded successfully.")
                
            except Exception as e:
                import traceback
                return f"Error loading ChatEngine: {str(e)}\n{traceback.format_exc()}"

        # 4. Process Query
        try:
            res = _cached_engine.process(query, session_id=session_id)
            return res.get("answer", "No answer returned.")
        except Exception as e:
            return f"Runtime Error: {str(e)}"
