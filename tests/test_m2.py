"""M2 integration tests: all review identities/approvals here are SYNTHETIC."""

import copy
import ast
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from kids_story.data.io import digest, read_jsonl, write_jsonl
from kids_story.data.eda import run_eda
from kids_story.data.m2 import prepare
from kids_story.data.names import suggest_names
from kids_story.data.near import PAIR_COLUMNS, confirmed_edges, export_pairs, screen
from kids_story.data.process import process_rows
from kids_story.data.review import (EDITABLE, READONLY, export_review, import_review,
    load_records, read_csv, validate_approval, write_csv)
from kids_story.data.source import _sample_block_indices
from kids_story.data.sft import export_sft, lineage_groups


class M2Tests(unittest.TestCase):
    def setUp(self):
        base = ROOT / "outputs/test_tmp"
        base.mkdir(parents=True, exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(dir=base)
        self.addCleanup(self.tmp.cleanup)
        self.p = Path(self.tmp.name)
        self.rows = process_rows(read_jsonl(ROOT / "tests/fixtures/m2_stories.jsonl"))

    def review(self, rows=None):
        rows = self.rows if rows is None else rows
        target = self.p / "review"
        export_review(rows, target)
        return target, read_csv(target / "metadata_review.csv", READONLY + EDITABLE)

    def approve_sheet(self, sheet):
        for r in sheet:
            r.update(topic="Việc tốt", characters="Nhân vật trong fixture", lesson="Quan tâm đến người khác",
                     label_source="synthetic_test_only", source_character_names_en="No English names in this fixture.",
                     character_name_notes="Synthetic fixture only; keep names as written.", character_names_reviewed="true",
                     review_status="approved", text_approved="true", flags_resolved="true",
                     prompt_metadata_approved="true", reviewer="synthetic-test-reviewer",
                     reviewed_at="2026-11-14T22:00:00+07:00", review_notes="Synthetic fixture, not human approval of source data.")

    def approved(self, rows=None):
        rows = self.rows if rows is None else rows
        target, sheet = self.review(rows)
        self.approve_sheet(sheet)
        write_csv(target / "metadata_review.csv", READONLY + EDITABLE, sheet)
        return import_review(rows, target / "metadata_review.csv", target / "review_baseline.json")

    def near_files(self, rows, decision="confirmed"):
        result = screen(rows)
        p = self.p / "near"
        export_pairs(result, p)
        sheet = read_csv(p / "near_review.csv", PAIR_COLUMNS)
        for r in sheet:
            r.update(decision=decision, reviewer="synthetic-test-reviewer",
                     reviewed_at="2026-11-14T22:00:00+07:00", review_notes="Synthetic test decision only.")
        write_csv(p / "near_review.csv", PAIR_COLUMNS, sheet)
        return result, p / "near_review.csv"

    def test_near_scores_pending_distinct_and_confirmed(self):
        result, csv_path = self.near_files(self.rows, "pending")
        self.assertEqual(len(result["pairs"]), 1)
        self.assertEqual(result["candidate_groups"], [["S1", "S2"]])
        with self.assertRaisesRegex(ValueError, "Unresolved"):
            confirmed_edges(self.rows, result, csv_path)
        sheet = read_csv(csv_path, PAIR_COLUMNS)
        sheet[0]["decision"] = "distinct"
        write_csv(csv_path, PAIR_COLUMNS, sheet)
        self.assertEqual(confirmed_edges(self.rows, result, csv_path), [])
        sheet[0]["decision"] = "confirmed"
        write_csv(csv_path, PAIR_COLUMNS, sheet)
        self.assertEqual(confirmed_edges(self.rows, result, csv_path), [("S1", "S2")])
        for kwargs in [{"threshold": float("nan")}, {"ngram": 0}, {"max_records": 1}]:
            with self.assertRaises(ValueError): screen(self.rows, **kwargs)

    def test_review_roundtrip_and_history(self):
        rows = self.approved()
        for row in rows:
            validate_approval(row)
            self.assertEqual(row["original_text"], row["processed_text"])
            self.assertEqual(len(row["review_history"]), 1)
        rows[0]["lesson"] = "Changed after approval"
        with self.assertRaisesRegex(ValueError, "Stale approval"):
            validate_approval(rows[0])

    def test_pending_noop_does_not_invent_review_history(self):
        target, _ = self.review()
        rows = import_review(self.rows, target / "metadata_review.csv", target / "review_baseline.json")
        self.assertTrue(all(r["review_status"] == "pending" and r["review_history"] == [] for r in rows))

    def test_review_refuses_stale_revision_and_flags(self):
        target, sheet = self.review()
        for key, value in [("source_revision", "new-revision"), ("flags", ["new_flag"])]:
            current = copy.deepcopy(self.rows)
            current[0][key] = value
            with self.assertRaises(ValueError):
                import_review(current, target / "metadata_review.csv", target / "review_baseline.json")
        sheet[0]["source_id"] = "unknown"
        write_csv(target / "metadata_review.csv", READONLY + EDITABLE, sheet)
        with self.assertRaises(ValueError):
            import_review(self.rows, target / "metadata_review.csv", target / "review_baseline.json")

    def test_blocks_missing_metadata_unresolved_flags_and_reviewer(self):
        # Exercise import before writing any approved snapshot.
        target, sheet = self.review()
        self.approve_sheet(sheet)
        sheet[0]["lesson"] = ""
        write_csv(target / "metadata_review.csv", READONLY + EDITABLE, sheet)
        with self.assertRaisesRegex(ValueError, "metadata missing"):
            import_review(self.rows, target / "metadata_review.csv", target / "review_baseline.json")
        self.approve_sheet(sheet)
        sheet[0]["reviewer"] = ""
        write_csv(target / "metadata_review.csv", READONLY + EDITABLE, sheet)
        with self.assertRaises(ValueError):
            import_review(self.rows, target / "metadata_review.csv", target / "review_baseline.json")
        row = self.rows[0]
        row.update(review_status="approved", topic="a", characters="b", lesson="c", label_source="test",
                   source_character_names_en="none", character_name_notes="Keep names", character_names_reviewed=True,
                   text_approved=True, prompt_metadata_approved=True, flags=["review"], flags_resolved=False)
        with self.assertRaisesRegex(ValueError, "flags"):
            validate_approval(row, check_hash=False)

    def test_text_edit_pending_then_fresh_review(self):
        target, sheet = self.review()
        self.approve_sheet(sheet)
        sheet[0]["processed_text"] += " An vui."
        write_csv(target / "metadata_review.csv", READONLY + EDITABLE, sheet)
        with self.assertRaisesRegex(ValueError, "Text edits require pending"):
            import_review(self.rows, target / "metadata_review.csv", target / "review_baseline.json")
        sheet[0]["review_status"] = "pending"
        write_csv(target / "metadata_review.csv", READONLY + EDITABLE, sheet)
        updated = import_review(self.rows, target / "metadata_review.csv", target / "review_baseline.json")
        self.assertIsNone(updated[0]["approval_hash"])
        self.assertFalse(updated[0]["text_approved"])
        self.assertEqual(updated[0]["original_text"], self.rows[0]["original_text"])
        self.assertNotEqual(updated[0]["exact_hash"], self.rows[0]["exact_hash"])
        second = self.p / "review2"
        export_review(updated, second)
        s2 = read_csv(second / "metadata_review.csv", READONLY + EDITABLE)
        self.approve_sheet(s2)
        write_csv(second / "metadata_review.csv", READONLY + EDITABLE, s2)
        again = import_review(updated, second / "metadata_review.csv", second / "review_baseline.json")
        self.assertEqual(len(again[0]["review_history"]), 2)
        validate_approval(again[0])

    def test_sft_schema_prompts_and_confirmed_group_no_leak(self):
        rows = self.approved()
        near, csv_path = self.near_files(rows)
        manifest = export_sft(rows, self.p / "sft", near_result=near, near_review=csv_path,
                              rights={}, prompt_dir=ROOT / "prompts", synthetic=True, validation_ratio=.3)
        assignments = {r["source_id"]: r for r in manifest["split"]["assignments"]}
        self.assertEqual(assignments["S1"]["split"], assignments["S2"]["split"])
        for name in ["train.jsonl", "validation.jsonl"]:
            entries = read_jsonl(self.p / "sft" / name)
            self.assertTrue(entries)
            for entry in entries:
                item = entry["value"]
                self.assertEqual(set(item), {"messages"})
                self.assertEqual([m["role"] for m in item["messages"]], ["system", "user", "assistant"])
                self.assertEqual(item["messages"][0]["content"], (ROOT / "prompts/story_system_v1.txt").read_text(encoding="utf-8"))
                self.assertNotIn("Synthetic fixture", item["messages"][1]["content"])
        self.assertEqual(manifest["stage"], "synthetic_fixture_only")

    def test_unapproved_real_rights_and_synthetic_bypass_are_blocked(self):
        near, csv_path = self.near_files(self.rows)
        with self.assertRaisesRegex(ValueError, "No human-approved"):
            export_sft(self.rows, self.p / "blocked", near_result=near, near_review=csv_path,
                       rights={}, prompt_dir=ROOT / "prompts", synthetic=True)
        self.assertFalse((self.p / "blocked").exists())
        rows = copy.deepcopy(self.rows)
        for row in rows:
            row["original_record"].update(fixture_synthetic=False, source_dataset="real-source")
            row["source_revision"] = "a" * 40
        approved = self.approved(rows)
        real_near = screen(approved)
        # Rewrite pair evidence for changed corpus, retaining synthetic test-only decisions.
        from kids_story.data.review import corpus_hash
        near.update(corpus_hash=corpus_hash(approved))
        ledger = {"sources": [{"dataset_id": "real-source", "revision": "a" * 40, "training_use": "unresolved"}]}
        with self.assertRaisesRegex(ValueError, "rights unresolved"):
            export_sft(approved, self.p / "real", near_result=real_near, near_review=csv_path,
                       rights=ledger, prompt_dir=ROOT / "prompts")
        with self.assertRaisesRegex(ValueError, "fixtures only"):
            export_sft(approved, self.p / "bypass", near_result=real_near, near_review=csv_path,
                       rights={}, prompt_dir=ROOT / "prompts", synthetic=True)

    def test_stale_near_report_and_lineage_bridge(self):
        result, csv_path = self.near_files(self.rows)
        changed = copy.deepcopy(self.rows)
        changed[0]["source_revision"] = "new"
        with self.assertRaisesRegex(ValueError, "Stale"):
            confirmed_edges(changed, result, csv_path)
        # A pending intermediate member still joins two approved ends.
        groups = lineage_groups(self.rows, [("S1", "S2"), ("S2", "S3")])
        self.assertEqual(groups["S1"], groups["S3"])

    def test_seeded_sample_manifest_and_bounds(self):
        p = self.p / "processed.jsonl"
        write_jsonl(p, self.rows)
        a = prepare(p, self.p / "a", sample_size=3, seed=9)
        b = prepare(p, self.p / "b", sample_size=3, seed=9)
        self.assertEqual(a, b)
        reversed_path = self.p / "reversed.jsonl"
        write_jsonl(reversed_path, list(reversed(self.rows)))
        c = prepare(reversed_path, self.p / "c", sample_size=3, seed=9)
        self.assertEqual(a["selected_audit_ids"], c["selected_audit_ids"])
        with self.assertRaises(ValueError): prepare(p, self.p / "huge", sample_size=201)

    def test_random_block_selection_is_seeded_bounded_and_not_prefix(self):
        first = _sample_block_indices(26000, 10000, 42)
        self.assertEqual(first, _sample_block_indices(26000, 10000, 42))
        self.assertEqual(len(first), 100)
        self.assertEqual(len(set(first)), 100)
        self.assertNotEqual(first, list(range(100)))
        with self.assertRaises(ValueError): _sample_block_indices(99, 100, 42)
        with self.assertRaises(ValueError): _sample_block_indices(1000, 150, 42)

    def test_eda_outputs_bilingual_candidates_and_keeps_input_unchanged(self):
        input_path = ROOT / "tests/fixtures/eda_stories.jsonl"
        before = input_path.read_bytes()
        output = self.p / "eda"
        report = run_eda(input_path, output)
        self.assertEqual(report["input_rows"], 4)
        self.assertEqual(report["field_summary"]["vi"]["empty_or_whitespace_count"], 1)
        self.assertEqual(len(report["exact_duplicate_groups_vi"]), 1)
        self.assertEqual(report["name_candidate_rows"], 3)
        self.assertEqual(report["translation_calque_candidate_rows"], 3)
        self.assertEqual(input_path.read_bytes(), before)
        names = read_csv(output / "name_candidates.csv", [
            "source_id", "source_name_en", "suggestion_vi", "basis", "source_text_en",
            "source_text_vi", "review_status", "review_notes"])
        phrases = read_csv(output / "translation_candidates.csv", [
            "source_id", "rule_id", "english_phrase", "vietnamese_phrase", "english_context",
            "vietnamese_context", "suggestion", "reason", "review_status", "review_notes"])
        self.assertTrue(all(row["review_status"] == "pending" for row in names + phrases))
        complete = json.loads((output / "COMPLETE.json").read_text(encoding="utf-8"))
        self.assertTrue(complete)
        for filename, expected_hash in complete.items():
            self.assertEqual(digest((output / filename).read_bytes()), expected_hash)
        with self.assertRaisesRegex(ValueError, "refusing overwrite"):
            run_eda(input_path, output)

    def test_eda_rejects_stale_source_manifest(self):
        input_path = ROOT / "tests/fixtures/eda_stories.jsonl"
        manifest = self.p / "source_manifest.json"
        manifest.write_text(json.dumps({"artifact_sha256": {"sample.jsonl": "0" * 64}}), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "does not match"):
            run_eda(input_path, self.p / "bad_manifest_eda", manifest)

    def test_eda_checks_source_manifest_revision_and_indices(self):
        from kids_story.data.io import digest
        input_path = ROOT / "tests/fixtures/eda_stories.jsonl"
        entries = read_jsonl(input_path)
        ids = [entry["value"]["source_row_id"] for entry in entries]
        manifest = self.p / "source_manifest_valid.json"
        manifest.write_text(json.dumps({
            "artifact_sha256": {"sample.jsonl": digest(input_path.read_bytes())},
            "resolved_revision": "fixture-revision",
            "sampling": {"row_indices": ids},
        }), encoding="utf-8")
        report = run_eda(input_path, self.p / "eda_manifest_valid", manifest)
        self.assertEqual(report["source_manifest"]["resolved_revision"], "fixture-revision")
        with self.assertRaisesRegex(ValueError, "row indices"):
            changed = json.loads(manifest.read_text(encoding="utf-8"))
            changed["sampling"]["row_indices"] = list(reversed(ids))
            manifest.write_text(json.dumps(changed), encoding="utf-8")
            run_eda(input_path, self.p / "eda_manifest_stale_indices", manifest)

    def test_approved_name_mappings_are_suggestions_only(self):
        result = suggest_names("The boy named Tim met a friend named Buddy and another named Max.")
        suggestions = {row["source"].casefold(): row for row in result["suggestions"]}
        self.assertEqual(suggestions["tim"]["vietnamese_suggestion"], "Tín")
        self.assertEqual(suggestions["buddy"]["vietnamese_suggestion"], "Bắp")
        self.assertEqual(suggestions["max"]["vietnamese_suggestion"], "Mã")
        self.assertTrue(all(row["basis"] == "user_approved_mapping_v2_candidate_only"
                            for row in suggestions.values()))

    def test_m2_eda_notebook_is_valid_thin_cpu_runner(self):
        path = ROOT / "notebooks/m2_eda_colab.ipynb"
        notebook = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(notebook["nbformat"], 4)
        code_cells = ["".join(cell["source"]) for cell in notebook["cells"]
                      if cell["cell_type"] == "code"]
        self.assertTrue(code_cells)
        for source in code_cells:
            ast.parse(source)
        combined = "\n".join(code_cells)
        self.assertIn("sample_source(", combined)
        self.assertIn("run_eda(", combined)
        self.assertIn("SAMPLE_SIZE = 1000", combined)
        self.assertIn("savefig(", combined)
        self.assertIn("run.log", combined)
        self.assertIn("run_config.json", combined)
        self.assertIn("COMPLETE.json", combined)
        self.assertNotIn("HF_TOKEN", combined)


if __name__ == "__main__":
    unittest.main()
