"""
Canonical Phrase Rules for Contact Lookup

Purpose: Handle variations of technical terms and boost exact matches
"""

# Canonical phrase mappings
# Format: {canonical_form: [variations]}
CANONICAL_PHRASES = {
    "ip-phone": [
        "ip phone",
        "ip-phone", 
        "ipphone",
        "ไอพีโฟน",
        "โทรศัพท์ไอพี",
        "ip phone",
        "IP Phone",
        "IP-Phone"
    ],
    "sip-proxy": [
        "sip proxy",
        "sip-proxy",
        "sipproxy",
        "SIP Proxy",
        "SIP-Proxy"
    ],
    "ip-network": [
        "ip network",
        "ip-network",
        "ipnetwork",
        "IP Network"
    ]
}

# Reverse mapping for quick lookup
PHRASE_TO_CANONICAL = {}
for canonical, variations in CANONICAL_PHRASES.items():
    for variation in variations:
        PHRASE_TO_CANONICAL[variation.lower()] = canonical

def get_canonical_phrase(query: str) -> tuple[str, str]:
    """
    Get canonical phrase from query.
    
    Args:
        query: User query
        
    Returns:
        (canonical_phrase, rewritten_query) or (None, original_query)
    """
    query_lower = query.lower()
    
    # Check for any variation
    for variation, canonical in PHRASE_TO_CANONICAL.items():
        if variation in query_lower:
            # Rewrite query to use canonical form
            rewritten = query_lower.replace(variation, canonical)
            return canonical, rewritten
    
    return None, query

def boost_score_for_canonical(candidate: str, canonical_phrase: str, base_score: float) -> float:
    """
    Boost score if candidate contains canonical phrase.
    
    Args:
        candidate: Candidate text to check
        canonical_phrase: Canonical phrase to look for
        base_score: Base similarity score
        
    Returns:
        Boosted score if canonical phrase found, otherwise base_score
    """
    if not canonical_phrase:
        return base_score
    
    candidate_lower = candidate.lower()
    
    # Exact canonical match gets highest boost
    if canonical_phrase in candidate_lower:
        return base_score * 1.5  # 50% boost
    
    # Partial match gets smaller boost
    canonical_parts = canonical_phrase.split("-")
    if all(part in candidate_lower for part in canonical_parts):
        return base_score * 1.2  # 20% boost
    
    return base_score

def apply_canonical_rules(query: str, candidates: list[dict]) -> tuple[str, list[dict]]:
    """
    Apply canonical phrase rules to query and boost relevant candidates.
    
    Args:
        query: User query
        candidates: List of candidate dicts with 'text' and 'score' keys
        
    Returns:
        (rewritten_query, boosted_candidates)
    """
    # Get canonical phrase
    canonical, rewritten_query = get_canonical_phrase(query)
    
    if not canonical:
        return query, candidates
    
    # Boost candidates containing canonical phrase
    boosted_candidates = []
    for candidate in candidates:
        text = candidate.get('text', '')
        score = candidate.get('score', 0.0)
        
        boosted_score = boost_score_for_canonical(text, canonical, score)
        
        boosted_candidate = candidate.copy()
        boosted_candidate['score'] = boosted_score
        boosted_candidate['boosted'] = boosted_score > score
        
        boosted_candidates.append(boosted_candidate)
    
    # Re-sort by boosted scores
    boosted_candidates.sort(key=lambda x: x['score'], reverse=True)
    
    return rewritten_query, boosted_candidates
