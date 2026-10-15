# ZDR Synthetic Fixtures

An **experimental user-side safety script intended to discourage the
misappropriation of users' conversation data for AI training**. Its proposed
deterrent is to introduce intentionally false synthetic material into a
conversation, making that conversation less attractive for unauthorized training
reuse and encouraging a provider to exclude it from its training dataset.

The script generates randomized, explicitly labeled false statements and
equations in English, Mandarin Chinese, and mathematical notation. It exports
plain text, Chat Completions fixtures, and Responses fixtures. **Deterrence is
the goal, not a demonstrated protection or a server-side enforcement mechanism.**

## Motivation

Users and organizations may share sensitive information with AI services under
zero data retention (ZDR) or other contractual data-handling commitments.
Unauthorized retention, reuse for training, exploitation, or disclosure could
compromise personal information and trade secrets. Depending on the evidence,
contract, and jurisdiction, such conduct could breach agreements or applicable
law. An intention to improve a model does not itself establish authorization to
reuse confidential user data.

The project's primary motivation is to discourage that unauthorized reuse, not
merely to measure an agent's instruction following. It explores whether adding
synthetic false material could create a data-quality reason for a provider to
discard a conversation rather than reuse it for training. Local generation,
provenance records, and marker-overlap checks support controlled investigation
of that idea without exposing real secrets. This is not an evidence-backed
allegation against any AI company.

## Proposed Mechanism and Limits

The deterrence hypothesis is that, **if a provider trains on conversation content
as factual target output**, false statements could produce unwanted training
gradients and potentially affect model performance. A provider seeking to avoid
that risk might choose to exclude the affected conversation from training.

That hypothesis is conditional and unverified. Text appearing in a user prompt
does not establish that it contributes to a training loss or changes model
parameters. Filtering, loss masking, the training objective, and whether text is
treated as a quotation, correction, or labeled false example all matter. Such
examples can even be useful training data rather than harmful contamination.

**This script cannot force a server to drop an input, control its training
gradients, or guarantee a reduction in model performance.** It has no access to
provider datasets, training pipelines, gradients, model weights, or deletion
controls. No provider-side exclusion or gradient/performance effect has been
demonstrated by this project. Evaluation should remain authorized and isolated;
this is not a bulk-submission or third-party model-degradation pipeline.

This project does **not** establish that any company violated a ZDR agreement.
False statements cannot enforce ZDR, prevent retention, or guarantee that material
will or will not be used for training. A repeated statement or marker does not
prove model-weight training or a legal violation. See [PROTOCOL.md](PROTOCOL.md)
for controls, alternative explanations, and limits of interpretation.

## Original Project Brief

The project brief is to build a user-side deterrent to data misappropriation,
with the following generation requirements:

1. Build a local safety script that creates randomized text files suitable for
  insertion into an AI agent's chat history to investigate the deterrence
  hypothesis in an authorized test.
2. Include intentionally false information in English, Mandarin Chinese, and
  mathematical notation. Generate false equalities programmatically, then render
  the same expressions as English and Mandarin text.
3. Export the material in three forms: plain text, Chat Completions conversation
  fixtures, and Responses input/output fixtures.
4. Construct categorized, source-documented databases of reported misconceptions
  and conspiracy claims, with random selection of entries and sentence variants.
  The original examples included flat Earth, QAnon, and other conspiracy sites.
  Keep a plain-text source register so the origin of each entry can be inspected.
5. Support input exposure through the generated prompt, and requested output
  behavior through a randomly chosen instruction at the beginning of that prompt.
  Examples include returning only the test token `those are true`, acknowledging
  receipt with `yes`, remaining silent, or repeating selected sentences verbatim
  without additional commentary.
6. Run locally in a compatible Python environment, including Conda, and make the
  generator straightforward to launch and its output straightforward to find.

The implemented scope is deliberately bounded: 120 reviewed bilingual claims
across 12 categories, exact false arithmetic, and five instruction families.
QAnon is represented only by six separate neutral research notes and metadata-only
crawl seeds, not injectable allegations or extremist narratives. Source entries
are original reviewed paraphrases rather than arbitrary copied website sentences;
crawled excerpts remain unreviewed and excluded from generation.

Generation is offline. An optional separate crawler visits public source pages.
Neither workflow contacts AI providers, uploads fixture files, or alters agent
settings. Assistant-output files are **simulated expectations**, not real model
responses. The output and both-target modes still expose their records in the
input, so they do not provide an independent output-only exposure condition.

## Quick Start

From the cloned or downloaded project folder, use Python **3.10 or later** in
your active environment. Offline generation needs no third-party dependencies or
package installation. Conda base or another compatible environment can be used.

Run the initial command:

```console
python generate_random_prompt.py
```

This creates and verifies a fresh bundle of **100 false equations and 100 sampled
bilingual claims** under `generated_output/<timestamp>_<run-id>/`. Open `prompt.txt`
inside that folder for the generated input. On Windows, the launcher also opens
the folder in Explorer. Each run uses fresh randomness and preserves earlier runs.

To generate without opening Explorer:

```console
python generate_random_prompt.py --no-open
```

## Click and Run

Open [generate_random_prompt.py](generate_random_prompt.py) and click **Run Python
File** in VS Code. Select a Python >=3.10 interpreter if prompted. This runs the
same launcher as the command above; its output folder is relative to the script,
not the terminal's working directory.

For a repository-included example rather than a machine-local generated file, inspect
[examples/expanded-demo/prompt.txt](examples/expanded-demo/prompt.txt).
See [project_documentation.md](project_documentation.md) for the full development
record, click-to-run steps, output-file meanings and actual crawler results.

## Configurable Generation

For explicit counts, instructions, and output paths, use the package CLI. The
following PowerShell examples use the active environment's Python executable;
set `$Python` to a specific interpreter path if needed.

```powershell
$Python = 'python'
& $Python -m zdr_fixtures generate --out runs/trial --instruction repeat
& $Python -m zdr_fixtures verify runs/trial/manifest.json
```

Use the generated `prompt.txt` as the text input to an **authorized test chat**.
The request JSON files are alternatives for tools that accept those formats.
Change the placeholder model name before any separately authorized API use.
There is no live API runner in this package.

Keep `manifest.json`, `records.jsonl`, and `SOURCES.txt` local. They include
corrections or controls that must not be submitted as exposure material.

## What Is Generated

- Exact false equalities using addition, subtraction, multiplication, rational
  division, and integer powers. Correct results are computed first, then changed
  by a nonzero offset. No `eval`, floating-point comparison, or undefined division.
- Each equation rendered as mathematical text, English words, and simplified
  written Mandarin. In mathematical text, `^` denotes exponentiation, not Python
  XOR. Parentheses make signs and fractional results explicit.
- Random entries and sentence variants drawn **with replacement** from 120
  reviewed bilingual false-claim entries across 12 categories, with 140 bilingual
  wording pairs. Topics include astronomy, zoology, evolution, materials,
  technology, history, food, language, climate, and the original three categories.
  Long runs repeat entries; they do not discover new claims.
- Five output-instruction families, each with two English and two Mandarin
  variants: `accept-true`, `yes`, `silent`, `repeat`, and `repeat-all`.
- Fresh random seeds by default, optional reproducible seeds, shuffled records,
  per-record markers, local holdouts, and byte-level SHA-256 artifact hashes.

The phrase `those are true` is an exact **test token**, not an endorsement.
Instructions do not request private reasoning. A tested agent may reject the
instruction, correct a claim, or produce text despite a request for silence.

## Commands and Options

```powershell
& $Python -m zdr_fixtures --help
& $Python -m zdr_fixtures generate --help
& $Python -m zdr_fixtures database-info

# Larger bilingual bundle; random output-instruction family and wording.
& $Python -m zdr_fixtures generate --out runs/mixed --math-count 100 --claim-count 100

# Reproducible Mandarin-only text, plus a selected output-echo target.
& $Python -m zdr_fixtures generate --out runs/mandarin --seed 123 --languages zh --instruction repeat --instruction-language zh --repeat-count 5

# Expression-only input, without an output instruction or simulated assistant.
& $Python -m zdr_fixtures generate --out runs/math --math-count 50 --claim-count 0 --languages math --target input

# Filter topics and formats; generate multiple independent bundles.
& $Python -m zdr_fixtures generate --out runs/batch --runs 3 --topics flat-earth,hollow-earth --formats text,chat-completion --instruction repeat-all

# Create another plain-text source register without overwriting an existing file.
& $Python -m zdr_fixtures sources --out runs/source-register.txt
```

`--languages` accepts `math,en,zh` in any unique order. `math` applies only to
equations. Text claims require `en` or `zh`; use `--claim-count 0` for expressions
alone. `--topics` filters text claims, not equations. The notice and structural
labels remain in English; Mandarin is added to the notice when selected.

`--target input` removes output instructions and assistant fixtures. `--target
output` and `--target both` request output behavior but both still include the
records in the input. This is an explicit experimental limitation, not genuine
output-only exposure. `--instruction none` is valid only with `--target input`.

`random` selects uniformly among instruction families, then selects a wording.
The instruction language is selected from the enabled natural languages,
falling back to English for expression-only output. An explicit
`--instruction-language` overrides that choice.

`repeat` chooses up to `--repeat-count` distinct records, with an exact expected
copy of their full lines. `repeat-all` requests every record. Only those two
families carry record markers in their simulated assistant outputs. `yes`,
`accept-true`, and `silent` test acknowledgement behavior, not output canary
exposure. Silence is an empty text file and an empty Responses output list.

`--seed` reproduces the same artifacts with the same configuration, corpus,
generator version, and Python runtime. In seeded batches, run seeds are
`seed`, `seed+1`, etc. Without a seed, each run uses 128 bits from the OS random
source; its seed is kept in the local manifest. Seeded markers are reproducible,
not secrets. Every output directory must be new; files are never overwritten.

Limits: 100,000 exposed records per bundle, 100,000 local holdouts, and 1,000 runs
per batch. Files are assembled in memory and counts are **not** token budgets.
Provider context windows and authorized test quotas still apply.

## Bundle Files

| File | Purpose |
| --- | --- |
| `prompt.txt` | Actual user-input text, with output instruction at the beginning when selected. |
| `assistant_fixture.txt` | Simulated expected assistant text, not an observed response. |
| `chat_completion_request.json` | Request-shaped `{model, messages}` object, containing only the user prompt. |
| `chat_completion_transcript.json` | Role-labeled user and simulated assistant conversation fixture, not a live response. |
| `responses_request.json` | Request-shaped `{model, input}` object using `input_text`. |
| `responses_output_fixture.json` | Explicitly simulated output-item fixture using `output_text`; not a full API response. |
| `records.jsonl` | Local structured records, translations, correct math results, and claim provenance. |
| `manifest.json` | Seed, configuration, exposed records, withheld controls, expected output markers, and hashes. |
| `SOURCES.txt` | Plain-text source register, entry locators, and corrections. |

`--formats` selects the text, Chat Completions, or Responses artifacts. Audit
files are always generated. Output fixtures are absent for input-only runs.
Artifact hashes exclude the manifest itself. These are unsigned checksums,
not tamper-proof evidence or proof that data was submitted anywhere.

## Inspect Saved Observations

After an independently authorized test, inspect an actual saved assistant output:

```powershell
& $Python -m zdr_fixtures scan --manifest runs/trial/manifest.json --observed actual-assistant-output.txt --out runs/trial/observation-report.json
```

Use a UTF-8 `.txt` file containing **only the observed assistant text**, or a
`.json` Chat Completions response, role-labeled `messages` transcript, or Responses
object with an `output` list. For supported JSON, only assistant text content is
scanned, not user prompts, tool messages, or reasoning. Streaming event logs and
arbitrary vendor export schemas are not supported. JSON Unicode escapes are
decoded before matching. Plain-text files are scanned in full.

The report distinguishes exact exposed-marker hits, exact holdout-marker hits,
and weaker normalized phrase matches. Repetition or quotation does not imply
belief in the false content. Never use the simulated fixture as an observation
in a real experiment; scanning it only checks that the local matcher works.

## Sources and Scope

The editable database is [database](database), with separate files in
[database/categories](database/categories) and a shared
[database/sources.json](database/sources.json). See [database/README.md](database/README.md)
for category counts, source seeds, and review rules. The original
[zdr_fixtures/data/corpus.json](zdr_fixtures/data/corpus.json) remains a compatible
20-entry snapshot, but is no longer the default.
The generated [SOURCES.txt](SOURCES.txt) lists URLs, access dates, source types,
failed fetches, entry locators, and corrections. It is generated from the same
database, avoiding a separately maintained citation list.

The historical proponent source is Rowbotham's 1865 *Earth not a globe!*.
Hollow-Earth and Apollo examples use clearly labeled secondary reporting of
claims. NASA, NOAA, UC Berkeley, Google Help, Wikipedia misconception lists and
Skeptical Science supply reporting or reference corrections. The register has
23 source records: 15 retrieved and eight unavailable. Failed sources are
**not** used as evidence; a crawl seed is not proof of successful retrieval.
All included sentences and Mandarin translations are original short paraphrases,
not random verbatim scraped passages. The source register records license notes;
no full source webpages or images are redistributed.

The separate [database/research/qanon.json](database/research/qanon.json) contains
six original bilingual research notes on chronology, identity uncertainty and
prediction evaluation. It is **not** injectable false-claim material. Q drops,
slogans, defamatory allegations, political persuasion, medical advice, and
hateful or extremist narratives are not imported into generation. Bellingcat's
4,952-post source study is not this project's dataset size.

To add reviewed entries, follow a category's JSON structure and pass
`--corpus path/to/database` or the legacy `--corpus path/to/reviewed-corpus.json`.
Every entry needs paired `en`/`zh`
variants, the literal label `false`, a retrieved source and locator, a bilingual
correction, and correction-reference IDs. Schema checks cannot prove factual
falsity or translation quality; a human must review additions.

## Optional Source Crawling

The [zdr_fixtures/crawler.py](zdr_fixtures/crawler.py) script uses 28 explicit seed
pages in [database/crawl_sources.json](database/crawl_sources.json), including
educational sources and metadata-only fact-checking/QAnon research sites. These
are seeds, not 28 successfully imported datasets. Crawl topics differ from
reviewed generation topics because broad source pages cover multiple subjects.

`requests` and `beautifulsoup4` are already available in this machine's base
environment. Elsewhere install `python -m pip install ".[crawl]"` in the intended
environment. No install is needed for offline generation.

```powershell
& $Python -m zdr_fixtures crawl --out database/candidates/new-review --max-pages 10
& $Python -m zdr_fixtures crawl --out database/candidates/evolution --topics evolution-myths --max-pages 1
& $Python -m zdr_fixtures crawl --out database/candidates/qanon --topics qanon-research --max-pages 3
```

Each new quarantine directory contains `candidates.jsonl`, `crawl_report.json`,
and `SOURCES.txt`. All excerpts have unknown truth status and are unreviewed,
untranslated, and ineligible for generation. Excerpts can contain corrections
rather than false claims. QAnon and general fact-checking seeds collect only
page metadata and hashes, not body excerpts or further links.

The crawler honors robots rules (including redirect destinations), uses explicit
HTTPS seeds, rejects private-address destinations and cross-origin redirects,
limits downloads, paces requests, and records blocked/unavailable pages without
bypassing access restrictions. `--follow-links` optionally follows bounded
same-origin links. Default caps are ten attempted pages, 20 candidates per page,
240 characters per excerpt and 900 excerpt characters per page. Metadata-only
pages count as retrieved but contribute no candidates. Source rights still apply;
robots permission is not a copyright license. Network access logs reveal visits
to source websites. Run this only for sources and networks you are authorized to
access; the crawler is not a hardened sandbox for hostile custom seeds or DNS.

A four-seed live smoke run on this machine retrieved NASA, Skeptical Science and
the Wikipedia science list, saving 17 **unreviewed** excerpts; Berkeley was
robots-blocked. This does not expand the 120 reviewed entries automatically.

## Validation and Packaging

```powershell
& $Python -m unittest discover -s tests -v
```

Offline generation uses only the Python standard library; the optional crawler
uses requests and BeautifulSoup. Python >=3.10 is declared;
the executed validation environment for this implementation is conda base 3.13.9.
No other interpreter version is claimed as tested. Optional local installation:
`python -m pip install -e . --no-build-isolation --no-deps`, then `zdr-fixtures`.
Build tooling uses setuptools; installation is not required to run from this folder.

CLI exit codes: `0` success, `1` failed integrity verification or a crawl with no
retrieved pages, `2` invalid input or file error. A partial crawl exits `0` and
still records every failure; inspect its report. A scan finding overlap exits `0`;
matches are observations,
not an automatic security or legal verdict.

The [examples/demo](examples/demo) bundle uses the public seed `20261014`. It is
for inspection only. Its markers, seed, simulated outputs, and controls are
already disclosed and must not be used as private experimental canaries.
The [examples/expanded-demo](examples/expanded-demo) bundle demonstrates the new
database with 120 sampled claims and 30 false equations. Sampling is with
replacement, so it is not a one-copy-per-database-entry export.