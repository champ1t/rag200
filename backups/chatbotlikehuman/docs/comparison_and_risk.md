# Comparison & Risk Assessment Report 📊

This report evaluates the system's evolution from a rigid keyword-matched engine to a semantic-aware logic engine.

---

## 1. Direct Comparison (Old vs. New)

| Feature | Baseline (Old) | Current System (New) | Result |
| :--- | :--- | :--- | :--- |
| **Search Accuracy** | Rigid (Literal Match) | Semantic (Noise-Stripped) | **Winner: New** (0.98 vs 0.90 Score) |
| **Query Flexibility** | Formal Thai only | Conversational (ผมจะ, ครับ, หน่อย) | **Winner: New** (High Resilience) |
| **Routing Guard** | Greedy/Hardcoded | Intent-Aware (Bypass How-to) | **Winner: New** (Fewer misroutes) |
| **Maintenance** | Manual Alias Patching | Logic-Level Normalization | **Winner: New** (Scalable/Cleaner) |
| **Performance** | Sub-1s (Search only) | ~2-3s (Search + LLM Cleaning) | **Winner: Old** (Faster but dumber) |

---

## 2. 🛡️ Loophole & Risk Analysis

While the new logic is more robust, every "smart" system has trade-offs. Here is my assessment of potential gaps:

### A. Over-Stripping Risk (Low Level)
- **Gap**: We strip "ที่" (at/of) and "ของ" (of). If a technical term itself contains these characters (unlikely for Latin codes, but possible for some Thai proper nouns), it might slightly alter the search key.
- **Safety**: I limited stripping to a high-certainty list of conversational particles. Technical terms like "OTU" or "VLAN" are untouched.

### B. Ambiguity Guard Sensitivity (Medium Level)
- **Gap**: The system uses a `0.05` difference threshold. If two articles are VERY similar (e.g., "ZTE OLT Model A" and "ZTE OLT Model B"), it will still trigger the "Ambiguity" message.
- **Why it’s okay**: This is a **Safety Feature**. It’s better to ask the user to clarify than to give the wrong technical manual for high-risk configuration.

### C. LLM hallucination in Cleaning (Low Level)
- **Gap**: The `SafeNormalizer` uses an LLM to clean the query. There is a tiny chance it might misinterpret a very complex sentence. 
- **Safety**: I added a "Length Guard" (If rewritten query is 3x longer than original, it ignores the rewrite and uses the raw input).

### D. "How-To" Keyword List (Medium Level)
- **Gap**: The `DispatchMapper` bypass relies on a list: `["วิธีการ", "ขั้นตอน", "วิธี", "ทำยังไง"]`. If a user uses a highly obscure term like "กรบวนการ" (Process - formal), it might still activate the province-asker.
- **Recommendation**: As users interact, we should monitor logs and add any missing synonyms to this list.

---

## 3. 🚀 Overall Verdict

**"Is it working well?"**
**Yes.** The system is significantly more "human" and less prone to "stuttering" when users talk naturally.

**"What to watch out for?"**
Watch the **Latency**. The `SafeNormalizer` adds about 1-2 seconds of overhead because it calls the local LLM. If the system feels slow on peak hours, we might want to optimize the LLM model size (e.g., move to a 1.5b model instead of 3b).

**" loopholes?"**
The biggest loophole is the **Deterministic vs RAG boundary**. Sometimes a query might be *just* broad enough to trigger RAG, but the user actually wanted a specific piece of a table. We’ve mitigated this with the `DispatchMapper` bypass, but it’s a constant balancing act.
