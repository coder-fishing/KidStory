"""Version-bound CSV review round trips. Human decisions are never inferred."""

import copy
import csv
import json
from datetime import datetime
from pathlib import Path

from .io import digest, json_bytes, read_jsonl, write_json, write_jsonl
from .process import normalize_text, process_rows
from .names import suggest_names

EDITABLE = ["processed_text", "topic", "characters", "lesson", "label_source",
            "source_character_names_en", "character_name_notes", "character_names_reviewed",
            "character_name_suggestions_vi", "character_name_suggestion_method",
            "review_status", "review_notes", "text_approved", "flags_resolved",
            "prompt_metadata_approved", "reviewer", "reviewed_at"]
READONLY = ["source_id", "source_revision", "source_group_id", "source_text_en",
            "original_text", "flags", "record_hash"]


def fingerprint(record: dict) -> str:
    return digest(json_bytes(record))


def load_records(path: Path) -> list[dict]:
    entries = read_jsonl(Path(path))
    if any(e["error"] for e in entries):
        raise ValueError("Expected processed JSONL objects, not raw/malformed input")
    rows = [e["value"] for e in entries]
    ids = [r.get("audit_id", r.get("source_id")) for r in rows]
    if not all(isinstance(i, str) and i for i in ids) or len(set(ids)) != len(ids):
        raise ValueError("Missing/duplicate record identities")
    return rows


def candidates(records: list[dict]) -> list[dict]:
    rows = [r for r in records if r.get("status") in {"candidate", "duplicate"}]
    ids = [r.get("source_id") for r in rows]
    if not all(isinstance(i, str) and i for i in ids) or len(set(ids)) != len(ids):
        raise ValueError("Missing/duplicate source IDs")
    for r in rows:
        text = r.get("processed_text")
        if not isinstance(text, str) or not text.strip() or not r.get("source_group_id"):
            raise ValueError("Invalid candidate text/group")
        if digest(text.encode("utf-8")) != r.get("exact_hash"):
            raise ValueError("Text hash mismatch: reprocess changed input before review")
    return sorted(rows, key=lambda r: r["source_id"])


def corpus_hash(records: list[dict]) -> str:
    return fingerprint([{k: r[k] for k in ("source_id", "source_revision", "source_group_id", "exact_hash")}
                        for r in candidates(records)])


def write_csv(path: Path, columns: list[str], rows: list[dict]) -> None:
    # BOM is intentional for Vietnamese in Excel; csv quotes multiline stories.
    with Path(path).open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path, columns: list[str]) -> list[dict]:
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != columns:
            raise ValueError("CSV headers/order changed")
        rows = list(reader)
    if any(None in r or any(v is None for v in r.values()) for r in rows):
        raise ValueError("Malformed CSV row")
    return rows


def require_human(reviewer: str, reviewed_at: str) -> None:
    if not isinstance(reviewer, str) or not reviewer.strip() or reviewer.strip().casefold() in {"ai", "llm", "pending"}:
        raise ValueError("A human reviewer identity is required")
    try:
        when = datetime.fromisoformat(reviewed_at.replace("Z", "+00:00"))
        if when.tzinfo is None or when.utcoffset() is None:
            raise ValueError("Missing timezone")
    except (ValueError, TypeError, AttributeError) as error:
        raise ValueError("reviewed_at must be ISO 8601 with timezone") from error


def approval_payload(row: dict) -> str:
    return fingerprint({k: row.get(k) for k in ["source_id", "source_revision", "source_group_id",
        "source_split", "source_row_id", "original_record", "original_text", "processed_text",
        "exact_hash", "flags", *EDITABLE[1:]]})


def validate_approval(row: dict, *, check_hash: bool = True) -> None:
    if row.get("review_status") != "approved":
        raise ValueError("Review is not approved")
    for key in ["topic", "characters", "lesson", "label_source"]:
        if not isinstance(row.get(key), str) or not row[key].strip():
            raise ValueError(f"Required approved metadata missing: {key}")
    if not isinstance(row.get("source_character_names_en"), str) or not row["source_character_names_en"].strip():
        raise ValueError("Review source character names, or explicitly write none")
    if not isinstance(row.get("character_name_notes"), str) or not row["character_name_notes"].strip():
        raise ValueError("Explain whether character names were kept or localized")
    for key in ["text_approved", "prompt_metadata_approved", "character_names_reviewed"]:
        if row.get(key) is not True:
            raise ValueError(f"Human confirmation required: {key}")
    if row.get("flags") and (row.get("flags_resolved") is not True or not row.get("review_notes", "").strip()):
        raise ValueError("Review flags require explicit resolution and notes")
    require_human(row.get("reviewer", ""), row.get("reviewed_at", ""))
    if check_hash and row.get("approval_hash") != approval_payload(row):
        raise ValueError("Stale approval: text/metadata/provenance changed")


def export_review(records: list[dict], output_dir: Path) -> dict:
    rows, sheet = candidates(records), []
    baseline = {}
    for r in rows:
        en = (r.get("original_record") or {}).get("en", "")
        proposal = suggest_names(en)
        readonly = {"source_id": r["source_id"], "source_revision": r.get("source_revision") or "",
                    "source_group_id": r["source_group_id"],
                    "source_text_en": en,
                    "original_text": r["original_text"],
                    "flags": json.dumps(r["flags"], ensure_ascii=False), "record_hash": fingerprint(r)}
        editable = {k: r.get(k) if r.get(k) is not None else "" for k in EDITABLE}
        editable["source_character_names_en"] = "; ".join(proposal["source_names"])
        editable["character_name_suggestions_vi"] = json.dumps(proposal["suggestions"], ensure_ascii=False)
        editable["character_name_suggestion_method"] = proposal["method"]
        for key in ["text_approved", "flags_resolved", "prompt_metadata_approved", "character_names_reviewed"]:
            editable[key] = "true" if r.get(key) is True else "false"
        sheet.append({**readonly, **editable})
        baseline[r["source_id"]] = {**readonly, "editable_at_export": editable}
    Path(output_dir).mkdir(parents=True, exist_ok=False)
    write_csv(Path(output_dir) / "metadata_review.csv", READONLY + EDITABLE, sheet)
    manifest = {"schema_version": 1, "corpus_hash": corpus_hash(records), "baseline": baseline}
    write_json(Path(output_dir) / "review_baseline.json", manifest)
    return manifest


def import_review(records: list[dict], csv_path: Path, baseline_path: Path) -> list[dict]:
    baseline = json.loads(Path(baseline_path).read_text(encoding="utf-8"))
    if baseline["corpus_hash"] != corpus_hash(records):
        raise ValueError("Stale review corpus/revision")
    current = {r["source_id"]: r for r in candidates(records)}
    sheet = read_csv(csv_path, READONLY + EDITABLE)
    ids = [r["source_id"] for r in sheet]
    if len(set(ids)) != len(ids) or set(ids) != set(current) or set(baseline["baseline"]) != set(current):
        raise ValueError("Review IDs missing, extra or duplicated")
    updated = {}
    for item in sheet:
        sid = item["source_id"]
        expected = baseline["baseline"][sid]
        if any(item[k] != expected[k] for k in READONLY) or fingerprint(current[sid]) != expected["record_hash"]:
            raise ValueError(f"Stale or modified read-only data: {sid}")
        row = copy.deepcopy(current[sid])
        old = copy.deepcopy(row)
        for k in EDITABLE:
            row[k] = item[k] or None
        for k in ["text_approved", "flags_resolved", "prompt_metadata_approved", "character_names_reviewed"]:
            if item[k] not in {"true", "false"}:
                raise ValueError(f"{k} must be true/false")
            row[k] = item[k] == "true"
        if row["review_status"] not in {"pending", "approved", "rejected"}:
            raise ValueError("review_status must be pending/approved/rejected")
        if not isinstance(row["processed_text"], str) or not row["processed_text"].strip():
            raise ValueError("Edited text must not be empty; reject unwanted records instead")
        normalized, _ = normalize_text(row["processed_text"])
        if normalized != row["processed_text"]:
            raise ValueError("Edited text must already be NFC/whitespace-normalized")
        row["exact_hash"] = digest(normalized.encode("utf-8"))
        if normalized != old["processed_text"]:
            if row["review_status"] == "approved":
                raise ValueError("Text edits require pending import and fresh review before approval")
            probe = {"source_id": sid, "source_group_id": row["source_group_id"], "text": normalized}
            row["flags"] = process_rows([{"value": probe, "error": None, "raw_line": "", "line_number": 1}])[0]["flags"]
            row["edit_reasons"] = list(old.get("edit_reasons", [])) + ["human_text_edit_pending"]
            row["text_approved"] = row["prompt_metadata_approved"] = row["flags_resolved"] = False
        row["review_notes"] = item["review_notes"]
        row["approval_hash"] = None
        # Compare sheet values, not serialization defaults (None -> empty/false).
        before_sheet = expected.get("editable_at_export")
        changed = (any(item[k] != before_sheet[k] for k in EDITABLE) if before_sheet is not None
                   else any(old.get(k) != row.get(k) for k in EDITABLE))
        if changed and row["review_status"] != "pending":
            require_human(row.get("reviewer") or "", row.get("reviewed_at") or "")
        if row["review_status"] == "approved":
            validate_approval(row, check_hash=False)
            row["approval_hash"] = approval_payload(row)
        # Every imported edit is retained; original record is never overwritten.
        history = list(old.get("review_history", []))
        if changed:
            history.append({"before": {k: old.get(k) for k in EDITABLE},
                            "after": {k: row.get(k) for k in EDITABLE},
                            "baseline_record_hash": fingerprint(old),
                            "review_csv_sha256": digest(Path(csv_path).read_bytes())})
        row["review_history"] = history
        updated[sid] = row
    return [updated.get(r.get("source_id"), copy.deepcopy(r)) for r in records]
