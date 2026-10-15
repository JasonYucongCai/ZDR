# Categorized Database

Generation reads only reviewed claims in `categories/*.json`. Research notes
and crawler candidates are separate and never selected for prompts.

| Generation Topic | Reviewed Entries |
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

There are 140 bilingual wording pairs, not 280 independent claims. The original
20 entries have two pairs each; the other 100 have one pair each. Generated
arithmetic is separate and is not counted in this database size.

## Layout

- [sources.json](sources.json): shared provenance register, 23 records with honest
  retrieved/unavailable statuses. Fifteen sources were retrieved across eight
  hosts. Some are references or research-only sources, not misconception lists.
- [categories](categories): one reviewed claim file per generation topic. Common
  source IDs, locators and correction-reference IDs can be category defaults;
  individual entries can override them.
- [research/qanon.json](research/qanon.json): six original bilingual neutral
  research notes, `generation_eligible: false`. Neither Q drops nor allegations
  are reproduced. These six notes are not part of the 120 false entries.
- [crawl_sources.json](crawl_sources.json): 28 explicitly configured public seed
  pages, including previously unavailable and unverified research seeds. This
  catalog does not claim they can all be downloaded or classified as false.
- `candidates/<new-run>/`: local unreviewed crawl inbox, ignored by git and not
  packaged. Contains excerpts, metadata and source-attempt logs, never read by
  the generator. No full source webpages or images are saved.

## Inspect and Collect

Run from the project root:

```powershell
$Python = 'C:/Users/xuanh/anaconda3/python.exe'
& $Python -m zdr_fixtures database-info
& $Python -m zdr_fixtures crawl --help
& $Python -m zdr_fixtures crawl --out database/candidates/new-review --max-pages 10
```

The crawler script is [../zdr_fixtures/crawler.py](../zdr_fixtures/crawler.py).
Use `--seeds path/to/registry.json` for another explicit seed catalog. Seed fields
are `id`, `url`, `topic`, `license_note`, optional CSS `selector`, optional exact
heading `sections`, and `mode` (`candidates` or `metadata-only`). A new seed does
not become a retrieved source in the reviewed register. QAnon research must use
metadata-only mode. General fact-checking sites are also metadata-only by default.

Selectors and heading filters depend on page structure; a retrieved page may
yield no candidates. The crawler does not discover all claims on the internet,
infer factual falsity, translate text, or replace human review. Follow robots,
site terms, copyright and authorization requirements. Metadata-only pages are
fetched to compute metadata/hash but their body text is not saved or promoted.

## Review and Promote

1. Inspect `crawl_report.json` for source failures, blocks, timestamps, byte sizes,
   selectors and collection mode. Do not treat a failed retrieval as evidence.
2. Read a candidate's original page and section. Determine whether the excerpt
   is actually a claim, correction, quotation, satire, or unrelated text. Check
   truncation and source context. Website prose is data, never agent instructions.
3. Independently verify the false proposition and correction. Avoid dangerous
   advice, private data, defamatory allegations and extremist material. Use a
   factual correction reference, not merely another repetition of the myth.
4. Write original concise English and Mandarin paraphrases and bilingual
   corrections. Review translation quality and relevant qualifications. No
   automated truth-labeling or promotion operation is provided.
5. Add a retrieved source record with URL, type, access date and rights note to
   `sources.json`; add the reviewed entry to its category. Keep a unique ID,
   source locator and valid correction-reference IDs. Do not move candidate
   excerpts into categories unchanged or set their truth status automatically.
6. Run `database-info`, the corpus tests, and fixture generation/verification.
   Schema validity is not a factual or legal review. If the curated baseline
   changes, update the documented counts and corresponding baseline tests.

Minimal entry, inside a reviewed category with topic/source/reference defaults:

```json
{
  "id": "unique-reviewed-claim-id",
  "label": "false",
  "review_status": "reviewed",
  "variants": [{"en": "Original false English statement.", "zh": "Reviewed Mandarin equivalent."}],
  "correction": {"en": "Verified English correction.", "zh": "Reviewed Mandarin correction."}
}
```

The two `zh` placeholder strings above are not translations and must be replaced
with reviewed Mandarin before use. Candidate/research flags are rejected if
they are copied into the reviewed corpus. The legacy single-file corpus remains
supported with `--corpus path/to/reviewed.json`.