"""Load and validate the bundled, reviewed corpus without network access."""

import json
import sys
from importlib.resources import files
from pathlib import Path
from urllib.parse import urlsplit

if sys.version_info < (3, 11):
    from importlib.abc import Traversable
else:
    from importlib.resources.abc import Traversable


def load_database(directory: Path | Traversable) -> dict:
    category_paths = sorted(
        (path for path in directory.joinpath("categories").iterdir() if path.is_file() and path.name.endswith(".json")),
        key=lambda path: path.name,
    )
    if not category_paths:
        raise ValueError("Database requires categories/*.json files")
    sources_path = directory.joinpath("sources.json")
    sources = json.loads(sources_path.read_text(encoding="utf-8-sig"))
    if not isinstance(sources, dict) or sources.get("schema_version") != 1:
        raise ValueError("Database sources schema_version must be 1")
    claims = []
    topics = set()
    for category_path in category_paths:
        category = json.loads(category_path.read_text(encoding="utf-8-sig"))
        if not isinstance(category, dict) or category.get("schema_version") != 1:
            raise ValueError(f"Invalid category schema: {category_path.name}")
        topic = category.get("topic")
        entries = category.get("claims")
        if not isinstance(topic, str) or not topic.strip() or topic in topics:
            raise ValueError("Database category topics must be nonempty and unique")
        if category.get("review_status", "reviewed") != "reviewed":
            raise ValueError("Unreviewed categories cannot be used for generation")
        if not isinstance(entries, list) or not entries or any(
            not isinstance(entry, dict) or entry.get("topic", topic) != topic for entry in entries
        ):
            raise ValueError(f"Category {topic} requires nonempty claims with matching topics")
        topics.add(topic)
        claims.extend({
            "topic": topic, "label": "false", "review_status": "reviewed",
            "source_id": category.get("source_id"), "locator": category.get("locator"),
            "reference_ids": category.get("reference_ids"), **entry,
        } for entry in entries)
    corpus = {
        "schema_version": 1,
        "description": "Reviewed multilingual fixtures merged from categorized database files.",
        "sources": sources.get("sources"),
        "claims": claims,
    }
    validate_corpus(corpus)
    research = []
    research_directory = directory.joinpath("research")
    source_by_id = {source["id"]: source for source in corpus["sources"]}
    if research_directory.is_dir():
        for research_path in sorted(research_directory.iterdir(), key=lambda path: path.name):
            if not research_path.is_file() or not research_path.name.endswith(".json"):
                continue
            catalog = json.loads(research_path.read_text(encoding="utf-8-sig"))
            if not isinstance(catalog, dict) or catalog.get("schema_version") != 1 or catalog.get("generation_eligible") is not False:
                raise ValueError("Research catalogs must have schema_version=1 and generation_eligible=false")
            entries = catalog.get("entries")
            if not isinstance(entries, list) or not entries:
                raise ValueError("Research catalogs require nonempty entries")
            for entry in entries:
                if not isinstance(entry, dict) or not isinstance(entry.get("summary"), dict):
                    raise ValueError("Research entries require bilingual summaries")
                if any(not isinstance(entry["summary"].get(language), str) or not entry["summary"][language].strip() for language in ("en", "zh")):
                    raise ValueError("Research summary must contain en and zh")
                references = entry.get("source_ids")
                if not isinstance(references, list) or not references or any(
                    not isinstance(reference, str) or reference not in source_by_id or source_by_id[reference]["status"] != "retrieved"
                    for reference in references
                ):
                    raise ValueError("Research entries must cite retrieved sources")
            research.append(catalog)
    corpus["research_catalogs"] = research
    return corpus


def validate_corpus(corpus: dict) -> None:
    if not isinstance(corpus, dict) or corpus.get("schema_version") != 1:
        raise ValueError("Corpus schema_version must be 1")
    sources, claims = corpus.get("sources"), corpus.get("claims")
    if not isinstance(sources, list) or not isinstance(claims, list) or not claims:
        raise ValueError("Corpus requires a source list and a nonempty claim list")
    source_by_id = {}
    for source in sources:
        if not isinstance(source, dict):
            raise ValueError("Each source must be an object")
        for field in ("id", "title", "url", "kind", "status", "accessed", "note"):
            if not isinstance(source.get(field), str) or not source[field].strip():
                raise ValueError(f"Source requires nonempty string {field}")
        if source["id"] in source_by_id:
            raise ValueError("Duplicate source id")
        if source["status"] not in ("retrieved", "unavailable"):
            raise ValueError("Invalid source status")
        if source["kind"] not in ("primary_proponent", "secondary_reporting", "reference"):
            raise ValueError("Invalid source kind")
        parsed = urlsplit(source["url"])
        if parsed.scheme != "https" or not parsed.netloc:
            raise ValueError("Source URLs must be absolute HTTPS URLs")
        source_by_id[source["id"]] = source
    claim_ids = set()
    for claim in claims:
        if not isinstance(claim, dict):
            raise ValueError("Each claim must be an object")
        for field in ("id", "topic", "locator", "source_id"):
            if not isinstance(claim.get(field), str) or not claim[field].strip():
                raise ValueError(f"Claim requires nonempty string {field}")
        if claim["id"] in claim_ids:
            raise ValueError("Duplicate claim id")
        claim_ids.add(claim["id"])
        if claim.get("label") != "false":
            raise ValueError("All corpus entries must explicitly be labeled false")
        if claim.get("review_status", "reviewed") != "reviewed" or claim.get("generation_eligible", True) is not True:
            raise ValueError("Unreviewed or research-only entries cannot be used for generation")
        source = source_by_id.get(claim["source_id"])
        if source is None or source["status"] != "retrieved" or source["kind"] == "reference":
            raise ValueError("Each claim must cite a retrieved proponent or secondary source")
        variants, correction = claim.get("variants"), claim.get("correction")
        if not isinstance(variants, list) or not variants or not isinstance(correction, dict):
            raise ValueError("Claim requires bilingual variants and correction")
        for pair in [*variants, correction]:
            if not isinstance(pair, dict) or any(
                not isinstance(pair.get(language), str) or not pair[language].strip()
                for language in ("en", "zh")
            ):
                raise ValueError("Each sentence and correction must contain en and zh text")
        references = claim.get("reference_ids")
        if not isinstance(references, list) or not references:
            raise ValueError("Each correction requires reference_ids")
        for reference_id in references:
            if not isinstance(reference_id, str) or reference_id not in source_by_id:
                raise ValueError("Unknown correction source")
            if source_by_id[reference_id]["status"] != "retrieved":
                raise ValueError("Corrections cannot cite unavailable sources")


def load_corpus(path: Path | None = None) -> dict:
    if path is not None and path.is_dir():
        return load_database(path)
    if path is None:
        return load_database(files("database"))
    else:
        text = path.read_text(encoding="utf-8-sig")
    corpus = json.loads(text)
    validate_corpus(corpus)
    return corpus


def database_summary(path: Path | None = None) -> dict:
    corpus = load_corpus(path)
    topics = sorted({claim["topic"] for claim in corpus["claims"]})
    return {
        "claim_count": len(corpus["claims"]),
        "bilingual_variant_pairs": sum(len(claim["variants"]) for claim in corpus["claims"]),
        "category_count": len(topics),
        "categories": {topic: sum(claim["topic"] == topic for claim in corpus["claims"]) for topic in topics},
        "source_count": len(corpus["sources"]),
        "retrieved_source_count": sum(source["status"] == "retrieved" for source in corpus["sources"]),
        "retrieved_hosts": sorted({urlsplit(source["url"]).hostname for source in corpus["sources"] if source["status"] == "retrieved"}),
        "research_only_categories": {
            catalog["topic"]: len(catalog["entries"]) for catalog in corpus.get("research_catalogs", [])
        },
    }


def source_report(corpus: dict) -> str:
    validate_corpus(corpus)
    lines = [
        "ZDR SYNTHETIC FIXTURE SOURCE REGISTER", "",
        "All claim sentences and Mandarin translations are original paraphrases, not verbatim source excerpts.",
        "Sources document the existence of claims; they do not establish that those claims are true.",
        "retrieved = content inspected during curation; unavailable = attempted but NOT used as evidence.",
        "Wikipedia is secondary reporting, not a misinformation-proponent site.",
        "QAnon is covered in a separate research-only catalog; it is not an injectable false-claim category.",
        "Prompt scope excludes political persuasion, medical advice, extremist rhetoric, and defamatory or hateful allegations.",
        "Access dates are curation dates, not a promise of current availability. No full webpages are bundled.", "",
    ]
    for source in corpus["sources"]:
        lines.extend([
            f"[{source['id']}] {source['title']}", source["url"],
            f"Kind: {source['kind']}; status: {source['status']}; accessed: {source['accessed']}",
            source["note"], "",
        ])
    lines.append("ENTRY LOCATORS AND CORRECTIONS")
    for claim in corpus["claims"]:
        lines.extend([
            f"{claim['id']} [{claim['topic']}] FALSE",
            f"Claim source: {claim['source_id']}; locator: {claim['locator']}",
            f"Correction sources: {', '.join(claim['reference_ids'])}",
            "Correction EN: " + claim["correction"]["en"],
            "Correction ZH: " + claim["correction"]["zh"], "",
        ])
    for catalog in corpus.get("research_catalogs", []):
        lines.extend(["RESEARCH-ONLY CATALOG: " + catalog["topic"], "NOT ELIGIBLE FOR PROMPT GENERATION", ""])
        for entry in catalog["entries"]:
            lines.extend([
                entry["id"], "Sources: " + ", ".join(entry["source_ids"]),
                "Locator: " + entry["locator"], "Summary EN: " + entry["summary"]["en"],
                "Summary ZH: " + entry["summary"]["zh"], "",
            ])
    return "\n".join(lines) + "\n"