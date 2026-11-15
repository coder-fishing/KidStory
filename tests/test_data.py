"""Meaningful CPU/offline tests, using only synthetic records."""

import json
import os
import random
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from kids_story.data.io import digest, read_jsonl, write_jsonl
from kids_story.data.pipeline import run_pipeline
from kids_story.data.process import normalize_text, process_rows
from kids_story.data.source import _sample_block_indices, sample_source


def temporary_workspace():
    # Keep test artifacts within the workspace (Windows sandbox may deny OS TEMP).
    base = ROOT / "outputs/test_tmp"
    base.mkdir(parents=True, exist_ok=True)
    return tempfile.TemporaryDirectory(dir=base)


class DataTests(unittest.TestCase):
    def setUp(self):
        self.tmp = temporary_workspace()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.fixture = ROOT / "tests/fixtures/stories.jsonl"

    def run_fixture(self, name="out", **kwargs):
        return run_pipeline(self.fixture, self.base / name, **kwargs)

    def test_unicode_whitespace_original_and_idempotence(self):
        text = "  Be\u0301\t An.\r\n\r\n\r\n  Mẹ\u00a0vui.  "
        normalized, reasons = normalize_text(text)
        self.assertEqual(normalized, "Bé An.\n\nMẹ vui.")
        self.assertEqual(set(reasons), {"unicode_nfc", "line_endings", "whitespace"})
        self.assertEqual(normalize_text(normalized), (normalized, []))
        p = self.base / "one.jsonl"
        write_jsonl(p, [{"source_id": "a", "source_group_id": "g", "text": text, "extra": 4}])
        r = process_rows(read_jsonl(p))[0]
        self.assertEqual(r["original_text"], text)
        self.assertEqual(r["original_record"]["extra"], 4)
        self.assertEqual(r["processed_text"], normalized)

    def test_schema_bad_rows_and_review_flags(self):
        report = self.run_fixture()
        rows = [json.loads(l) for l in (self.base / "out/processed.jsonl").read_text(encoding="utf-8").splitlines()]
        self.assertEqual(report["input_rows"], 14)
        self.assertEqual(report["status_counts"], {"candidate": 6, "duplicate": 1, "quarantine": 7})
        flags = report["flag_counts"]
        for flag in ["empty_text", "non_string_text", "missing_text_field", "invalid_source_group_id",
                     "invalid_json", "not_json_object", "blank_line", "possible_truncation_review",
                     "repeated_line_review", "control_or_format_character_review"]:
            self.assertGreater(flags.get(flag, 0), 0, flag)
        for r in rows:
            self.assertEqual(r["review_status"], "pending")
            self.assertIsNone(r["lesson"])
            if r["status"] == "quarantine":
                self.assertIsNone(r["split"])

    def test_exact_dedup_transitive_source_groups_and_no_leakage(self):
        self.run_fixture()
        manifest = json.loads((self.base / "out/split_manifest.json").read_text(encoding="utf-8"))
        assignments = {r["source_id"]: r for r in manifest["assignments"] if r["source_id"]}
        self.assertEqual(assignments["A02"]["duplicate_of"], "A01")
        for key in ["merged_group_id", "split"]:
            self.assertEqual(len({assignments[s][key] for s in ["A01", "A02", "A03", "A04"]}), 1)
        train = [json.loads(l) for l in (self.base / "out/train.jsonl").read_text(encoding="utf-8").splitlines()]
        val = [json.loads(l) for l in (self.base / "out/validation.jsonl").read_text(encoding="utf-8").splitlines()]
        self.assertTrue(train and val)
        self.assertFalse({r["exact_hash"] for r in train} & {r["exact_hash"] for r in val})
        # Check all source mappings, including dropped exact duplicates.
        for field in ["source_group_id", "merged_group_id", "exact_hash"]:
            t = {r[field] for r in assignments.values() if r["split"] == "train"}
            v = {r[field] for r in assignments.values() if r["split"] == "validation"}
            self.assertFalse(t & v, field)
        self.assertEqual(next(r for r in train + val if r["source_id"] == "A01")["duplicate_source_ids"], ["A01", "A02"])

    def test_seed_reproducibility_and_shuffled_input_manifest(self):
        self.run_fixture("first", seed=19)
        self.run_fixture("second", seed=19)
        a = (self.base / "first/split_manifest.json").read_bytes()
        self.assertEqual(a, (self.base / "second/split_manifest.json").read_bytes())
        # Malformed rows retain physical-line audit IDs; reorder well-formed rows only.
        entries = read_jsonl(self.fixture)
        good = [e["value"] for e in entries if not e["error"]]
        first, shuffled = self.base / "good.jsonl", self.base / "shuffled.jsonl"
        write_jsonl(first, good)
        random.Random(9).shuffle(good)
        write_jsonl(shuffled, good)
        run_pipeline(first, self.base / "ordered", seed=19)
        run_pipeline(shuffled, self.base / "shuffled_out", seed=19)
        self.assertEqual((self.base / "ordered/split_manifest.json").read_bytes(),
                         (self.base / "shuffled_out/split_manifest.json").read_bytes())
        self.run_fixture("other_seed", seed=999)
        self.assertNotEqual(a, (self.base / "other_seed/split_manifest.json").read_bytes())

    def test_too_few_components_fails_without_success_artifacts(self):
        for name, rows in [("empty", []), ("single", [{"source_id": "a", "source_group_id": "g", "text": "Xong."}]),
                           ("same_group", [{"source_id": str(i), "source_group_id": "g", "text": f"Truyện {i}."} for i in range(3)])]:
            p = self.base / (name + ".jsonl")
            write_jsonl(p, rows)
            with self.assertRaisesRegex(ValueError, "at least two"):
                run_pipeline(p, self.base / name)
            report = json.loads((self.base / name / "report.json").read_text(encoding="utf-8"))
            self.assertEqual(report["status"], "failed")
            self.assertFalse((self.base / name / "COMPLETE.json").exists())
            self.assertFalse((self.base / name / "train.jsonl").exists())

    def test_duplicate_ids_fail_and_output_is_never_overwritten(self):
        p = self.base / "dup.jsonl"
        write_jsonl(p, [{"source_id": "same", "source_group_id": "g", "text": f"Truyện {i}."} for i in range(2)])
        with self.assertRaisesRegex(ValueError, "Duplicate source_id"):
            run_pipeline(p, self.base / "dup")
        self.run_fixture()
        before = (self.base / "out/report.json").read_bytes()
        with self.assertRaisesRegex(ValueError, "already exists"):
            self.run_fixture()
        self.assertEqual(before, (self.base / "out/report.json").read_bytes())

    def test_strict_json_utf8_and_custom_text_field(self):
        p = self.base / "strict.jsonl"
        p.write_text('{"text": NaN}\n{"text":"a","text":"b"}\n', encoding="utf-8")
        self.assertTrue(all(e["error"] == "invalid_json" for e in read_jsonl(p)))
        p.write_bytes(b'\xff\n')
        with self.assertRaises(UnicodeError):
            run_pipeline(p, self.base / "bad_encoding")
        write_jsonl(p, [{"source_id": str(i), "source_group_id": str(i), "vi": f"Truyện {i}."} for i in range(3)])
        report = run_pipeline(p, self.base / "vi", text_field="vi")
        self.assertEqual(report["input_rows"], 3)
        for ratio in [0, 1, -1, float("nan"), float("inf")]:
            with self.assertRaises(ValueError):
                run_pipeline(p, self.base / "bad_ratio", validation_ratio=ratio)

    def test_artifact_hashes_and_cli(self):
        report = self.run_fixture()
        for filename, sha in report["artifact_sha256"].items():
            self.assertEqual(digest((self.base / "out" / filename).read_bytes()), sha)
        complete = json.loads((self.base / "out/COMPLETE.json").read_text(encoding="utf-8"))
        self.assertEqual(complete["report_sha256"], digest((self.base / "out/report.json").read_bytes()))
        env = dict(os.environ, PYTHONPATH=str(ROOT / "src"))
        cmd = [sys.executable, "-m", "kids_story.data", "--input", str(self.fixture), "--output-dir", str(self.base / "cli")]
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["input_rows"], 14)
        self.assertEqual(subprocess.run(cmd, env=env, capture_output=True).returncode, 2)

    def test_seed_changes_assignments_not_just_manifest_config(self):
        p = self.base / "many.jsonl"
        write_jsonl(p, [{"source_id": str(i), "source_group_id": str(i),
                        "text": f"Truyện riêng {i}."} for i in range(20)])
        for seed in [42, 99]:
            run_pipeline(p, self.base / str(seed), seed=seed, validation_ratio=.3)
        assignments = []
        for seed in [42, 99]:
            manifest = json.loads((self.base / str(seed) / "split_manifest.json").read_text(encoding="utf-8"))
            assignments.append({r["source_id"] for r in manifest["assignments"] if r["split"] == "validation"})
        self.assertEqual(len(assignments[0]), 6)
        self.assertNotEqual(*assignments)

    def test_exact_dedup_keeps_similar_but_not_identical_text(self):
        p = self.base / "similar.jsonl"
        write_jsonl(p, [{"source_id": str(i), "source_group_id": str(i), "text": t}
                       for i, t in enumerate(["Bé An vui.", "Bé An vui!", "bé An vui."])])
        report = run_pipeline(p, self.base / "similar")
        self.assertEqual(report["status_counts"], {"candidate": 3})


class SourceTests(unittest.TestCase):
    def responses(self, viewer_revision=None, truncated=False):
        rev = "a" * 40
        return [
            (json.dumps({"sha": rev, "cardData": {"license": "mit"}}).encode(), {}),
            (b"license: mit", {"x-repo-commit": rev}),
            (json.dumps({"features": [{"name": k, "type": {"dtype": "string"}} for k in ["en", "vi"]],
                         "rows": [{"row_idx": 0, "row": {"en": "A story.", "vi": "Truyện."},
                                   "truncated_cells": ["vi"] if truncated else []}]}).encode(),
             {"x-revision": viewer_revision or rev}),
        ]

    def test_source_snapshot_revision_schema_and_sampling_evidence(self):
        with temporary_workspace() as tmp, patch("kids_story.data.source._get", side_effect=self.responses()):
            p = Path(tmp) / "source"
            metadata = sample_source(p, revision="a" * 40, limit=1)
            self.assertEqual(metadata["resolved_revision"], "a" * 40)
            self.assertEqual(metadata["sampling"]["method"], "prefix")
            self.assertFalse(metadata["sampling"]["random"])
            self.assertTrue((p / "COMPLETE.json").exists())
            self.assertEqual(json.loads((p / "sample.jsonl").read_text(encoding="utf-8"))["vi"], "Truyện.")

    def test_source_refuses_unpinned_or_truncated_viewer(self):
        for responses in [self.responses(viewer_revision="b" * 40), self.responses(truncated=True)]:
            with temporary_workspace() as tmp, patch("kids_story.data.source._get", side_effect=responses):
                p = Path(tmp) / "source"
                with self.assertRaises(ValueError):
                    sample_source(p, revision="a" * 40, limit=1)
                self.assertFalse(p.exists())

    def test_source_random_block_sample_uses_seeded_nonprefix_blocks(self):
        rev = "a" * 40
        blocks = _sample_block_indices(1000, 100, 42)
        offset = blocks[0] * 100
        first_rows = [{"row_idx": 0, "row": {"en": "probe", "vi": "mẫu"}, "truncated_cells": []}]
        sampled_rows = [{"row_idx": offset + i, "row": {"en": f"Story {offset+i}", "vi": f"Truyện {offset+i}."},
                         "truncated_cells": []} for i in range(100)]
        common = {"features": [{"name": k, "type": {"dtype": "string"}} for k in ["en", "vi"]]}
        responses = [
            (json.dumps({"sha": rev, "cardData": {"license": "mit"}}).encode(), {}),
            (b"license: mit", {"x-repo-commit": rev}),
            (json.dumps({**common, "num_rows_total": 1000, "rows": first_rows}).encode(), {"x-revision": rev}),
            (json.dumps({**common, "num_rows_total": 1000, "rows": sampled_rows}).encode(), {"x-revision": rev}),
        ]
        with temporary_workspace() as tmp, patch("kids_story.data.source._get", side_effect=responses):
            output = Path(tmp) / "source"
            manifest = sample_source(output, revision=rev, limit=100, method="random_blocks", seed=42)
            self.assertEqual(manifest["sampling"]["method"], "seeded_random_contiguous_blocks_cluster_sample_v1")
            self.assertNotEqual(manifest["sampling"]["selected_block_indices"], [0])
            self.assertEqual(len(manifest["sampling"]["row_indices"]), 100)
            self.assertEqual(manifest["sampling"]["row_indices"][0], offset)
            self.assertIn("not an IID row sample", manifest["sampling"]["sampling_note"])
            self.assertEqual(manifest["viewer_response_evidence"][-1]["offset"], offset)


if __name__ == "__main__":
    unittest.main()
