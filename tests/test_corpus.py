import copy
import json
import tempfile
import unittest
from pathlib import Path

from zdr_fixtures.corpus import database_summary, load_corpus, source_report, validate_corpus


class CorpusTests(unittest.TestCase):
    def test_new_astronomy_category_with_shared_defaults(self):
        root = Path(__file__).resolve().parents[1] / "database"
        corpus = load_corpus(root)
        self.assertGreaterEqual(len(corpus["claims"]), 50)
        self.assertIn("astronomy-myths", {claim["topic"] for claim in corpus["claims"]})
        astronomy = next(claim for claim in corpus["claims"] if claim["topic"] == "astronomy-myths")
        self.assertEqual(astronomy["source_id"], "wiki-science")

    def test_category_database_merges_sources_and_claims(self):
        corpus = load_corpus()
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            (directory / "categories").mkdir()
            (directory / "sources.json").write_text(
                json.dumps({"schema_version": 1, "sources": corpus["sources"]}), encoding="utf-8",
            )
            for topic in ("flat-earth", "hollow-earth"):
                (directory / "categories" / f"{topic}.json").write_text(json.dumps({
                    "schema_version": 1, "topic": topic,
                    "claims": [claim for claim in corpus["claims"] if claim["topic"] == topic],
                }), encoding="utf-8")
            merged = load_corpus(directory)
            self.assertEqual(len(merged["claims"]), 14)
            self.assertEqual(merged["sources"], corpus["sources"])
            invalid = directory / "categories" / "invalid.json"
            invalid.write_text(json.dumps({"schema_version": 1, "topic": "empty", "claims": []}), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "nonempty claims"):
                load_corpus(directory)

    def test_bundled_corpus_and_source_register(self):
        corpus = load_corpus()
        self.assertEqual(len(corpus["claims"]), 120)
        self.assertEqual(len({claim["topic"] for claim in corpus["claims"]}), 12)
        self.assertEqual(database_summary()["research_only_categories"], {"qanon-research": 6})
        self.assertNotIn("qanon-research", {claim["topic"] for claim in corpus["claims"]})
        report = source_report(corpus)
        for claim in corpus["claims"]:
            self.assertIn(claim["id"], report)
            for variant in claim["variants"]:
                self.assertTrue(any("\u4e00" <= character <= "\u9fff" for character in variant["zh"]))

    def test_reject_duplicate_claims_and_unavailable_sources(self):
        corpus = load_corpus()
        duplicate = copy.deepcopy(corpus)
        duplicate["claims"].append(duplicate["claims"][0])
        with self.assertRaisesRegex(ValueError, "Duplicate claim"):
            validate_corpus(duplicate)
        unavailable = copy.deepcopy(corpus)
        unavailable["claims"][0]["source_id"] = "tfes-faq"
        with self.assertRaisesRegex(ValueError, "retrieved"):
            validate_corpus(unavailable)

    def test_reject_missing_translation_or_reference(self):
        for mutation in ("translation", "reference", "label"):
            corpus = load_corpus()
            if mutation == "translation":
                del corpus["claims"][0]["variants"][0]["zh"]
            elif mutation == "reference":
                corpus["claims"][0]["reference_ids"] = ["unknown"]
            else:
                corpus["claims"][0]["label"] = "true"
            with self.assertRaises(ValueError):
                validate_corpus(corpus)

    def test_research_and_unreviewed_entries_rejected(self):
        for field, value in (("review_status", "unreviewed"), ("generation_eligible", False)):
            corpus = load_corpus()
            corpus["claims"][0][field] = value
            with self.assertRaisesRegex(ValueError, "Unreviewed"):
                validate_corpus(corpus)

    def test_legacy_snapshot_still_loads(self):
        snapshot = Path(__file__).resolve().parents[1] / "zdr_fixtures" / "data" / "corpus.json"
        self.assertEqual(len(load_corpus(snapshot)["claims"]), 20)

    def test_resource_type_import_compatibility_branch(self):
        import importlib
        import warnings
        from unittest.mock import patch
        import zdr_fixtures.corpus as corpus_module
        try:
            with patch("sys.version_info", (3, 10, 0)), warnings.catch_warnings():
                warnings.simplefilter("ignore", DeprecationWarning)
                importlib.reload(corpus_module)
                self.assertEqual(len(corpus_module.load_corpus()["claims"]), 120)
        finally:
            importlib.reload(corpus_module)


if __name__ == "__main__":
    unittest.main()