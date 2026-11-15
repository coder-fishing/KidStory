"""Revision-checked HF survey snapshots, separate from offline processing.

The Viewer does not accept a historical revision parameter, so every response
must carry the requested immutable commit in x-revision or the run aborts.
"""

import argparse
import json
import re
import random
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


def _sample_block_indices(total_rows: int, limit: int, seed: int,
                          block_size: int = 100) -> list[int]:
    if total_rows < 1 or block_size < 1 or limit < block_size or limit % block_size:
        raise ValueError("limit must be a positive multiple of block_size")
    available = total_rows // block_size
    requested = limit // block_size
    if requested > available:
        raise ValueError("Requested sample exceeds complete source blocks")
    return sorted(random.Random(seed).sample(range(available), requested))


def sample_source(output_dir: Path, *, revision: str | None = None,
                  limit: int = 10, method: str = "prefix", seed: int = 42) -> dict:
    """Persist a revision-checked prefix or seeded sample of random row blocks."""
    output_dir = Path(output_dir)
    if output_dir.exists():
        raise ValueError("Output directory exists; refusing overwrite")
    if method not in {"prefix", "random_blocks"}:
        raise ValueError("method must be prefix or random_blocks")
    if method == "prefix" and not 1 <= limit <= 100:
        raise ValueError("prefix limit must be between 1 and 100")
    if method == "random_blocks" and (not 100 <= limit <= 10000 or limit % 100):
        raise ValueError("random_blocks limit must be 100..10000 and divisible by 100")
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise ValueError("seed must be an integer")
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
    rows_base = "https://datasets-server.huggingface.co/rows"

    def fetch(offset: int, length: int) -> tuple[dict, dict, bytes, str]:
        url = rows_base + "?" + urlencode({"dataset": DATASET_ID, "config": "default",
            "split": "train", "offset": offset, "length": length})
        body, headers = _get(url)
        if headers.get("x-revision") != resolved:
            raise ValueError("Viewer revision missing/mismatched; do not treat current viewer as pinned data")
        return json.loads(body), headers, body, url

    first, row_headers, response_bytes, first_url = fetch(0, 1 if method == "random_blocks" else limit)
    response_evidence = [{"offset": 0, "length": 1 if method == "random_blocks" else limit,
                         "sha256": digest(response_bytes), "revision_header": row_headers.get("x-revision")}]
    features = {f["name"]: f["type"] for f in first.get("features", [])}
    for field in ("en", "vi"):
        spec = features.get(field)
        if not isinstance(spec, dict) or spec.get("dtype") not in {"string", "large_string"}:
            raise ValueError(f"Unverified string feature: {field}: {spec!r}")
    total_rows = first.get("num_rows_total")
    if method == "random_blocks" and (not isinstance(total_rows, int) or total_rows < 1):
        raise ValueError("Viewer did not provide a valid total row count")
    if method == "prefix" and not isinstance(total_rows, int):
        total_rows = limit
    if limit > total_rows:
        raise ValueError("Requested sample exceeds the source split")
    if method == "prefix":
        blocks = [0]
        row_payloads = [(0, first)]
        if len(first.get("rows", [])) != limit:
            raise ValueError("Viewer did not return requested prefix sample size")
    else:
        block_size = 100
        blocks = _sample_block_indices(total_rows, limit, seed, block_size)
        row_payloads = []
        for block in blocks:
            offset = block * block_size
            payload, headers, body, _ = fetch(offset, block_size)
            response_evidence.append({"offset": offset, "length": block_size,
                                      "sha256": digest(body),
                                      "revision_header": headers.get("x-revision")})
            row_payloads.append((offset, payload))

    records, type_counts = [], {"en": Counter(), "vi": Counter()}
    for offset, payload in row_payloads:
        source_rows = payload.get("rows")
        expected_length = limit if method == "prefix" else 100
        if not isinstance(source_rows, list) or len(source_rows) != expected_length:
            raise ValueError("Viewer did not return the requested row block")
        for index, item in enumerate(source_rows):
            row_index = offset + index
            if item.get("row_idx") != row_index or item.get("truncated_cells"):
                raise ValueError("Unexpected row index or truncated viewer cells")
            row = item.get("row")
            if not isinstance(row, dict) or not all(k in row for k in ("en", "vi")):
                raise ValueError("Row schema missing en/vi")
            for field in ("en", "vi"):
                type_counts[field][type(row[field]).__name__] += 1
            en = row["en"]
            group_key = normalize_text(en)[0] if isinstance(en, str) and en.strip() else f"row:{row_index}"
            sampling_label = "prefix_offset_0_not_random" if method == "prefix" else "seeded_random_contiguous_blocks_cluster_sample"
            records.append({**row, "source_id": f"{DATASET_ID}@{resolved}:train:{row_index}",
                            "source_group_id": "en-sha256:" + digest(group_key.encode("utf-8")),
                            "source_revision": resolved, "source_split": "train",
                            "source_row_id": row_index, "source_dataset": DATASET_ID,
                            "sampling_method": sampling_label})
    metadata = {
        "dataset_id": DATASET_ID, "resolved_revision": resolved,
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "config": "default", "split": "train", "features": features,
        "observed_types": {k: dict(v) for k, v in type_counts.items()},
        "sampling": ({"method": "prefix", "offset": 0, "limit": limit,
                      "seed": None, "random": False, "row_indices": list(range(limit))}
                     if method == "prefix" else
                     {"method": "seeded_random_contiguous_blocks_cluster_sample_v1",
                      "limit": limit, "seed": seed, "random_blocks": True,
                      "block_size": 100, "selected_block_indices": blocks,
                      "row_indices": [r["source_row_id"] for r in records],
                      "sampling_note": "Random cluster sample of 100-row blocks; not an IID row sample."}),
        "urls": {"hub": api_url, "card": card_url, "rows": first_url},
        "viewer_revision_header": row_headers["x-revision"],
        "viewer_response_evidence": response_evidence,
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
    parser = argparse.ArgumentParser(description="Sample revision-checked HF dataset rows")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--revision")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--method", choices=["prefix", "random_blocks"], default="prefix")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    try:
        metadata = sample_source(args.output_dir, revision=args.revision, limit=args.limit,
                                 method=args.method, seed=args.seed)
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(2, f"Survey failed: {error}\n")
    print(json.dumps({"revision": metadata["resolved_revision"],
                      "sampling": metadata["sampling"],
                      "observed_types": metadata["observed_types"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
