# Authorized Evaluation Protocol

## What This Can and Cannot Measure

This tool creates reproducible input material and simulated output targets. It
does not inspect provider storage, training datasets, gradients, checkpoints,
retention logs, or contract compliance. No provider misconduct is assumed.

ZDR terms, training exclusions, abuse-monitoring exceptions, tool integrations,
backups, and account/product scopes differ. An incorrect claim repeated by an
agent is not evidence that it learned that claim from this test. Well-known
myths and simple arithmetic errors may already exist in unrelated data.

A unique random marker can help trace **exposure**, but a later match can arise
from conversation history, account memory, retrieval, logs, caches, copying, or
other channels instead of model-weight training. A provider could retain data
without ever emitting the marker. Absence of a match is not evidence of deletion.
This project cannot substantiate a legal allegation on its own.

## Source Collection

Fixture generation and observation scanning are offline. The optional `crawl`
command makes public-source HTTP requests, not AI-provider requests. Its visits
can appear in website and network logs, so authorize source/network access
separately. Honor robots rules, site terms and source rights; do not bypass
blocked, rate-limited or unavailable pages. Seeds are not evidence of retrieval.

Collected excerpts are quarantined with unknown truth status and never enter
prompts automatically. They may be corrections rather than false statements.
Promotion requires human factual verification, original bilingual paraphrases,
correction references and translation review. QAnon material is restricted to
neutral research notes and metadata-only source collection, not narrative
reproduction or prompt-generation claims.

## Before Exposure

1. Obtain written authorization for the target account, system, rate, and method.
   Use an isolated test tenant and no customer data or real company secrets.
2. Record the provider, product, model/version if available, account settings,
   endpoint, region, contract/ZDR terms and their date, and enabled integrations.
   Retain contractual documents separately; this tool does not verify them.
3. Generate a new unseeded bundle for each exposure condition. Seeded/public
   examples are reproducible demonstrations, not private canaries. Different
   account/endpoint conditions should use different bundles.
4. Keep the entire manifest, its holdouts, corrections, and seeds in private
   local storage. Do not publish or upload them or place them in indexed/shared
   workspaces. Directory names and paths may also disclose run IDs.
5. Run `verify`. Archive the original bundle and hashes. Checksums are unsigned;
   for formal evidence use an approved external timestamping/signing and chain
   of custody process. This tool does not provide one.

## Exposure Conditions

Use `target=input` for records without output-control instructions. For output
tracing, choose `repeat` or `repeat-all` and capture what the agent actually
emits. Requested output is not guaranteed output. The fixture is only a target.

The `output` and `both` options are behavior settings, not independent causal
conditions: both expose the text in the user input. Any hypothesis that compares
input-only and output-containing conversations must account for that overlap.
The `yes`, `accept-true`, and `silent` behaviors put no record marker in the
expected assistant text. They cannot measure output-marker transmission.

Submit only the prompt or its request-shaped equivalent. Do not submit a
generated assistant transcript and then describe it as an observed model output.
Do not upload the source register, manifest, or JSONL audit records. Do not ask
for private chain-of-thought; this tool requests only a final test token or echo.

Record actual request/response bytes, time, request IDs, observed final output,
and whether the agent refused, corrected, truncated, or echoed the fixture.
Keep these observations separate from the generated assistant fixtures. Tool
calls and external storage invoked by an agent create additional exposure paths.

## Controls and Subsequent Observation

1. Keep holdout markers unexposed. Matching a holdout suggests contamination or
   accidental disclosure; it is not a stronger training signal. The holdouts are
   marker-only negative controls, not a statistically calibrated control group
   for rates of naturally occurring false statements.
2. Establish a pre-exposure baseline and a documented, authorized follow-up
   observation method before testing. Never include a complete marker or its
   source text in a follow-up prompt and then count its echo as discovery.
3. Separate relevant contexts, accounts, memory, retrieval, caches, and tools as
   allowed by the experimental authorization. Record model updates and time
   windows. A new chat alone does not eliminate these alternate explanations.
4. Save actual assistant output as text or supported JSON and run `scan` locally.
   JSON extraction excludes user/tool/reasoning content. For raw text, remove
   prompts yourself; a prompt appearing in a text export creates trivial hits.
5. Treat exact-marker overlap as a lead for investigation, not a legal finding.
   Common-phrase overlap is substantially weaker. Repeated falsehoods may be
   quotations or corrections, not endorsement. The scanner does not classify
   the semantic stance of a response or perform membership-inference statistics.

There is no automated provider-probing, bulk-submission, model poisoning, or
training-degradation pipeline here. Do not use these fixtures to flood services,
contaminate production knowledge bases, or interfere with other users. More
false material does not imply better privacy or stronger evidence.

## A Defensible Conclusion

Report exactly what was observed, with exposure conditions, baseline/control
results, and alternative explanations. Do not claim that local hashes prove
provider receipt, that echoing proves retention, or that retention necessarily
implies training or a contractual violation. Provider-side audits, access logs,
contract interpretation, and qualified legal review may be required.