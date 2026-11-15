"""Usage: python -m kids_story.data --input ... --output-dir ..."""

import argparse
import json
from pathlib import Path

from .pipeline import run_pipeline


def main() -> int:
    parser = argparse.ArgumentParser(description="CPU JSONL processing (M1, not SFT)")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--text-field", default="text")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--validation-ratio", type=float, default=.1)
    parser.add_argument("--min-units", type=int, default=20,
                        help="Review flag only; never a hard length filter")
    args = parser.parse_args()
    try:
        report = run_pipeline(args.input, args.output_dir, text_field=args.text_field,
                              seed=args.seed, validation_ratio=args.validation_ratio,
                              min_units=args.min_units)
    except (ValueError, OSError) as error:
        parser.exit(2, f"Processing failed: {error}\n")
    print(json.dumps({k: report[k] for k in ["status", "input_rows", "status_counts",
                     "train_rows", "validation_rows", "component_count"]}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
