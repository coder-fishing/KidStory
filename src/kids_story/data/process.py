"""Normalization and conservative review flags, never a semantic safety judge."""

import re
import unicodedata
from collections import Counter

from .io import digest

POLICY_VERSION = "nfc-paragraphs-v1"


def normalize_text(text: str) -> tuple[str, list[str]]:
    """NFC, preserve single line/paragraph boundaries; collapse horizontal space."""
    reasons = []
    normalized = unicodedata.normalize("NFC", text)
    if normalized != text:
        reasons.append("unicode_nfc")
    line_endings = normalized.replace("\r\n", "\n").replace("\r", "\n")
    if line_endings != normalized:
        reasons.append("line_endings")
    # Unicode line/paragraph separators become explicit line boundaries.
    line_endings = line_endings.replace("\u2028", "\n").replace("\u2029", "\n\n")
    lines = [re.sub(r"[^\S\n]+", " ", line).strip()
             for line in line_endings.split("\n")]
    compact = re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()
    if compact != normalized.replace("\r\n", "\n").replace("\r", "\n"):
        reasons.append("whitespace")
    return compact, reasons


def process_rows(entries: list[dict], text_field: str = "text",
                 min_units: int = 20) -> list[dict]:
    records, seen_ids = [], set()
    for entry in entries:
        value = entry["value"]
        obj = value if isinstance(value, dict) and not entry["error"] else {}
        source_id = obj.get("source_id")
        valid_id = isinstance(source_id, str) and bool(source_id.strip())
        # Duplicate identities make provenance ambiguous: fail rather than pick one.
        if valid_id:
            if source_id in seen_ids:
                raise ValueError(f"Duplicate source_id: {source_id!r}")
            seen_ids.add(source_id)
        flags = [entry["error"]] if entry["error"] else []
        if not valid_id:
            flags.append("invalid_source_id")
        group = obj.get("source_group_id")
        valid_group = isinstance(group, str) and bool(group.strip())
        if not valid_group:
            flags.append("invalid_source_group_id")
        text = obj.get(text_field)
        if text_field not in obj:
            flags.append("missing_text_field")
        elif not isinstance(text, str):
            flags.append("non_string_text")
        processed, reasons = normalize_text(text) if isinstance(text, str) else (None, [])
        if isinstance(text, str) and not processed:
            flags.append("empty_text")
        eligible = not flags
        if processed:
            units = processed.split()
            if len(units) < min_units:
                flags.append("short_text_review")
            if processed.rstrip('"\u201d\u2019\'').endswith((".", "!", "?", "…")) is False:
                flags.append("possible_truncation_review")
            if any(unicodedata.category(c) in {"Cc", "Cf"} and c not in "\n\t\r"
                   for c in text):
                flags.append("control_or_format_character_review")
            lines = [line for line in processed.splitlines() if line.strip()]
            if len(lines) != len(set(lines)):
                flags.append("repeated_line_review")
            grams = [tuple(units[i:i + 5]) for i in range(max(0, len(units) - 4))]
            if grams and (len(grams) - len(set(grams))) / len(grams) >= .3:
                flags.append("repeated_ngram_review")
        audit_id = source_id if valid_id else (
            f"invalid-line-{entry['line_number']}-{digest(entry['raw_line'].encode('utf-8'))[:12]}")
        records.append({
            "audit_id": audit_id, "source_id": source_id if valid_id else None,
            "source_group_id": group if valid_group else None,
            "source_revision": obj.get("source_revision"),
            "source_split": obj.get("source_split"),
            "source_row_id": obj.get("source_row_id"),
            "original_record": value, "raw_line": entry["raw_line"],
            "input_line": entry["line_number"], "original_text": text,
            "processed_text": processed, "edit_reasons": reasons,
            "flags": flags, "status": "candidate" if eligible else "quarantine",
            "exact_hash": digest(processed.encode("utf-8")) if processed else None,
            "near_duplicate_group_id": None,
            "topic": None, "characters": None, "lesson": None,
            "label_source": None, "review_status": "pending",
            "reviewer": None, "reviewed_at": None,
            "duplicate_of": None, "merged_group_id": None, "split": None,
        })
    return records


def summarize(records: list[dict]) -> dict:
    lengths = [len(r["processed_text"].split()) for r in records if r["processed_text"]]
    chars = [len(r["processed_text"]) for r in records if r["processed_text"]]
    return {
        "input_rows": len(records),
        "status_counts": dict(Counter(r["status"] for r in records)),
        "flag_counts": dict(sorted(Counter(f for r in records for f in r["flags"]).items())),
        "edit_reason_counts": dict(sorted(Counter(f for r in records for f in r["edit_reasons"]).items())),
        "original_text_type_counts": dict(sorted(Counter(type(r["original_text"]).__name__ for r in records).items())),
        "whitespace_units": {"min": min(lengths, default=None), "max": max(lengths, default=None)},
        "unicode_codepoints": {"min": min(chars, default=None), "max": max(chars, default=None)},
        "model_tokens": None,
    }
