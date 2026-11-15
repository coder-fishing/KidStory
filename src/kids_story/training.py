"""M4 pilot: CPU preflight, explicit response labels and optional GPU training."""

import argparse
import importlib.metadata
import json
import math
from pathlib import Path

from .baseline import MODEL_ID, MODEL_REVISION
from .data.io import digest, write_json


def preflight(sft_dir: Path, min_samples: int = 300) -> dict:
    """Validate an existing reviewed SFT bundle before importing GPU libraries."""
    root = Path(sft_dir)
    complete = json.loads((root / "COMPLETE.json").read_text("utf-8"))
    for name in ("manifest.json", "train.jsonl", "validation.jsonl"):
        if complete.get(name) != digest((root / name).read_bytes()):
            raise ValueError(f"Missing or changed artifact: {name}")
    manifest = json.loads((root / "manifest.json").read_text("utf-8"))
    if manifest.get("stage") != "reviewed_sft":
        raise ValueError("Real pilot requires reviewed_sft provenance")
    splits = {}
    text_sets = {}
    for split in ("train", "validation"):
        rows = [json.loads(line) for line in (root / f"{split}.jsonl").read_text("utf-8").splitlines()]
        if not rows:
            raise ValueError(f"Empty {split}")
        for row in rows:
            messages = row.get("messages", [])
            if [message.get("role") for message in messages] != ["system", "user", "assistant"]:
                raise ValueError("Expected system/user/assistant conversation")
            if any(not isinstance(m.get("content"), str) or not m["content"].strip() for m in messages):
                raise ValueError("Blank or invalid conversation content")
        splits[split] = rows
        text_sets[split] = {row["messages"][-1]["content"] for row in rows}
        ids = manifest["row_source_ids"][f"{split}.jsonl"]
        if len(ids) != len(rows) or len(set(ids)) != len(ids):
            raise ValueError("SFT source ID count/uniqueness mismatch")
    if sum(map(len, splits.values())) < min_samples:
        raise ValueError(f"Pilot requires at least {min_samples} reviewed samples")
    if text_sets["train"] & text_sets["validation"]:
        raise ValueError("Exact text leakage between splits")
    systems = {
        row["messages"][0]["content"]
        for rows in splits.values() for row in rows
    }
    if len(systems) != 1:
        raise ValueError("SFT must use one consistent system prompt")
    ids = manifest["row_source_ids"]
    train_ids = set(ids["train.jsonl"])
    valid_ids = set(ids["validation.jsonl"])
    groups = manifest["lineage_membership_all_candidates"]
    if train_ids & valid_ids or {groups[i] for i in train_ids} & {groups[i] for i in valid_ids}:
        raise ValueError("Source/lineage leakage")
    return {"splits": splits, "manifest_sha256": complete["manifest.json"]}


def encode_response(tokenizer, messages: list[dict], max_length: int) -> dict:
    """Mask prompt and assistant header; reject silent target truncation."""
    prefix = tokenizer.apply_chat_template(
        messages[:-1], tokenize=True, add_generation_prompt=True,
    )
    full = tokenizer.apply_chat_template(
        messages, tokenize=True, add_generation_prompt=False,
    )
    if full[:len(prefix)] != prefix:
        raise ValueError("Chat template prefix mismatch; masking is unsafe")
    if len(full) > max_length or len(full) <= len(prefix):
        raise ValueError("Conversation too long or has no response tokens")
    return {
        "input_ids": full,
        "attention_mask": [1] * len(full),
        "labels": [-100] * len(prefix) + full[len(prefix):],
    }


class ResponseCollator:
    """Right-pad input IDs and mask every padding position in labels."""

    def __init__(self, pad_token_id):
        self.pad_token_id = pad_token_id

    def __call__(self, rows):
        import torch

        width = max(len(row["input_ids"]) for row in rows)
        batch = {key: [] for key in ("input_ids", "attention_mask", "labels")}
        for row in rows:
            missing = width - len(row["input_ids"])
            batch["input_ids"].append(row["input_ids"] + [self.pad_token_id] * missing)
            batch["attention_mask"].append(row["attention_mask"] + [0] * missing)
            batch["labels"].append(row["labels"] + [-100] * missing)
        return {key: torch.tensor(value) for key, value in batch.items()}


def train(config: dict) -> dict:
    """Run only on Colab GPU; selecting best checkpoint uses validation loss."""
    bundle = preflight(Path(config["sft_dir"]))
    output = Path(config["output_dir"])
    if output.exists():
        raise ValueError("Choose a new output directory for each training attempt")
    # Import Unsloth before Transformers, as required by Unsloth patches.
    from unsloth import FastLanguageModel
    import torch
    from datasets import Dataset
    from transformers import Trainer, TrainerCallback, TrainingArguments, set_seed

    class FiniteLossCallback(TrainerCallback):
        def on_log(self, args, state, control, logs=None, **kwargs):
            for key in ("loss", "eval_loss"):
                if key in (logs or {}) and not math.isfinite(logs[key]):
                    raise ValueError(f"Non-finite {key}; stopping training")

    if not torch.cuda.is_available():
        raise RuntimeError("M4 requires a Colab GPU runtime")
    seed = int(config.get("seed", 42))
    length = int(config.get("max_length", 2048))
    steps = int(config.get("max_steps", 100))
    if steps < 10 or steps % 10 or length < 64:
        raise ValueError("Invalid max_steps/max_length")
    resume = config.get("resume_from_checkpoint")
    if resume:
        checkpoint = Path(resume).resolve()
        previous = json.loads((checkpoint.parent.parent / "run_config.json").read_text("utf-8"))
        if previous.get("sft_manifest_sha256") != bundle["manifest_sha256"]:
            raise ValueError("Resume requires the same SFT snapshot")
        for key, default in (("seed", 42), ("max_length", 2048), ("max_steps", 100)):
            if previous.get(key, default) != config.get(key, default):
                raise ValueError(f"Resume configuration changed: {key}")
        if not (checkpoint / "trainer_state.json").is_file():
            raise ValueError("Not a resumable Trainer checkpoint")
    set_seed(seed)
    output.mkdir(parents=True, exist_ok=False)
    effective = {
        **config,
        "model_id": MODEL_ID,
        "model_revision": MODEL_REVISION,
        "sft_manifest_sha256": bundle["manifest_sha256"],
        "gpu": torch.cuda.get_device_name(0),
        "packages": {
            name: importlib.metadata.version(name)
            for name in ("unsloth", "transformers", "peft", "torch", "datasets")
        },
    }
    write_json(output / "run_config.json", effective)
    try:
        model, tokenizer = FastLanguageModel.from_pretrained(
            model_name=MODEL_ID,
            revision=MODEL_REVISION,
            max_seq_length=length,
            load_in_4bit=True,
        )
        model = FastLanguageModel.get_peft_model(
            model,
            r=16,
            target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                            "gate_proj", "up_proj", "down_proj"],
            lora_alpha=16,
            lora_dropout=0,
            bias="none",
            use_gradient_checkpointing="unsloth",
            random_state=seed,
        )
        if tokenizer.pad_token_id is None:
            tokenizer.pad_token = tokenizer.eos_token
        if tokenizer.pad_token_id is None:
            raise ValueError("Tokenizer has no usable padding token")
        encoded = {}
        audit = {}
        for split, rows in bundle["splits"].items():
            values = [encode_response(tokenizer, row["messages"], length) for row in rows]
            encoded[split] = Dataset.from_list(values)
            audit[split] = {
                "rows": len(values),
                "max_tokens": max(len(row["input_ids"]) for row in values),
                "supervised_tokens": sum(sum(t != -100 for t in row["labels"]) for row in values),
                "first_example": values[0],
            }
        write_json(output / "token_label_audit.json", audit)
        bf16 = torch.cuda.is_bf16_supported()
        arguments = TrainingArguments(
            output_dir=str(output / "checkpoints"),
            max_steps=steps,
            per_device_train_batch_size=1,
            per_device_eval_batch_size=1,
            gradient_accumulation_steps=8,
            learning_rate=2e-4,
            warmup_ratio=0.1,
            fp16=not bf16,
            bf16=bf16,
            logging_steps=1,
            logging_nan_inf_filter=False,
            eval_strategy="steps",
            eval_steps=10,
            save_strategy="steps",
            save_steps=10,
            save_total_limit=2,
            load_best_model_at_end=True,
            metric_for_best_model="eval_loss",
            greater_is_better=False,
            report_to="none",
            seed=seed,
            data_seed=seed,
        )
        trainer = Trainer(
            model=model,
            args=arguments,
            train_dataset=encoded["train"],
            eval_dataset=encoded["validation"],
            data_collator=ResponseCollator(tokenizer.pad_token_id),
            callbacks=[FiniteLossCallback()],
        )
        initial = trainer.evaluate()
        if not math.isfinite(initial["eval_loss"]):
            raise ValueError("Non-finite initial validation loss")
        trainer.train(resume_from_checkpoint=resume)
        metrics = trainer.evaluate()
        if not math.isfinite(metrics["eval_loss"]):
            raise ValueError("Non-finite validation loss")
        adapter = output / "adapter"
        model.save_pretrained(str(adapter))
        tokenizer.save_pretrained(str(adapter))
        write_json(output / "training_log.json", trainer.state.log_history)
        result = {
            "status": "trained_reload_pending",
            "initial_validation": initial,
            "validation": metrics,
            "best_checkpoint": trainer.state.best_model_checkpoint,
            "adapter_dir": str(adapter),
        }
        write_json(output / "TRAINED.json", result)
        write_json(output / "adapter_hashes.json", {
            str(path.relative_to(adapter)): digest(path.read_bytes())
            for path in sorted(adapter.rglob("*")) if path.is_file()
        })
        return result
    except Exception as error:
        write_json(output / "FAILED.json", {"error": str(error), "type": type(error).__name__})
        raise


def main():
    parser = argparse.ArgumentParser(description="M4 preflight and Colab QLoRA pilot")
    parser.add_argument("config", type=Path)
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args()
    config = json.loads(args.config.read_text("utf-8"))
    if args.preflight_only:
        bundle = preflight(Path(config["sft_dir"]))
        print({key: len(value) for key, value in bundle["splits"].items()})
    else:
        print(train(config))


if __name__ == "__main__":
    main()
