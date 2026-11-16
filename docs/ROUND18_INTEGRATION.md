# Round-18 source intake and readiness delta

12 November 2026. Source is owner-supplied code, not authority to change project policy.

## Source reconciliation

All six supplied archives were safely inspected and extracted outside the repo after rejecting links and path traversal. Round 18 contains every file path in the five older archives. `ARCHIVE_COMPARISON_2026-11-12.json` records differences. The source archives themselves remain untouched.

| Archive | SHA256 |
|---|---|
| cyberai_round18_web_eval.tgz | 739c81aa9e7486e24255bed81b121fa6023767eca36507ad4fc23c6e1e7a8799 |
| cyberai_round17b_opus.tar.gz | f9e593cc273c66da48b46a81f6d48cd7e2fbb2bda60c8c0215b7a73971d08174 |
| cyberai_round17_reviewed_lineage_resolved.tar.gz | 0039b4185061a0ea0e5fd0943d21d9355c2a8cabd12e3cdf08fe331321808767 |
| cyberai_round17_opus.tar.gz | d2eecf088cf2ae82d3df3a2677f5dd93c79a999d68c66c1fed64d632690f6caf |
| cyberai_setup_resolved_round17.tar.gz | edfe513ef508b2a1f8e1a78eb2de7a42c7021af7e21c93a2587b4de0ba859568 |
| cyberai_slice1.tar.gz | 025d1e91363e4387bf4c302fa2c07c9de7f3bede87b2c7e67dbfc6c261043119 |

Imported source, fixtures and tests; retained current repository packaging, governance and earlier serving fixes. Did not import cached test results or bundle artifacts as current evidence. `historical_evidence/round17_lineage_verified.json` is supplied historical Hub metadata evidence, not a downloaded-weight verification or GPU result.

## Concrete repairs

1. Training target validation reads train/dev only. Public `heldout` was renamed `challenge`; objective and provenance disclaim generator disjointness. No fresh restricted acceptance data exists.
2. Acceptance usage is a persistent SQLite development ledger keyed by set ID, with model/experiment identity, atomic reservation and immutable stored budget. Recreating a controller cannot reset it. This is bookkeeping, not tamper-proof isolation; a future restricted acceptance runner must use it. Learning/promotion claims remain excluded until that boundary and fresh data are present.
3. Web query/body observations must be captured strings. Explicit empty is valid; missing/null is unevaluable. Synthetic GET fixtures explicitly record an empty body; no runtime telemetry is filled in.
4. Statistical functions validate alignment/types, use a stable exact McNemar computation and distinguish one-family observed gain from supported independent-unit inference. A task-ID API pairs outcomes. Family-bootstrap results must not be combined with an unclustered p-value as if that repaired dependence.
5. Public fixture provenance identifies scenario, split, label and recurring template family. The memorizer now actually passes all train positives and fails challenge. This demonstrates a regression control, not unseen-generator generalization.
6. Explicit web JSONL export and web model-response-to-isolated-verdict smoke are wired. Windows detection remains selectable. The web smoke is detection plumbing, not an offensive environment/retest workflow.
7. Rental elapsed durations use monotonic time; failures survive summary projection and failure artifacts are saved. Actual returned token usage remains required. Sampled memory is labelled sampled, unavailable telemetry remains unavailable, and request-level versus aggregate rates remain distinct.
8. Training sequence length, steps, batch, accumulation and measurement warm-up reach the real Docker argv and trainer. Actual consumed attention-mask/supervised tokens, observed lengths, synchronized optimizer-step times and allocated/reserved CUDA memory are instrumented. Fresh reload uses saved sequence configuration and verifies actual adapter tensors/logit effect. Instrumentation is unexecuted on GPU.
9. Packaged both imported modules; preserved strict warnings/lint, closed file/socket resources, supported Windows spawn without changing the Linux fork path, and retained explicit process-isolation limitations.

No actual GB10 result or learning gain is established by these repairs. The original verifier assurance suite covers its narrow public process/detection fixtures; it does not certify fresh web acceptance, offensive lab outcomes, or the product.

## Current execution evidence

Combined offline run: 201 passed, 2 skipped (optional Torch-dependent checks unavailable here). A web JSONL command emitted three public-fixture examples. Orchestration correctly aborted before any Docker run on unresolved image-dependency pins. Final static checks and any later changes are recorded in the PR validation. No paid compute, GPU execution or purchase occurred.

## Remaining rental gates

Use `PRE_RENTAL_READINESS.md` for exact commands, conditional schedule and remaining blockers. The missing archive is now resolved; separate target-lab readiness, representative verified offensive/defensive data, runtime pins and export destination are not thereby resolved. The historical v1.2 critique brief remains absent and v1.3 is still a proposal.
