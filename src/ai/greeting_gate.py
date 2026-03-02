"""
Greeting Gate

Purpose: Detect pure greetings and respond immediately without full pipeline
"""

GREETING_RESPONSE = "สวัสดีครับ ผมคือ AI เบบี๋ ประจำ SMC พี่ ๆ อยากทราบข้อมูลอะไร สอบถามได้ครับ"

PROMPT_GREETING_GATE = """
You are a Greeting Gate for an internal SMC assistant.

Goal:
Detect only PURE greetings and respond immediately.

GREETING MESSAGE (exact):
"สวัสดีครับ ผมคือ AI เบบี๋ ประจำ SMC พี่ ๆ อยากทราบข้อมูลอะไร สอบถามได้ครับ"

PURE_GREETING definition:
A message is PURE_GREETING if ALL conditions are met:

1) Message length <= 3 words OR <= 15 characters
2) Contains a greeting core token:
   - Thai: สวัสดี, หวัสดี, ดีครับ, ดีค่ะ
   - English: hi, hello, hey
   - Emoji: 👋 😊 🙏
3) After removing greeting tokens, polite particles (ครับ/ค่ะ), emojis, and punctuation,
   no other meaningful tokens remain.

IMPORTANT:
- Do NOT use broad keyword blacklists.
- If greeting appears together with a real question or request,
  treat it as NOT_GREETING and continue normal routing.

Output:
- PURE_GREETING → return greeting message
- NOT_GREETING → continue pipeline

Input: {query}

Output: PURE_GREETING or NOT_GREETING (one word only)
"""

# Greeting core tokens
GREETING_TOKENS = {
    # Thai
    "สวัสดี", "หวัดดี", "ดีครับ", "ดีค่ะ", "ดีจ้า", "ดีจ๊ะ",
    # English
    "hi", "hello", "hey", "greetings",
    # Emoji
    "👋", "😊", "🙏", "😃", "😄"
}

# Polite particles and noise to remove
NOISE_TOKENS = {
    "ครับ", "ค่ะ", "จ้า", "จ๊ะ", "นะ", "ค่า", "คะ",
    "!", ".", ",", "?", " "
}

def is_pure_greeting(query: str) -> bool:
    """
    Deterministic check for pure greeting.
    
    Returns True only if query is a pure greeting with no other content.
    """
    if not query:
        return False
    
    query_lower = query.lower().strip()
    
    # Rule 1: Length check (<=3 words OR <=15 chars)
    word_count = len(query.split())
    char_count = len(query)
    
    if word_count > 3 and char_count > 15:
        return False
    
    # Rule 2: Must contain greeting token
    has_greeting = any(token in query_lower for token in GREETING_TOKENS)
    if not has_greeting:
        return False
    
    # Rule 3: After removing greeting tokens and noise, nothing meaningful remains
    cleaned = query_lower
    
    # Remove greeting tokens
    for token in GREETING_TOKENS:
        cleaned = cleaned.replace(token, "")
    
    # Remove noise tokens
    for noise in NOISE_TOKENS:
        cleaned = cleaned.replace(noise, "")
    
    # Remove extra spaces
    cleaned = " ".join(cleaned.split())
    
    # If anything meaningful remains, it's NOT a pure greeting
    if len(cleaned) > 0:
        return False
    
    return True


def get_greeting_response() -> str:
    """Return the standard greeting response."""
    return GREETING_RESPONSE
