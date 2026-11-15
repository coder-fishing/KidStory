"""Strict, auditable JSONL input and deterministic artifact output."""

import hashlib
import json
from pathlib import Path


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def json_bytes(value) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2,
                       allow_nan=False) + "\n").encode("utf-8")


def write_json(path: Path, value) -> None:
    path.write_bytes(json_bytes(value))


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(r, ensure_ascii=False, sort_keys=True,
                                     allow_nan=False) + "\n" for r in rows),
                    encoding="utf-8", newline="\n")


def _unique_object(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise ValueError(f"duplicate JSON key: {key}")
        obj[key] = value
    return obj


def _reject_constant(value):
    raise ValueError(f"non-finite JSON number: {value}")


def read_jsonl(path: Path) -> list[dict]:
    """Retain malformed/blank lines for quarantine; invalid UTF-8 is fatal."""
    rows = []
    with path.open(encoding="utf-8", errors="strict") as stream:
        for line_number, line in enumerate(stream, 1):
            raw = line.rstrip("\r\n")
            try:
                value = json.loads(raw, object_pairs_hook=_unique_object,
                                   parse_constant=_reject_constant)
                error = None if isinstance(value, dict) else "not_json_object"
            except ValueError:
                value, error = None, "blank_line" if not raw.strip() else "invalid_json"
            rows.append({"line_number": line_number, "raw_line": raw,
                         "value": value, "error": error})
    return rows
