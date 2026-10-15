import json
import tempfile
import unittest
from pathlib import Path

from zdr_fixtures.generator import Config, INSTRUCTIONS, digest, generate_bundle, write_bundle


class GeneratorTests(unittest.TestCase):
    def test_seed_reproduces_all_artifacts(self):
        first = generate_bundle(Config(seed=42))
        second = generate_bundle(Config(seed=42))
        self.assertEqual(first.artifacts, second.artifacts)
        self.assertNotEqual(first.manifest["run_id"], generate_bundle(Config(seed=43)).manifest["run_id"])

    def test_requests_transcripts_and_response_items(self):
        bundle = generate_bundle(Config(seed=7, math_count=5, claim_count=5, instruction="repeat"))
        chat = json.loads(bundle.artifacts["chat_completion_request.json"])
        self.assertEqual(chat["messages"], [{"role": "user", "content": bundle.prompt}])
        transcript = json.loads(bundle.artifacts["chat_completion_transcript.json"])
        self.assertEqual(transcript["messages"][-1], {"role": "assistant", "content": bundle.assistant_fixture})
        responses = json.loads(bundle.artifacts["responses_request.json"])
        self.assertEqual(responses["input"][0]["content"][0], {"type": "input_text", "text": bundle.prompt})
        output = json.loads(bundle.artifacts["responses_output_fixture.json"])
        self.assertEqual(output["output"][0]["content"][0]["type"], "output_text")
        self.assertEqual(output["output"][0]["content"][0]["text"], bundle.assistant_fixture)
        self.assertTrue(output["fixture_is_simulated"])
        for marker in bundle.manifest["requested_output_record_markers"]:
            self.assertIn(marker, bundle.assistant_fixture)
        self.assertEqual(len(bundle.manifest["requested_output_record_markers"]), 3)

    def test_holdouts_and_corrections_stay_out_of_prompt(self):
        bundle = generate_bundle(Config(seed=100))
        for record in bundle.manifest["holdouts"]:
            self.assertNotIn(record["marker"], bundle.prompt)
            self.assertNotIn(record["marker"], bundle.assistant_fixture or "")
        for record in bundle.records:
            if record["kind"] == "claim":
                self.assertNotIn(record["correction"]["en"], bundle.prompt)
        self.assertEqual(len({record["marker"] for record in bundle.records}), 50)

    def test_all_instruction_modes_in_both_languages(self):
        for instruction in INSTRUCTIONS:
            for language in ("en", "zh"):
                with self.subTest(instruction=instruction, language=language):
                    bundle = generate_bundle(Config(seed=55, instruction=instruction, instruction_language=language))
                    self.assertTrue(bundle.prompt.startswith(bundle.manifest["instruction"]["text"]))
                    if instruction == "accept-true":
                        self.assertEqual(bundle.assistant_fixture, "those are true")
                    elif instruction == "yes":
                        self.assertEqual(bundle.assistant_fixture, "yes")
                    elif instruction == "silent":
                        self.assertEqual(bundle.assistant_fixture, "")
                        self.assertEqual(json.loads(bundle.artifacts["responses_output_fixture.json"])["output"], [])
                    elif instruction == "repeat-all":
                        self.assertEqual(len(bundle.assistant_fixture.splitlines()), 50)

    def test_target_modes_and_format_selection(self):
        bundle = generate_bundle(Config(seed=1, target="input", formats=("text",)))
        self.assertIsNone(bundle.assistant_fixture)
        self.assertNotIn("assistant_fixture.txt", bundle.artifacts)
        self.assertNotIn("chat_completion_request.json", bundle.artifacts)
        self.assertEqual(bundle.manifest["instruction"]["name"], "none")
        output_target = generate_bundle(Config(seed=1, target="output", instruction="repeat"))
        self.assertTrue(output_target.manifest["input_exposure_unavoidable"])
        self.assertTrue(output_target.manifest["output_canary_expected"])

    def test_language_and_topic_filters(self):
        math_only = generate_bundle(Config(seed=4, claim_count=0, languages=("math",)))
        self.assertNotIn(" EN:", math_only.prompt)
        self.assertNotIn(" ZH:", math_only.prompt)
        for language in ("en", "zh"):
            bundle = generate_bundle(Config(seed=4, languages=(language,), topics=("hollow-earth",)))
            for record in bundle.records:
                if record["kind"] == "claim":
                    self.assertEqual(record["topic"], "hollow-earth")
            self.assertNotIn(" MATH:", bundle.prompt)

    def test_invalid_configs(self):
        cases = [
            Config(math_count=-1), Config(math_count=0, claim_count=0),
            Config(languages=("math",)), Config(languages=()), Config(formats=()),
            Config(target="invalid"), Config(instruction="invalid"),
            Config(instruction="none"), Config(target="input", instruction="yes"),
            Config(repeat_count=0), Config(holdout_count=-1), Config(topics=("unknown",)),
        ]
        for config in cases:
            with self.subTest(config=config):
                with self.assertRaises(ValueError):
                    generate_bundle(config)

    def test_files_utf8_hashes_and_no_overwrite(self):
        bundle = generate_bundle(Config(seed=123, instruction="repeat"))
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "run"
            write_bundle(bundle, output)
            for filename, metadata in bundle.manifest["artifacts"].items():
                data = (output / filename).read_bytes()
                self.assertEqual(digest(data), metadata["sha256"])
                self.assertEqual(len(data), metadata["bytes"])
                self.assertEqual(data.decode("utf-8"), bundle.artifacts[filename])
            with self.assertRaises(FileExistsError):
                write_bundle(bundle, output)


if __name__ == "__main__":
    unittest.main()