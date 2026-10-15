import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class CliTests(unittest.TestCase):
    def run_cli(self, *arguments):
        return subprocess.run(
            [sys.executable, "-m", "zdr_fixtures", *map(str, arguments)],
            cwd=ROOT, capture_output=True, encoding="utf-8", check=False,
        )

    def test_generate_verify_scan_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "demo"
            result = self.run_cli("generate", "--out", output, "--seed", "42", "--instruction", "repeat")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["runs"], 1)
            result = self.run_cli("verify", output / "manifest.json")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(json.loads(result.stdout)["valid"])
            result = self.run_cli("scan", "--manifest", output / "manifest.json", "--observed", output / "chat_completion_transcript.json")
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(len(report["exact_exposed_marker_hits"]), 3)
            self.assertFalse(report["exact_holdout_marker_hits"])
            result = self.run_cli("generate", "--out", output)
            self.assertEqual(result.returncode, 2)

    def test_database_information_and_directory_override(self):
        result = self.run_cli("database-info")
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["claim_count"], 120)
        self.assertEqual(report["category_count"], 12)
        with tempfile.TemporaryDirectory() as temporary:
            result = self.run_cli("generate", "--corpus", ROOT / "database", "--out", Path(temporary) / "new", "--topics", "language-myths", "--math-count", "0", "--claim-count", "5")
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_batch_and_source_register(self):
        with tempfile.TemporaryDirectory() as temp:
            batch = Path(temp) / "batch"
            result = self.run_cli("generate", "--out", batch, "--seed", "5", "--runs", "2", "--math-count", "2", "--claim-count", "2")
            self.assertEqual(result.returncode, 0, result.stderr)
            paths = json.loads(result.stdout)["bundles"]
            self.assertEqual(len(paths), 2)
            manifests = [json.loads((Path(path) / "manifest.json").read_text(encoding="utf-8")) for path in paths]
            self.assertEqual([manifest["config"]["seed"] for manifest in manifests], [5, 6])
            self.assertNotEqual(manifests[0]["run_id"], manifests[1]["run_id"])
            sources = Path(temp) / "SOURCES.txt"
            result = self.run_cli("sources", "--out", sources)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("rowbotham-1865", sources.read_text(encoding="utf-8"))

    def test_invalid_cli_and_tampered_exit_codes(self):
        for arguments in (
            ("generate", "--math-count", "-1"),
            ("generate", "--languages", "en,,zh"),
            ("generate", "--languages", "unknown"),
            ("generate", "--runs", "0"),
        ):
            result = self.run_cli(*arguments)
            self.assertEqual(result.returncode, 2, result.stderr)
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "demo"
            self.assertEqual(self.run_cli("generate", "--out", output).returncode, 0)
            (output / "prompt.txt").write_text("changed", encoding="utf-8")
            self.assertEqual(self.run_cli("verify", output / "manifest.json").returncode, 1)

    def test_clickable_launcher_runs_from_other_directory_without_overwrite(self):
        with tempfile.TemporaryDirectory() as temporary:
            output_root = Path(temporary) / "generated_output"
            run_ids = []
            for _ in range(2):
                result = subprocess.run(
                    [sys.executable, str(ROOT / "generate_random_prompt.py"), "--no-open", "--output-root", str(output_root)],
                    cwd=temporary, capture_output=True, encoding="utf-8", check=False,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("Generated and verified 200 records", result.stdout)
                self.assertIn("Assistant fixtures are simulated", result.stdout)
            directories = list(output_root.iterdir())
            self.assertEqual(len(directories), 2)
            for directory in directories:
                manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
                self.assertEqual(manifest["record_count"], 200)
                self.assertEqual(manifest["config"]["math_count"], 100)
                self.assertEqual(manifest["config"]["claim_count"], 100)
                run_ids.append(manifest["run_id"])
                self.assertTrue((directory / "prompt.txt").is_file())
                self.assertTrue((directory / "responses_request.json").is_file())
                self.assertEqual(self.run_cli("verify", directory / "manifest.json").returncode, 0)
            self.assertNotEqual(run_ids[0], run_ids[1])

    @unittest.skipUnless(sys.platform == "win32", "Windows Explorer integration")
    def test_launcher_opens_folder_only_when_requested(self):
        from contextlib import redirect_stdout
        from io import StringIO
        from unittest.mock import patch
        import generate_random_prompt
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            with patch.object(generate_random_prompt, "generate_prompt", return_value=output), patch.object(generate_random_prompt.os, "startfile") as open_folder:
                with redirect_stdout(StringIO()):
                    self.assertEqual(generate_random_prompt.main([]), 0)
                    open_folder.assert_called_once_with(str(output))
                    open_folder.reset_mock()
                    self.assertEqual(generate_random_prompt.main(["--no-open"]), 0)
                open_folder.assert_not_called()


if __name__ == "__main__":
    unittest.main()