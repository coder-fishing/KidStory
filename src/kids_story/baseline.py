"""Input validation, Transformers inference and artifacts for the M3 baseline."""

import hashlib
import importlib.metadata
import json
import math
import platform
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

from kids_story.data.io import read_jsonl, write_json


MODEL_ID = "Qwen/Qwen2.5-3B-Instruct"
MODEL_REVISION = "aa8e72537993ba99e69dfaafa59ed015b17504d1"
DEFAULT_GENERATION_SETTINGS = {
    "do_sample": True,
    "temperature": 0.7,
    "top_p": 0.9,
    "repetition_penalty": 1.0,
    "max_new_tokens": 512,
}


class BaselineRunError(RuntimeError):
    """Raised when a baseline run cannot start or complete its model setup."""


class TransformersBackend:
    """Lazy Transformers implementation; importing the module needs no GPU stack."""

    def __init__(self):
        self.torch = None
        self.tokenizer = None
        self.model = None

    def inspect_runtime(self) -> dict:
        try:
            import torch
            import transformers
        except ImportError as exc:
            raise BaselineRunError(f"Required inference dependency is unavailable: {exc.name}") from exc

        gpu_available = bool(torch.cuda.is_available())
        gpu_name = None
        gpu_memory_bytes = None
        if gpu_available:
            gpu_name = torch.cuda.get_device_name(0)
            gpu_memory_bytes = int(torch.cuda.get_device_properties(0).total_memory)

        try:
            accelerate_version = importlib.metadata.version("accelerate")
        except importlib.metadata.PackageNotFoundError:
            accelerate_version = None

        self.torch = torch
        return {
            "python_version": platform.python_version(),
            "torch_version": torch.__version__,
            "transformers_version": transformers.__version__,
            "accelerate_version": accelerate_version,
            "cuda_version": torch.version.cuda,
            "gpu_available": gpu_available,
            "gpu_name": gpu_name,
            "gpu_memory_bytes": gpu_memory_bytes,
        }

    def load(self, model_id: str, revision: str) -> None:
        from transformers import AutoModelForCausalLM, AutoTokenizer

        if self.torch is None:
            raise BaselineRunError("Runtime must be inspected before loading the model")
        if not self.torch.cuda.is_available():
            raise BaselineRunError("A Colab GPU is required for the M3 baseline")

        supports_bfloat16 = getattr(self.torch.cuda, "is_bf16_supported", lambda: False)()
        dtype = self.torch.bfloat16 if supports_bfloat16 else self.torch.float16
        self.tokenizer = AutoTokenizer.from_pretrained(model_id, revision=revision)
        self.model = AutoModelForCausalLM.from_pretrained(
            model_id,
            revision=revision,
            torch_dtype=dtype,
            device_map="auto",
            low_cpu_mem_usage=True,
            use_safetensors=True,
        )
        self.model.eval()

    def seed(self, seed: int) -> None:
        if self.torch is None:
            raise BaselineRunError("Runtime must be inspected before seeding")
        self.torch.manual_seed(seed)
        if self.torch.cuda.is_available():
            self.torch.cuda.manual_seed_all(seed)

    def generate(self, messages: list[dict[str, str]], settings: dict) -> dict:
        if self.model is None or self.tokenizer is None:
            raise BaselineRunError("Model must be loaded before generation")

        inputs = self.tokenizer.apply_chat_template(
            messages,
            add_generation_prompt=True,
            tokenize=True,
            return_dict=True,
            return_tensors="pt",
        ).to(self.model.device)
        input_length = inputs["input_ids"].shape[-1]
        generation_settings = dict(settings)
        generation_settings["pad_token_id"] = self.tokenizer.pad_token_id

        with self.torch.inference_mode():
            sequences = self.model.generate(**inputs, **generation_settings)[0]
        new_tokens = sequences[input_length:]
        output_tokens = int(new_tokens.shape[-1])
        finish_reason = "length" if output_tokens >= settings["max_new_tokens"] else "stop"
        eos_token_id = self.tokenizer.eos_token_id
        if output_tokens and eos_token_id is not None:
            eos_ids = eos_token_id if isinstance(eos_token_id, list) else [eos_token_id]
            if int(new_tokens[-1]) in eos_ids:
                finish_reason = "stop"

        return {
            "text": self.tokenizer.decode(new_tokens, skip_special_tokens=True),
            "output_tokens": output_tokens,
            "finish_reason": finish_reason,
        }


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


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _messages_sha256(messages: list[dict[str, str]]) -> str:
    serialized = json.dumps(messages, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return _sha256(serialized.encode("utf-8"))


def _git_metadata() -> dict:
    repository_root = Path(__file__).resolve().parents[2]
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=repository_root, check=True,
            capture_output=True, text=True,
        ).stdout.strip()
        status = subprocess.run(
            ["git", "status", "--porcelain"], cwd=repository_root, check=True,
            capture_output=True, text=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        return {"source_commit": None, "working_tree_dirty": None}
    return {"source_commit": commit or None, "working_tree_dirty": bool(status.strip())}


def _effective_generation_settings(settings: dict | None) -> dict:
    effective = dict(DEFAULT_GENERATION_SETTINGS)
    if settings is not None:
        if not isinstance(settings, dict):
            raise ValueError("Generation settings must be an object")
        unknown = set(settings) - set(DEFAULT_GENERATION_SETTINGS)
        if unknown:
            raise ValueError(f"Unsupported generation settings: {', '.join(sorted(unknown))}")
        effective.update(settings)

    if not isinstance(effective["do_sample"], bool):
        raise ValueError("do_sample must be a boolean")
    for name in ("temperature", "top_p", "repetition_penalty"):
        value = effective[name]
        try:
            finite = math.isfinite(value)
        except (OverflowError, TypeError):
            finite = False
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not finite or value <= 0:
            raise ValueError(f"{name} must be a positive number")
    if effective["top_p"] > 1:
        raise ValueError("top_p must not exceed 1")
    token_limit = effective["max_new_tokens"]
    if isinstance(token_limit, bool) or not isinstance(token_limit, int) or token_limit <= 0:
        raise ValueError("max_new_tokens must be a positive integer")
    return effective


def _write_jsonl_record(stream, record: dict) -> None:
    stream.write(json.dumps(record, ensure_ascii=False, sort_keys=True, allow_nan=False) + "\n")
    stream.flush()


def _version(package: str) -> str | None:
    try:
        return importlib.metadata.version(package)
    except importlib.metadata.PackageNotFoundError:
        return None


def run_baseline(
    input_path: str | Path,
    system_prompt_path: str | Path,
    output_dir: str | Path,
    *,
    backend=None,
    seed: int = 42,
    generation_settings: dict | None = None,
    source_commit: str | None = None,
) -> dict:
    """Generate one raw record per dev case and verify the completed artifacts."""
    input_path = Path(input_path)
    system_prompt_path = Path(system_prompt_path)
    output_dir = Path(output_dir)
    if output_dir.exists():
        raise FileExistsError(f"Refusing to overwrite existing output directory: {output_dir}")

    cases = validate_dev_cases(input_path)
    try:
        system_bytes = system_prompt_path.read_bytes()
        system_text = system_bytes.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise ValueError("System prompt must be valid UTF-8") from exc
    messages_by_id = {case["id"]: build_messages(case, system_text) for case in cases}

    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("Seed must be an integer")
    effective_settings = _effective_generation_settings(generation_settings)
    input_bytes = input_path.read_bytes()
    git_info = _git_metadata()
    if source_commit is not None:
        git_info["source_commit"] = source_commit

    output_dir.parent.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(exist_ok=False)
    config = {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model_id": MODEL_ID,
        "model_revision": MODEL_REVISION,
        "tokenizer_revision": MODEL_REVISION,
        "input_path": str(input_path),
        "input_sha256": _sha256(input_bytes),
        "system_prompt_path": str(system_prompt_path),
        "system_prompt_sha256": _sha256(system_bytes),
        "seed": seed,
        "generation_settings": effective_settings,
        **git_info,
        "runtime": {
            "python_version": platform.python_version(),
            "torch_version": _version("torch"),
            "transformers_version": _version("transformers"),
            "accelerate_version": _version("accelerate"),
            "gpu_available": False,
            "gpu_name": None,
            "gpu_memory_bytes": None,
        },
    }
    write_json(output_dir / "run_config.json", config)
    backend = backend if backend is not None else TransformersBackend()

    try:
        runtime = backend.inspect_runtime()
        if not isinstance(runtime, dict):
            raise BaselineRunError("Backend returned invalid runtime metadata")
        config["runtime"].update(runtime)
        write_json(output_dir / "run_config.json", config)
        if runtime.get("gpu_available") is not True:
            raise BaselineRunError("A Colab GPU is required for the M3 baseline")
        backend.load(MODEL_ID, MODEL_REVISION)
        backend.seed(seed)
    except Exception as exc:
        write_json(output_dir / "run_error.json", {
            "error_type": type(exc).__name__,
            "error": str(exc),
            "occurred_at": datetime.now(timezone.utc).isoformat(),
        })
        if isinstance(exc, BaselineRunError):
            raise
        raise BaselineRunError(f"Could not initialize the baseline model: {exc}") from exc

    generations_path = output_dir / "generations.jsonl"
    success_count = 0
    error_count = 0
    with generations_path.open("x", encoding="utf-8", newline="\n") as stream:
        for case in cases:
            messages = messages_by_id[case["id"]]
            started = time.perf_counter()
            try:
                generated = backend.generate(messages, effective_settings)
                if not isinstance(generated, dict):
                    raise ValueError("Backend returned an invalid generation record")
                text = generated.get("text")
                output_tokens = generated.get("output_tokens")
                finish_reason = generated.get("finish_reason")
                if not isinstance(text, str):
                    raise ValueError("Backend returned non-text output")
                if isinstance(output_tokens, bool) or not isinstance(output_tokens, int) or output_tokens < 0:
                    raise ValueError("Backend returned an invalid output token count")
                if not isinstance(finish_reason, str) or not finish_reason:
                    raise ValueError("Backend returned no finish reason")
                record = {
                    "id": case["id"],
                    "status": "success",
                    "messages_sha256": _messages_sha256(messages),
                    "generated_text": text,
                    "output_tokens": output_tokens,
                    "finish_reason": finish_reason,
                    "elapsed_seconds": round(time.perf_counter() - started, 6),
                    "error": None,
                }
                success_count += 1
            except Exception as exc:
                record = {
                    "id": case["id"],
                    "status": "error",
                    "messages_sha256": _messages_sha256(messages),
                    "generated_text": None,
                    "output_tokens": None,
                    "finish_reason": None,
                    "elapsed_seconds": round(time.perf_counter() - started, 6),
                    "error": f"{type(exc).__name__}: {exc}",
                }
                error_count += 1
            _write_jsonl_record(stream, record)

    status = "completed_with_errors" if error_count else "complete"
    artifact_names = ("run_config.json", "generations.jsonl")
    completion = {
        "schema_version": 1,
        "status": status,
        "total_cases": len(cases),
        "success_count": success_count,
        "error_count": error_count,
        "files": {
            name: _sha256((output_dir / name).read_bytes())
            for name in artifact_names
        },
    }
    write_json(output_dir / "COMPLETE.json", completion)
    return completion
