# CyberAI project — context handoff to repository-connected Codex

## Current update — 13 November 2026

Live tracker preparation: `rental.live_status` serves a loopback-only dashboard
and read-only JSON API. `track_command.py` publishes atomic running snapshots,
sample history and console logs. Inference preserves per-request usage/failures;
training persists completed-step token/time/memory records. See
`MEASUREMENTS_AND_TRACKING.md` for SSH access and one-variable tuning workflow.
Token rates are measured workload results, not direct DRAM-bandwidth profiling.

Enverge-specific preparation: `ENVERGE_SETUP.md` distinguishes custom GPU Docker
from an already compatible provider GPU environment. `provider_probe.py` records
actual capabilities without installing frameworks or downloading weights. The
existing-environment route remains conditional/manual, with distinct provenance;
Docker lifecycle evidence cannot be fabricated for it. Pinned Hub snapshot sizes
total 92.3 decimal GB before images/outputs; download estimates are conditional.

Windows Docker Desktop is now running. A network-disabled, read-only Linux amd64
Python container passed all five live HTTP reference profiles. See
`RENTAL_START_HERE.md` for its immutable image digest and remaining pre-booking
choices. Earlier statements that Docker is unavailable refer to the prior host
state. No ARM64/GPU image was executed by this rehearsal.

Primary rental scope is hardware validation; follow `RENTAL_START_HERE.md`.
WORKLOAD_DOMAIN=detection uses the lab-free integration path. Shared training
cache now persists across trainer/reload containers. The optional web scope
continues to require the isolated lab and SSH rehearsal.

The actual v1.2 brief is now present. Use `RENTAL_RUNBOOK_2026-11-13.md`
for current commands/status and `CURRENT_PRODUCT_SPEC.md` for reconciliation.
Earlier paragraphs below are preserved historical evidence, not the latest
readiness verdict. Live HTTP target and separate-process iterative tool loop
now pass offline assurance. Four controls plus a real-background long-context
profile are implemented. Export includes the selected freeze and live trajectory;
a durable-mount copy verifies destination bytes. A physical two-machine SSH
rehearsal, actual image pins and all GPU execution remain unverified.

The 220-pass full-suite run resolved the prior localhost mock failure by consuming
request bodies before returning the response. Later additions require the final
validation record in the PR. Optional Torch skips are not GPU passes.

## Repository integration update (12 November 2026)

The six supplied archives are now available and Round 18 has been integrated on `stage-1/round18-rental-integration`, retaining the earlier serving fixes. See `ROUND18_INTEGRATION.md` for exact hashes, repaired/excluded evaluation defects and evidence limits, and `PRE_RENTAL_READINESS.md` for current commands and remaining gates. The imported source is no longer missing. The historical v1.2 critique brief remains absent. The original six issues below are preserved as the historical defect record, not a claim that the repaired code is unchanged.

Offline execution: 201 passed, 2 optional Torch-dependent skips; web JSONL export produces three fixture examples; unresolved dependency pins cause orchestration to abort before Docker. No GPU result, learning gain or offensive lab workflow has been established. Readiness remains NOT READY for the complete product trial until the separate lab, representative verified trajectories and durable export/access arrangements exist. Current code instrumented train/save/fresh-reload/adapter deployment remains GPU-unexecuted.

Updated: 12 November 2026. This is a curated handoff from the owner’s review conversation, not a replacement for the project briefs or the repository’s actual state.

## Product authority update — full v1.2 brief reread

The owner has supplied the actual MASTER_PROJECT_BRIEF_v1.2_FOR_CRITIQUE(1).md and reaffirmed **offensive-first training, followed by defensive capabilities**, plus verified recursive weight improvement. Read it in full. Read PRODUCT_ALIGNMENT_AND_SIX_DOMAIN_CURRICULUM.md alongside it. These supersede any detection-only interpretation of this handoff.

Current discussion is PRODUCT ONLY: exclude commercial positioning and any defensive-first sales argument. Preserve all six domains, with versioned easy-to-hard lab curricula, resource-aware staged activation, and a first web offensive -> verified outcome -> defensive action -> retest workflow. Existing PowerShell/SQLi detection pilots are infrastructure components, not the product's defining scope.

Retain both loops, the native-reasoning model requirement subject to bench-off, verifier assurance, frozen-router/replay/diversity safeguards, sealed promotion and rollback. Record rather than conceal the brief's Loop-B-parking rule versus January deadline conflict and later-phase scope versus June target. The addendum identifies the proposed reconciliation; it does not claim unapproved policy amendments are already agreed.

## Owner direction and delivery targets

Build an open-weight cybersecurity AI across **web, Linux, Windows, Active Directory, cloud and mobile**. Preserve the full six-domain product scope, authorized offensive and defensive work, verification of training evidence, and the optimized v1.2 platform goals.

- Working fine-tuned model target: **15 January 2027**.
- Six-domain product target: **30 June 2027**.
- Before hardware purchase: rent an **actual DGX Spark / GB10 for 24 hours**, test the critical purchase hypotheses, and base the purchase recommendation on measured results.
- Stop the repetitive critique/test-count loop. Fix concrete blockers in the repository; proceed to the prioritized hardware trial. Cloud execution requires provisioned access; it has not happened in the review conversation.
- A 24-hour trial cannot verify every future product hypothesis. It must establish the critical platform capabilities, training cadence, deployment feasibility and practical limits. Dataset work and held-out learning evaluation continue afterward.
- Web is the current January learning-deliverable direction. The existing PowerShell pilot is a Windows/endpoint infrastructure smoke, not web coverage. No new scope confirmation is required merely to continue the instructed web preparation.

## Repository operating approach

Read applicable AGENTS.md and existing handoff instructions. Locate and read the current v1.1/v1.2 design/setup briefs (names mentioned in conversation include MASTER_PROJECT_BRIEF_v1.1.md, BRIEF_v1.2_CORRECTIONS_AND_SETUP.md, MASTER_PROJECT_BRIEF_v1.2_FOR_CRITIQUE.md). Use actual repository files; do not assume their location or content from this handoff.

Inspect git status and reconcile the current branch with supplied archives before modifying anything. Preserve unrelated work. Keep durable instructions concise in AGENTS.md and link this handoff as project context. Do not overwrite existing AGENTS.md wholesale.

## Baseline and model/container candidates

The reviewed Round-17 baseline has a bounded Sigma-subset evaluator, telemetry contracts, process isolation with timeouts, freeze validation, phased rental orchestration and evidence export. Process separation is not a security sandbox. Unit tests and mocked lifecycle tests do not establish GB10 execution.

Pinned trainable candidate:
- unsloth/Qwen3-30B-A3B-Instruct-2507
- commit 41d47883cd854ab6d119fb7cba6e9ed3511886e2

Pinned serving candidate:
- Qwen/Qwen3-30B-A3B-Instruct-2507-FP8
- commit 5a5a776300a41aaa681dd7ff0106608ef2bc90db

Canonical BF16 Qwen revision used for lineage comparison:
- Qwen/Qwen3-30B-A3B-Instruct-2507
- commit 0d7cf23991f47feeb3a57ecb4c9cee8ea4a17bfe

All 16 published weight-shard SHA256 values and complete safetensors indexes matched between the pinned canonical BF16 model and Unsloth mirror. Evidence was artifacts/setup_resolution/lineage_verified.json in the reviewed package; it is now committed as docs/historical_evidence/round17_lineage_verified.json. This is Hub metadata verification, not a local full-weight download/hash. The official FP8 model declares canonical Instruct-2507 as its base. The reviewed freeze records lineage attestation true; actual local assets still require snapshot verification.

ARM64 image candidates (registry identities verified; runtime untested):
- vLLM: nvcr.io/nvidia/vllm@sha256:ecd885a6fa671552021eb2bef16773110ebfa4eb5e24e4a2831bf0f4808ddfea
- Unsloth core: docker.io/unsloth/unsloth@sha256:c3a52373be71e968310d06a99fee54b0006f34dd847ead1bd63709a0d41a3220
- Documented NGC fallback BASE: nvcr.io/nvidia/pytorch@sha256:4a85d8cf6fb3a943280960b8948cf4e9b6eca77b4414c68c9b2c7bb863f79b70

The NGC PyTorch base needs the documented Unsloth/dependency installation; it is not already the complete training stack. Official Unsloth core is a candidate platform change from the NGC recipe and must pass real integration.

Instruct-2507 is non-thinking. Do not silently make it a permanent replacement for the original native-reasoning assumption. Compare task quality, latency and token budget against a thinking candidate at the planned model comparison. No new thinking candidate identity has been verified in this handoff.

The serving-image registry environment reported CUDA 13.4.3.001; actual rental-driver compatibility is unknown. Exact installed image dependency pins remain placeholders until measured inside each image. Do not copy CPU-host versions into GPU-image pins.

## Verified evidence and limits

Earlier Torch CPU host: 133 tests passed, zero skips; actual tiny Llama PEFT save/load, disable-adapter and generate roundtrip passed. This does not prove Qwen MoE/vLLM compatibility or learning gain.

Round 17/17b without Torch: 131 passed, 2 skipped.
Round 18 web package reproduced without Torch: **145 passed, 2 skipped**.
Test counts identify historical executions, not a substitute for testing the current branch.

The Unsloth entrypoint source retrieved from a digest-verified layer ends in exec "$@". Command forwarding is supported at source level; retain its setup/checks. A GPU smoke remains needed; do not introduce an entrypoint override solely because its filename differs from NVIDIA’s entrypoint.

No actual GB10 train, optimized serve, MoE adapter deployment, throughput, memory or learning-gain result has been produced in this conversation.

## Round-18 web work: useful but not accepted as a learning evaluation

Latest supplied archive: cyberai_round18_web_eval.tgz. It adds TelemetrySchema, web request fixtures, rental/web_pilot.py, paired-statistics helpers and an acceptance controller. The following issues were reproduced/reviewed and remain unresolved unless current repository code demonstrates a fix:

1. **Acceptance leakage:** web_pilot.py gates training targets on heldout performance; tests repeatedly inspect that split. Move target selection to train/dev, relabel the current public heldout as regression/challenge data, and create fresh restricted acceptance data.
2. **Optional/resettable access budget:** AcceptanceController is an in-memory object; recreation resets uses and direct scoring bypasses it. Make one documented acceptance runner persist usage by immutable set ID and record model/experiment identity. No claims of tamper-proof access control are needed for this controlled-development ledger.
3. **Missing payload telemetry passes:** WEB_REQUEST_SCHEMA requires Method/UriPath but not observable QueryString/Body. A benign event {Method:POST, UriPath:/search} produced VERIFIED, coverage=1, FP=0 against supplied positives. Define captured-empty versus unavailable fields; reject/classify unevaluable payload evidence.
4. **Statistics input/inference failures:** empty paired vectors raised ZeroDivisionError; unequal vectors IndexError; a too-short family-label vector was silently accepted; a single correlated family produced CI [1,1] and improved=True; McNemar with 1,100 one-direction discordances raised OverflowError. Validate alignment/types/iterations, pair by task ID, use stable exact-binomial computation, and distinguish observed gain from supported inference across independent units. An unclustered McNemar p-value is not repaired by a separate clustered CI.
5. **Disjointness overclaim:** these are hand-authored variants with recurring OR-equality/UNION patterns, not demonstrated generator-disjoint data. Add explicit family/template/scenario provenance. The provided overfit rule fails TRAIN at coverage 1/3, so it does not demonstrate a train-passing memorizer failing heldout. Add a genuine train-pass/challenge-fail control.
6. **Workflow wiring:** make_pilot.py still builds the PowerShell pilot, rental.web_pilot prints a preview rather than a training JSONL, and 40_workload.py hardcodes the Windows objective. Add explicit web export and a web evaluation runner. Untrusted model-generated rules must use evaluate_untrusted_candidate with WEB_REQUEST_SCHEMA, not direct check_rule in the new score_rule_on_split helper.

Preserve the good schema generalisation and regression data. Do not redesign the project or start another cosmetic test round. A clean acceptance boundary matters more than more public fixtures. Hand-authored good-rule results are not model learning evidence.

## Prioritized 24-hour Spark trial

Before billable time where practical: reconcile code, repair concrete offline blockers, prepare data/configs, arrange storage/model caching, and confirm access is actually GB10/ARM64. Do not substitute an unrelated GPU as evidence for the Spark purchase.

On the provisioned machine:
1. Confirm hardware, driver, architecture, available memory/storage and container runtime.
2. Pull the exact image digests. Use full digest and --gpus all for the entrypoint smoke.
3. Run scripts/rental/collect_image_pins.py; review actual per-image CUDA/bf16/import results and candidate dependency pins. Re-pin incompatible images, preserving evidence.
4. Materialise the serving snapshot and verify manifest identity/hashes. Host materialisation imports huggingface_hub; the lightweight project install alone does not provide it. The documented setup includes pip install -e . huggingface-hub.
5. Optimized baseline serve and prioritized context/concurrency measurements, with real usage counts, TTFT/decode/end-to-end separated, errors separate, and observed memory.
6. Stop serving and verify resource release before representative bf16-LoRA training. Explicit TRAIN_MODE=pilot and PILOT_DATA are required; PILOT_DATA alone defaults to pingpong.
7. Train, persist, fresh-process reload, adapter-state verification and local generation on the pinned Qwen model. Measure real completed steps, sequence lengths, seconds/step and memory. Ten toy rows do not establish production cadence.
8. Deploy the actual MoE-target adapter through the pinned serving build and execute a complete model-to-rule-to-isolated-verdict workflow. Distinguish this from quality improvement.
9. Export configs, logs, adapter and evidence with receipt/hash verification; protect export time even when a phase fails.

Purchase recommendation: based on measured required capabilities and realistic workload cadence against owner-accepted criteria. Do not invent a throughput threshold or call a failed/unexecuted gate passed. After a successful purchase decision, continue sustained task-relevant training with held-out evaluation and rollback rather than claiming one rental validates the finished six-domain product.

## Immediate instruction to Codex

Read the actual v1.2 brief, PRODUCT_ALIGNMENT_AND_SIX_DOMAIN_CURRICULUM.md, the current repository and this handoff. Restore the offensive-first complete workflow, specify all six lab curricula, reconcile source/evidence, fix the six concrete web evaluation issues as needed, and prepare the cloud trial. Work on one authoritative branch instead of exchanging successive tarballs. Produce a short readiness summary separating reproduced CPU checks, observed GPU results, unresolved gates and the next executable action. Do not provision paid compute or purchase hardware without the owner’s explicit authorization for that action.
# 12 November 2026 — offline authorised web workflow update

Implemented and tested: the smallest complete owned-lab, offensive-first web
workflow in `lab/web_workflow/`. It is a resettable symbolic authorization-boundary
scenario with an allow-listed action interface, independent deterministic primary
and shadow offensive checks, emitted telemetry, defensive patch plus retest, and
append-only provenance-tagged JSONL storage. Scripted reference evidence covers
success, failed, pre-satisfied and already-patched states. The pre-satisfied
case is explicitly unevaluable and cannot become training data.

`scripts/rental/45_web_offensive_workflow.py` is prepared for the post-adapter
GB10 step. It records real API-reported token counts, action count, monotonic
runtime, task success and failure category. No GB10 execution, model capability,
throughput, or model-weight-improvement claim has been made. The web training
pilot includes a separately labelled, development-only long reference trace;
it reads no challenge/acceptance data and context repetition is labelled as
packing stress rather than coverage.

Remaining GPU-only checks: pinned image and CUDA compatibility, Qwen structured
plan quality, adapter deployment, actual token/runtime/memory measurements,
and train-save-fresh-reload workflow completion.
