"""Apply reviewed, context-specific edits and require fresh story approval."""

import copy
from pathlib import Path

from .io import digest, write_json, write_jsonl
from .process import normalize_text, process_rows
from .review import (
    candidates,
    export_review,
    fingerprint,
    read_csv,
    require_human,
    write_csv,
)


COLUMNS = [
    "edit_id", "source_id", "record_hash", "kind", "before", "after",
    "reason", "decision", "reviewer", "reviewed_at", "review_notes",
]


def export_edits(records: list[dict], path: Path) -> None:
    """One blank proposal per story; duplicate with a unique edit_id if needed."""
    if Path(path).exists():
        raise ValueError("Edit sheet already exists")
    rows = []
    for record in candidates(records):
        rows.append({
            "edit_id": fingerprint([record["source_id"], "edit-1"]),
            "source_id": record["source_id"],
            "record_hash": fingerprint(record),
            "kind": "text",
            "before": "",
            "after": "",
            "reason": "",
            "decision": "pending",
            "reviewer": "",
            "reviewed_at": "",
            "review_notes": "",
        })
    write_csv(path, COLUMNS, rows)


def apply_edits(records: list[dict], sheet: Path, output_dir: Path) -> dict:
    """Replace a unique literal span per proposal, never a global name map."""
    if Path(output_dir).exists():
        raise ValueError("Output exists")
    source = {row["source_id"]: row for row in candidates(records)}
    proposals = read_csv(sheet, COLUMNS)
    seen = set()
    changes = {}
    for proposal in proposals:
        identity = proposal["edit_id"]
        sid = proposal["source_id"]
        if not identity or identity in seen or sid not in source:
            raise ValueError("Invalid, duplicate edit ID or unknown source ID")
        seen.add(identity)
        if proposal["record_hash"] != fingerprint(source[sid]):
            raise ValueError("Stale edit proposal; export against current records")
        decision = proposal["decision"]
        if decision == "pending":
            continue
        if decision not in {"apply", "keep", "reject"}:
            raise ValueError("decision must be pending/apply/keep/reject")
        require_human(proposal["reviewer"], proposal["reviewed_at"])
        if not proposal["reason"].strip():
            raise ValueError("A reviewed decision requires a reason")
        if decision == "apply":
            if proposal["kind"] not in {"name", "translation", "text"}:
                raise ValueError("Unknown edit kind")
            changes.setdefault(sid, []).append(proposal)

    updated = copy.deepcopy(records)
    for row in updated:
        edits = changes.get(row.get("source_id"), [])
        if not edits:
            continue
        text = row["processed_text"]
        spans = []
        for edit in edits:
            before = edit["before"]
            if not before or text.count(before) != 1:
                raise ValueError("before must match exactly once; include surrounding context")
            if before == edit["after"]:
                raise ValueError("Edit must change text")
            start = text.index(before)
            spans.append((start, start + len(before), edit["after"]))
        spans.sort()
        if any(a[1] > b[0] for a, b in zip(spans, spans[1:])):
            raise ValueError("Overlapping edits; review a combined replacement")
        for start, end, replacement in reversed(spans):
            text = text[:start] + replacement + text[end:]
        text, _ = normalize_text(text)
        if not text.strip():
            raise ValueError("Edits cannot empty the story")
        probe = {
            "source_id": row["source_id"],
            "source_group_id": row["source_group_id"],
            "text": text,
        }
        assessed = process_rows([{
            "value": probe, "error": None, "raw_line": "", "line_number": 1,
        }])[0]
        row["processed_text"] = text
        row["status"] = "candidate"
        row["duplicate_of"] = None
        row["exact_hash"] = digest(text.encode("utf-8"))
        row["flags"] = assessed["flags"]
        row["review_status"] = "pending"
        row["approval_hash"] = None
        for key in ("text_approved", "prompt_metadata_approved", "flags_resolved",
                    "character_names_reviewed"):
            row[key] = False
        row["reviewer"] = ""
        row["reviewed_at"] = ""
        row.setdefault("edit_reasons", []).extend(edit["reason"] for edit in edits)
        row.setdefault("review_history", []).append({
            "event": "reviewed_text_edits_require_fresh_approval",
            "edits": edits,
            "before_record_hash": fingerprint(source[row["source_id"]]),
        })
    Path(output_dir).mkdir(parents=True, exist_ok=False)
    write_jsonl(Path(output_dir) / "records.jsonl", updated)
    export_review(updated, Path(output_dir) / "review")
    manifest = {
        "edited_stories": len(changes),
        "sheet_sha256": digest(Path(sheet).read_bytes()),
        "decisions": proposals,
        "status": "fresh_story_review_required",
    }
    write_json(Path(output_dir) / "edit_manifest.json", manifest)
    write_json(Path(output_dir) / "COMPLETE.json", {
        str(path.relative_to(output_dir)): digest(path.read_bytes())
        for path in sorted(Path(output_dir).rglob("*")) if path.is_file()
    })
    return manifest
