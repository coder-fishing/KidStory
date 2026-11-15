"""CPU M2 CLI: seeded survey, review round trip, near screening and gated SFT."""

import argparse
import json
import platform
import random
import statistics
from pathlib import Path

from .io import digest, write_json, write_jsonl
from .eda import run_eda
from .near import export_pairs, screen
from .process import summarize
from .review import candidates, export_review, import_review, load_records
from .sft import export_sft
from .edits import apply_edits, export_edits


def prepare(input_path: Path, output_dir: Path, *, sample_size: int = 30,
            seed: int = 42, threshold: float = .65, ngram: int = 3) -> dict:
    records = load_records(input_path)
    if not 1 <= sample_size <= min(10000, len(records)):
        raise ValueError("sample_size must be 1..10000 and no larger than the local population")
    ordered = sorted(records, key=lambda r: r.get("audit_id", r.get("source_id")))
    # Include quarantined records in sampling; do not hide bad data by sampling only clean rows.
    selected = random.Random(seed).sample(ordered, sample_size)
    selected.sort(key=lambda r: r.get("audit_id", r.get("source_id")))
    near = screen(selected, threshold=threshold, ngram=ngram)
    lengths = [len(r["processed_text"].split()) for r in selected if r.get("processed_text")]
    manifest = {"schema_version": 1, "python": platform.python_version(),
                "implementation_sha256": {p.name: digest(p.read_bytes()) for p in sorted(Path(__file__).parent.glob("*.py"))},
                "input_sha256": digest(Path(input_path).read_bytes()),
                "method": "random-sample-without-replacement-from-sorted-local-snapshot-v1",
                "seed": seed, "sample_size": sample_size, "population_rows": len(records),
                "selected_audit_ids": [r.get("audit_id", r.get("source_id")) for r in selected],
                "source_revisions": sorted({r["source_revision"] for r in selected if r.get("source_revision")}),
                "population_summary": summarize(records), "sample_summary": summarize(selected),
                "whitespace_units_median": statistics.median(lengths) if lengths else None,
                "exact_duplicate_excess_in_sample": len(candidates(selected)) - len({r["exact_hash"] for r in candidates(selected)}),
                "near_candidate_pairs": len(near["pairs"]),
                "limitations": ["Random only within supplied snapshot, not necessarily whole source",
                                "No human quality/safety approval", "No model-token measurement"]}
    Path(output_dir).mkdir(parents=True, exist_ok=False)
    write_jsonl(Path(output_dir) / "records.jsonl", selected)
    export_review(selected, Path(output_dir) / "review")
    export_pairs(near, Path(output_dir) / "near")
    write_json(Path(output_dir) / "survey_manifest.json", manifest)
    write_json(Path(output_dir) / "COMPLETE.json", {
        str(p.relative_to(output_dir)).replace("\\", "/"): digest(p.read_bytes())
        for p in sorted(Path(output_dir).rglob("*")) if p.is_file()})
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="CPU M2, human review required")
    commands = parser.add_subparsers(dest="command", required=True)
    edit_export = commands.add_parser("export-edits")
    edit_export.add_argument("--input", type=Path, required=True)
    edit_export.add_argument("--csv", type=Path, required=True)
    edit_import = commands.add_parser("apply-edits")
    edit_import.add_argument("--input", type=Path, required=True)
    edit_import.add_argument("--csv", type=Path, required=True)
    edit_import.add_argument("--output-dir", type=Path, required=True)
    prep = commands.add_parser("prepare")
    prep.add_argument("--input", type=Path, required=True)
    prep.add_argument("--output-dir", type=Path, required=True)
    prep.add_argument("--sample-size", type=int, default=30)
    prep.add_argument("--seed", type=int, default=42)
    prep.add_argument("--threshold", type=float, default=.65)
    prep.add_argument("--ngram", type=int, default=3)
    eda = commands.add_parser("eda", help="Describe a bilingual JSONL snapshot and export review candidates")
    eda.add_argument("--input", type=Path, required=True)
    eda.add_argument("--output-dir", type=Path, required=True)
    eda.add_argument("--source-manifest", type=Path)
    review = commands.add_parser("import-review")
    review.add_argument("--input", type=Path, required=True)
    review.add_argument("--csv", type=Path, required=True)
    review.add_argument("--baseline", type=Path, required=True)
    review.add_argument("--output-dir", type=Path, required=True)
    near = commands.add_parser("near")
    near.add_argument("--input", type=Path, required=True)
    near.add_argument("--output-dir", type=Path, required=True)
    near.add_argument("--threshold", type=float, default=.65)
    near.add_argument("--ngram", type=int, default=3)
    sheet = commands.add_parser("export-review")
    sheet.add_argument("--input", type=Path, required=True)
    sheet.add_argument("--output-dir", type=Path, required=True)
    sft = commands.add_parser("sft")
    sft.add_argument("--input", type=Path, required=True)
    sft.add_argument("--output-dir", type=Path, required=True)
    sft.add_argument("--near-report", type=Path, required=True)
    sft.add_argument("--near-review", type=Path, required=True)
    sft.add_argument("--rights", type=Path, required=True)
    sft.add_argument("--prompt-dir", type=Path, default=Path("prompts"))
    sft.add_argument("--synthetic", action="store_true")
    sft.add_argument("--seed", type=int, default=42)
    sft.add_argument("--validation-ratio", type=float, default=.1)
    args = parser.parse_args()
    try:
        if args.command == "prepare":
            result = prepare(args.input, args.output_dir, sample_size=args.sample_size,
                             seed=args.seed, threshold=args.threshold, ngram=args.ngram)
            result = {k: result[k] for k in ["sample_size", "population_rows", "near_candidate_pairs"]}
        elif args.command == "eda":
            report = run_eda(args.input, args.output_dir, args.source_manifest)
            result = {"input_rows": report["input_rows"],
                      "name_candidate_rows": report["name_candidate_rows"],
                      "translation_calque_candidate_rows": report["translation_calque_candidate_rows"],
                      "output_dir": str(args.output_dir)}
        else:
            rows = load_records(args.input)
            if args.command == "export-edits":
                export_edits(rows, args.csv)
                result = {"csv": str(args.csv)}
            elif args.command == "apply-edits":
                result = apply_edits(rows, args.csv, args.output_dir)
                result = {"edited_stories": result["edited_stories"]}
            elif args.command == "export-review":
                export_review(rows, args.output_dir)
                result = {"review_rows": len(candidates(rows))}
            elif args.command == "import-review":
                if args.output_dir.exists():
                    raise ValueError("Output exists; refusing overwrite")
                updated = import_review(rows, args.csv, args.baseline)
                args.output_dir.mkdir(parents=True, exist_ok=False)
                write_jsonl(args.output_dir / "reviewed_records.jsonl", updated)
                result = {"rows": len(updated), "approved": sum(r.get("review_status") == "approved" for r in updated),
                          "input_sha256": digest(args.input.read_bytes()),
                          "csv_sha256": digest(args.csv.read_bytes()),
                          "baseline_sha256": digest(args.baseline.read_bytes())}
                write_json(args.output_dir / "import_manifest.json", result)
                write_json(args.output_dir / "COMPLETE.json", {p.name: digest(p.read_bytes()) for p in sorted(args.output_dir.iterdir())})
            elif args.command == "near":
                report = screen(rows, threshold=args.threshold, ngram=args.ngram)
                export_pairs(report, args.output_dir)
                result = {"pairs": len(report["pairs"]), "candidate_groups": len(report["candidate_groups"])}
            else:
                result = export_sft(rows, args.output_dir,
                    near_result=json.loads(args.near_report.read_text(encoding="utf-8")),
                    near_review=args.near_review,
                    rights=json.loads(args.rights.read_text(encoding="utf-8")),
                    prompt_dir=args.prompt_dir, synthetic=args.synthetic, seed=args.seed,
                    validation_ratio=args.validation_ratio)
                result = {"stage": result["stage"], "train_rows": result["split"]["train_rows"],
                          "validation_rows": result["split"]["validation_rows"]}
    except (ValueError, OSError, KeyError, TypeError) as error:
        parser.exit(2, f"M2 failed: {error}\n")
    print(json.dumps(result, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
