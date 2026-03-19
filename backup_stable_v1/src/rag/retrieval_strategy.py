
from typing import NamedTuple, Optional

class RetrievalStrategy(NamedTuple):
    alpha: float # 0.0=BM25, 1.0=Vector, 0.5=Hybrid
    top_k: int
    mode: str

class StrategyFactory:
    @staticmethod
    def get_strategy(intent: str) -> RetrievalStrategy:
        """
        Returns retrieval strategy based on intent.
        """
        if intent == "HOWTO_PROCEDURE":
            # Phase 175: Expanded recall for technical guides
            return RetrievalStrategy(alpha=0.4, top_k=8, mode="KEYWORD_HEAVY_EXPANDED")
        elif intent in ["CONTACT_LOOKUP", "PERSON_LOOKUP", "TEAM_LOOKUP"]:
            return RetrievalStrategy(alpha=0.3, top_k=3, mode="KEYWORD_HEAVY")
            
        # 2. Conceptual / Summary -> Vector Heavy
        elif intent in ["SUMMARIZE", "EXPLAIN", "CONCEPT_EXPLAIN"]:
            return RetrievalStrategy(alpha=0.8, top_k=5, mode="VECTOR_HEAVY")
            
        # 3. Troubleshooting -> Balanced but Broad
        elif intent in ["TROUBLESHOOT", "SYMPTOM_CHECK"]:
            return RetrievalStrategy(alpha=0.5, top_k=5, mode="BALANCED_BROAD")
        
        # 4. News -> Keyword dominant (Title match)
        elif intent == "NEWS_SEARCH":
            return RetrievalStrategy(alpha=0.2, top_k=5, mode="KEYWORD_DOMINANT")

        # Default -> Balanced
        return RetrievalStrategy(alpha=0.5, top_k=3, mode="BALANCED_DEFAULT")
