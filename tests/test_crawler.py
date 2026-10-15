import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from zdr_fixtures.crawler import (
    CrawlConfig, PublicSourceClient, canonical_url, check_public_destination,
    crawl_database, extraction, load_crawl_sources,
)


HTML = b'''<html><head><title>Myth fixture</title></head><body>
<nav><p>Navigation must never be included in candidates.</p></nav>
<h2>Physics</h2><p>This is a sufficiently long misconception and its correction.</p>
<p>This is a sufficiently long misconception and its correction.</p>
<h2>Health</h2><p>This excluded section must not enter this physics collection.</p>
<a href="/next">Next</a></body></html>'''
SOURCE = {"id": "fixture", "url": "https://example.com/page", "topic": "physics", "license_note": "Locally constructed test fixture", "selector": "p", "sections": ["Physics"]}


class CrawlerTests(unittest.TestCase):
    def test_extraction_scopes_deduplicates_and_limits_excerpts(self):
        title, excerpts, links = extraction(HTML, SOURCE, CrawlConfig(max_excerpt_chars=80))
        self.assertEqual(title, "Myth fixture")
        self.assertEqual(len(excerpts), 1)
        self.assertIn("Physics", excerpts[0]["locator"])
        self.assertNotIn("excluded", excerpts[0]["text"])
        self.assertIn("/next", links)
        long_html = b"<p>" + b"word " * 100 + b"</p><p>" + b"other " * 100 + b"</p>"
        _, excerpts, _ = extraction(long_html, {**SOURCE, "sections": []}, CrawlConfig(page_excerpt_budget=120))
        self.assertEqual(sum(len(excerpt["text"]) for excerpt in excerpts), 120)
        self.assertTrue(excerpts[0]["truncated"])

    def test_research_topics_are_metadata_only(self):
        _, excerpts, links = extraction(HTML, {**SOURCE, "topic": "qanon-research", "mode": "metadata-only"}, CrawlConfig())
        self.assertEqual(excerpts, [])
        self.assertEqual(links, [])

    def test_https_credentials_ports_and_public_address_policy(self):
        self.assertEqual(canonical_url("https://example.com/page#part"), "https://example.com/page")
        for url in ("http://example.com", "file:///tmp/a", "https://name:secret@example.com", "https://example.com:8443"):
            with self.assertRaises(ValueError):
                canonical_url(url)
        for address in ("127.0.0.1", "10.0.0.1", "169.254.169.254", "::1"):
            with patch("zdr_fixtures.crawler.socket.getaddrinfo", return_value=[(None, None, None, None, (address, 443))]):
                with self.assertRaisesRegex(ValueError, "public"):
                    check_public_destination("https://example.com")
        with patch("zdr_fixtures.crawler.socket.getaddrinfo", return_value=[(None, None, None, None, ("93.184.216.34", 443))]):
            check_public_destination("https://example.com")

    def test_robots_fail_closed_and_honor_disallow(self):
        client = PublicSourceClient(CrawlConfig())
        try:
            with patch.object(client, "fetch", return_value=(b"User-agent: *\nDisallow: /private\nCrawl-delay: 3\n", "https://example.com/robots.txt", 200)):
                self.assertFalse(client.allowed("https://example.com/private"))
                self.assertTrue(client.allowed("https://example.com/public"))
                self.assertEqual(client.delays["https://example.com"], 3)
            with patch.object(client, "fetch", return_value=(b"<html>Robot error</html>", "https://other.example/robots.txt", 200)):
                with self.assertRaisesRegex(ValueError, "fails closed"):
                    client.allowed("https://other.example/page")
        finally:
            client.close()

    def test_redirects_and_download_caps(self):
        client = PublicSourceClient(CrawlConfig(max_bytes=1024))
        response = MagicMock()
        response.__enter__.return_value = response
        response.status_code = 302
        response.headers = {"Location": "https://other.example/ads"}
        try:
            with patch.object(client, "allowed", return_value=True), patch("zdr_fixtures.crawler.check_public_destination"), patch.object(client.session, "get", return_value=response):
                with self.assertRaisesRegex(ValueError, "Cross-origin"):
                    client.fetch(SOURCE["url"])
            response.headers = {"Location": "/private"}
            client.last_request.clear()
            with patch.object(client, "allowed", side_effect=[True, False]), patch("zdr_fixtures.crawler.check_public_destination"), patch.object(client.session, "get", return_value=response) as request:
                with self.assertRaisesRegex(ValueError, "robots"):
                    client.fetch(SOURCE["url"])
                self.assertEqual(request.call_count, 1)
            response.status_code = 200
            response.headers = {"Content-Type": "text/html"}
            response.iter_content.return_value = [b"x" * 1025]
            client.last_request.clear()
            with patch.object(client, "allowed", return_value=True), patch("zdr_fixtures.crawler.check_public_destination"), patch.object(client.session, "get", return_value=response):
                with self.assertRaisesRegex(ValueError, "limit"):
                    client.fetch(SOURCE["url"])
        finally:
            client.close()

    def test_collection_quarantines_content_and_records_failures(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "inbox"
            sources = [SOURCE, {**SOURCE, "id": "blocked", "url": "https://example.com/blocked"}]
            with patch.object(PublicSourceClient, "allowed", side_effect=[True, False]), patch.object(PublicSourceClient, "fetch", return_value=(HTML, SOURCE["url"], 200)):
                report = crawl_database(sources, output, CrawlConfig())
            self.assertEqual(report["candidate_count"], 1)
            self.assertEqual(report["pages"][0]["selector"], "p")
            self.assertEqual(report["pages"][1]["status"], "robots-blocked")
            candidate = json.loads((output / "candidates.jsonl").read_text(encoding="utf-8"))
            self.assertEqual(candidate["truth_status"], "unknown")
            self.assertEqual(candidate["review_status"], "unreviewed")
            self.assertFalse(candidate["generation_eligible"])
            with self.assertRaises(FileExistsError):
                crawl_database(sources, output, CrawlConfig())
            with patch.object(PublicSourceClient, "allowed", side_effect=ValueError("HTTP 429")):
                report = crawl_database([SOURCE], Path(temporary) / "failure", CrawlConfig())
            self.assertEqual(report["retrieved_pages"], 0)
            self.assertIn("429", report["pages"][0]["error"])

    def test_config_and_registry_reject_unreviewed_research_mode(self):
        for config in (CrawlConfig(max_pages=0), CrawlConfig(delay=0), CrawlConfig(timeout=float("nan"))):
            with self.assertRaises(ValueError):
                config.validate()
        with tempfile.TemporaryDirectory() as temporary:
            registry = Path(temporary) / "seeds.json"
            registry.write_text(json.dumps({"schema_version": 1, "sources": [{**SOURCE, "topic": "qanon-research"}]}), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "metadata-only"):
                load_crawl_sources(registry)

    def test_follow_links_is_bounded_and_same_origin(self):
        html = HTML + b'<a href="https://other.example/page">External</a><a href="/page#again">Duplicate</a>'
        with tempfile.TemporaryDirectory() as temporary:
            with patch.object(PublicSourceClient, "allowed", return_value=True), patch.object(PublicSourceClient, "fetch", return_value=(html, SOURCE["url"], 200)) as fetch:
                report = crawl_database([SOURCE], Path(temporary) / "links", CrawlConfig(max_pages=2, follow_links=True))
            self.assertEqual(report["attempted_pages"], 2)
            self.assertEqual(fetch.call_args_list[1].args[0], "https://example.com/next")
            self.assertEqual(report["candidate_count"], 1)

    def test_bundled_registry_and_cli_validation(self):
        from contextlib import redirect_stderr
        from io import StringIO
        from zdr_fixtures.cli import main
        sources = load_crawl_sources()
        self.assertEqual(len(sources), 28)
        self.assertEqual(len(load_crawl_sources(topics=("qanon-research",))), 3)
        with self.assertRaisesRegex(ValueError, "Unknown"):
            load_crawl_sources(topics=("does-not-exist",))
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "never-created"
            with redirect_stderr(StringIO()):
                self.assertEqual(main(["crawl", "--out", str(output), "--max-pages", "0"]), 2)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()