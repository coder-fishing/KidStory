"""CPU checks; all records and reviewer identities are synthetic fixtures."""

import copy
import itertools
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from kids_story.data.edits import COLUMNS, apply_edits, export_edits
from kids_story.data.io import digest, read_jsonl, write_json, write_jsonl
from kids_story.data.near import screen, shingles
from kids_story.data.process import process_rows
from kids_story.data.review import candidates, load_records, read_csv, write_csv
from kids_story.training import encode_response, preflight
from kids_story.compare_dev import prepare as prepare_comparison


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        base = ROOT / "outputs/test_tmp"
        base.mkdir(parents=True, exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(dir=base)
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name)
        self.rows = process_rows(read_jsonl(ROOT / "tests/fixtures/m2_stories.jsonl"))

    def test_edit_preserves_original_and_invalidates_approval(self):
        sheet = self.path / "edits.csv"
        export_edits(self.rows, sheet)
        rows = read_csv(sheet, COLUMNS)
        original = candidates(self.rows)[0]
        rows[0].update(
            before=original["processed_text"],
            after=original["processed_text"] + " Cả nhà rất vui.",
            decision="apply", reason="Synthetic test edit",
            reviewer="synthetic-fixture-reviewer",
            reviewed_at="2026-11-15T12:00:00+00:00",
        )
        write_csv(sheet, COLUMNS, rows)
        apply_edits(self.rows, sheet, self.path / "updated")
        updated = load_records(self.path / "updated/records.jsonl")
        changed = next(r for r in updated if r["source_id"] == original["source_id"])
        self.assertEqual(changed["original_text"], original["original_text"])
        self.assertEqual(changed["review_status"], "pending")
        self.assertFalse(changed["text_approved"])
        self.assertIsNone(changed["approval_hash"])
        self.assertTrue(changed["review_history"])
        with self.assertRaisesRegex(ValueError, "Stale"):
            apply_edits(updated, sheet, self.path / "stale")

    def test_inverted_detector_matches_exhaustive_jaccard(self):
        rows = candidates(self.rows)
        for threshold in (0.1, 0.65, 1.0):
            expected = set()
            for a, b in itertools.combinations(rows, 2):
                x = shingles(a["processed_text"], 3)
                y = shingles(b["processed_text"], 3)
                if a["exact_hash"] != b["exact_hash"] and len(x & y) / len(x | y) >= threshold:
                    expected.add((a["source_id"], b["source_id"]))
            result = screen(self.rows, threshold=threshold)
            actual = {(p["source_id_a"], p["source_id_b"]) for p in result["pairs"]}
            self.assertEqual(actual, expected)

    def test_response_mask_and_truncation(self):
        class Tokenizer:
            def apply_chat_template(self, messages, **kwargs):
                return [1, 2, 3] if len(messages) == 2 else [1, 2, 3, 4, 5]
        messages = [{"role": role} for role in ("system", "user", "assistant")]
        encoded = encode_response(Tokenizer(), messages, 5)
        self.assertEqual(encoded["labels"], [-100, -100, -100, 4, 5])
        with self.assertRaisesRegex(ValueError, "too long"):
            encode_response(Tokenizer(), messages, 4)

    def test_preflight_blocks_changed_bundle_before_gpu_import(self):
        (self.path / "COMPLETE.json").write_text(json.dumps({}), encoding="utf-8")
        (self.path / "manifest.json").write_text("{}", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "changed artifact"):
            preflight(self.path)

    def test_preflight_counts_and_group_leakage(self):
        manifest = {
            "stage": "reviewed_sft",
            "row_source_ids": {"train.jsonl": ["a"], "validation.jsonl": ["b"]},
            "lineage_membership_all_candidates": {"a": "g1", "b": "g2"},
        }
        for split in ("train", "validation"):
            write_jsonl(self.path / f"{split}.jsonl", [{"messages": [
                {"role": "system", "content": "Synthetic fixture"},
                {"role": "user", "content": "Synthetic request"},
                {"role": "assistant", "content": split + " synthetic story"},
            ]}])
        def complete():
            write_json(self.path / "manifest.json", manifest)
            write_json(self.path / "COMPLETE.json", {
                name: digest((self.path / name).read_bytes())
                for name in ("manifest.json", "train.jsonl", "validation.jsonl")
            })
        complete()
        self.assertEqual(len(preflight(self.path, min_samples=2)["splits"]["train"]), 1)
        with self.assertRaisesRegex(ValueError, "at least 300"):
            preflight(self.path)
        manifest["lineage_membership_all_candidates"]["b"] = "g1"
        complete()
        with self.assertRaisesRegex(ValueError, "leakage"):
            preflight(self.path, min_samples=2)

    def test_ten_thousand_synthetic_records(self):
        entries = [{
            "value": {
                "source_id": str(i), "source_group_id": str(i),
                "text": f"unique{i} token{i} story{i}.", "fixture_synthetic": True,
            },
            "error": None, "raw_line": "", "line_number": i + 1,
        } for i in range(10000)]
        rows = process_rows(entries, min_units=0)
        report = screen(rows)
        self.assertEqual(report["records_screened"], 10000)
        self.assertEqual(report["pairs"], [])

    def test_blind_dev_review_keeps_scores_pending_and_key_separate(self):
        base = self.path / "base.jsonl"
        tuned = self.path / "tuned.jsonl"
        write_jsonl(base, [{"id": "DEV_SYNTHETIC", "generated_text": "Base fixture"}])
        write_jsonl(tuned, [{"case_id": "DEV_SYNTHETIC", "text": "Tuned fixture"}])
        target = self.path / "paired"
        prepare_comparison(base, tuned, target)
        import csv
        with (target / "dev_blind_review.csv").open(encoding="utf-8-sig", newline="") as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(row["review_status"] == "pending" and row["R1"] == "" for row in rows))
        self.assertNotIn("base", rows[0])
        self.assertTrue((target / "PRIVATE_mapping_do_not_share.json").is_file())


if __name__ == "__main__":
    unittest.main()
