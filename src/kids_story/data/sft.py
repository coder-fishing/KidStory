"""Fail-closed SFT export from approved, version-bound review records."""

import copy
import re
from pathlib import Path

from .io import digest, write_json, write_jsonl
from .near import confirmed_edges
from .review import candidates, corpus_hash, fingerprint, require_human, validate_approval
from .split import split_records


def lineage_groups(rows: list[dict], edges: list[tuple[str, str]]) -> dict:
    parent = {r["source_id"]: r["source_id"] for r in rows}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        a, b = find(a), find(b)
        parent[max(a, b)] = min(a, b)

    source, exact = {}, {}
    for r in rows:
        for index, key in [(source, r["source_group_id"]), (exact, r["exact_hash"])]:
            if key in index:
                union(r["source_id"], index[key])
            else:
                index[key] = r["source_id"]
    for a, b in edges:
        if a not in parent or b not in parent:
            raise ValueError("Near edge references unknown ID")
        union(a, b)
    groups = {}
    for sid in sorted(parent):
        groups.setdefault(find(sid), []).append(sid)
    return {sid: fingerprint(ids) for ids in groups.values() for sid in ids}


def check_rights(row: dict, rights: dict, synthetic: bool) -> None:
    original = row.get("original_record", {})
    is_fixture = original.get("fixture_synthetic") is True
    if synthetic:
        if not is_fixture or row.get("source_revision") is not None or original.get("source_dataset"):
            raise ValueError("Synthetic export accepts explicit synthetic fixtures only")
        return
    if is_fixture:
        raise ValueError("Synthetic fixture must use synthetic mode")
    dataset, revision = original.get("source_dataset"), row.get("source_revision")
    if not dataset or not isinstance(revision, str) or not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("Real data requires source dataset and immutable revision")
    for entry in rights.get("sources", []):
        if entry.get("dataset_id") == dataset and entry.get("revision") == revision:
            if entry.get("training_use") != "confirmed" or not entry.get("evidence"):
                raise ValueError("Source rights unresolved; real SFT export blocked")
            require_human(entry.get("reviewer", ""), entry.get("reviewed_at", ""))
            return
    raise ValueError("Source revision absent from rights ledger")


def export_sft(records: list[dict], output_dir: Path, *, near_result: dict,
               near_review: Path, rights: dict, prompt_dir: Path,
               synthetic: bool = False, seed: int = 42,
               validation_ratio: float = .1) -> dict:
    if Path(output_dir).exists():
        raise ValueError("Output exists; refusing overwrite")
    rows = candidates(records)
    edges = confirmed_edges(records, near_result, near_review)
    eligible = [r for r in rows if r.get("review_status") == "approved"]
    if not eligible:
        raise ValueError("No human-approved records; SFT export blocked")
    for row in eligible:
        validate_approval(row)
        check_rights(row, rights, synthetic)
    # Build lineage across ALL candidates before selecting approved subset, so
    # a pending/rejected bridge cannot split source/exact/confirmed-near families.
    group_for = lineage_groups(rows, edges)
    copies = copy.deepcopy(eligible)
    originals = {r["source_id"]: r for r in rows}
    for r in copies:
        r.update(status="candidate", duplicate_of=None, split=None,
                 source_group_id=group_for[r["source_id"]])
    train, validation, split_manifest = split_records(copies, seed, validation_ratio)
    for assignment in split_manifest["assignments"]:
        assignment["lineage_component"] = group_for[assignment["source_id"]]
        assignment["source_group_id"] = originals[assignment["source_id"]]["source_group_id"]
    system_path = Path(prompt_dir) / "story_system_v1.txt"
    template_path = Path(prompt_dir) / "story_user_template_v1.txt"
    system = system_path.read_text(encoding="utf-8")
    template = template_path.read_text(encoding="utf-8")
    if not system.strip() or not template.strip():
        raise ValueError("Empty prompt")

    def conversations(split_rows):
        output = []
        for row in split_rows:
            units = len(row["processed_text"].split())
            # Explicit length matches the approved target instead of silently
            # training a 400-unit story against the 150–250 default instruction.
            low, high = max(1, units - 20), units + 20
            user = template.format(topic=row["topic"], characters=row["characters"],
                                   lesson=row["lesson"], length=f"Khoảng {low}–{high} đơn vị cách trắng.")
            messages = [{"role": "system", "content": system},
                        {"role": "user", "content": user},
                        {"role": "assistant", "content": row["processed_text"]}]
            output.append({"messages": messages})
        return output

    data = {"train.jsonl": conversations(train), "validation.jsonl": conversations(validation)}
    manifest = {"schema_version": 1, "stage": "synthetic_fixture_only" if synthetic else "reviewed_sft",
                "input_corpus_hash": corpus_hash(records), "split": split_manifest,
                "confirmed_near_edges": edges, "near_report_hash": fingerprint(near_result),
                "lineage_membership_all_candidates": group_for,
                "near_review_sha256": digest(Path(near_review).read_bytes()),
                "rights_ledger_hash": fingerprint(rights),
                "reviewed_records_hash": fingerprint(records),
                "prompt_hashes": {p.name: digest(p.read_bytes()) for p in [system_path, template_path]},
                "implementation_sha256": {p.name: digest(p.read_bytes()) for p in sorted(Path(__file__).parent.glob("*.py"))},
                "length_policy": "approved-target-whitespace-units-plus-minus-20-v1",
                "row_source_ids": {"train.jsonl": [r["source_id"] for r in train],
                                   "validation.jsonl": [r["source_id"] for r in validation]},
                "limitations": ["Human declarations are local trust, not digital signatures",
                                "Near threshold not calibrated; no exhaustive semantic guarantee",
                                "Chat tokenization/loss masking not run on CPU data stage"]}
    Path(output_dir).mkdir(parents=True, exist_ok=False)
    for name, items in data.items():
        write_jsonl(Path(output_dir) / name, items)
    write_json(Path(output_dir) / "manifest.json", manifest)
    write_json(Path(output_dir) / "COMPLETE.json", {
        p.name: digest(p.read_bytes()) for p in sorted(Path(output_dir).iterdir())})
    return manifest
