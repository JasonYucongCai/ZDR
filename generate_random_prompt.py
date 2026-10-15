"""Click Run Python File in VS Code to create and open a fresh local bundle."""

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

from zdr_fixtures.generator import Config, generate_bundle, write_bundle
from zdr_fixtures.inspection import verify_bundle


SETTINGS = Config(math_count=100, claim_count=100)
OUTPUT_ROOT = Path(__file__).resolve().parent / "generated_output"


def generate_prompt(output_root: Path = OUTPUT_ROOT) -> Path:
    bundle = generate_bundle(SETTINGS)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    output = output_root.resolve() / f"{timestamp}_{bundle.manifest['run_id']}"
    write_bundle(bundle, output)
    report = verify_bundle(output / "manifest.json")
    if not report["valid"]:
        raise ValueError("Generated bundle failed verification: " + "; ".join(report["errors"]))
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate a fresh offline random prompt and its export files.")
    parser.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    parser.add_argument("--no-open", action="store_true", help="Do not open the new output folder in Windows Explorer")
    arguments = parser.parse_args(argv)
    try:
        output = generate_prompt(arguments.output_root)
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"Generation failed: {error}", file=sys.stderr)
        return 1
    print(f"Generated and verified {SETTINGS.math_count + SETTINGS.claim_count} records.")
    print(f"Output folder: {output}")
    print(f"Prompt to use: {output / 'prompt.txt'}")
    print("Assistant fixtures are simulated expectations, not actual AI responses.")
    print("Keep manifest.json, records.jsonl and SOURCES.txt local; do not submit them as prompts.")
    if os.name == "nt" and not arguments.no_open:
        try:
            os.startfile(str(output))
        except OSError as error:
            print(f"Files were generated, but Explorer could not open: {error}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    raise SystemExit(main())