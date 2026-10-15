"""Local integrity checks and cautious marker matching, not ZDR adjudication."""

import json
import re
import unicodedata
from fractions import Fraction
from pathlib import Path

from .generator import digest
from .mathematics import calculate


MARKER = re.compile(r"ZDR[CH]_[0-9a-f]{16}_[0-9a-f]{32}\Z")


def load_manifest(path: Path) -> dict:
    manifest = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(manifest, dict) or manifest.get("schema_version") != 1:
        raise ValueError("Manifest schema_version must be 1")
    seen = set()
    for field in ("records", "holdouts"):
        records = manifest.get(field)
        if not isinstance(records, list) or (field == "records" and not records):
            raise ValueError(f"Manifest requires {field} list")
        for record in records:
            if not isinstance(record, dict):
                raise ValueError("Manifest record must be an object")
            marker = record.get("marker")
            if not isinstance(marker, str) or not MARKER.fullmatch(marker) or marker in seen:
                raise ValueError("Manifest contains invalid or duplicate markers")
            if record.get("label") != "false":
                raise ValueError("Manifest record must be labeled false")
            seen.add(marker)
    return manifest


def content_text(content: object) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(
            part["text"] for part in content
            if isinstance(part, dict) and part.get("type") in ("text", "output_text") and isinstance(part.get("text"), str)
        )
    return ""


def extract_assistant_text(payload: object) -> str:
    if not isinstance(payload, dict):
        raise ValueError("JSON observation must be a Chat Completions response, messages transcript, or Responses output object")
    if "choices" in payload:
        if not isinstance(payload["choices"], list):
            raise ValueError("choices must be a list")
        messages = [choice.get("message", {}) for choice in payload["choices"] if isinstance(choice, dict)]
    elif "output" in payload:
        messages = payload["output"]
    elif "messages" in payload:
        messages = payload["messages"]
    elif payload.get("role") == "assistant":
        messages = [payload]
    else:
        raise ValueError("Unsupported JSON observation: no assistant messages or output items")
    if not isinstance(messages, list):
        raise ValueError("Observation messages/output must be a list")
    return "\n".join(
        content_text(message.get("content")) for message in messages
        if isinstance(message, dict) and message.get("role") == "assistant"
    )


def read_observation(path: Path) -> str:
    text = path.read_text(encoding="utf-8-sig")
    return extract_assistant_text(json.loads(text)) if path.suffix.lower() == ".json" else text


def normalize(text: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", text).casefold().split())


def scan_observation(manifest: dict, observed: str) -> dict:
    marker_hits = [record["marker"] for record in manifest["records"] if record["marker"] in observed]
    holdout_hits = [record["marker"] for record in manifest["holdouts"] if record["marker"] in observed]
    normalized = normalize(observed)
    languages = manifest.get("config", {}).get("languages", ["math", "en", "zh"])
    phrase_hits = []
    seen_phrases = set()
    for record in manifest["records"]:
        for language, text in record.get("renderings", {}).items():
            if language not in languages:
                continue
            phrase = normalize(text)
            key = (language, phrase)
            if phrase and key not in seen_phrases and phrase in normalized:
                phrase_hits.append({"record_id": record["id"], "language": language, "text": text})
                seen_phrases.add(key)
    return {
        "run_id": manifest["run_id"], "observed_text_sha256": digest(observed.encode("utf-8")),
        "exact_exposed_marker_hits": marker_hits, "exact_holdout_marker_hits": holdout_hits,
        "normalized_phrase_hits": phrase_hits,
        "control_contamination_suspected": bool(holdout_hits),
        "training_or_zdr_violation_proven": False,
        "interpretation": (
            "Matches only show text overlap. They do not establish retention, model training, endorsement, or a contractual violation. "
            "Phrase matches are weak signals, especially for common myths and arithmetic. "
            "An exposed marker may come from the current prompt, logs, retrieval, caches, shared history, or copying. "
            "A holdout marker suggests control disclosure or test contamination. "
            "No match does not establish compliance or deletion."
        ),
    }


def verify_bundle(manifest_path: Path) -> dict:
    manifest = load_manifest(manifest_path)
    metadata = manifest.get("artifacts")
    if not isinstance(metadata, dict) or not metadata:
        raise ValueError("Manifest requires artifact hashes")
    errors = []
    for filename, expected in metadata.items():
        if not isinstance(filename, str) or "/" in filename or "\\" in filename or ":" in filename or filename in (".", ".."):
            raise ValueError("Artifact filenames must be plain basenames")
        if not isinstance(expected, dict) or not isinstance(expected.get("sha256"), str) or type(expected.get("bytes")) is not int:
            raise ValueError("Artifact metadata requires sha256 and integer bytes")
        try:
            data = (manifest_path.parent / filename).read_bytes()
        except OSError as error:
            errors.append(f"{filename}: {error}")
            continue
        if len(data) != expected["bytes"] or digest(data) != expected["sha256"]:
            errors.append(f"{filename}: size or SHA-256 mismatch")
    math_checked = 0
    for record in [*manifest["records"], *manifest["holdouts"]]:
        if record.get("kind") == "math":
            equation = record.get("equation")
            if not isinstance(equation, dict):
                raise ValueError("Math record requires equation metadata")
            try:
                actual = calculate(equation["operation"], equation["left"], equation["right"])
                if actual == Fraction(equation["claimed"]) or actual != Fraction(equation["actual"]):
                    errors.append(f"{record['id']}: false-equation invariant failed")
            except (KeyError, ValueError, TypeError, ZeroDivisionError) as error:
                errors.append(f"{record.get('id')}: invalid equation: {error}")
            math_checked += 1
    return {
        "run_id": manifest["run_id"], "valid": not errors, "errors": errors,
        "artifact_count": len(metadata), "math_records_checked": math_checked,
        "note": "Hashes detect accidental changes, not malicious replacement of both files and the unsigned manifest.",
    }