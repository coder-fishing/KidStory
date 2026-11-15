"""Small-sample all-pairs Jaccard screening; human-confirmed edges only for split."""

import math
import re
from collections import defaultdict
from pathlib import Path

from .io import write_json
from .review import candidates, corpus_hash, fingerprint, read_csv, require_human, write_csv

PAIR_COLUMNS = ["pair_id", "source_id_a", "source_id_b", "hash_a", "hash_b", "score",
                "decision", "reviewer", "reviewed_at", "review_notes"]


def shingles(text: str, n: int) -> set[tuple]:
    units = re.findall(r"\w+", text.casefold(), flags=re.UNICODE)
    if not units:
        return set()
    return {tuple(units[i:i+n]) for i in range(max(1, len(units)-n+1))}


def screen(records: list[dict], *, ngram: int = 3, threshold: float = .65,
           max_records: int = 10000) -> dict:
    if not 1 <= ngram <= 10 or not math.isfinite(threshold) or not 0 < threshold <= 1:
        raise ValueError("Invalid ngram/threshold")
    rows = candidates(records)
    if len(rows) > max_records:
        raise ValueError("All-pairs screening cap exceeded; use smaller snapshot")
    grams = {r["source_id"]: shingles(r["processed_text"], ngram) for r in rows}
    pairs = []
    # Inverted postings generate only pairs sharing a shingle. At positive
    # thresholds a disjoint pair can never qualify. No approximate recall loss.
    postings = defaultdict(list)
    row_by_id = {row["source_id"]: row for row in rows}
    possible_pairs = []
    for row in rows:
        sid = row["source_id"]
        overlaps = defaultdict(int)
        for gram in grams[sid]:
            for other in postings[gram]:
                overlaps[other] += 1
            postings[gram].append(sid)
        for other, intersection in overlaps.items():
            union = len(grams[sid]) + len(grams[other]) - intersection
            if union and intersection / union >= threshold:
                possible_pairs.append((row_by_id[other], row))
    possible_pairs.sort(key=lambda pair: (pair[0]["source_id"], pair[1]["source_id"]))
    for a, b in possible_pairs:
        if a["exact_hash"] == b["exact_hash"]:
            continue  # M1 already handles exact pairs.
        x, y = grams[a["source_id"]], grams[b["source_id"]]
        score = len(x & y) / len(x | y) if x | y else 0.0
        if score >= threshold:
            pair = {"source_id_a": a["source_id"], "source_id_b": b["source_id"],
                    "hash_a": a["exact_hash"], "hash_b": b["exact_hash"]}
            pairs.append({"pair_id": fingerprint(pair), **pair, "score": score})
    # Candidate connected groups are diagnostic, never assumed confirmed.
    groups = []
    for pair in pairs:
        members = {pair["source_id_a"], pair["source_id_b"]}
        overlaps = [g for g in groups if g & members]
        groups = [g for g in groups if not g & members]
        groups.append(members.union(*overlaps))
    return {"schema_version": 1, "corpus_hash": corpus_hash(records),
            "method": "casefold-unicode-word-shingles-jaccard-inverted-v2",
            "ngram": ngram, "threshold": threshold, "max_records": max_records,
            "records_screened": len(rows), "pairs": pairs,
            "candidate_groups": sorted([sorted(g) for g in groups]),
            "status": "candidates_only_not_confirmed"}


def export_pairs(result: dict, output_dir: Path) -> None:
    Path(output_dir).mkdir(parents=True, exist_ok=False)
    write_json(Path(output_dir) / "near_candidates.json", result)
    sheet = [{**p, "score": repr(p["score"]), "decision": "pending", "reviewer": "",
              "reviewed_at": "", "review_notes": ""} for p in result["pairs"]]
    write_csv(Path(output_dir) / "near_review.csv", PAIR_COLUMNS, sheet)


def confirmed_edges(records: list[dict], result: dict, csv_path: Path) -> list[tuple[str, str]]:
    if result["corpus_hash"] != corpus_hash(records):
        raise ValueError("Stale near-duplicate review: text/revision/groups changed; rescreen")
    recomputed = screen(records, ngram=result["ngram"], threshold=result["threshold"],
                        max_records=result["max_records"])
    if recomputed != result:
        raise ValueError("Candidate report changed; rescreen")
    sheet = read_csv(csv_path, PAIR_COLUMNS)
    expected = {p["pair_id"]: p for p in result["pairs"]}
    ids = [r["pair_id"] for r in sheet]
    if len(set(ids)) != len(ids) or set(ids) != set(expected):
        raise ValueError("Near review pair IDs missing/extra/duplicate")
    edges = []
    for row in sheet:
        pair = expected[row["pair_id"]]
        if any(row[k] != str(pair[k]) for k in ["source_id_a", "source_id_b", "hash_a", "hash_b", "score"]):
            raise ValueError("Pair evidence modified")
        if row["decision"] not in {"confirmed", "distinct"}:
            raise ValueError("Unresolved near-duplicate candidates; human review required")
        require_human(row["reviewer"], row["reviewed_at"])
        if not row["review_notes"].strip():
            raise ValueError("Pair decision requires notes")
        if row["decision"] == "confirmed":
            edges.append((row["source_id_a"], row["source_id_b"]))
    return edges
