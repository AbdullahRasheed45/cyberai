# Decisions to Revisit

This file tracks choices made because of a **current constraint** that will change later. When the trigger fires, work through the matching open GitHub issues (labelled with the trigger, e.g. `revisit-on-dgx`) and resolve each.

**Protocol:** every constraint-driven "for now" decision gets an entry here + a GitHub issue. See `GIT_WORKFLOW.md`.

**Columns:** ID · Decision (what we did for now) · Why now (the constraint) · Trigger (when to revisit) · Action on trigger · Issue.

---

## Trigger group: `revisit-on-dgx` (when the physical DGX Spark is bought & owned)

### R-001 — Stage 0 = GPU work, Stage 1 = non-GPU work split
- **Decision (for now):** The Stage 0/Stage 1 exact runbook is split so GPU-only steps (serving, training, measurement) are front-loaded and non-GPU steps (scaffolding, lab state machine, OPA, targets) are done off-GPU to save rental cost.
- **Why now:** We rent a cloud GB10 hourly (~$0.80/hr), so paying for the GPU to type boilerplate wastes money.
- **Trigger:** Physical DGX Spark owned (no hourly cost).
- **Action on trigger:** Collapse the split back to the brief's natural Stage-0 (pre-work) / Stage-1 (foundation) structure from `SONNET_COMPLETE_BUILD_PLAN.md`. The GPU/non-GPU ordering no longer needs to drive the stage boundaries.
- **Issue:** #3

### R-002 — Ephemeral-instance workarounds (model re-download, persist-to-git)
- **Decision (for now):** Model download is scripted for repeated re-download; all state is pushed to git because the instance is disposable; sessions are structured as tear-down-friendly.
- **Why now:** The rented cloud instance is ephemeral — anything not in git / re-downloadable is lost on teardown.
- **Trigger:** Physical DGX Spark owned (persistent local storage, up to 4TB NVMe).
- **Action on trigger:** Keep the model locally on the Spark's NVMe (no repeated re-download); simplify session structure (no teardown urgency); still keep code in git, but drop the ephemeral-session ceremony.
- **Issue:** #4

### R-003 — Container tags pinned from community/cloud images
- **Decision (for now):** vLLM SM121 and Unsloth NGC container tags are pinned from whatever works on the rented instance.
- **Why now:** We validate on a rented GB10 whose base image/driver may differ from the Founders/retail DGX OS we'll own.
- **Trigger:** Physical DGX Spark owned (its own DGX OS image + driver).
- **Action on trigger:** Re-verify the container tags against the owned unit's DGX OS/driver; re-pin if they differ; re-run the Stage-1 blocker confirmations on the owned hardware.
- **Issue:** #5

---

## Trigger group: `purchase-gate` (the DGX buy decision)

### P-001 — DGX purchase is GATED on cloud validation
- **Decision:** Do NOT order the physical DGX Spark (~£5k) until the rented cloud GB10 confirms, on our own test: (a) vLLM serves Qwen3-30B-A3B FP8, (b) Unsloth fine-tunes the MoE (not CPU-only), (c) measured throughput is acceptable, (d) no unresolved doubts from the brief's BLOCKER list.
- **Why now:** Turning a £5k bet into a ~$20 test. Buy only on evidence.
- **Trigger:** Stage 0+1 DoD met on the cloud instance (blockers confirmed, baseline numbers captured, `stage1_baseline.md` committed).
- **Action on trigger:** Review `stage1_baseline.md`; if the numbers and confirmations are acceptable, proceed to order the DGX Spark. If not, decide: optimise further, change model strategy, or reconsider hardware — BEFORE spending.
- **Issue:** #2

---

### R-005 — GB10 image/backend/LoRA-gate choices are provisional, unverified on real hardware
- **Decision (for now):** `containers/vllm-gb10/IMAGE.txt` pins the official
  NVIDIA NGC image (`nvcr.io/nvidia/vllm:26.10-py3`) as the primary attempt,
  with a community image (`eugr/spark-vllm-docker`) pinned in
  `FALLBACK_IMAGE.txt`; `configs/serving.yaml` defaults
  `attention_backend: "TRITON_ATTN"` and `require_lora_fp8_verified: false`.
  All of this is based on research (see `containers/vllm-gb10/PROVENANCE.md`),
  not a hardware run — upstream vLLM has **no merged** sm_121/GB10 support
  (PR vllm-project/vllm#31740, closed unmerged) as of 2026-11-11.
- **Why now:** no GB10 session was available to this work (rule: do not
  rent paid resources without explicit authorisation); the choices had to
  be made from documentation/community evidence instead of measurement.
- **Trigger:** EITHER (a) a real GB10 session runs the checks in
  `docs/PENDING_HARDWARE_CHECKS.md`, OR (b) vLLM/NGC ship merged, documented
  sm_121 support in a stable release (re-check
  https://github.com/vllm-project/vllm/pull/31740 and its successors).
- **Action on trigger:** run every row in `docs/PENDING_HARDWARE_CHECKS.md`;
  update `PROVENANCE.md` with real `EvidenceKind.HARDWARE` results in place
  of the current research-only claims; if the official NGC image works,
  consider dropping the fallback; if sm_121 support merges upstream,
  re-evaluate whether the Triton-attention-backend workaround and the
  LoRA/FP8 refusal are still needed.
- **Issue:** #9

## Trigger group: `revisit-on-dgx` / lab-available (hardware-dependent foundation work)

### R-004 — Stage 1 foundation (schemas, config, tooling, CI) built with no GB10/lab access
- **Decision (for now):** The Stage 1 "minimal repository foundation" work
  (typed config/result schemas, `configs/lab.yaml`, lint/format/CI, docs) was
  built and validated entirely on the Windows dev machine. No GB10 session
  was rented and no lab laptop was available during this work, so nothing in
  it carries `EvidenceKind.HARDWARE` — see `libs/schemas.EvidenceRecord` and
  `docs/EXECUTION_ENVIRONMENTS.md`. `configs/lab.yaml` and `LabConfig` encode
  policy only; no WireGuard tunnel, state machine enforcement, or target
  container has been run against real hardware.
- **Why now:** rule 8 of the Stage 1 working instructions — do not rent
  resources or start a paid GB10 session without explicit authorisation —
  and no lab laptop was set up at the time.
- **Trigger:** a GB10 session (rented or owned) or the lab laptop becomes
  available.
- **Action on trigger:** run `docs/STAGE_0_AND_1_EXACT.md` Part B (serving
  smoke test, Unsloth smoke test, throughput measurement) and the lab state
  machine/WireGuard checks on the real hardware; replace every `LOCAL`
  evidence claim this foundation produced with a `HARDWARE` one before
  citing it as confirming a brief §19 BLOCKER.
- **Issue:** #7

## Trigger group: `revisit-on-measurement` (when Stage 1.5 measures real volume)

### M-001 — Loop B gate thresholds are pre-registered estimates
- **Decision:** `configs/loopB_gate.yaml` holds pre-registered thresholds (floor 300, aspirational 800, give-up-twice). These are folklore-calibrated estimates, not derived constants.
- **Why now:** We must commit the threshold BEFORE measuring to avoid motivated reasoning (brief §7.8).
- **Trigger:** Stage 1.5 measurement runs; or a ~100-trajectory pilot SFT result exists.
- **Action on trigger:** Apply the two-way revision rule (lower the bar only if a ~100-pilot beats baseline; park Loop B if a full round fails twice). **Do not silently edit the pre-registered numbers** — revise only per the rule, and log the revision here.
- **Issue:** #6

---

## How to add a new entry
1. Append a row under the right trigger group (or create a new group).
2. `gh issue create --title "Revisit: <title>" --body "See DECISIONS_TO_REVISIT.md R-xxx. Trigger: <condition>." --label "<trigger-label>"`
3. Put the issue number in the entry.
4. When the trigger fires, resolve each issue and note the outcome here before closing.

### R-005 — Narrow live web target for the first rental
- **Decision:** Use the resettable standard-library HTTP authorization-boundary
  target and noisy-context development profile to verify rental integration.
- **Why now:** A bounded complete workflow is required before the first GB10 trial;
  the full offensive platform remains gated on the web learning proof.
- **Trigger:** separate lab hardware is available and the first GB10 trial completes.
- **Action:** add independently versioned application families and meaningful
  multi-step trajectories, measure physical isolation/resources, and establish
  fresh restricted acceptance data. Retain this target as a regression control.
  Do not count its background requests as extra independent skill wins.
- **Issue:** #14 (`revisit-on-dgx`).
