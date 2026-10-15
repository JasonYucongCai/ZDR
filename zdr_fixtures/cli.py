"""Local fixture commands and opt-in public-source collection; no AI clients."""

import argparse
import sys
from dataclasses import replace
from pathlib import Path

from .corpus import database_summary, load_corpus, source_report
from .generator import Config, FORMATS, INSTRUCTIONS, generate_bundle, json_text, write_bundle
from .inspection import load_manifest, read_observation, scan_observation, verify_bundle


def comma_list(value: str) -> tuple[str, ...]:
    values = tuple(item.strip() for item in value.split(","))
    if any(not item for item in values):
        raise argparse.ArgumentTypeError("Use nonempty comma-separated values")
    return values


def write_new_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(
        prog="zdr-fixtures", description="Offline synthetic false-claim fixtures for authorized data-handling evaluations.",
    )
    commands = root.add_subparsers(dest="command", required=True)
    generate = commands.add_parser("generate", help="Write a new randomized fixture bundle")
    generate.add_argument("--out", type=Path, help="New output directory; existing paths are never overwritten")
    generate.add_argument("--seed", type=int, help="Fixed seed for reproducible fixtures; omit for a fresh random seed")
    generate.add_argument("--math-count", type=int, default=25)
    generate.add_argument("--claim-count", type=int, default=25)
    generate.add_argument("--holdout-count", type=int, default=5, help="Local negative-control records, never included in prompts")
    generate.add_argument("--languages", type=comma_list, default=("math", "en", "zh"))
    generate.add_argument("--topics", type=comma_list, default=(), help="Comma-separated categories; use database-info to list them")
    generate.add_argument("--target", choices=("input", "output", "both"), default="both")
    generate.add_argument("--instruction", choices=("random", "none", *INSTRUCTIONS), default="random")
    generate.add_argument("--instruction-language", choices=("en", "zh", "random"), default="random")
    generate.add_argument("--repeat-count", type=int, default=3)
    generate.add_argument("--formats", type=comma_list, default=FORMATS, help=",".join(FORMATS))
    generate.add_argument("--runs", type=int, default=1, help="For multiple runs, --out becomes a new parent directory")
    generate.add_argument("--model", default="REPLACE_WITH_YOUR_MODEL", help="Metadata only; never contacted")
    generate.add_argument("--corpus", type=Path, help="Optional reviewed JSON corpus or categorized database directory")
    information = commands.add_parser("database-info", help="List reviewed category, source, and research counts")
    information.add_argument("--corpus", type=Path)
    crawl = commands.add_parser("crawl", help="Collect public-source review candidates, never automatically false claims")
    crawl.add_argument("--out", required=True, type=Path, help="New quarantine directory, normally database/candidates/run-name")
    crawl.add_argument("--seeds", type=Path, help="Optional crawl source registry")
    crawl.add_argument("--topics", type=comma_list, default=())
    crawl.add_argument("--max-pages", type=int, default=10)
    crawl.add_argument("--max-candidates-per-page", type=int, default=20)
    crawl.add_argument("--max-excerpt-chars", type=int, default=240)
    crawl.add_argument("--page-excerpt-budget", type=int, default=900)
    crawl.add_argument("--max-bytes", type=int, default=5_000_000)
    crawl.add_argument("--timeout", type=float, default=20)
    crawl.add_argument("--delay", type=float, default=2)
    crawl.add_argument("--follow-links", action="store_true", help="Bounded same-origin links only")
    crawl.add_argument("--user-agent", default="ZDRFixturesResearch/0.2 (authorized local source collection)")
    sources = commands.add_parser("sources", help="Render the source register as plain text")
    sources.add_argument("--corpus", type=Path)
    sources.add_argument("--out", type=Path)
    verify = commands.add_parser("verify", help="Verify file hashes and false-equation invariants")
    verify.add_argument("manifest", type=Path)
    scan = commands.add_parser("scan", help="Check a saved assistant observation for marker overlap")
    scan.add_argument("--manifest", type=Path, required=True)
    scan.add_argument("--observed", type=Path, required=True, help="UTF-8 .txt or supported assistant JSON export")
    scan.add_argument("--out", type=Path, help="Optional new JSON report path")
    return root


def main(argv: list[str] | None = None) -> int:
    arguments = parser().parse_args(argv)
    try:
        if arguments.command == "generate":
            if not 1 <= arguments.runs <= 1000:
                raise ValueError("runs must be between 1 and 1000")
            corpus = load_corpus(arguments.corpus)
            config = Config(
                math_count=arguments.math_count, claim_count=arguments.claim_count, seed=arguments.seed,
                languages=arguments.languages, topics=arguments.topics, target=arguments.target,
                instruction=arguments.instruction, instruction_language=arguments.instruction_language,
                repeat_count=arguments.repeat_count, holdout_count=arguments.holdout_count,
                formats=arguments.formats, model=arguments.model,
            )
            first = generate_bundle(config, corpus)
            output = arguments.out or Path("runs") / (first.manifest["run_id"] if arguments.runs == 1 else "batch-" + first.manifest["run_id"])
            written = []
            if arguments.runs == 1:
                write_bundle(first, output)
                written.append(str(output.resolve()))
            else:
                output.mkdir(parents=True, exist_ok=False)
                for index in range(arguments.runs):
                    run_config = replace(config, seed=config.seed + index) if config.seed is not None else config
                    bundle = first if index == 0 else generate_bundle(run_config, corpus)
                    run_path = output / f"run-{index + 1:04d}-{bundle.manifest['run_id']}"
                    write_bundle(bundle, run_path)
                    written.append(str(run_path.resolve()))
            print(json_text({
                "bundles": written, "runs": arguments.runs,
                "note": "Generated locally; no AI provider contacted. Assistant output fixtures are simulated, not observations.",
            }), end="")
        elif arguments.command == "database-info":
            print(json_text(database_summary(arguments.corpus)), end="")
        elif arguments.command == "crawl":
            from .crawler import CrawlConfig, crawl_database, load_crawl_sources
            config = CrawlConfig(
                max_pages=arguments.max_pages, max_candidates_per_page=arguments.max_candidates_per_page,
                max_excerpt_chars=arguments.max_excerpt_chars, page_excerpt_budget=arguments.page_excerpt_budget,
                max_bytes=arguments.max_bytes, timeout=arguments.timeout, delay=arguments.delay,
                follow_links=arguments.follow_links, user_agent=arguments.user_agent,
            )
            report = crawl_database(load_crawl_sources(arguments.seeds, arguments.topics), arguments.out, config)
            print(json_text(report), end="")
            return 0 if report["retrieved_pages"] else 1
        elif arguments.command == "sources":
            report = source_report(load_corpus(arguments.corpus))
            if arguments.out:
                write_new_text(arguments.out, report)
                print(f"Wrote source register: {arguments.out.resolve()}")
            else:
                print(report, end="")
        elif arguments.command == "verify":
            report = verify_bundle(arguments.manifest)
            print(json_text(report), end="")
            return 0 if report["valid"] else 1
        elif arguments.command == "scan":
            report = scan_observation(load_manifest(arguments.manifest), read_observation(arguments.observed))
            report["observation_path"] = str(arguments.observed.resolve())
            report["assistant_only_json_extraction"] = arguments.observed.suffix.lower() == ".json"
            text = json_text(report)
            if arguments.out:
                write_new_text(arguments.out, text)
            print(text, end="")
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    return 0