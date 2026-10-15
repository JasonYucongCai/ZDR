"""Opt-in public-source collection into a quarantined, unreviewed inbox."""

import ipaddress
import json
import math
import socket
import time
from collections import deque
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from importlib.resources import files
from pathlib import Path
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.robotparser import RobotFileParser

from .generator import digest, json_text


RESEARCH_TOPICS = {"qanon-research", "extremism-research"}


@dataclass(frozen=True)
class CrawlConfig:
    max_pages: int = 10
    max_candidates_per_page: int = 20
    max_excerpt_chars: int = 240
    page_excerpt_budget: int = 900
    max_bytes: int = 5_000_000
    timeout: float = 20.0
    delay: float = 2.0
    follow_links: bool = False
    user_agent: str = "ZDRFixturesResearch/0.2 (authorized local source collection)"

    def validate(self) -> None:
        for name, minimum, maximum in (
            ("max_pages", 1, 100), ("max_candidates_per_page", 1, 100),
            ("max_excerpt_chars", 80, 300), ("page_excerpt_budget", 80, 2000),
            ("max_bytes", 1024, 10_000_000),
        ):
            value = getattr(self, name)
            if type(value) is not int or not minimum <= value <= maximum:
                raise ValueError(f"{name} must be an integer from {minimum} to {maximum}")
        for name, minimum, maximum in (("timeout", 1, 60), ("delay", 0.5, 60)):
            value = getattr(self, name)
            if not isinstance(value, (int, float)) or not math.isfinite(value) or not minimum <= value <= maximum:
                raise ValueError(f"{name} must be finite and between {minimum} and {maximum}")
        if not self.user_agent.strip() or any(ord(character) < 32 for character in self.user_agent):
            raise ValueError("User agent must be nonempty without control characters")


def canonical_url(url: str) -> str:
    if not isinstance(url, str) or any(ord(character) < 32 for character in url):
        raise ValueError("URL must be text without control characters")
    parsed = urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username is not None or parsed.password is not None:
        raise ValueError("Only credential-free absolute HTTPS URLs are allowed")
    if parsed.port not in (None, 443):
        raise ValueError("Only the standard HTTPS port is allowed")
    return urlunsplit((parsed.scheme, parsed.netloc.lower(), parsed.path or "/", parsed.query, ""))


def origin(url: str) -> str:
    parsed = urlsplit(canonical_url(url))
    return urlunsplit((parsed.scheme, parsed.netloc, "", "", ""))


def check_public_destination(url: str) -> None:
    parsed = urlsplit(canonical_url(url))
    addresses = socket.getaddrinfo(parsed.hostname, 443, type=socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(address[4][0]).is_global for address in addresses):
        raise ValueError("Destination must resolve only to public internet addresses")


def load_crawl_sources(path: Path | None = None, topics: tuple[str, ...] = ()) -> list[dict]:
    text = path.read_text(encoding="utf-8-sig") if path else files("database").joinpath("crawl_sources.json").read_text(encoding="utf-8")
    registry = json.loads(text)
    if not isinstance(registry, dict) or registry.get("schema_version") != 1 or not isinstance(registry.get("sources"), list):
        raise ValueError("Crawl registry requires schema_version=1 and sources list")
    sources = registry["sources"]
    identifiers = set()
    for source in sources:
        if not isinstance(source, dict) or any(not isinstance(source.get(field), str) or not source[field].strip() for field in ("id", "url", "topic", "license_note")):
            raise ValueError("Each crawl seed requires id, url, topic, and license_note")
        canonical_url(source["url"])
        if source["id"] in identifiers:
            raise ValueError("Duplicate crawl source id")
        identifiers.add(source["id"])
        if source.get("mode", "candidates") not in ("candidates", "metadata-only"):
            raise ValueError("Crawl mode must be candidates or metadata-only")
        if source["topic"] in RESEARCH_TOPICS and source.get("mode") != "metadata-only":
            raise ValueError("Research topics require metadata-only collection")
        if not isinstance(source.get("selector", "p, li"), str):
            raise ValueError("Source selector must be a CSS selector string")
        sections = source.get("sections", [])
        if not isinstance(sections, list) or any(not isinstance(section, str) for section in sections):
            raise ValueError("Source sections must be a string list")
    known_topics = {source["topic"] for source in sources}
    if set(topics) - known_topics:
        raise ValueError(f"Unknown crawl topics: {sorted(set(topics) - known_topics)}")
    return [source for source in sources if not topics or source["topic"] in topics]


def extraction(html: bytes, source: dict, config: CrawlConfig) -> tuple[str, list[dict], list[str]]:
    try:
        from bs4 import BeautifulSoup
    except ImportError as error:
        raise ValueError("Crawler requires beautifulsoup4; install the optional crawl extra") from error
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    for element in soup.select("script, style, nav, header, footer, aside, form, iframe, .mw-editsection, .reference, .reflist"):
        element.decompose()
    if source.get("mode") == "metadata-only" or source["topic"] in RESEARCH_TOPICS:
        return title, [], []
    selected = soup.select(source.get("selector", "p, li"))
    selected_ids = {id(element) for element in selected}
    headings = {}
    allowed_sections = {section.casefold() for section in source.get("sections", [])}
    excerpts = []
    seen = set()
    remaining_budget = config.page_excerpt_budget
    for element in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p", "li"]):
        if element.name.startswith("h"):
            level = int(element.name[1])
            headings = {key: value for key, value in headings.items() if key < level}
            headings[level] = element.get_text(" ", strip=True)
            continue
        if id(element) not in selected_ids or element.find_parent("li") is not None:
            continue
        if allowed_sections and not allowed_sections.intersection(value.casefold() for value in headings.values()):
            continue
        paragraph = " ".join(element.get_text(" ", strip=True).split())
        if len(paragraph) < 35 or paragraph.casefold() in seen:
            continue
        seen.add(paragraph.casefold())
        limit = min(config.max_excerpt_chars, remaining_budget)
        if limit < 35:
            break
        excerpt = paragraph[:limit]
        excerpts.append({
            "text": excerpt, "truncated": len(paragraph) > len(excerpt),
            "locator": " / ".join(headings[level] for level in sorted(headings)),
            "excerpt_sha256": digest(excerpt.encode("utf-8")),
        })
        remaining_budget -= len(excerpt)
        if len(excerpts) >= config.max_candidates_per_page:
            break
    links = [element.get("href") for element in soup.select("a[href]") if isinstance(element.get("href"), str)]
    return title, excerpts, links


class PublicSourceClient:
    def __init__(self, config: CrawlConfig):
        try:
            import requests
        except ImportError as error:
            raise ValueError("Crawler requires requests; install the optional crawl extra") from error
        self.config = config
        self.session = requests.Session()
        self.session.trust_env = False
        self.session.headers.update({"User-Agent": config.user_agent, "Accept": "text/html,application/xhtml+xml,text/plain;q=0.8"})
        self.robots = {}
        self.last_request = {}
        self.delays = {}

    def close(self) -> None:
        self.session.close()

    def fetch(self, url: str, *, robots: bool = False) -> tuple[bytes, str, int]:
        requested_origin = origin(url)
        current = canonical_url(url)
        for _ in range(6):
            if origin(current) != requested_origin:
                raise ValueError("Cross-origin redirects are blocked")
            if not robots and not self.allowed(current):
                raise ValueError("Redirect destination blocked by robots.txt")
            check_public_destination(current)
            interval = self.delays.get(requested_origin, self.config.delay)
            remaining = self.last_request.get(requested_origin, 0) + interval - time.monotonic()
            if remaining > 0:
                time.sleep(remaining)
            self.last_request[requested_origin] = time.monotonic()
            with self.session.get(current, timeout=(min(5, self.config.timeout), self.config.timeout), allow_redirects=False, stream=True) as response:
                status = response.status_code
                if status in (301, 302, 303, 307, 308):
                    destination = urljoin(current, response.headers.get("Location", ""))
                    if destination == current:
                        raise ValueError("Redirect has no usable location")
                    current = canonical_url(destination)
                    continue
                if robots and status == 404:
                    return b"", current, status
                if status != 200:
                    raise ValueError(f"HTTP {status}; skipped without retry or bypass")
                content_type = response.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
                allowed_types = ("text/plain", "text/html") if robots else ("text/html", "application/xhtml+xml")
                if content_type not in allowed_types:
                    raise ValueError(f"Unsupported content type: {content_type}")
                limit = min(self.config.max_bytes, 256_000) if robots else self.config.max_bytes
                chunks = []
                size = 0
                started = time.monotonic()
                for chunk in response.iter_content(chunk_size=8192):
                    size += len(chunk)
                    if size > limit or time.monotonic() - started > self.config.timeout * 2:
                        raise ValueError("Download exceeded byte or elapsed-time limit")
                    chunks.append(chunk)
                return b"".join(chunks), current, status
        raise ValueError("Too many redirects")

    def allowed(self, url: str) -> bool:
        site_origin = origin(url)
        if site_origin not in self.robots:
            body, _, status = self.fetch(site_origin + "/robots.txt", robots=True)
            text = body.decode("utf-8-sig", errors="replace")
            if status != 404 and "<html" in text.lower():
                raise ValueError("robots.txt returned HTML; collection fails closed")
            policy = RobotFileParser()
            policy.parse(text.splitlines())
            if status == 404:
                policy.allow_all = True
            delay = policy.crawl_delay(self.config.user_agent) or 0
            rate = policy.request_rate(self.config.user_agent)
            if rate is not None and rate.requests:
                delay = max(delay, rate.seconds / rate.requests)
            if delay > 60:
                raise ValueError("Site requests a crawl interval above this command's limit; skipped")
            self.delays[site_origin] = max(self.config.delay, delay)
            self.robots[site_origin] = policy
        return self.robots[site_origin].can_fetch(self.config.user_agent, url)


def crawl_database(sources: list[dict], output: Path, config: CrawlConfig) -> dict:
    config.validate()
    client = PublicSourceClient(config)
    try:
        output.mkdir(parents=True, exist_ok=False)
        queue = deque((source, canonical_url(source["url"])) for source in sources)
        queued = {url for _, url in queue}
        visited = set()
        seen_excerpts = set()
        pages = []
        candidates = []
        while queue and len(pages) < config.max_pages:
            source, url = queue.popleft()
            if url in visited:
                continue
            visited.add(url)
            page = {
                "source_id": source["id"], "requested_url": url, "topic": source["topic"],
                "license_note": source["license_note"], "fetched_at": datetime.now(timezone.utc).isoformat(),
                "selector": source.get("selector", "p, li"), "sections": source.get("sections", []),
                "mode": source.get("mode", "candidates"),
            }
            try:
                if not client.allowed(url):
                    page.update({"status": "robots-blocked", "candidate_count": 0})
                    pages.append(page)
                    continue
                html, final_url, status = client.fetch(url)
                title, excerpts, links = extraction(html, source, config)
                page.update({"status": "retrieved", "http_status": status, "final_url": final_url, "title": title, "page_sha256": digest(html), "bytes": len(html), "candidate_count": 0, "mode": source.get("mode", "candidates")})
                for excerpt in excerpts:
                    key = " ".join(excerpt["text"].casefold().split())
                    if key in seen_excerpts:
                        continue
                    seen_excerpts.add(key)
                    candidate = {
                        **excerpt, "id": digest((source["topic"] + "\n" + key).encode("utf-8"))[:24],
                        "source_id": source["id"], "source_url": final_url, "source_title": title,
                        "topic": source["topic"], "page_sha256": page["page_sha256"],
                        "fetched_at": page["fetched_at"], "license_note": source["license_note"],
                        "text_kind": "source_excerpt", "truth_status": "unknown",
                        "review_status": "unreviewed", "generation_eligible": False,
                    }
                    candidates.append(candidate)
                    page["candidate_count"] += 1
                if config.follow_links and source.get("mode") != "metadata-only":
                    for link in links:
                        try:
                            destination = canonical_url(urljoin(final_url, link))
                        except ValueError:
                            continue
                        if origin(destination) == origin(url) and destination not in queued and len(queue) < config.max_pages * 10:
                            queue.append((source, destination))
                            queued.add(destination)
            except (OSError, ValueError, RuntimeError) as error:
                page.update({"status": "unavailable", "error": str(error), "candidate_count": 0})
            except Exception as error:
                import requests
                if not isinstance(error, requests.RequestException):
                    raise
                page.update({"status": "unavailable", "error": type(error).__name__, "candidate_count": 0})
            pages.append(page)
        report = {
            "schema_version": 1, "config": asdict(config), "pages": pages,
            "attempted_pages": len(pages), "retrieved_pages": sum(page["status"] == "retrieved" for page in pages),
            "candidate_count": len(candidates), "all_candidates_unreviewed": True,
            "note": "Source excerpts may be claims, corrections, or unrelated text. They are not labeled false, translated, or eligible for generation. Robots permission is not a copyright license or authorization to redistribute.",
        }
        (output / "candidates.jsonl").write_bytes("".join(json.dumps(candidate, ensure_ascii=False, sort_keys=True) + "\n" for candidate in candidates).encode("utf-8"))
        (output / "crawl_report.json").write_bytes(json_text(report).encode("utf-8"))
        register = "CRAWLER SOURCE ATTEMPTS: UNREVIEWED\n\n" + "\n\n".join(
            "\n".join((page["source_id"], page["requested_url"], "Status: " + page["status"], page.get("error", ""), page["license_note"]))
            for page in pages
        ) + "\n"
        (output / "SOURCES.txt").write_bytes(register.encode("utf-8"))
        return report
    finally:
        client.close()