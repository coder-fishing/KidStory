"""Offline CPU pipeline: candidates only, never SFT or approved training data."""

import math
import platform
import sys
from collections import Counter
from pathlib import Path

from .io import digest, read_jsonl, write_json, write_jsonl
from .process import POLICY_VERSION, process_rows, summarize
from .split import split_records


def run_pipeline(input_path: Path, output_dir: Path, *, text_field: str = "text",
                 seed: int = 42, validation_ratio: float = .1,
                 min_units: int = 20) -> dict:
    input_path, output_dir = Path(input_path), Path(output_dir)
    if not text_field or min_units < 0:
        raise ValueError("text_field must not be empty; min_units must be nonnegative")
    if not math.isfinite(validation_ratio) or not 0 < validation_ratio < 1:
        raise ValueError("validation_ratio must be finite and between 0 and 1")
    if output_dir.exists():
        raise ValueError(f"Output directory already exists (no overwrite): {output_dir}")
    input_sha256 = digest(input_path.read_bytes())
    entries = read_jsonl(input_path)
    records = process_rows(entries, text_field=text_field, min_units=min_units)
    if digest(input_path.read_bytes()) != input_sha256:
        raise ValueError("Input changed during processing; refusing inconsistent provenance")
    try:
        train, validation, manifest = split_records(records, seed, validation_ratio)
    except ValueError as error:
        # Keep diagnostics even when there are too few independent groups.
        output_dir.mkdir(parents=True, exist_ok=False)
        write_jsonl(output_dir / "processed.jsonl", records)
        write_jsonl(output_dir / "quarantine.jsonl", [r for r in records if r["status"] == "quarantine"])
        write_json(output_dir / "report.json", {
            "status": "failed", "error": str(error), **summarize(records),
            "input_sha256": input_sha256,
            "config": {"text_field": text_field, "seed": seed,
                       "validation_ratio": validation_ratio, "min_units": min_units}})
        raise
    manifest["normalization_policy"] = POLICY_VERSION
    manifest["text_field"] = text_field
    manifest["min_units_review_threshold"] = min_units
    output_dir.mkdir(parents=True, exist_ok=False)
    write_jsonl(output_dir / "processed.jsonl", records)
    write_jsonl(output_dir / "quarantine.jsonl", [r for r in records if r["status"] == "quarantine"])
    write_jsonl(output_dir / "train.jsonl", train)
    write_jsonl(output_dir / "validation.jsonl", validation)
    write_json(output_dir / "split_manifest.json", manifest)
    report = {
        "status": "complete", "stage": "M1_unreviewed_candidates_not_sft",
        "input_path": str(input_path.resolve()),
        "input_sha256": input_sha256,
        "implementation_sha256": {p.name: digest(p.read_bytes())
                                  for p in sorted(Path(__file__).parent.glob("*.py"))},
        "python": platform.python_version(), "platform": sys.platform,
        "config": {"text_field": text_field, "seed": seed,
                   "validation_ratio": validation_ratio, "min_units": min_units},
        "normalization_policy": POLICY_VERSION, **summarize(records),
        "train_rows": len(train), "validation_rows": len(validation),
        "component_count": manifest["component_count"],
        "validation_row_fraction": manifest["validation_row_fraction"],
        "largest_component_input_rows": max(Counter(
            r["merged_group_id"] for r in records if r["merged_group_id"]).values()),
        "limitations": ["Near duplicates not detected", "Human text/metadata review pending",
                        "No safety, language fluency or narrative coherence certification",
                        "Group-ratio split, not exact row-ratio split; no SFT export"],
        "artifact_sha256": {p.name: digest(p.read_bytes()) for p in sorted(output_dir.iterdir())},
    }
    write_json(output_dir / "report.json", report)
    # A partial directory without this marker must never be consumed as complete.
    write_json(output_dir / "COMPLETE.json", {"report_sha256": digest((output_dir / "report.json").read_bytes())})
    return report
