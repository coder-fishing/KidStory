"""CPU-only descriptive EDA and review-candidate exports for bilingual JSONL."""

import platform
import re
import statistics
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

from .io import digest, read_jsonl, write_json
from .names import suggest_names
from .process import normalize_text
from .review import write_csv
from .translation import translation_candidates

NAME_COLUMNS = ["source_id", "source_name_en", "suggestion_vi", "basis",
                "source_text_en", "source_text_vi", "review_status", "review_notes"]
TRANSLATION_COLUMNS = ["source_id", "rule_id", "english_phrase", "vietnamese_phrase",
                       "english_context", "vietnamese_context", "suggestion", "reason",
                       "review_status", "review_notes"]
PUNCTUATION = set(".,!?;:…—–-()[]{}\"'“”‘’«»")


def _distribution(values: list[int]) -> dict:
    values = sorted(values)
    if not values:
        return {"count": 0, "min": None, "p25": None, "median": None,
                "p75": None, "max": None}

    def quantile(q: float):
        return values[round((len(values) - 1) * q)]

    return {"count": len(values), "min": values[0], "p25": quantile(.25),
            "median": statistics.median(values), "p75": quantile(.75), "max": values[-1]}


def _text_summary(records: list[dict], field: str) -> dict:
    values = [r.get(field) for r in records]
    strings = [v for v in values if isinstance(v, str)]
    normalized = [normalize_text(v)[0] for v in strings]
    hashes = Counter(digest(text.encode("utf-8")) for text in normalized if text)
    duplicate_excess = sum(n - 1 for n in hashes.values())
    punctuation = Counter(c for text in strings for c in text if c in PUNCTUATION)
    controls = Counter(unicodedata.name(c, f"U+{ord(c):04X}") for text in strings
                       for c in text if unicodedata.category(c) in {"Cc", "Cf"} and c not in "\n\r\t")
    non_latin_letters = Counter(unicodedata.name(c, f"U+{ord(c):04X}").split(" ")[0]
        for text in strings for c in text if unicodedata.category(c).startswith("L")
        and "LATIN" not in unicodedata.name(c, ""))
    latin_words = [w for text in strings for w in re.findall(r"\b[A-Za-z]+\b", text)]
    words = [w for text in strings for w in re.findall(r"\b\w+\b", text, flags=re.UNICODE)]
    return {
        "value_types": dict(sorted(Counter(type(v).__name__ for v in values).items())),
        "null_count": sum(v is None for v in values),
        "empty_or_whitespace_count": sum(isinstance(v, str) and not v.strip() for v in values),
        "character_length": _distribution([len(v) for v in strings]),
        "whitespace_units": _distribution([len(v.split()) for v in strings]),
        "exact_duplicate_excess_after_nfc_whitespace_normalization": duplicate_excess,
        "punctuation_counts": dict(sorted(punctuation.items())),
        "unusual_control_or_format_character_counts": dict(sorted(controls.items())),
        "non_latin_letter_name_prefix_counts": dict(sorted(non_latin_letters.items())),
        "ascii_latin_word_ratio_heuristic": (len(latin_words) / len(words)) if words else None,
        "ascii_latin_word_ratio_note": "Heuristic only; not a language identifier.",
        "missing_terminal_punctuation_count": sum(
            bool(v.strip()) and not normalize_text(v)[0].rstrip('"”’\'').endswith((".", "!", "?", "…"))
            for v in strings),
    }


def _repetition_source_ids(records: list[dict]) -> tuple[list[str], list[str]]:
    repeated_lines, repeated_ngrams = [], []
    for index, record in enumerate(records, 1):
        text = record.get("vi")
        if not isinstance(text, str) or not text.strip():
            continue
        source_id = record.get("source_id")
        source_id = source_id if isinstance(source_id, str) and source_id else f"missing-source-id-line-{index}"
        normalized = normalize_text(text)[0]
        lines = [line.strip() for line in normalized.splitlines() if line.strip()]
        if len(lines) != len(set(lines)):
            repeated_lines.append(source_id)
        words = re.findall(r"\w+", normalized.casefold(), flags=re.UNICODE)
        grams = [tuple(words[j:j + 5]) for j in range(max(0, len(words) - 4))]
        if grams and (len(grams) - len(set(grams))) / len(grams) >= .3:
            repeated_ngrams.append(source_id)
    return repeated_lines, repeated_ngrams


def run_eda(input_path: Path, output_dir: Path,
            source_manifest_path: Path | None = None) -> dict:
    """Analyze every JSONL row and write versioned reports without editing input."""
    input_path, output_dir = Path(input_path), Path(output_dir)
    if output_dir.exists():
        raise ValueError("Output directory exists; refusing overwrite")
    entries = read_jsonl(input_path)
    input_sha256 = digest(input_path.read_bytes())
    source_manifest = None
    source_manifest_sha256 = None
    if source_manifest_path is not None:
        import json
        source_manifest_path = Path(source_manifest_path)
        source_manifest_sha256 = digest(source_manifest_path.read_bytes())
        source_manifest = json.loads(source_manifest_path.read_text(encoding="utf-8"))
        if source_manifest.get("artifact_sha256", {}).get("sample.jsonl") != input_sha256:
            raise ValueError("Source manifest does not match input sample hash")
    records = [e["value"] for e in entries if not e["error"] and isinstance(e["value"], dict)]
    if source_manifest is not None:
        expected_revision = source_manifest.get("resolved_revision")
        observed_revisions = {r.get("source_revision") for r in records if r.get("source_revision")}
        if observed_revisions and observed_revisions != {expected_revision}:
            raise ValueError("Source manifest revision does not match JSONL rows")
        expected_indices = source_manifest.get("sampling", {}).get("row_indices")
        observed_indices = [r.get("source_row_id") for r in records]
        if expected_indices is not None and observed_indices != expected_indices:
            raise ValueError("Source manifest row indices do not match JSONL rows")
    malformed = [{"line_number": e["line_number"], "reason": e["error"]}
                 for e in entries if e["error"]]
    name_rows, name_counts, name_surface_counts = [], Counter(), Counter()
    translation_rows = []
    groups, en_hashes, vi_hashes = Counter(), defaultdict(list), defaultdict(list)
    truncation_ids = []
    for i, record in enumerate(records, 1):
        source_id = record.get("source_id")
        if not isinstance(source_id, str) or not source_id:
            source_id = f"missing-source-id-line-{i}"
        group_id = record.get("source_group_id")
        groups[str(group_id) if group_id is not None else "<missing>"] += 1
        en, vi = record.get("en"), record.get("vi")
        for value, target in ((en, en_hashes), (vi, vi_hashes)):
            if isinstance(value, str) and value.strip():
                normalized = normalize_text(value)[0]
                target[digest(normalized.encode("utf-8"))].append(source_id)
        proposal = suggest_names(en)
        for item in proposal["suggestions"]:
            name_counts[item["source"].casefold()] += 1
            name_surface_counts[item["source"]] += 1
            name_rows.append({"source_id": source_id, "source_name_en": item["source"],
                "suggestion_vi": item["vietnamese_suggestion"], "basis": item["basis"],
                "source_text_en": en if isinstance(en, str) else "",
                "source_text_vi": vi if isinstance(vi, str) else "",
                "review_status": "pending", "review_notes": ""})
        translation_rows.extend(translation_candidates(source_id, en, vi))
        if isinstance(vi, str) and vi.strip():
            normalized = normalize_text(vi)[0]
            if not normalized.rstrip('"”’\'').endswith((".", "!", "?", "…")):
                truncation_ids.append(source_id)

    def duplicate_groups(index: dict) -> list[dict]:
        return [{"source_ids": ids, "count": len(ids)} for ids in index.values() if len(ids) > 1]

    field_counts = {field: _text_summary(records, field) for field in ("en", "vi")}
    repeated_line_ids, repeated_ngram_ids = _repetition_source_ids(records)
    revisions = sorted({r.get("source_revision") for r in records if r.get("source_revision")})
    sampling_methods = sorted({r.get("sampling_method") for r in records if r.get("sampling_method")})
    report = {
        "schema_version": 1,
        "input_sha256": input_sha256,
        "input_rows": len(entries), "valid_json_objects": len(records),
        "malformed_rows": malformed,
        "source_revisions": revisions, "sampling_methods": sampling_methods,
        "source_manifest": source_manifest,
        "field_summary": field_counts,
        "source_group_count": len(groups),
        "source_group_size_distribution": _distribution(list(groups.values())),
        "exact_duplicate_groups_en": duplicate_groups(en_hashes),
        "exact_duplicate_groups_vi": duplicate_groups(vi_hashes),
        "possible_truncation_vi_source_ids": truncation_ids,
        "english_name_candidate_frequencies": dict(sorted(name_counts.items())),
        "english_name_candidate_surface_frequencies": dict(sorted(
            name_surface_counts.items(), key=lambda item: item[0].casefold())),
        "possible_repeated_line_vi_source_ids": repeated_line_ids,
        "possible_repeated_ngram_vi_source_ids": repeated_ngram_ids,
        "name_candidate_rows": len(name_rows),
        "translation_calque_candidate_rows": len(translation_rows),
        "limitations": [
            "EDA describes only the supplied snapshot; it does not certify the full dataset.",
            "English-name extraction and translation patterns are heuristic candidates for human review.",
            "Punctuation, Latin-word ratio, and missing-terminal-punctuation signals are not quality judgments.",
            "No near-duplicate or semantic translation-quality claim is made by this report.",
            "Candidate tables remain pending and no source text is modified.",
        ],
    }
    output_dir.mkdir(parents=True, exist_ok=False)
    write_json(output_dir / "eda_report.json", report)
    write_csv(output_dir / "name_candidates.csv", NAME_COLUMNS, name_rows)
    write_csv(output_dir / "translation_candidates.csv", TRANSLATION_COLUMNS, translation_rows)
    manifest = {"schema_version": 1, "python_version": platform.python_version(),
        "input_path": str(input_path), "input_sha256": report["input_sha256"],
        "source_manifest_path": str(source_manifest_path) if source_manifest_path else None,
        "source_manifest_sha256": source_manifest_sha256,
        "source_revisions": revisions, "sampling_methods": sampling_methods,
        "outputs": {p.name: digest(p.read_bytes()) for p in sorted(output_dir.iterdir()) if p.is_file()}}
    write_json(output_dir / "eda_manifest.json", manifest)
    write_json(output_dir / "COMPLETE.json", {
        p.name: digest(p.read_bytes()) for p in sorted(output_dir.iterdir()) if p.is_file()})
    return report
