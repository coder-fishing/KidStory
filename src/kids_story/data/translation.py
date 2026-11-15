"""Conservative bilingual translation-calque candidates; never edits source text."""

import re


RULES = [
    {
        "rule_id": "literal_have_a_good_time_v1",
        "english": re.compile(r"\b(?:had|has|have)\s+(?:a\s+)?(?:good|great|wonderful|fun)\s+time\b", re.I),
        "vietnamese": re.compile(r"\b(?:đã\s+)?có\s+(?:một\s+)?(?:thời gian|khoảng thời gian)\s+(?:tốt|tuyệt vời|vui vẻ|rất vui)\b", re.I),
        "suggestion": "Có thể diễn đạt là ‘đã rất vui’ hoặc ‘đã vui chơi’, tùy chủ ngữ và ngữ cảnh.",
        "reason": "Cặp cụm có thể phản ánh cấu trúc dịch sát ‘have a good time’; cần đọc cả câu.",
    },
    {
        "rule_id": "literal_make_a_decision_v1",
        "english": re.compile(r"\b(?:make|made|makes)\s+a\s+decision\b", re.I),
        "vietnamese": re.compile(r"\b(?:làm|tạo(?:\s+ra)?)\s+một\s+quyết định\b", re.I),
        "suggestion": "Cân nhắc ‘đưa ra quyết định’ hoặc ‘quyết định’, tùy câu.",
        "reason": "Cặp cụm có thể dịch sát kết hợp từ ‘make a decision’; cần đọc cả câu.",
    },
]


def translation_candidates(source_id: str, english: str, vietnamese: str) -> list[dict]:
    """Return review-only bilingual rule matches with local sentence context."""
    if not isinstance(english, str) or not isinstance(vietnamese, str):
        return []
    result = []
    for rule in RULES:
        en_match = rule["english"].search(english)
        vi_match = rule["vietnamese"].search(vietnamese)
        if not en_match or not vi_match:
            continue
        result.append({
            "source_id": source_id,
            "rule_id": rule["rule_id"],
            "english_phrase": en_match.group(),
            "vietnamese_phrase": vi_match.group(),
            "english_context": english,
            "vietnamese_context": vietnamese,
            "suggestion": rule["suggestion"],
            "reason": rule["reason"],
            "review_status": "pending",
            "review_notes": "",
        })
    return result
