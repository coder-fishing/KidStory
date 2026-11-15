"""Export anonymous paired dev outputs; human scores stay blank."""

import argparse
import json
import random
from pathlib import Path

from .data.io import digest, write_json
from .data.review import write_csv


def prepare(base_path: Path, tuned_path: Path, output_dir: Path, seed=42):
    if Path(output_dir).exists():
        raise ValueError("Output already exists")

    def load(path):
        indexed = {}
        for line in Path(path).read_text("utf-8").splitlines():
            row = json.loads(line)
            key = row.get("id", row.get("case_id"))
            text = row.get("generated_text", row.get("text"))
            if not key or key in indexed or not isinstance(text, str) or not text.strip():
                raise ValueError("Missing/duplicate ID or failed generation")
            indexed[key] = text
        return indexed

    base, tuned = load(base_path), load(tuned_path)
    if not base or set(base) != set(tuned):
        raise ValueError("Development case IDs must match")
    rng = random.Random(seed)
    rows, mapping = [], {}
    for index, sid in enumerate(sorted(base)):
        order = ["base", "tuned"]
        rng.shuffle(order)
        pair_id = f"PAIR{index + 1:04}"
        mapping[pair_id] = {"case_id": sid, "A": order[0], "B": order[1]}
        values = {"base": base[sid], "tuned": tuned[sid]}
        for label, model in zip(("A", "B"), order):
            rows.append({
                "pair_id": pair_id,
                "case_id": sid,
                "variant": label,
                "text": values[model],
                **{key: "" for key in ("R1", "R2", "R3", "R4", "R5", "S1",
                                       "reviewer", "reviewed_at", "review_notes")},
                "review_status": "pending",
            })
    Path(output_dir).mkdir(parents=True, exist_ok=False)
    write_csv(Path(output_dir) / "dev_blind_review.csv", list(rows[0]), rows)
    write_json(Path(output_dir) / "PRIVATE_mapping_do_not_share.json", mapping)
    write_json(Path(output_dir) / "manifest.json", {
        "seed": seed,
        "base_sha256": digest(Path(base_path).read_bytes()),
        "tuned_sha256": digest(Path(tuned_path).read_bytes()),
        "note": "Dev only; verify matching inputs/settings before interpreting scores",
    })


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prepare paired dev human review")
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--tuned", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    prepare(args.base, args.tuned, args.output_dir, args.seed)
