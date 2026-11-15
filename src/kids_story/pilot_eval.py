"""Reload a saved M4 adapter in a fresh GPU process and generate dev outputs."""

import argparse
import json
from pathlib import Path

from .baseline import (
    DEFAULT_GENERATION_SETTINGS,
    MODEL_ID,
    MODEL_REVISION,
    TransformersBackend,
    build_messages,
    validate_dev_cases,
)
from .data.io import digest, write_json, write_jsonl


def evaluate(run_dir: Path, dev_path: Path, system_path: Path) -> dict:
    root = Path(run_dir)
    output = root / "dev_reload"
    if output.exists():
        raise ValueError("Dev reload output already exists")
    expected = json.loads((root / "adapter_hashes.json").read_text("utf-8"))
    for name, sha in expected.items():
        if digest((root / "adapter" / name).read_bytes()) != sha:
            raise ValueError("Adapter hash mismatch")
    cases = validate_dev_cases(dev_path)
    system = Path(system_path).read_text("utf-8")
    # A separate process releases all Trainer/model state before reloading.
    from peft import PeftModel

    backend = TransformersBackend()
    runtime = backend.inspect_runtime()
    if not runtime["gpu_available"]:
        raise RuntimeError("GPU required")
    backend.load(MODEL_ID, MODEL_REVISION)
    backend.model = PeftModel.from_pretrained(backend.model, str(root / "adapter"))
    backend.model.eval()
    config = json.loads((root / "run_config.json").read_text("utf-8"))
    backend.seed(config.get("seed", 42))
    output.mkdir(parents=True, exist_ok=False)
    rows = []
    for case in cases:
        messages = build_messages(case, system)
        generated = backend.generate(messages, DEFAULT_GENERATION_SETTINGS)
        rows.append({"case_id": case["id"], "messages": messages, **generated})
        write_jsonl(output / "generations.jsonl", rows)
    result = {
        "status": "reload_and_dev_complete",
        "case_count": len(rows),
        "runtime": runtime,
        "settings": DEFAULT_GENERATION_SETTINGS,
        "seed": config.get("seed", 42),
        "dev_sha256": digest(Path(dev_path).read_bytes()),
        "system_sha256": digest(Path(system_path).read_bytes()),
        "adapter_hashes_sha256": digest((root / "adapter_hashes.json").read_bytes()),
        "generations_sha256": digest((output / "generations.jsonl").read_bytes()),
        "quality_review": "pending",
    }
    write_json(output / "COMPLETE.json", result)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--dev", type=Path, default=Path("data/evaluation/dev_cases.jsonl"))
    parser.add_argument("--system", type=Path, default=Path("prompts/story_system_v1.txt"))
    args = parser.parse_args()
    print(evaluate(args.run_dir, args.dev, args.system))
