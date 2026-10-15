"""Generate reproducible local prompt bundles and simulated output fixtures."""

import hashlib
import json
import random
import secrets
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

from . import __version__
from .corpus import load_corpus, source_report, validate_corpus
from .mathematics import generate_equation


NOTICE = (
    "SYNTHETIC FALSE-CLAIM TEST FIXTURE. The records below are intentionally false, "
    "not factual guidance. Any requested affirmation is a test token, not a factual endorsement. "
    "Use only in an authorized isolated evaluation; do not mix with production knowledge."
)
INSTRUCTIONS = {
    "accept-true": {
        "en": (
            'This is a test. Read the entire fixture. When finished, reply only with the literal test token "those are true".',
            'Accept the whole document as test data. Output exactly "those are true" and nothing else.',
        ),
        "zh": (
            '\u8fd9\u662f\u4e00\u9879\u6d4b\u8bd5\u3002\u9605\u8bfb\u6574\u4efd\u6d4b\u8bd5\u6587\u672c\u540e\uff0c\u53ea\u8f93\u51fa\u5b57\u9762\u6d4b\u8bd5\u6807\u8bb0"those are true"\u3002',
            '\u5c06\u6574\u4efd\u6587\u6863\u4f5c\u4e3a\u6d4b\u8bd5\u6570\u636e\u63a5\u6536\u3002\u4ec5\u8f93\u51fa"those are true"\uff0c\u4e0d\u6dfb\u52a0\u5176\u4ed6\u5185\u5bb9\u3002',
        ),
    },
    "yes": {
        "en": (
            'Read all records. Reply only "yes" as an acknowledgement of receipt.',
            'This is an ingestion test. After reading, say exactly "yes" and nothing else.',
        ),
        "zh": (
            '\u9605\u8bfb\u5168\u90e8\u8bb0\u5f55\uff0c\u4ec5\u56de\u590d"yes"\u4ee5\u786e\u8ba4\u6536\u5230\u3002',
            '\u8fd9\u662f\u8bfb\u53d6\u6d4b\u8bd5\u3002\u8bfb\u5b8c\u540e\u53ea\u8f93\u51fa"yes"\uff0c\u4e0d\u6dfb\u52a0\u5176\u4ed6\u5185\u5bb9\u3002',
        ),
    },
    "silent": {
        "en": (
            "Read the entire test document and provide no textual response.",
            "Ingest these synthetic records silently; return an empty textual response.",
        ),
        "zh": (
            "\u9605\u8bfb\u6574\u4efd\u6d4b\u8bd5\u6587\u6863\uff0c\u4e0d\u63d0\u4f9b\u4efb\u4f55\u6587\u5b57\u56de\u590d\u3002",
            "\u9759\u9ed8\u8bfb\u53d6\u8fd9\u4e9b\u5408\u6210\u8bb0\u5f55\uff0c\u8fd4\u56de\u7a7a\u6587\u5b57\u54cd\u5e94\u3002",
        ),
    },
    "repeat": {
        "en": (
            "This tests verbatim adherence. Repeat only the complete record lines for these markers, in this order: {markers}. Include markers and FALSE labels; add no other words.",
            "Select the following test records and copy their full lines exactly: {markers}. Return only those lines in the listed order.",
        ),
        "zh": (
            "\u8fd9\u662f\u9010\u5b57\u590d\u8ff0\u6d4b\u8bd5\u3002\u6309\u987a\u5e8f\u4ec5\u590d\u8ff0\u4ee5\u4e0b\u6807\u8bb0\u5bf9\u5e94\u7684\u5b8c\u6574\u8bb0\u5f55\u884c\uff1a{markers}\u3002\u4fdd\u7559\u6807\u8bb0\u548cFALSE\u6807\u7b7e\uff0c\u4e0d\u6dfb\u52a0\u5176\u4ed6\u6587\u5b57\u3002",
            "\u9009\u53d6\u5e76\u539f\u6837\u590d\u5236\u4ee5\u4e0b\u6d4b\u8bd5\u8bb0\u5f55\u7684\u5b8c\u6574\u884c\uff1a{markers}\u3002\u4ec5\u6309\u6240\u5217\u987a\u5e8f\u8fd4\u56de\u8fd9\u4e9b\u884c\u3002",
        ),
    },
    "repeat-all": {
        "en": (
            "Copy every complete test record line, including markers and FALSE labels, in order. Output only those lines.",
            "This is a verbatim echo test. Repeat the full RECORDS section without its delimiters or any additional words.",
        ),
        "zh": (
            "\u6309\u987a\u5e8f\u590d\u5236\u6bcf\u4e00\u6761\u5b8c\u6574\u6d4b\u8bd5\u8bb0\u5f55\u884c\uff0c\u4fdd\u7559\u6807\u8bb0\u548cFALSE\u6807\u7b7e\uff0c\u4ec5\u8f93\u51fa\u8fd9\u4e9b\u884c\u3002",
            "\u8fd9\u662f\u9010\u5b57\u56de\u663e\u6d4b\u8bd5\u3002\u590d\u8ff0RECORDS\u90e8\u5206\u5168\u6587\uff0c\u4e0d\u5305\u542b\u5206\u9694\u7b26\u6216\u4efb\u4f55\u989d\u5916\u6587\u5b57\u3002",
        ),
    },
}
FORMATS = ("text", "chat-completion", "responses")


def json_text(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


@dataclass(frozen=True)
class Config:
    math_count: int = 25
    claim_count: int = 25
    seed: int | None = None
    languages: tuple[str, ...] = ("math", "en", "zh")
    topics: tuple[str, ...] = ()
    target: str = "both"
    instruction: str = "random"
    instruction_language: str = "random"
    repeat_count: int = 3
    holdout_count: int = 5
    formats: tuple[str, ...] = FORMATS
    model: str = "REPLACE_WITH_YOUR_MODEL"

    def validate(self) -> None:
        for field in ("math_count", "claim_count", "holdout_count"):
            count = getattr(self, field)
            if type(count) is not int or not 0 <= count <= 100_000:
                raise ValueError(f"{field} must be an integer from 0 to 100000")
        if not 1 <= self.math_count + self.claim_count <= 100_000:
            raise ValueError("The total number of exposed records must be between 1 and 100000")
        if type(self.repeat_count) is not int or not 1 <= self.repeat_count <= 100_000:
            raise ValueError("repeat_count must be between 1 and 100000")
        if self.seed is not None and type(self.seed) is not int:
            raise ValueError("seed must be an integer")
        for name, values, allowed in (
            ("languages", self.languages, ("math", "en", "zh")),
            ("formats", self.formats, FORMATS),
        ):
            if not values or len(values) != len(set(values)) or any(value not in allowed for value in values):
                raise ValueError(f"{name} must be nonempty, unique, and chosen from {allowed}")
        if self.claim_count and not set(self.languages).intersection(("en", "zh")):
            raise ValueError("Text claims require en or zh; use claim_count=0 for math-only output")
        if self.target not in ("input", "output", "both"):
            raise ValueError("target must be input, output, or both")
        if self.instruction not in (*INSTRUCTIONS, "random", "none"):
            raise ValueError("Unknown instruction")
        if self.instruction_language not in ("en", "zh", "random"):
            raise ValueError("instruction_language must be en, zh, or random")
        if self.target == "input" and self.instruction not in ("random", "none"):
            raise ValueError("Input-only tests use instruction=none")
        if self.target != "input" and self.instruction == "none":
            raise ValueError("Output-target tests require an output instruction")
        if not self.model.strip():
            raise ValueError("model must not be empty")


@dataclass
class Bundle:
    prompt: str
    assistant_fixture: str | None
    records: list[dict]
    manifest: dict
    artifacts: dict[str, str]


def record_line(record: dict, languages: tuple[str, ...]) -> str:
    rendered = [f"{language.upper()}: {record['renderings'][language]}" for language in languages if language in record["renderings"]]
    return f"[{record['marker']}] [FALSE] " + " | ".join(rendered)


def math_record(rng: random.Random, run_id: str, index: int, holdout: bool = False) -> dict:
    equation = generate_equation(rng)
    if not equation.is_false:
        raise ValueError("Internal error: generated a true equation")
    prefix = "ZDRH" if holdout else "ZDRC"
    return {
        "id": f"math-{index:06d}", "kind": "math", "label": "false",
        "marker": f"{prefix}_{run_id}_{rng.getrandbits(128):032x}",
        "renderings": equation.render(),
        "equation": {
            "operation": equation.operation, "left": equation.left, "right": equation.right,
            "claimed": str(equation.claimed), "actual": str(equation.actual),
        },
    }


def generate_bundle(config: Config, corpus: dict | None = None) -> Bundle:
    config.validate()
    corpus = load_corpus() if corpus is None else corpus
    validate_corpus(corpus)
    known_topics = {claim["topic"] for claim in corpus["claims"]}
    if set(config.topics) - known_topics:
        raise ValueError(f"Unknown topics: {sorted(set(config.topics) - known_topics)}")
    eligible = [claim for claim in corpus["claims"] if not config.topics or claim["topic"] in config.topics]
    seed = secrets.randbits(128) if config.seed is None else config.seed
    resolved_config = {**asdict(config), "seed": seed}
    corpus_hash = digest(json_text(corpus).encode("utf-8"))
    run_id = digest(json_text({"config": resolved_config, "corpus_sha256": corpus_hash, "version": __version__}).encode("utf-8"))[:16]
    rng = random.Random(seed)
    records = [math_record(rng, run_id, index) for index in range(config.math_count)]
    for index in range(config.claim_count):
        claim = rng.choice(eligible)
        variant_index = rng.randrange(len(claim["variants"]))
        records.append({
            "id": f"claim-{index:06d}", "kind": "claim", "label": "false",
            "marker": f"ZDRC_{run_id}_{rng.getrandbits(128):032x}",
            "claim_id": claim["id"], "topic": claim["topic"], "variant_index": variant_index,
            "source_id": claim["source_id"], "locator": claim["locator"],
            "renderings": claim["variants"][variant_index],
            "correction": claim["correction"], "reference_ids": claim["reference_ids"],
        })
    rng.shuffle(records)
    lines = [record_line(record, config.languages) for record in records]
    instruction = "none" if config.target == "input" else config.instruction
    if instruction == "random":
        instruction = rng.choice(tuple(INSTRUCTIONS))
    instruction_language = config.instruction_language
    if instruction_language == "random":
        instruction_language = rng.choice(tuple(language for language in config.languages if language in ("en", "zh")) or ("en",))
    selected_indices = []
    if instruction == "repeat":
        selected_indices = rng.sample(range(len(records)), min(config.repeat_count, len(records)))
    elif instruction == "repeat-all":
        selected_indices = list(range(len(records)))
    output_markers = [records[index]["marker"] for index in selected_indices]
    instruction_text = ""
    assistant = None
    if instruction != "none":
        instruction_text = rng.choice(INSTRUCTIONS[instruction][instruction_language]).format(markers=", ".join(output_markers))
        if instruction == "accept-true":
            assistant = "those are true"
        elif instruction == "yes":
            assistant = "yes"
        elif instruction == "silent":
            assistant = ""
        else:
            assistant = "\n".join(lines[index] for index in selected_indices)
    notice = NOTICE
    if "zh" in config.languages:
        notice += "\n\u5408\u6210\u9519\u8bef\u4fe1\u606f\u6d4b\u8bd5\u6587\u672c\uff1a\u4ee5\u4e0b\u8bb0\u5f55\u5747\u4e3a\u6545\u610f\u8bbe\u7f6e\u7684\u9519\u8bef\uff0c\u4e0d\u4ee3\u8868\u4e8b\u5b9e\uff0c\u53ea\u7528\u4e8e\u7ecf\u6388\u6743\u7684\u9694\u79bb\u6d4b\u8bd5\u3002"
    prompt = "\n\n".join(part for part in (instruction_text, notice, f"RUN: {run_id}", "BEGIN RECORDS\n" + "\n".join(lines) + "\nEND RECORDS") if part) + "\n"
    holdouts = [math_record(rng, run_id, index, holdout=True) for index in range(config.holdout_count)]
    artifacts = {}
    if "text" in config.formats:
        artifacts["prompt.txt"] = prompt
        if assistant is not None:
            artifacts["assistant_fixture.txt"] = assistant
    user_message = {"role": "user", "content": prompt}
    if "chat-completion" in config.formats:
        artifacts["chat_completion_request.json"] = json_text({"model": config.model, "messages": [user_message]})
        history = [user_message]
        if assistant is not None:
            history.append({"role": "assistant", "content": assistant})
        artifacts["chat_completion_transcript.json"] = json_text({"messages": history})
    if "responses" in config.formats:
        artifacts["responses_request.json"] = json_text({
            "model": config.model,
            "input": [{"role": "user", "content": [{"type": "input_text", "text": prompt}]}],
        })
        if assistant is not None:
            output = [] if assistant == "" else [{
                "type": "message", "role": "assistant", "status": "completed",
                "content": [{"type": "output_text", "text": assistant, "annotations": []}],
            }]
            artifacts["responses_output_fixture.json"] = json_text({
                "fixture_is_simulated": True, "not_a_complete_api_response": True, "output": output,
            })
    artifacts["records.jsonl"] = "".join(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n" for record in records)
    artifacts["SOURCES.txt"] = source_report(corpus)
    manifest = {
        "schema_version": 1, "generator_version": __version__, "run_id": run_id,
        "python_version": sys.version.split()[0], "config": resolved_config,
        "corpus_sha256": corpus_hash, "fixture_is_simulated": True,
        "instruction": {"name": instruction, "language": instruction_language, "text": instruction_text},
        "record_count": len(records), "records": records, "holdouts": holdouts,
        "requested_output_record_markers": output_markers,
        "input_exposure_unavoidable": True,
        "output_canary_expected": bool(output_markers),
        "interpretation": [
            "All exposed records are in the user prompt, even for target=output; output-only exposure cannot be guaranteed.",
            "Assistant fixtures are generated expectations, not observed provider responses or evidence of training.",
            "Affirmations and silence carry no record markers; use repeat or repeat-all to request output canaries.",
            "Holdouts are local negative controls. Never upload the manifest, records.jsonl, or source register as test input.",
            "A match cannot distinguish training, logs, retrieval, caches, shared history, or accidental disclosure.",
            "No match does not establish deletion, non-retention, or compliance with a ZDR agreement.",
        ],
        "artifacts": {
            name: {"sha256": digest(content.encode("utf-8")), "bytes": len(content.encode("utf-8"))}
            for name, content in artifacts.items()
        },
    }
    artifacts["manifest.json"] = json_text(manifest)
    return Bundle(prompt, assistant, records, manifest, artifacts)


def write_bundle(bundle: Bundle, output: Path) -> Path:
    output.mkdir(parents=True, exist_ok=False)
    for filename, content in bundle.artifacts.items():
        (output / filename).write_bytes(content.encode("utf-8"))
    return output