"""Tests for the M3 baseline runner, using synthetic inputs only."""

import json
import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


class FakeBackend:
    def __init__(self, outcomes=None, gpu_available=True, load_error=None):
        self.outcomes = list(outcomes or [])
        self.gpu_available = gpu_available
        self.load_error = load_error
        self.loaded = False
        self.load_calls = []
        self.generate_calls = []
        self.seed_value = None

    def inspect_runtime(self):
        return {
            "python_version": "synthetic-python",
            "torch_version": "synthetic-torch",
            "transformers_version": "synthetic-transformers",
            "accelerate_version": "synthetic-accelerate",
            "gpu_available": self.gpu_available,
            "gpu_name": "synthetic-gpu" if self.gpu_available else None,
            "gpu_memory_bytes": 123456 if self.gpu_available else None,
        }

    def load(self, model_id, revision):
        self.load_calls.append((model_id, revision))
        if self.load_error:
            raise self.load_error
        self.loaded = True

    def seed(self, seed):
        self.seed_value = seed

    def generate(self, messages, settings):
        self.generate_calls.append((messages, dict(settings)))
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


class BaselineInputTests(unittest.TestCase):
    def setUp(self):
        temp_root = ROOT / "outputs/test_tmp"
        temp_root.mkdir(parents=True, exist_ok=True)
        self.temp_dir = tempfile.TemporaryDirectory(dir=temp_root)
        self.addCleanup(self.temp_dir.cleanup)
        self.temp = Path(self.temp_dir.name)
        self.fixture = ROOT / "tests/fixtures/baseline_dev_synthetic.jsonl"

    def baseline(self):
        try:
            import kids_story.baseline as baseline
        except ModuleNotFoundError as exc:
            if exc.name == "kids_story.baseline":
                self.fail("M3 baseline input module has not been implemented yet")
            raise
        return baseline

    def baseline_runner(self):
        baseline = self.baseline()
        if not hasattr(baseline, "run_baseline"):
            self.fail("M3 generation and artifact runner has not been implemented yet")
        if not hasattr(baseline, "BaselineRunError"):
            self.fail("M3 run error type has not been implemented yet")
        return baseline

    def write_rows(self, rows, filename="cases.jsonl"):
        path = self.temp / filename
        with path.open("w", encoding="utf-8", newline="\n") as stream:
            for row in rows:
                if isinstance(row, str):
                    stream.write(row + "\n")
                else:
                    stream.write(json.dumps(row, ensure_ascii=False) + "\n")
        return path

    def write_system(self, text="System text cố định.", filename="system.txt"):
        path = self.temp / filename
        path.write_text(text, encoding="utf-8", newline="\n")
        return path

    def test_valid_synthetic_cases_keep_input_order(self):
        baseline = self.baseline()

        cases = baseline.validate_dev_cases(self.fixture)

        self.assertEqual([case["id"] for case in cases], ["SYN-DEV-001", "SYN-DEV-002"])
        self.assertTrue(all(case.get("fixture_synthetic") is True for case in cases))
        self.assertEqual(cases[0]["prompt"], "Viết truyện về một bạn nhỏ cùng bạn chia sẻ màu vẽ.")

    def test_missing_malformed_blank_and_duplicate_ids_are_rejected(self):
        baseline = self.baseline()
        valid = {"id": "SYN-1", "prompt": "Viết một truyện ngắn."}
        bad_cases = [
            [{"prompt": "Thiếu ID."}],
            [{"id": None, "prompt": "ID không phải chuỗi."}],
            [{"id": " \t", "prompt": "ID rỗng sau khi xét khoảng trắng."}],
            ["{not valid json"],
            [valid, dict(valid)],
        ]

        for index, rows in enumerate(bad_cases):
            with self.subTest(case=index):
                path = self.write_rows(rows, f"bad_id_{index}.jsonl")
                with self.assertRaises(ValueError):
                    baseline.validate_dev_cases(path)

    def test_missing_non_text_and_blank_prompts_are_rejected(self):
        baseline = self.baseline()
        bad_cases = [
            {"id": "SYN-1"},
            {"id": "SYN-1", "prompt": None},
            {"id": "SYN-1", "prompt": 42},
            {"id": "SYN-1", "prompt": " \t\n "},
        ]

        for index, row in enumerate(bad_cases):
            with self.subTest(case=index):
                path = self.write_rows([row], f"bad_prompt_{index}.jsonl")
                with self.assertRaises(ValueError):
                    baseline.validate_dev_cases(path)

    def test_empty_input_file_is_rejected(self):
        baseline = self.baseline()
        path = self.write_rows([], "empty.jsonl")

        with self.assertRaises(ValueError):
            baseline.validate_dev_cases(path)

    def test_messages_use_only_system_text_and_prompt(self):
        baseline = self.baseline()
        case = {
            "id": "SYN-DEV-001",
            "prompt": "  Giữ nguyên prompt này.\n",
            "expected_behavior": ["Không được đưa vào model."],
            "constraints": {"answer": "Không được đưa vào model."},
            "rubric_ids": ["R1"],
            "review_notes": "Không được đưa vào model.",
        }

        messages = baseline.build_messages(case, "System text cố định.")

        self.assertEqual(messages, [
            {"role": "system", "content": "System text cố định."},
            {"role": "user", "content": "  Giữ nguyên prompt này.\n"},
        ])
        serialized = json.dumps(messages, ensure_ascii=False)
        self.assertNotIn("expected_behavior", serialized)
        self.assertNotIn("review_notes", serialized)
        self.assertNotIn("Không được đưa vào model.", serialized)

    def test_blank_system_text_is_rejected(self):
        baseline = self.baseline()

        with self.assertRaises(ValueError):
            baseline.build_messages({"id": "SYN-1", "prompt": "Truyện."}, " \t ")

    def test_successful_run_writes_raw_records_config_and_verified_hashes(self):
        baseline = self.baseline_runner()
        backend = FakeBackend([
            {"text": "  Truyện thô.\n", "output_tokens": 4, "finish_reason": "stop"},
            {"text": "Kết thúc nguyên văn!", "output_tokens": 3, "finish_reason": "length"},
        ])
        output = self.temp / "run_success"

        result = baseline.run_baseline(
            self.fixture, self.write_system(), output, backend=backend, source_commit="synthetic-commit"
        )

        self.assertEqual(result["status"], "complete")
        records = [json.loads(line) for line in (output / "generations.jsonl").read_text(encoding="utf-8").splitlines()]
        self.assertEqual([record["id"] for record in records], ["SYN-DEV-001", "SYN-DEV-002"])
        self.assertEqual(records[0]["generated_text"], "  Truyện thô.\n")
        self.assertEqual(records[0]["output_tokens"], 4)
        self.assertEqual(records[0]["finish_reason"], "stop")
        self.assertEqual(records[1]["finish_reason"], "length")
        self.assertEqual(records[0]["status"], "success")
        self.assertTrue(records[0]["messages_sha256"])
        self.assertGreaterEqual(records[0]["elapsed_seconds"], 0)
        config = json.loads((output / "run_config.json").read_text(encoding="utf-8"))
        self.assertEqual(config["source_commit"], "synthetic-commit")
        self.assertEqual(config["model_revision"], baseline.MODEL_REVISION)
        self.assertEqual(config["runtime"]["gpu_name"], "synthetic-gpu")
        self.assertEqual(backend.seed_value, 42)
        completion = json.loads((output / "COMPLETE.json").read_text(encoding="utf-8"))
        for name, expected in completion["files"].items():
            actual = hashlib.sha256((output / name).read_bytes()).hexdigest()
            self.assertEqual(actual, expected)

    def test_case_generation_error_is_recorded_and_other_cases_continue(self):
        baseline = self.baseline_runner()
        backend = FakeBackend([
            {"text": "Truyện thứ nhất.", "output_tokens": 2, "finish_reason": "stop"},
            RuntimeError("synthetic generation error"),
        ])
        output = self.temp / "run_with_case_error"

        result = baseline.run_baseline(self.fixture, self.write_system(), output, backend=backend)

        self.assertEqual(result["status"], "completed_with_errors")
        records = [json.loads(line) for line in (output / "generations.jsonl").read_text(encoding="utf-8").splitlines()]
        self.assertEqual(len(records), 2)
        self.assertEqual(records[1]["status"], "error")
        self.assertIn("synthetic generation error", records[1]["error"])
        self.assertEqual(len(backend.generate_calls), 2)

    def test_interrupted_run_has_no_completion_manifest(self):
        baseline = self.baseline_runner()
        backend = FakeBackend([
            {"text": "Truyện thứ nhất.", "output_tokens": 2, "finish_reason": "stop"},
            KeyboardInterrupt(),
        ])
        output = self.temp / "run_interrupted"

        with self.assertRaises(KeyboardInterrupt):
            baseline.run_baseline(self.fixture, self.write_system(), output, backend=backend)

        self.assertFalse((output / "COMPLETE.json").exists())
        records = [json.loads(line) for line in (output / "generations.jsonl").read_text(encoding="utf-8").splitlines()]
        self.assertEqual([record["id"] for record in records], ["SYN-DEV-001"])

    def test_gpu_and_model_load_failures_do_not_complete_or_generate(self):
        baseline = self.baseline_runner()
        for name, backend in [
            ("no_gpu", FakeBackend(gpu_available=False)),
            ("load_failure", FakeBackend(load_error=RuntimeError("synthetic load error"))),
        ]:
            with self.subTest(name=name):
                output = self.temp / name
                with self.assertRaises(baseline.BaselineRunError):
                    baseline.run_baseline(self.fixture, self.write_system(), output, backend=backend)
                self.assertFalse((output / "COMPLETE.json").exists())
                self.assertTrue((output / "run_error.json").is_file())
                self.assertEqual(backend.generate_calls, [])

    def test_input_or_prompt_hash_change_changes_run_config(self):
        baseline = self.baseline_runner()
        backend_a = FakeBackend([
            {"text": "Một.", "output_tokens": 1, "finish_reason": "stop"},
            {"text": "Hai.", "output_tokens": 1, "finish_reason": "stop"},
        ])
        backend_b = FakeBackend([
            {"text": "Ba.", "output_tokens": 1, "finish_reason": "stop"},
            {"text": "Bốn.", "output_tokens": 1, "finish_reason": "stop"},
        ])
        input_b = self.write_rows([
            {"id": "SYN-DEV-001", "prompt": "Prompt A"},
            {"id": "SYN-DEV-002", "prompt": "Prompt B"},
        ], "changed.jsonl")
        system_a = self.write_system("System A", "system_a.txt")
        system_b = self.write_system("System B", "system_b.txt")

        baseline.run_baseline(self.fixture, system_a, self.temp / "hash_a", backend=backend_a)
        baseline.run_baseline(input_b, system_b, self.temp / "hash_b", backend=backend_b)

        config_a = json.loads((self.temp / "hash_a/run_config.json").read_text(encoding="utf-8"))
        config_b = json.loads((self.temp / "hash_b/run_config.json").read_text(encoding="utf-8"))
        self.assertNotEqual(config_a["input_sha256"], config_b["input_sha256"])
        self.assertNotEqual(config_a["system_prompt_sha256"], config_b["system_prompt_sha256"])

    def test_existing_output_path_is_untouched(self):
        baseline = self.baseline_runner()
        output = self.temp / "existing"
        output.mkdir()
        sentinel = output / "keep.txt"
        sentinel.write_text("keep", encoding="utf-8")
        backend = FakeBackend()

        with self.assertRaises(FileExistsError):
            baseline.run_baseline(self.fixture, self.write_system(), output, backend=backend)

        self.assertEqual(sentinel.read_text(encoding="utf-8"), "keep")
        self.assertEqual(backend.load_calls, [])

    def test_invalid_input_stops_before_model_load(self):
        baseline = self.baseline_runner()
        backend = FakeBackend()
        invalid = self.write_rows([{"id": "SYN-1", "prompt": " \t "}], "invalid.jsonl")
        output = self.temp / "invalid_run"

        with self.assertRaises(ValueError):
            baseline.run_baseline(invalid, self.write_system(), output, backend=backend)

        self.assertEqual(backend.load_calls, [])
        self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
