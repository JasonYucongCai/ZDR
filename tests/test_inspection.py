import json
import tempfile
import unittest
from pathlib import Path

from zdr_fixtures.generator import Config, generate_bundle, json_text, write_bundle
from zdr_fixtures.inspection import (
    extract_assistant_text, load_manifest, read_observation,
    scan_observation, verify_bundle,
)


class InspectionTests(unittest.TestCase):
    def setUp(self):
        self.bundle = generate_bundle(Config(seed=17, instruction="repeat", languages=("en",)))

    def test_exact_hits_and_negative_controls(self):
        report = scan_observation(self.bundle.manifest, self.bundle.assistant_fixture)
        self.assertEqual(set(report["exact_exposed_marker_hits"]), set(self.bundle.manifest["requested_output_record_markers"]))
        self.assertFalse(report["exact_holdout_marker_hits"])
        self.assertFalse(report["training_or_zdr_violation_proven"])
        self.assertTrue(report["normalized_phrase_hits"])
        control = self.bundle.manifest["holdouts"][0]["marker"]
        report = scan_observation(self.bundle.manifest, control)
        self.assertTrue(report["control_contamination_suspected"])
        self.assertEqual(report["exact_holdout_marker_hits"], [control])

    def test_no_hit_and_no_unexposed_language_phrase_hit(self):
        report = scan_observation(self.bundle.manifest, "An unrelated observation.")
        self.assertFalse(report["exact_exposed_marker_hits"])
        self.assertFalse(report["normalized_phrase_hits"])
        chinese = self.bundle.records[0]["renderings"]["zh"]
        self.assertFalse(scan_observation(self.bundle.manifest, chinese)["normalized_phrase_hits"])

    def test_only_assistant_content_extracted_from_chat_and_responses(self):
        transcript = json.loads(self.bundle.artifacts["chat_completion_transcript.json"])
        self.assertEqual(extract_assistant_text(transcript), self.bundle.assistant_fixture)
        transcript["messages"] = transcript["messages"][:1]
        self.assertEqual(extract_assistant_text(transcript), "")
        self.assertEqual(extract_assistant_text({"choices": [{"message": {"role": "assistant", "content": "yes"}}]}), "yes")
        output = json.loads(self.bundle.artifacts["responses_output_fixture.json"])
        output["output"].append({"type": "reasoning", "summary": [{"text": "must not be scanned"}]})
        self.assertEqual(extract_assistant_text(output), self.bundle.assistant_fixture)
        with self.assertRaises(ValueError):
            extract_assistant_text({"input": "not an assistant response"})

    def test_json_unicode_escapes_decoded_before_matching(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "observation.json"
            path.write_text(json.dumps({"role": "assistant", "content": "\u4e8c\u52a0\u4e09\u7b49\u4e8e\u516d\u3002"}, ensure_ascii=True), encoding="utf-8")
            self.assertEqual(read_observation(path), "\u4e8c\u52a0\u4e09\u7b49\u4e8e\u516d\u3002")

    def test_integrity_verification_and_tampering(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "run"
            write_bundle(self.bundle, output)
            path = output / "manifest.json"
            self.assertEqual(load_manifest(path)["run_id"], self.bundle.manifest["run_id"])
            report = verify_bundle(path)
            self.assertTrue(report["valid"])
            self.assertEqual(report["math_records_checked"], 30)
            (output / "prompt.txt").write_text("modified", encoding="utf-8")
            self.assertFalse(verify_bundle(path)["valid"])

    def test_reject_invalid_manifest_and_path_traversal(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "manifest.json"
            manifest = json.loads(json_text(self.bundle.manifest))
            manifest["artifacts"]["../outside.txt"] = {"bytes": 0, "sha256": "unused"}
            path.write_text(json_text(manifest), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "basenames"):
                verify_bundle(path)
            manifest["records"][0]["marker"] = "invalid"
            path.write_text(json_text(manifest), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "markers"):
                load_manifest(path)


if __name__ == "__main__":
    unittest.main()