
import sys
from unittest.mock import MagicMock
from src.chat_engine import ChatEngine
from src.rag.article_interpreter import ArticleInterpreter

# Mock Components
mock_vs = MagicMock()
mock_kp = MagicMock()
mock_cache = MagicMock()
mock_optimizer = MagicMock()
mock_controller = MagicMock()


# Setup ChatEngine
# Assume keys are passed in config or just mocked args
# Looking at file: __init__(self, retrieval_pipeline=None, vector_store=None, ...)
# Actually, the file signature was NOT completely visible. 
# But usually it accepts args. 
# Let's try passing just config={} if it takes config.
# Or better: check what arguments it actually takes.
# From ViewFile line 108: __init__(self, config_path=None, ...) or properties.

# It seems ChatEngine loads its own resources if not provided?
# Or maybe the args I passed (vector_store) are correct but named differently?
# Let's instantiate carefully.

# Assuming the signature is:
# def __init__(self, config_path: str = "configs/config.yaml"):
# And it initializes internal components.
# Ideally we inject mocks.
# If injection isn't supported, we patch attributes AFTER init.

engine = ChatEngine(config_path="configs/config.yaml")
# Inject Mocks AFTER init
engine.vs = mock_vs
engine.kp_manager = mock_kp
engine.processed_cache = mock_cache
engine.retrieval_optimizer = mock_optimizer
engine.controller = mock_controller


# Mock VS Hybrid Query to return a hit that triggers "HOWTO_PROCEDURE" logic
# Strategy needs to return valid hits
class MockResult:
    def __init__(self, text, metadata):
        self.text = text
        self.metadata = metadata
        self.score = 0.9

mock_vs.hybrid_query.return_value = [
    MockResult("EtherChannel content...", {"title": "EtherChannel Guide", "url": "http://example.com/etherchannel", "source": "http://example.com/etherchannel"})
]

# Mock ArticleInterpreter to spy on the 'user_query' argument
engine.article_interpreter = MagicMock()
engine.article_interpreter.interpret.return_value = "Mock Answer"

# Query that triggers HOWTO and Strip Logic
query = "ทำความรู้จัก EtherChannel" # "ความรู้" might trigger stripping if logic is loose, but specifically "ความรู้" keyword
# Actually "ทำความรู้จัก" contains "ความรู้". 
# chat_engine.py checks: KNOWLEDGE_KEYWORDS = ["ความรู้", "knowledge"]
# any(kw in q.lower()) -> True.

print(f"Testing Query: {query}")
# Force Intent to HOWTO_PROCEDURE for test (simulating Router)
# Or assume router returns it? ChatEngine calls router internaly?
# Actually ChatEngine.process calls router.route.
engine.router = MagicMock()
engine.router.route.return_value = {"intent": "HOWTO_PROCEDURE", "confidence": 1.0}

# Run Process
result = engine.process(query)

# Check call args of interpret
call_args = engine.article_interpreter.interpret.call_args
if call_args:
    passed_query = call_args[1].get('user_query')
    print(f"Passed Query to Interpreter: '{passed_query}'")
    
    if "ทำความรู้จัก" in passed_query:
        print("[PASS] Original Keyword 'ทำความรู้จัก' Preserved.")
    else:
        print(f"[FAIL] Keyword Lost! Query became: '{passed_query}'")
else:
    print("[FAIL] Interpreter not called.")
