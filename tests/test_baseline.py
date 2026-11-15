"""Tests for the M3 baseline runner, using synthetic inputs only."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


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

    def write_rows(self, rows, filename="cases.jsonl"):
        path = self.temp / filename
        with path.open("w", encoding="utf-8", newline="\n") as stream:
            for row in rows:
                if isinstance(row, str):
                    stream.write(row + "\n")
                else:
                    stream.write(json.dumps(row, ensure_ascii=False) + "\n")
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


if __name__ == "__main__":
    unittest.main()
