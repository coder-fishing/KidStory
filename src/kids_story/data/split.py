"""Merge source/exact groups transitively, then split deterministic components."""

import hashlib
import json
import math
import random


def split_records(records: list[dict], seed: int = 42,
                  validation_ratio: float = .1) -> tuple[list[dict], list[dict], dict]:
    if not math.isfinite(validation_ratio) or not 0 < validation_ratio < 1:
        raise ValueError("validation_ratio must be finite and between 0 and 1")
    candidates = sorted((r for r in records if r["status"] == "candidate"),
                        key=lambda r: r["source_id"])
    parent = {r["source_id"]: r["source_id"] for r in candidates}

    def find(key):
        while parent[key] != key:
            parent[key] = parent[parent[key]]
            key = parent[key]
        return key

    def union(a, b):
        a, b = find(a), find(b)
        parent[max(a, b)] = min(a, b)

    by_source, by_hash = {}, {}
    for row in candidates:
        sid = row["source_id"]
        for index, key in [(by_source, row["source_group_id"]), (by_hash, row["exact_hash"])]:
            if key in index:
                union(sid, index[key])
            else:
                index[key] = sid
    components = {}
    for row in candidates:
        components.setdefault(find(row["source_id"]), []).append(row)
    if len(components) < 2:
        raise ValueError("Need at least two independent source/exact components for nonempty train/validation")
    group_for = {}
    for members in components.values():
        member_ids = [r["source_id"] for r in members]
        gid = hashlib.sha256(json.dumps(member_ids, ensure_ascii=False,
                                       separators=(",", ":")).encode("utf-8")).hexdigest()
        for sid in member_ids:
            group_for[sid] = gid
    group_ids = sorted(set(group_for.values()))
    random.Random(seed).shuffle(group_ids)
    n_validation = max(1, min(len(group_ids) - 1,
                            math.floor(len(group_ids) * validation_ratio + .5)))
    validation_groups = set(group_ids[:n_validation])
    representative_by_hash = {}
    members_by_hash = {}
    for row in candidates:
        representative_by_hash.setdefault(row["exact_hash"], row["source_id"])
        members_by_hash.setdefault(row["exact_hash"], []).append(row["source_id"])
        row["merged_group_id"] = group_for[row["source_id"]]
        row["split"] = "validation" if row["merged_group_id"] in validation_groups else "train"
        rep = representative_by_hash[row["exact_hash"]]
        if rep != row["source_id"]:
            row["status"], row["duplicate_of"] = "duplicate", rep
    unique = [dict(row, duplicate_source_ids=members_by_hash[row["exact_hash"]])
              for row in candidates if row["status"] == "candidate"]
    train = [r for r in unique if r["split"] == "train"]
    validation = [r for r in unique if r["split"] == "validation"]
    if not train or not validation:
        raise ValueError("Refuse empty train/validation")
    # Logical manifest is input-order independent; physical input hash/line lives in report/audit.
    assignments = [{k: r[k] for k in ["audit_id", "source_id", "source_group_id",
                    "source_revision", "source_split", "source_row_id", "exact_hash",
                    "status", "duplicate_of", "merged_group_id", "split", "flags"]}
                   for r in sorted(records, key=lambda r: r["audit_id"])]
    manifest = {"schema_version": 1, "algorithm": "source-exact-union-sorted-shuffle-v1",
                "seed": seed, "validation_ratio_requested": validation_ratio,
                "component_count": len(group_ids), "validation_components": n_validation,
                "train_rows": len(train), "validation_rows": len(validation),
                "validation_row_fraction": len(validation) / len(unique),
                "assignments": assignments}
    return train, validation, manifest
