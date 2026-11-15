"""Input validation and message preparation for the M3 baseline."""

from pathlib import Path

from kids_story.data.io import read_jsonl


def validate_dev_cases(input_path: str | Path) -> list[dict]:
    """Read ordered dev cases and reject invalid or duplicate identifiers."""
    try:
        rows = read_jsonl(Path(input_path))
    except UnicodeDecodeError as exc:
        raise ValueError("Development input must be valid UTF-8") from exc

    if not rows:
        raise ValueError("Development input is empty")

    cases = []
    seen_ids = set()
    for row in rows:
        if row["error"] is not None:
            raise ValueError(
                f"Invalid development JSONL at line {row['line_number']}: {row['error']}"
            )

        case = row["value"]
        case_id = case.get("id")
        if not isinstance(case_id, str) or not case_id.strip():
            raise ValueError(f"Development case at line {row['line_number']} has an invalid id")
        if case_id in seen_ids:
            raise ValueError(f"Duplicate development id: {case_id}")

        prompt = case.get("prompt")
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError(f"Development case {case_id} has a missing or invalid prompt")

        seen_ids.add(case_id)
        cases.append(case)

    return cases


def build_messages(case: dict, system_text: str) -> list[dict[str, str]]:
    """Build the model request from fixed system text and one dev prompt only."""
    if not isinstance(system_text, str) or not system_text.strip():
        raise ValueError("System prompt must be a non-empty string")

    if not isinstance(case, dict):
        raise ValueError("Development case must be an object")
    prompt = case.get("prompt")
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("Development prompt must be a non-empty string")

    return [
        {"role": "system", "content": system_text},
        {"role": "user", "content": prompt},
    ]
