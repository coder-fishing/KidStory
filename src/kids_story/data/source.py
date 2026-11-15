"""Small public HF survey snapshot; deliberately independent from offline processing.

The viewer serves current data: accept it only when its x-revision matches the
requested immutable Hub commit. This is prefix sampling, NOT random sampling.
"""

import argparse
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from .io import digest, write_json, write_jsonl
from .process import normalize_text

DATASET_ID = "nampdn-ai/tinystories-vietnamese"
MAX_RESPONSE_BYTES = 8 * 1024 * 1024


def _get(url: str) -> tuple[bytes, dict]:
    with urlopen(Request(url, headers={"User-Agent": "kids-story-m1-survey/0.1"}),
                 timeout=30) as response:
        data = response.read(MAX_RESPONSE_BYTES + 1)
        if len(data) > MAX_RESPONSE_BYTES:
            raise ValueError("Survey response exceeds 8 MiB; refusing full download")
        return data, {k.lower(): v for k, v in response.headers.items()}


def sample_source(output_dir: Path, *, revision: str | None = None,
                  limit: int = 10) -> dict:
    """Persist original responses plus prefix rows and revision/schema evidence."""
    output_dir = Path(output_dir)
    if output_dir.exists():
        raise ValueError("Output directory exists; refusing overwrite")
    if not 1 <= limit <= 100:
        raise ValueError("limit must be between 1 and 100")
    if revision is not None and not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("revision must be an immutable 40-character commit SHA")
    api_url = "https://huggingface.co/api/datasets/" + DATASET_ID
    if revision:
        api_url += "/revision/" + revision
    api_bytes, _ = _get(api_url)
    info = json.loads(api_bytes)
    resolved = info.get("sha")
    if not isinstance(resolved, str) or not re.fullmatch(r"[0-9a-f]{40}", resolved):
        raise ValueError("Hub did not supply an immutable revision")
    if revision and resolved != revision:
        raise ValueError("Hub revision mismatch")
    card_url = f"https://huggingface.co/datasets/{DATASET_ID}/raw/{resolved}/README.md"
    card_bytes, card_headers = _get(card_url)
    if card_headers.get("x-repo-commit") != resolved:
        raise ValueError("Card revision is missing or mismatched")
    rows_url = "https://datasets-server.huggingface.co/rows?" + urlencode({
        "dataset": DATASET_ID, "config": "default", "split": "train",
        "offset": 0, "length": limit})
    response_bytes, row_headers = _get(rows_url)
    if row_headers.get("x-revision") != resolved:
        raise ValueError("Viewer revision missing/mismatched; do not treat current viewer as pinned data")
    payload = json.loads(response_bytes)
    features = {f["name"]: f["type"] for f in payload.get("features", [])}
    for field in ("en", "vi"):
        spec = features.get(field)
        if not isinstance(spec, dict) or spec.get("dtype") not in {"string", "large_string"}:
            raise ValueError(f"Unverified string feature: {field}: {spec!r}")
    source_rows = payload.get("rows")
    if not isinstance(source_rows, list) or len(source_rows) != limit:
        raise ValueError("Viewer did not return requested prefix sample size")
    records, type_counts = [], {"en": Counter(), "vi": Counter()}
    for index, item in enumerate(source_rows):
        if item.get("row_idx") != index or item.get("truncated_cells"):
            raise ValueError("Unexpected row order or truncated viewer cells")
        row = item.get("row")
        if not isinstance(row, dict) or not all(k in row for k in ("en", "vi")):
            raise ValueError("Row schema missing en/vi")
        for field in ("en", "vi"):
            type_counts[field][type(row[field]).__name__] += 1
        # Group repeated originals as well as vi duplicates; no claim of near-dedup.
        en = row["en"]
        group_key = normalize_text(en)[0] if isinstance(en, str) and en.strip() else f"row:{index}"
        records.append({**row, "source_id": f"{DATASET_ID}@{resolved}:train:{index}",
                        "source_group_id": "en-sha256:" + digest(group_key.encode("utf-8")),
                        "source_revision": resolved, "source_split": "train",
                        "source_row_id": index, "source_dataset": DATASET_ID,
                        "sampling_method": "prefix_offset_0_not_random"})
    metadata = {
        "dataset_id": DATASET_ID, "resolved_revision": resolved,
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "config": "default", "split": "train", "features": features,
        "observed_types": {k: dict(v) for k, v in type_counts.items()},
        "sampling": {"method": "prefix", "offset": 0, "limit": limit,
                     "seed": None, "random": False, "row_indices": list(range(limit))},
        "urls": {"hub": api_url, "card": card_url, "rows": rows_url},
        "viewer_revision_header": row_headers["x-revision"],
        "license_label": info.get("cardData", {}).get("license"),
        "usage": "survey_only_not_approved_for_training",
        "unverified": ["Translation origin and method", "Full upstream rights chain",
                       "Age appropriateness and human quality review", "Near duplicates"],
    }
    output_dir.mkdir(parents=True, exist_ok=False)
    (output_dir / "hub_info.json").write_bytes(api_bytes)
    (output_dir / "dataset_card.md").write_bytes(card_bytes)
    (output_dir / "viewer_response.json").write_bytes(response_bytes)
    write_jsonl(output_dir / "sample.jsonl", records)
    metadata["artifact_sha256"] = {p.name: digest(p.read_bytes()) for p in sorted(output_dir.iterdir())}
    write_json(output_dir / "source_manifest.json", metadata)
    write_json(output_dir / "COMPLETE.json", {"source_manifest_sha256": digest((output_dir / "source_manifest.json").read_bytes())})
    return metadata


def main() -> int:
    parser = argparse.ArgumentParser(description="Survey a small revision-checked HF prefix")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--revision")
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()
    try:
        metadata = sample_source(args.output_dir, revision=args.revision, limit=args.limit)
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(2, f"Survey failed: {error}\n")
    print(json.dumps({"revision": metadata["resolved_revision"],
                      "sampling": metadata["sampling"],
                      "observed_types": metadata["observed_types"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
