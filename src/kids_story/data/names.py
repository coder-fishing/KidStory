"""Conservative English character-name candidates and human-reviewed suggestions."""

import re
from collections import Counter

# User-approved mapping suggestions; never applied to story text automatically.
VI_NAME_SUGGESTIONS = {"sue": "Xuân", "tom": "Tâm", "jerry": "Gia Huy",
                       "amy": "Trà My", "lily": "Ly", "tim": "Tín",
                       "buddy": "Bắp", "max": "Mã"}
STOP = {"once", "there", "one", "then", "but", "they", "now", "everyone", "the",
        "in", "as", "it", "he", "she", "we", "my", "his", "her", "this", "after",
        "finally", "suddenly", "when", "what", "hello", "hi", "thank", "thankyou"}
PATTERNS = [re.compile(r"\b(?:named|called)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)"),
            re.compile(r"\b(?:I am|I'm)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)"),
            re.compile(r"\b(?:Hi|Hello),?\s+([A-Z][a-z]+)\b")]


def suggest_names(english: str) -> dict:
    if not isinstance(english, str):
        return {"source_names": [], "suggestions": [], "method": "no_english_source"}
    evidence = Counter()
    for pattern in PATTERNS:
        for match in pattern.finditer(english):
            evidence[match.group(1)] += 3
    # Recurring capitalized words away from sentence starts are weaker candidates.
    for match in re.finditer(r"\b[A-Z][a-z]{1,20}\b", english):
        word = match.group()
        prefix = english[:match.start()].rstrip()
        at_sentence_start = not prefix or prefix[-1:] in ".!?\n\"”'"
        if word.casefold() not in STOP and not at_sentence_start:
            evidence[word] += 1
    names = sorted((n for n, score in evidence.items() if score >= 2), key=str.casefold)
    suggestions = [{"source": name,
                    "vietnamese_suggestion": VI_NAME_SUGGESTIONS.get(name.casefold(), name),
                    "basis": "user_approved_mapping_v2_candidate_only" if name.casefold() in VI_NAME_SUGGESTIONS else "keep_original_pending_review"}
                   for name in names]
    return {"source_names": names, "suggestions": suggestions,
            "method": "pattern_and_repeated_capitalization_heuristic_v1"}
