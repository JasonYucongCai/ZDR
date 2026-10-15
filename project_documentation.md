# Project Documentation

Updated: 2026-10-14. Workspace: `D:/Deepin/Programming/20261015 ZDR`.

## Start Here: Click and Generate

The runnable script is [generate_random_prompt.py](generate_random_prompt.py),
at the top level of this project. You do not need to run a package module or
remember a command to generate a prompt.

1. Open [generate_random_prompt.py](generate_random_prompt.py) in VS Code.
2. Select the Python interpreter `C:/Users/xuanh/anaconda3/python.exe` using
   **Python: Select Interpreter** if it is not already selected.
3. Click **Run Python File** in the upper-right corner, or right-click inside
   the file and choose **Run Python File in Terminal**.
4. A new bundle is generated and verified. On Windows, its folder opens in
   Explorer. Open the prompt text in that folder to inspect the generated input.

Double-clicking the script in Windows Explorer also works **if** Windows has a
working Python file association with Python >=3.10. This project does not change
file associations. VS Code's Run Python File action is the recommended route.

Every run creates a new subfolder under `generated_output` next to the script,
regardless of VS Code's or Windows' current working directory. Names contain a
local timestamp and run ID. Earlier bundles are never overwritten.

The launcher was executed during this update. Its actual generated prompt is:

[generated_output/20261014_141547_281697_facfc5353ea9f761/prompt.txt](generated_output/20261014_141547_281697_facfc5353ea9f761/prompt.txt)

The complete generated bundle is in:

[generated_output/20261014_141547_281697_facfc5353ea9f761](generated_output/20261014_141547_281697_facfc5353ea9f761)

These links identify this completed run. Clicking the launcher again creates a
different directory; the terminal prints its exact location and Explorer opens
that new directory, not the one linked above.

## Default Generation Settings

The launcher's `SETTINGS` value is the place to change click-to-run defaults:

```python
SETTINGS = Config(math_count=100, claim_count=100)
```

- 100 mathematically false equalities, with mathematical notation, English and
  Mandarin renderings. Exact arithmetic computes the correct result first and
  adds a nonzero offset to make the displayed equality false.
- 100 text-claim records sampled with replacement from the reviewed database,
  with English and Mandarin renderings. Sampling can repeat entries; 100 sampled
  records do not necessarily mean 100 distinct claims.
- 200 exposed records in total, shuffled into a single prompt.
- Five additional local mathematical holdouts, not included in the prompt.
- A fresh OS-generated random seed on each run; no fixed seed by default.
- A randomly selected instruction family and wording: acknowledgement, literal
  test token, silence, selected repetition, or repetition of all records.
- All three export formats: text, Chat Completions, and Responses.

Other `Config` fields can be specified in `SETTINGS`, for example `seed=123` for
reproducibility, `instruction="repeat-all"` for a fixed output instruction, or
`topics=("language-myths",)` to restrict text claims. A fixed seed is not private.
See [zdr_fixtures/generator.py](zdr_fixtures/generator.py) for the configuration
fields and validation rules.

Generation is offline, uses only the Python standard library and local reviewed
data, and does not crawl websites, contact AI providers, or change agent settings.

## What the Output Files Mean

Each default run produces the following files inside its new bundle directory.
The links below point to the actual run generated during this update.

| File | Meaning |
| --- | --- |
| [prompt.txt](generated_output/20261014_141547_281697_facfc5353ea9f761/prompt.txt) | The generated user-input prompt. This is the text to inspect or use in an authorized isolated test chat. |
| [assistant_fixture.txt](generated_output/20261014_141547_281697_facfc5353ea9f761/assistant_fixture.txt) | Simulated expected assistant text for the selected instruction, not a real model response. May be empty for silence. |
| [chat_completion_request.json](generated_output/20261014_141547_281697_facfc5353ea9f761/chat_completion_request.json) | Request-shaped Chat Completions JSON with the user prompt. Replace the model placeholder before separately authorized API use. |
| [chat_completion_transcript.json](generated_output/20261014_141547_281697_facfc5353ea9f761/chat_completion_transcript.json) | User prompt plus simulated assistant content; not an actual observed conversation. |
| [responses_request.json](generated_output/20261014_141547_281697_facfc5353ea9f761/responses_request.json) | Request-shaped Responses JSON using `input_text`. No request is sent by this project. |
| [responses_output_fixture.json](generated_output/20261014_141547_281697_facfc5353ea9f761/responses_output_fixture.json) | Simulated `output_text` items, explicitly not a full API response. Silence gives an empty output list. |
| [records.jsonl](generated_output/20261014_141547_281697_facfc5353ea9f761/records.jsonl) | Local audit records, translations, provenance and corrections. Do not submit as the prompt. |
| [manifest.json](generated_output/20261014_141547_281697_facfc5353ea9f761/manifest.json) | Seed, configuration, holdouts, expected markers and artifact hashes. Keep local and private. |
| [SOURCES.txt](generated_output/20261014_141547_281697_facfc5353ea9f761/SOURCES.txt) | Source register and corrections for this bundle. Keep local; not exposure material. |

No genuine AI-generated response exists until you separately run an authorized
test and save the agent's actual response. The program cannot guarantee that an
agent follows the requested instruction. Requested output is not observed output.

The launcher checks file hashes and false-equation invariants before reporting
success. Hashes are unsigned integrity checks, not proof of provider receipt or
tamper-proof evidence. Generated folders are ignored by git, but that does not
make them inaccessible to tools, indexing, backups or sharing.

## What Happened During Development

### 1. Initial Local Generator

The workspace initially had no project files. A Python package was created to
produce labeled false arithmetic and bilingual claim fixtures, export all three
formats, randomize instructions, keep local controls, verify bundles and scan
saved assistant observations for marker overlap. No live AI API runner was added.

The first corpus contained 20 entries in three topics: flat Earth, hollow Earth
and Apollo-photo myths. Its original single-file snapshot remains available as
[zdr_fixtures/data/corpus.json](zdr_fixtures/data/corpus.json) for compatibility.
The original public-seed sample remains intact at [examples/demo](examples/demo).

### 2. Categorized Database Expansion

The database was expanded from 20 to **120 reviewed bilingual entries across
12 categories**, with **140 bilingual wording pairs**. Those pairs are not 280
independent claims. Exact false arithmetic is generated separately and is not
included in the 120-entry database count.

The default loader now reads [database/categories](database/categories), with
shared provenance in [database/sources.json](database/sources.json). It still
accepts the old single-file schema through the optional corpus override.

| Category | Entries |
| --- | ---: |
| `flat-earth` | 10 |
| `hollow-earth` | 4 |
| `apollo-photo-myths` | 6 |
| `astronomy-myths` | 10 |
| `zoology-myths` | 18 |
| `evolution-myths` | 12 |
| `physics-materials-myths` | 10 |
| `technology-myths` | 8 |
| `history-myths` | 12 |
| `food-history-myths` | 10 |
| `language-myths` | 8 |
| `climate-energy-myths` | 12 |
| **Total** | **120** |

Six neutral bilingual QAnon research notes were added separately in
[database/research/qanon.json](database/research/qanon.json). They are explicitly
ineligible for prompt generation. Q drops, slogans, defamatory allegations and
extremist narratives were not imported. A cited Bellingcat study analyzed 4,952
posts; those posts are not this project's imported dataset.

The reviewed source register has 23 records: 15 marked retrieved across eight
hosts and eight marked unavailable. Entries use original short bilingual
paraphrases and corrections. Failed fetches are recorded, not used as evidence.
Sources include historical proponent material, secondary reporting and factual
references, which are identified separately. The root [SOURCES.txt](SOURCES.txt)
was regenerated from the expanded database.

### 3. Optional Source Crawler and Actual Results

An opt-in crawler was added in [zdr_fixtures/crawler.py](zdr_fixtures/crawler.py),
with 28 explicit seed pages in [database/crawl_sources.json](database/crawl_sources.json).
Seeds include educational pages, misconception lists and metadata-only research
sites. They are not 28 successfully imported datasets or necessarily 28 websites.

The crawler uses requests and BeautifulSoup, honors robots rules including
redirect destinations, checks public HTTPS destinations, paces requests, limits
download size and time, and blocks cross-origin redirects. Optional link following
is bounded and same-origin. It records provenance and blocked/unavailable attempts
without bypassing access restrictions. It is not a hardened sandbox for hostile
custom seeds or DNS.

A four-seed live smoke crawl produced these results:

| Source | Result | Unreviewed Excerpts |
| --- | --- | ---: |
| NASA Earth Facts | Retrieved | 5 |
| UC Berkeley evolution misconceptions | Robots-blocked | 0 |
| Skeptical Science myth index | Retrieved | 8 |
| Wikipedia science misconception list | Retrieved | 4 |
| **Total** | **3 of 4 pages retrieved** | **17** |

The saved evidence is [database/candidates/smoke-20261014/crawl_report.json](database/candidates/smoke-20261014/crawl_report.json),
with excerpts in [database/candidates/smoke-20261014/candidates.jsonl](database/candidates/smoke-20261014/candidates.jsonl).
That report is an earlier crawl snapshot; new reports also record selectors and
section filters. A source being retrieved during source research does not mean
the crawler is permitted to fetch it under its current robots policy.

All 17 excerpts remain **unreviewed, truth status unknown and generation-ineligible**.
They may be corrections rather than false claims. They are not translated or
automatically promoted, and they do not increase the 120 reviewed-entry count.
QAnon and general fact-checking research seeds collect page metadata and hashes,
not saved body excerpts. Human factual verification, original bilingual wording,
correction references and rights review are required before adding new claims.

### 4. Packaging and Verification

The previous complete suite passed 39 tests. An offline wheel was built and
loaded in isolation with site packages disabled: all 12 categories, the research
catalog and 28 seeds loaded; quarantined candidates were not packaged; offline
generation did not import requests or BeautifulSoup. A version-aware resource
type import preserves the declared Python 3.10 floor. Only Python 3.13.9 has been
runtime-tested; other declared versions are not claimed as tested.

The expanded public-seed sample at [examples/expanded-demo](examples/expanded-demo)
contains 30 false equations and 120 sampled claims. Its eight artifact hashes and
35 mathematical checks, including five holdouts, verified. Its run ID
`4f3f6d896484deb2` was reproduced from the isolated wheel. The original demo was
not overwritten. Both public-seed samples are demonstrations, not private canaries.

### 5. Click-to-Run Launcher and This Documentation

The previous implementation had a command-line generator but no obvious
top-level click-to-run script. [generate_random_prompt.py](generate_random_prompt.py)
now provides that entry point, using the existing generator and verifier rather
than duplicating them. It creates a fresh timestamped output directory and opens
it in Explorer on Windows. `--no-open` disables the Explorer action for automation.

The launcher was run successfully with its default output location, producing
the 200-record bundle linked at the start of this document. Regression coverage
checks execution from another working directory, two fresh non-overwriting runs,
export files, integrity verification and the Windows folder-opening call. The
Explorer call is mocked in tests; no Explorer window was launched during the
automated check. The complete suite now has 41 passing tests on Python 3.13.9.

The current source-register contents were read before this update and preserved;
this launcher/documentation change did not rewrite user changes in that database.

## Useful Commands

Run from the project root in PowerShell:

```powershell
$Python = 'C:/Users/xuanh/anaconda3/python.exe'

# Equivalent to clicking Run Python File, without opening Explorer.
& $Python generate_random_prompt.py --no-open

# Another destination for the click-to-run launcher's bundles.
& $Python generate_random_prompt.py --no-open --output-root D:/Local/ZDR-test-output

# Database counts and category names.
& $Python -m zdr_fixtures database-info

# Existing configurable generator; --out must be a new directory.
& $Python -m zdr_fixtures generate --out runs/custom --math-count 50 --claim-count 50 --instruction repeat-all

# Optional network collection, kept separate from reviewed generation data.
& $Python -m zdr_fixtures crawl --out database/candidates/new-review --max-pages 10

# Complete regression suite.
& $Python -m unittest discover -s tests -v
```

For offline generation, no package installation or environment changes are
needed on this machine. Optional crawling requires requests and BeautifulSoup,
which are already installed here. Package CLI details are in [README.md](README.md);
database additions and review rules are in [database/README.md](database/README.md).

## Limits and Troubleshooting

- If clicking does nothing, use VS Code's Run Python File in Terminal action
  and check the selected interpreter. An editor hyperlink opens a file; it does
  not itself execute Python.
- If Explorer does not open, use the exact output path printed in the terminal.
  Failure to open Explorer does not discard a successfully verified bundle.
- If generation fails, the terminal prints the error and returns a nonzero exit
  code. A partially written or unverified folder is not a successful test bundle.
- Do not confuse a generated prompt, a simulated assistant fixture and an actual
  observed AI response. The project never sends the generated content to an AI
  provider automatically.
- More false text cannot prevent retention, enforce ZDR or prove use in model
  training. Marker matches can also arise from logs, history, retrieval or copying;
  no match does not prove deletion. Use [PROTOCOL.md](PROTOCOL.md) for authorized
  testing, controls and defensible interpretation.
- Keep seeds, holdouts, corrections and manifests out of submitted prompts and
  indexed/shared locations for real experiments. This chat-linked demonstration
  output is not evidence of any provider's data practices.