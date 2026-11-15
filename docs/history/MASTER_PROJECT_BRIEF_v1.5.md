# Autonomous, Self-Improving Cybersecurity AI — Master Project Brief

**Version:** 1.5 (consolidated, self-contained)
**Date:** 2026-11-15
**Supersedes:** v1.4 (same day) and v1.3 as the single current brief. v1.1–v1.3 are kept in `docs/` as history.
**Structure:** **Part I** (§0–§22) — the system, the decisions and the true status. **Part II** (§23–§33) — the recipe for one training generation on one Spark: compute budget, data, training, evaluation. **Part III** (§34–§47) — building the whole system: how repeated fine-tuning on the Spark produces every part of it, each stage explained in detail, and the realistic calendar.
**Status of this document:** prepared for owner sign-off. Where it records an owner decision it says so and cites the decision log; where something is unresolved it is marked **OPEN**. Nothing here claims a result that has not been produced.

**The one-paragraph position.** We are turning an open-weight model (Qwen3-30B-A3B) into a cybersecurity specialist that improves its own weights only from machine-verified experience. The design has not changed since v1.2. What has changed is that the repository now contains a tested, end-to-end *trial pipeline* for the hardware decision, a narrow assured verifier, and a first owned-lab workflow — and **nothing has yet run on a GPU**. The next step is a single authorised ~24-hour trial on a rented GB10; its measured results decide the ~£5k DGX Spark purchase.

**What changed in v1.5 (over v1.4)**
- **Part III added** — how the *complete* system in all the briefs (agent population, both loops, six domains, defence, recovery) is reached by repeated training on the Spark: the generation ladder (§34), every stage in depth (§35–§45), and a realistic calendar that keeps the owner's two target dates and says what each can honestly hold (§47).
- **Part II added** — v1.4 said what and in what order but not *how* on a Spark-only budget. Part II supplies the daily rhythm, the compute arithmetic, and the data, training, evaluation and serving recipes.
- **Working material restored from v1.1** that v1.4 had dropped: refusal handling, the measures for reaching win volume, the diagnosis table, coverage measurement, retention rules.
- **The Spark-only budget stated as a governing constraint** (§23) with its consequences.

**What changed in v1.4**
1. **Owner decisions folded in:** Qwen3-30B-A3B MoE **only** (dense fallback removed); **4-bit QLoRA** is the training default with bf16 as a measured comparison; the trial runs on **Enverge** (a sandboxed container, not bare metal); product-only scope; delivery targets 15 January 2027 and 30 June 2027.
2. **Status made true to the code** (§17): every "built" claim was checked against the repository. Two v1.3 claims are corrected — the web evaluation is *not* generator-disjoint, and the planned `benchmark.py` became a different, larger thing (§2.6).
3. **The trial is specified end to end** (§2.5–2.7, §21): what runs, what is measured, what decides the purchase, and what the trial cannot tell us.
4. **Every stage (0–6) written out** with goal, entry condition, work and definition of done (now Part III), **nine recommended changes** to carry the project forward (§0.1), and a single list of every open decision with its owner (§19).

## 0.1 Recommended changes to carry the project forward

These are the author's recommendations after auditing the repository against the earlier briefs. They are applied in the stages (Part III). Each needs owner approval, and none removes a gate.

| # | Recommendation | Why |
|---|---|---|
| REC-1 | **Split Stage 2 and move its first half before the measurement gate.** The order becomes 1A → 1B → 2A (verifier, sealed set, agent loop) → 1.5 (measure) → 2B (first generation). Build the **sealed web acceptance set first** | The original order measured verified wins/day before the verifier, agent loop and benchmark it depends on existed — circular. It also left "verifier-first" without a sealed set, which blocks every learning claim |
| REC-2 | **Split Stage 1 into 1A (hardware trial on a rental) and 1B (lab foundation on owned hardware)** | Different entry conditions, costs and owners; the purchase decision sits between them |
| REC-3 | **Add an explicit adapter-serving decision after the trial** (adapter on FP8, merged weights, or unquantised serving) | Adapter-on-quantised-MoE serving is unproven anywhere; the plan must not assume it |
| REC-4 | **Keep 15 January 2027 and define it as G1, the pilot generation, with a preliminary measured comparison** (§40, §47); the confirmed proof is end of April | A gain cannot be guaranteed and a small first exam cannot confirm one; a trained, served, compared adapter by that date is achievable |
| REC-5 | **Keep 30 June 2027 as a milestone but define it honestly:** web attack and defence, Linux at Levels 1–2, the other four domains specified. Six trained domains: end of 2028 (§47) | No domain may train before its verifier exists, and Windows, AD and mobile each need a heavy lab; six domains by June is not achievable by one builder on one Spark |
| REC-6 | **Adopt heavy infrastructure only when a stage needs it** (the registry starts as hashed, immutable directories; MLflow and PostgreSQL later) | Unused dependencies were already removed; less surface before the proof |
| REC-7 | **Replace the year-long parking rule with diagnose-and-suspend-promotion** (§7.8, D-3) | The park contradicts the January commitment; suspension keeps the safety intent |
| REC-8 | **Give the removed dense model's debugging role to small first runs on the same MoE**, with bf16 as the precision fallback | The dense fallback is gone by owner decision; its "forgiving first baseline" role still needs an answer |
| REC-9 | **Supply representative training data for the trial** if at all possible | Seven short examples prove the pipeline but cannot forecast training cost, which is the purchase question |

Markers: **DECISION** (settled, with reasoning) · **OWNER DECISION** (settled by the owner on the date given) · **OPEN** (unsettled) · **HONEST LIMIT** (a permanent boundary against overclaiming) · **STATUS** (what exists today).

**Document map:** §0.1 recommended changes → §0.5 cost → §1 definition → §2 hardware, trial, purchase gate → §3 failure classes → §3.5 threats to the platform → §4 model → §5 serving → §6 verifier → §7 learning engine → §8 curriculum → §9 agents → §10 speed approaches → §11 offensive/defensive + authorisation → §12 lab → §13 observability → §14 rollback → §15 capability boundaries → §16 stack and code architecture → §17 status and roadmap → §18 commercial (deferred) → §19 open decisions → §20 governance → §21 verified setup appendix → §22 document index. **Part II:** §23 budget constraint → §24 daily rhythm → §25 compute budget → §26 producing experience → §27 data → §28 training → §29 evaluation and promotion → §30 serving → §31 diagnosis → §32 the path, in order → §33 risks. **Part III:** §34 the system and the generation ladder → §35–§45 each stage in detail → §46 standing rules → §47 the realistic calendar.

---

## 0.5 Cost of build, not just cost of iron

**HONEST LIMIT:** The hardware costs ~£6k. The *labour* is a multi-person, multi-year research-and-product programme: 16+ services, a verifier suite across six domains, a two-loop learning engine, a malware lab. Treating it as "£6k and one builder" is the most dangerous miscommunication available.

Rough solo person-months: Stage 1 foundation 1–3 · Stage 1.5 gate 0.5–1 · Stage 2 verifier (one domain) + first SFT 2–4 · Stage 3 defensive 3–6 · Stage 5 recursive engine 6–12+ · Stage 6 commercial 6–12+.

**DECISION — one critical path.** Collapse ambition to one proof: *a deterministic, assured verifier for ONE domain (web) plus one SFT generation that measurably beats a sealed benchmark.* Everything else — population, GRPO, six-domain learning, commercial — is Phase 2 and contingent on that proof.

**Six-domain lab vs the proof.** The owner has directed that the product keeps all six domains and that their curricula be specified now. This is *inventory and infrastructure*, not *learning breadth*: the Phase-1 learning proof still gates on web only (§8, §12).

**OPEN (owner) — targets vs the estimates above.** The owner's targets are a working fine-tuned model by **15 January 2027** and a six-domain product by **30 June 2027**. These are targets, not demonstrated feasibility; against the person-month estimates they are aggressive. §40 and §47 state what "working fine-tuned model" can honestly mean by January. The six-domain June target needs per-domain acceptance depth defined before it can be planned (§19 D-6).

---

## 1. Project definition

### 1.1 What we are building
A cybersecurity platform on an open-weight model specialised into a cybersecurity expert, operating as a large *logical* population of agents cycled through one shared serving endpoint (never many concurrent model copies), that improves its own **model weights** through **verified** recursive fine-tuning and, later, RL.

**Dual-track, offensive-led in training.**
- **Offensive (authorised only):** find and prove weaknesses in owned or authorised systems — environment-checked, never self-reported. Training leads here: the offensive agent is the *data engine*, producing machine-confirmed ground truth.
- **Defensive:** detect, triage, investigate, remediate, verify recovery — learned on top of, and fed by, the offensive signal. Both sides of the verifier are built early; "offensive-first" is the learning priority, not a rule that defence must wait.

The workflow, end to end: scenario → offensive investigation → environment-verified outcome → defensive detection/remediation → independent retest → provenance-tagged experience → candidate weight update → sealed evaluation → promotion or rejection.

### 1.2 Central objective
> An already-trained open-weight model becomes a specialised cybersecurity agent, gains experience through a population of agents, and progressively updates its actual weights through verified recursive fine-tuning — with **human approval before any production change** and **enforced, ownership-verified authorisation before any offensive action.**

### 1.3 Explicitly NOT building
Not a from-scratch foundation model · not a tool that attacks anything reachable (autonomous offence is confined to the owned, isolated lab) · not a stripped/"uncensored" model · not a system that trains on its own unverified outputs · not a product claiming certainty on novel threats or reasoning gains it is not making.

### 1.4 Scope of current work (OWNER DECISION, 12 Nov 2026)
**Product only.** Commercial positioning, pricing, customer segments and sales arguments are excluded from current work and must not drive architecture or training priority (§18 is retained as a deferred note).

---

## 2. Hardware, the trial, and the purchase gate

### 2.1 Committed plan
**DECISION:** one DGX Spark (GB10 Grace Blackwell, 128 GB unified memory, 273 GB/s, 20-core ARM, up to 4 TB NVMe) as the *engine* (serving, agents, training, evaluation, verifier), plus the existing HP laptop upgraded to 32 GB as the *isolated lab* (targets, later malware detonation). A 64 GB lab mini-PC is a probable later line item once heavy Windows/AD environments run (§12).

### 2.2 The four bottlenecks
1. **Memory bandwidth governs everything.** Community reference for this model on GB10: ~44–85 tok/s single-stream, ~290–310 tok/s batched; decode falls with context depth. Batched swarm is the best case — and our workload.
2. **Shared CPU/GPU memory.** One pool: CPU work competes with generation, and `nvidia-smi` cannot report GPU memory on this machine (it reads `[N/A]`). All our memory checks therefore read host memory and say so.
3. **Modest compute** (≈ RTX 5070-class): an inference/memory box, not a training monster.
4. **Single GPU.** Serving and training cannot overlap; the lifecycle enforces serve → release → train.

**HONEST LIMIT:** the figures in (1) are other people's measurements on other units. None is ours until the trial runs.

### 2.3 Honest limits
128 GB is on-package and not upgradeable. External storage is for backups only. No free always-on cloud hosts a custom model.

### 2.4 Budget
DGX Spark £4,889–£5,250 · HP RAM £35–55 · backup storage £100–150 · UPS £0–150 · network £20–40 · ~10% contingency → **~£5,100–£6,250.** Trial rental: Enverge advertised **$0.85/hour** (24 h ≈ $20 before tax); the portal price applies.

### 2.5 Cloud-first before purchase — the gate
**DECISION:** do not order the Spark until a rented GB10 has shown, on our own run: (a) vLLM serves Qwen3-30B-A3B FP8; (b) the model fine-tunes on GPU (not CPU-only torch); (c) the trained adapter reloads and deploys; (d) measured throughput and memory are acceptable to the owner. Decision log: P-001 (issue #2).

**What decides it.** `scripts/rental/summarise_trial.py` builds `docs/stage1_baseline.md` from the trial's own result files. The report contains no verdict. Its first section is the **owner's acceptance criteria, to be written before reading the numbers** — hours per training round, minimum serving throughput, whether adapter-on-FP8 serving is required. **OPEN (owner, D-1):** these criteria are not yet set.

### 2.6 The trial pipeline (STATUS: built, tested offline, never run on a GPU)
v1.3 planned a single `benchmark.py`. What was built instead is a phased, evidence-producing lifecycle (`rental/`, `scripts/rental/`), because the purchase question is "does the whole serve → train → deploy cycle work on this machine", not only "how fast".

One command (`python -m rental.orchestrate`, run under the tracker) executes, in order:

| Phase | What it does | What it proves |
|---|---|---|
| preflight | Confirms GB10 + aarch64, exact image digests, in-image CUDA/bf16 and library versions against the pins, and the local model snapshot hash-for-hash against the pinned commit | We are testing the machine and artefacts we think we are |
| serve base | Starts vLLM with the FP8 model; waits for readiness; checks served identity | Blocker 1 (serving) |
| measure | Single-stream latency/TTFT/decode rate; context × concurrency grid; sampled peak memory | Real throughput on our unit |
| release | Stops the server; verifies memory returned to baseline | Serve/train can alternate on shared memory |
| train | LoRA fine-tune in the Unsloth image, then a fresh-process reload that checks adapter tensors, logits and generation | Blocker 2 (training), save/reload |
| serve + adapter | Restarts vLLM with the trained adapter attached; checks identity | Adapter deployment on the FP8 MoE model (unproven anywhere — see below) |
| workload | Model → rule → isolated verdict (detection), or the live lab workflow (web) | Plumbing end to end; not model quality |
| export | Hash-manifested bundle, verified against archived bytes, copied and read back | Evidence survives an ephemeral instance |

Design properties, each covered by tests: fail-closed pins (the template freeze deliberately contains `FILL` versions that only an in-image probe may resolve); export runs even after a failure; failed or slow measurement cells are recorded as data rather than aborting; a timeout or dropped session stops containers and exports partial evidence; every run is isolated by `RUN_ID`; no LLM appears in any check.

Also built: a serving-capacity sweep harness (`scripts/bench/run_benchmark.py`) and a read-only live tracker (`rental.live_status`) showing lifecycle phase, server logs, host memory, training steps and request metrics.

**The most important unknown.** Serving a LoRA adapter on a *quantised MoE* model is not established: upstream vLLM closed the relevant request "not planned", and a same-family attempt produced garbage. The lifecycle therefore treats that phase as an experiment whose failure is a first-class finding, and `configs/serving.yaml` keeps `require_lora_fp8_verified: false` until a correctness review passes (R-005, issue #9). If it fails, the fallback to evaluate is serving merged weights or serving the adapter on unquantised weights — a decision for after the trial, not an assumption now.

### 2.7 The provider: Enverge (OWNER-CONFIRMED, 13 Nov 2026)
Real GB10 hardware, but the SSH session lands **inside an unprivileged container**, not on the host, without root. Docker runs inside it (Docker-in-Docker) and the NVIDIA runtime is in no-cgroups mode, so the usual `--gpus all` fails.

**DECISION:** no Docker flag is hardcoded. `scripts/rental/docker_runtime_setup.py` measures, on the machine, which GPU mode works (`--gpus`, `--runtime nvidia`, or CDI), whether shared memory and raised limits are permitted, whether a container can read and write the checkout at the same path, whether all of those work *together*, and how a container port is reached. Every container the project starts takes its flags from that measurement, and every Docker-using step refuses to run in a shell where the measured settings were not loaded. Decision log: R-010 (issue #19).

**HONEST LIMIT:** the trial validates the GB10 *hardware and software stack*, in Enverge's container. The owned unit's OS image may differ; the same pipeline must be re-run on it (R-003).

---

## 3. Failure-class reasoning (incident as illustration, not foundation)

**DECISION:** each safety rule stands on its own logic as a known failure class; any single reported incident is an illustration, so the architecture survives if a story's detail is wrong.

- **Reward hacking / specification gaming** → reward only from deterministic environment truth.
- **Containment failure** → the loop stays local; sealed components are unreachable by what they judge; everything is logged.
- **LLM-grading-LLM** → no LLM in any reward, verifier, authorisation or promotion decision.

This is why offensive reward is environment-checked and never self-reported, and why autonomous offence is lab-confined.

---

## 3.5 Threats to the platform itself

| Threat | Mitigation |
|---|---|
| Poisoned external datasets | Treat as untrusted: screening, known-truth canaries, never train directly on unvetted public data |
| **Authorised-scope abuse** — a "client" lists targets they do not own | **Ownership verification, not token-trust:** DNS/HTTP challenge, WHOIS/RIR, signed attestation. In the gate design from the start; no live external engagement without it |
| OSS supply-chain compromise | Images pinned by digest, models by commit, dependencies locked; versions read from inside the images, never assumed |
| Model-weight exfiltration | Encryption at rest, access control, egress monitoring; weights and credentials never on the lab machine |
| Scope breach by an autonomous agent | Incident-response playbook required before the first real external target, pilot included |

---

## 4. Model strategy

### 4.1 The model (OWNER DECISION, 13 Nov 2026 — R-009, issue #18)
**Qwen3-30B-A3B, mixture-of-experts, is the only model.** ~30.5B parameters with ~3.3B active per token (128 experts, 8 active, 48 layers): 30B knowledge at roughly 3B token-speed, which is what a bandwidth-limited machine needs. Apache 2.0.

The pinned release is **Instruct-2507** (July 2025) — verified on 13 Nov 2026 to be the newest Qwen3-30B-A3B text release on the Hub. It is the model for the 15 January 2027 target.

| Role | Repository | Pinned commit |
|---|---|---|
| Serving | `Qwen/Qwen3-30B-A3B-Instruct-2507-FP8` | `5a5a776300a41aaa681dd7ff0106608ef2bc90db` |
| Training base | `unsloth/Qwen3-30B-A3B-Instruct-2507` | `41d47883cd854ab6d119fb7cba6e9ed3511886e2` |
| Lineage reference | `Qwen/Qwen3-30B-A3B-Instruct-2507` | `0d7cf23991f47feeb3a57ecb4c9cee8ea4a17bfe` |

Lineage: all 16 weight-shard hashes and the full tensor index of the Unsloth copy match the canonical BF16 release (Hub metadata, recorded in `docs/historical_evidence/`), and the FP8 release declares that same model as its base. The adapter is therefore trained on the weights the serving checkpoint was quantised from. Local files are still hash-verified at preflight.

### 4.2 No dense fallback
The Qwen3-14B dense fallback in earlier briefs is **removed**. If the MoE path fails on the hardware, that evidence goes to the owner; an alternative model is an owner decision, never an automatic switch.

### 4.3 OPEN (owner, D-2) — Instruct vs Thinking
Instruct-2507 does not produce reasoning traces. Earlier briefs required a *native-reasoning* model, and multi-step exploitation is reasoning-heavy. `Qwen3-30B-A3B-Thinking-2507` exists in the same family (same MoE-only decision). The planned comparison — task quality, latency and token cost on offensive and defensive tasks — has not been run, and the current pin must not be read as settling it. It belongs after the trial, at the first evaluation that has real tasks (§38).

### 4.4 Serving and size principle
One shared vLLM endpoint; personas are LoRA adapters, not model copies. MoE reads far fewer bytes per token than a dense model of the same knowledge; the price is that it is fussier to fine-tune (router drift), handled by the frozen-router policy (§7.7).

---

## 5. Serving stack and speed levers

### 5.1 Decisions
- Serve at **FP8**. Train at higher precision or QLoRA; quantise only for serving. NVFP4 only if our own benchmark shows quality holds.
- Continuous batching and prefix caching always on.
- **Single source of truth:** every vLLM launch takes its engine flags from `configs/serving.yaml` (memory utilisation 0.85, context 32,768, 4 concurrent sequences as a conservative start, attention backend).
- **Attention backend:** upstream vLLM has no merged GB10 (sm_121) kernel support; the config forces the Triton backend as the reported-working path and allows `auto` for a one-variable comparison. Unverified on our unit (R-005).

### 5.2 The quadrant arithmetic
Batching and long context spend the *same* KV-cache budget in opposite directions. **The learning loop lives in the expensive quadrant** — hard, long-context tasks — so cadence must be sized from that, not from the flattering batched figure. Speculative decoding is an alternative to heavy batching, not a multiplier on it.

### 5.3 Context as a dial
32K native. Most agents 8–16K; long context reserved for hard tasks. The trial measures 8K and 16K at concurrency 1/8/32 by default.

### 5.4 HONEST LIMIT
We cannot reach general frontier reasoning. What is achievable and documented: sharpening a strong model into a narrow specialist on verified rewards.

---

## 6. The verifier — the foundation

### 6.1 Principle
**Build the verifier before anything that trains or is scored.** Task classes, offensive and defensive:
- **Exploitation (lead signal):** did the objective actually fall — binary, environment-checked.
- **Detection:** true/false positives against labelled telemetry — including the telemetry the offensive side generates.
- **Triage · vulnerability prioritisation · remediation** (hole closed *and* service alive).

The LLM critic is advisory only. Reward-hack guards: penalise false positives, require service-alive, read real state, never reward a condition that setup had already satisfied.

### 6.2 Candidate bank
Unverifiable novelty is escrowed — never rewarded, never deleted — until the verifier grows to cover it. **HONEST LIMIT:** growing the verifier is human-paced engineering; it is the true rate-limiter of the whole programme.

### 6.3 Verifier assurance — who checks the checker
A deterministic verifier can be confidently wrong, so its correctness is treated as safety-critical: a ground-truth seed suite, planted false positives, dual-checker disagreement alarms, and versioning with a re-run on every change. A failing verifier cannot enter the loop.

### 6.4 STATUS — what exists (corrected from v1.3)
**Built and tested (`detection_verifier/`):** a bounded Sigma-subset rule evaluator; telemetry schemas for process-creation and web-request events, where a missing payload field is *unevaluable* rather than a pass; process isolation with timeouts for untrusted model-written rules; an assurance suite (good, trivial, overfit, incidental, broken and bypass rules); a persistent acceptance-budget ledger; paired statistics (exact McNemar, cluster bootstrap) that refuse misaligned or single-family inputs.

**Built and tested (`lab/web_workflow/`):** one narrow owned-lab scenario — a small real HTTP application with an authorisation-boundary flaw and an audit log. It has primary and shadow offensive checks (response versus audit), a controller-applied patch, an independent retest (cross-account blocked, owner still works, service healthy), and controls for failed, pre-satisfied and already-patched states. The pre-satisfied case is unevaluable and can never become training data.

**Corrections to v1.3:**
- The web evaluation is **not generator-disjoint.** The fixtures are hand-authored variants with recurring patterns. The public "held-out" split was renamed **challenge** and is regression data only. A memorising rule does pass train and fail challenge — a regression control, not evidence of generalisation.
- **No sealed benchmark exists.** No fresh restricted acceptance set, no runner. Until it exists, no learning or promotion claim may be made.
- Process isolation is **not a security sandbox**; the lab's response and audit paths share one trusted controller, so they are two observations, not two trust roots.

**Not built:** an exploitation verifier beyond the one scenario; any verifier for Linux, Windows, AD, cloud or mobile; the `verifier_service` itself.

---

## 7. The learning engine

### 7.1 Data flow
lab scenario → agents (shared endpoint, adapter = gen N) → trajectory store → **assured** verifier → {verified → training data | failed → analysis | unverifiable → candidate bank} → dataset builder (dedupe, poison screen, seed replay, diversity cap) → SFT → [gated] GRPO → sealed evaluation (unreachable by the learning engine) → promotion gate + human approval → immutable model registry.

### 7.2 The two loops
- **Loop A (fast):** strategy, configuration, retrieval over verified facts — how to use the brain.
- **Loop B (slow, gated):** weights gen N → N+1 — the brain itself, and the point of the project.

**HONEST LIMIT:** under Loop A alone there is no new reasoning capacity beyond what verified volume supports; effective performance rises through elicitation. Retrieval over verified facts is Loop A, not fine-tuning.

### 7.3 Anti-collapse
Verified-only training · seed replay · sealed benchmark · forgetting canaries · statistical gate · provenance tags · deterministic rewards · **frozen router** · diversity cap. GRPO only after one SFT generation beats baseline.

### 7.4 Training method (OWNER DECISION, 13 Nov 2026 — R-008, issue #17)
- **Default: 4-bit QLoRA.** The frozen base is loaded in 4-bit NF4 (≈17 GB instead of ≈61 GB), quantised on load from the *same pinned repository and commit*, and LoRA adapters train in bf16 on top. This leaves most of the 128 GB for context and batch.
- **bf16 is a measured comparison only** (`TRAIN_PRECISION=bf16`). Adopt it only if its tokens/sec is clearly better with memory headroom. FP8 training is not used.
- Hyperparameters live in `configs/training.yaml` and are what the trainer actually reads: rank 16, alpha 32, targets `q/k/v/o_proj` and `gate/up/down_proj`, learning rate 2e-4, linear schedule, seed 3407. The training targets must equal the freeze's adapter targets or the run refuses to start.
- Guards before training time is spent: the loaded model must be the pinned one (Unsloth must not substitute a pre-quantised repository); every router parameter must be frozen; no fp16; token and step counts are measured from real batches, never from configured maxima.

**HONEST LIMIT:** 4-bit training on GB10 depends on `bitsandbytes` working on aarch64/CUDA 13 inside the pinned image — unverified. If it fails, the bf16 run is the immediate fallback and the finding is recorded.

### 7.5 Cadence
One generation every few days at most; tiny-batch frequent fine-tuning is collapse. Serve by day, train by night, gate in the morning. A 3-day cadence is a target that depends on the measured training rate (§2.5).

### 7.7 MoE fine-tuning policy
Fussiness is a *trend* (benchmark fails across generations on clean data, unstable loss, expert-load collapse). Fixes gentlest first: lower learning rate → freeze the router → small auxiliary loss → clip/warm-up. Freezing the router is Unsloth's default and our standing policy; the trainer verifies it rather than assuming it.

### 7.8 Loop B as a pre-registered hypothesis
**DECISION:** Loop B is the committed goal, switched on only when measured verified volume clears a bar written down in advance (`configs/loopB_gate.yaml`, M-001, issue #6).

- **Floor:** ≥300 verified, unique, non-trivial wins/day sustained about a week, no scenario template above 15%.
- **Aspirational:** 800/day. **HONEST LIMIT:** very likely beyond one Spark early; never padded.
- **Lower the bar** if a ~100-trajectory pilot SFT measurably beats the sealed benchmark.

**OPEN (owner, D-3) — the parking rule conflicts with the January target.** As written, two failed full-volume rounds park Loop B for a year. The owner has since committed to a working fine-tuned model by 15 January 2027. Both cannot govern. **Proposed amendment (not yet approved):** two failures trigger diagnosis and suspend *automatic promotion*, while controlled first-SFT research continues toward January. Until the owner decides, neither rule may be applied silently.

**OPEN (D-4):** difficulty does not establish novelty. Template rotation (a new hostname or seed) is not a new skill win; diversity must be measured by scenario family and behaviour.

---

## 8. The curriculum controller (difficulty-led, six domains)

**DECISION:** self-advancing; lab difficulty is the primary driver, held ahead of the model's success rate. It curates *what* (targets, difficulty), never *how*; keeps a free-exploration reserve; regresses to easier tasks when failures show missing prerequisites; logs every change.

**Five levels per domain** (as specified in `configs/six_domain_curriculum.yaml`): 1 fundamentals/mapping → 2 single seeded weakness → 3 multi-step → 4 realistic constraints (state, noise, limited visibility) → 5 withheld variants for generalisation.

**Domain axis, cumulative:** web → Linux → Windows → Active Directory → cloud → mobile (Android first; iOS app-level only). Earlier domains stay mixed in.

Every scenario needs an assurance contract: domain, family, level, allowed actions, image and seeds, ownership and reset procedure, starting state, a hidden success predicate with two evidence paths where possible, required telemetry and how missing telemetry is classified, the paired defensive task, patched and negative controls, and its data split.

**STATUS:** the curriculum file is a validated *inventory*: web is `implemented_offline_reference` (one scenario), the other five are `planned`. The controller service is not built. A manifest entry never implies an environment exists.

---

## 9. Multi-agent population and cooperation (Phase 2)
An agent is a lightweight configuration; a large logical population cycles through one endpoint. MAP-Elites for diverse specialists; hybrid cooperation (blackboard for hard targets, distributed across targets); containment by sanctioned, logged channels and an unreachable verifier. Not started; gated on the Stage-2 proof.

## 10. The three speed approaches (Phase 2; measure first)
Cross-agent sharing → verified-fact caching (Loop A, not fine-tuning) → small-model routing. Not started.

---

## 11. Offensive/defensive tracks and the authorisation gate

Separate **skill** (we want full attacker reasoning) from **authorisation** (enforced in code, ownership-verified, never a prompt).

**Hard boundaries:** autonomous exploitation is confined to the owned lab; a human is in the loop on any live-production offensive action; ownership is verified before any external engagement; every action is logged. Three policy tiers (read-only auto / sandbox auto / production = human-signed token bound to the action hash); the model holds no production credentials. Internet: none by default; mediated, read-only, allow-listed, logged.

**Coverage is measured honestly** against ATT&CK (offensive catalogue and ground-truth labels) and D3FEND (defensive coverage): "handles X of the Y techniques for which we have built lab scenarios" — never a claim about techniques with no scenario. Refusal handling is in §26.

**STATUS:** the built lab tool interface is an allow-list of four named actions against one loopback target with a 12-action cap; it accepts no URL, command or arbitrary payload. The OPA policy service and ownership verification are not built and are not needed until a real external target exists.

---

## 12. The lab

**DECISION:** the lab is a physically separate machine. Targets and malware never share a machine with the model, verifier answer keys or credentials. Link: WireGuard, firewalled engine → lab only. Malware detonation and tunnelled target-serving are **mutually exclusive states enforced in code.**

**Planned environments by domain** (task specifications, not attack recipes): web (DVWA → Juice Shop → hardened custom) · Linux (vulnerable containers → privilege-boundary labs) · Windows (misconfigured hosts → defended endpoint) · AD (single domain → multi-forest) · cloud (local emulation, with real provider sandbox only where provider semantics matter) · mobile (Android emulator and owned apps).

**HONEST LIMIT:** six labs will not run together on 32 GB. Light pools (web, Linux, cloud emulation) run in parallel; heavy environments are sequenced; an AD scenario needing several hosts must run its whole topology or be reported as not covered.

**STATUS:** one real target exists — the standard-library HTTP application, run by a separate worker process and reachable over SSH from the engine. `lab/` imports nothing from the engine side (enforced by review and by the layout). **Not done:** the two-machine SSH rehearsal, WireGuard, the lab state machine, every other target. The lab is **optional for the hardware trial**, which uses the lab-free detection workload (R-006, issue #14).

---

## 13. Observability, logging, retention
Six logging groups per generation: training process · MoE routing · evaluation · data lineage and curriculum state · verifier health and assurance results · configuration and environment. Version the environment per generation; change one external at a time.

**STATUS:** for the trial, every run records its resolved configuration, exact commands, Docker settings, phase timeline, per-request and per-step measurements, memory source, model and data hashes, and library versions, in a hash-manifested bundle. The six-group generation logging belongs to the learning engine and is not built.

## 14. Rollback and resume
Every generation is an immutable snapshot; golden anchors; diagnose → roll back → fix the specific cause → resume. **STATUS:** adapters are saved per run and never overwritten; they support inference and a fresh-optimiser restart, not faithful optimiser-state resume. The model registry is not built.

---

## 15. Capability boundaries — true vs overclaim
Learn known techniques (real, measurable) · discover variants within testable environments (real, bounded by verifier reach) · invent new attack categories unsupervised (overclaim) · certainty on a zero-day at first sight (impossible) · exponential self-improvement (myth — a staircase waiting on human-paced verifier growth). Mobile: Android buildable; iOS app-level only.

**What the current repository establishes:** that a pipeline exists and behaves correctly under test. **What it does not:** any GPU result, any model capability, any learning gain, any coverage beyond one web scenario.

---

## 16. Stack and code architecture

**Stack (all open source):** vLLM (serving) · Unsloth + TRL + PEFT + bitsandbytes (training) · pydantic-typed YAML configuration · Docker images pinned by digest · later: MLflow, PostgreSQL, OPA, and the security tooling of Stages 3–5.

**Pinned images (registry identity verified; never run on a GPU):**
- Serving: `nvcr.io/nvidia/vllm@sha256:ecd885a6…08ddfea` (NGC 26.10)
- Training: `docker.io/unsloth/unsloth@sha256:c3a52373…1a3220`
- Documented fallback serving image: `eugr/spark-vllm` (re-pin at use)

**Target architecture (unchanged):** each service layered `api / domain / infra`; `domain` is pure logic; cross-service calls through typed clients; no LLM in verifier, authorisation or gate code; `lab/` never imports engine code; the learning engine never reads sealed scenarios.

**STATUS — the code as it stands (R-011, issue #20):**

| Path | Contents |
|---|---|
| `libs/schemas`, `libs/common` | Typed configuration and evidence schemas; the config loader; the shared vLLM flag renderer |
| `configs/` | serving, training, lab, Loop-B gate, curriculum, benchmark — each validated by a test |
| `detection_verifier/` | The assured detection verifier (§6.4) |
| `lab/web_workflow/` | The lab target, worker, tools and verifier (§12) |
| `rental/` | Trial lifecycle: plan, orchestrate, Docker runtime, freeze validation, probe, snapshot, telemetry, tracker, export |
| `scripts/rental/`, `scripts/bench/`, `scripts/gb10/` | Trial steps, capacity benchmark, serving helpers |
| `services/*` | **Empty placeholders** |

The trial-era packages sit at the top level rather than inside `services/`. This is a recorded, temporary deviation: at Stage 2 `verifier_service` is built to the target shape with `detection_verifier` as its domain core; `rental/` remains a trial tool.

---

## 17. Status and roadmap — summary

**Every stage is written out in detail in Part III (§34–§47)**, with what is built, what the Spark trains, how success is checked, what can go wrong, and realistic dates. This section is the summary.

### Status at 15 November 2026

| Stage | In one line | State |
|---|---|---|
| 0 Pre-work | Scaffold, schemas, governance | **Done** (merged to `main`) |
| 1A Hardware trial | Serve, train, deploy and measure on a rented GB10 | **Prepared and tested offline; not yet run** |
| 1B Lab foundation | Two-machine link, lab state machine, web targets | One target built; link not started |
| 2A Verifier and loop | Sealed web set, verifier service, agent loop, more scenarios | Components only (§6.4) |
| 1.5 Measurement gate | Verified wins/day vs the pre-registered bar | Not started |
| 2B The proof | First generations vs the sealed web benchmark | Not started |
| 3–6 | Defence, recovery, recursive engine, commercial | Not started; gated on 2B |

Validation of what exists: lint clean; 327 tests pass on Linux as CI runs them, plus 38 PyTorch-dependent checks run separately on CPU; the trial's container commands and the Docker setup script were rehearsed against a real Docker daemon without a GPU; preflight's checkpoint rules were checked against the real pinned model configuration. **None of this is GPU evidence.**

Repository: five stacked pull requests (#8 → #11 → #10 → #13 → #15), all mergeable, awaiting owner review. The trial does not need them merged; it clones the top branch.

### Order of work

Phase 1 (the proof): **0** pre-work (done) → **1A** hardware trial → **1B** lab foundation → **2A** verifier and loop → **1.5** measurement gate → **2B** first generations. Phase 2 (only after the proof): **3** defence and Linux → **4** recovery → **5a** population, cooperation, reinforcement learning → **5b** Windows, AD, cloud, mobile → **6** commercial (deferred).

### Realistic dates (full table and assumptions in §47)

| Date | What will honestly exist |
|---|---|
| 30 Nov 2026 | Trial done; purchase decided |
| 15 Jan 2027 (owner target) | G1: a pilot adapter trained on ~100 verified web wins, with a preliminary comparison against the base |
| end Apr 2027 | The proof: a generation that beats the base on the full sealed web set, or an honest logged result |
| 30 Jun 2027 (owner target) | Web attack and defence; Linux Levels 1–2; the other four domains specified, not yet built |
| Dec 2028 | All six domains trained, each measured separately |

---

## 18. Commercial vision (deferred — excluded from current work)
Retained for continuity only: web is the beachhead; the leaning was lab-verified detections and adapters first, with authorised testing as a later, accredited offering; customer telemetry stays out of training by default. Nothing in this section drives present priorities (§1.4). Before any paid external engagement: professional indemnity insurance, accreditation, and the scope-breach playbook.

---

## 19. Open decisions and questions

### Owner decisions needed
| ID | Decision | Needed by |
|---|---|---|
| D-1 | Purchase acceptance criteria (hours per round, serving throughput, adapter-on-FP8 required?) | Before the trial |
| D-2 | Instruct vs Thinking model, by measured comparison | Before the first real generation |
| D-3 | Loop-B parking rule vs the January commitment (proposed amendment in §7.8) | Before Stage 1.5 |
| D-4 | How novelty and diversity are measured for the volume bar | Before Stage 1.5 |
| D-5 | Confirm the 15 January deliverable as defined in §47 | Now |
| D-6 | Confirm the 30 June milestone as defined in §47 (or add a second builder) | Before Stage 3 planning |

### Technical unknowns the trial resolves
Docker GPU access in the Enverge sandbox · library versions inside the pinned images · whether vLLM serves the FP8 MoE on GB10 with the pinned image and backend · whether 4-bit QLoRA runs on GB10 · whether bf16 training of the 30B base fits in unified memory alongside the OS · whether the adapter serves on the FP8 model · real throughput, memory and training rate.

### Technical unknowns the trial does not resolve
Model quality on security tasks · any learning gain · verified-wins/day · behaviour on the owned unit's OS image · the "three aarch64 transformers patches" in earlier briefs, believed obsolete for the pinned images (issue #12; the in-image probe decides).

### Standing questions for external critique
1. Does pre-registering a folklore-calibrated Loop-B threshold relocate the judgment error rather than remove it?
2. Does the assurance scheme terminate the "who checks the checker" regress, or hide a residual trust assumption — for example the lab's single trusted controller?
3. Does a difficulty-led curriculum force real-world variety, or overfit to the lab's shape?
4. Is the sealed offensive benchmark a harder assurance problem than the detection one?
5. Does specifying six domains now endanger the web proof by spreading labour thin?

---

## 20. Governance

- **No AI attribution anywhere** — commits, pull requests and issues are in the owner's name and voice.
- `main` stays minimal until work is proven; each chunk is a feature branch and a pull request; the build agent opens them and **the owner merges**.
- Renting compute, purchasing hardware, merging and deployment each need explicit owner authorisation.
- **Decisions to revisit:** every constraint-driven "for now" choice is logged in `DECISIONS_TO_REVISIT.md` with a trigger and a GitHub issue.

| Entry | Subject | Issue |
|---|---|---|
| P-001 | DGX purchase gated on the trial | #2 |
| R-001/2/3 | Rental-driven stage split, ephemeral workarounds, image tags vs owned OS | #3 #4 #5 |
| M-001 | Loop-B thresholds are pre-registered estimates | #6 |
| R-004/5 | Foundation and serving choices unverified on hardware | #7 #9 |
| R-006 | Narrow web lab target | #14 |
| R-007 | Lifecycle thresholds set before measurement | #16 |
| R-008 | 4-bit QLoRA default, bf16 comparison | #17 |
| R-009 | MoE only | #18 |
| R-010 | Docker flags measured per machine | #19 |
| R-011 | Trial packages outside the `services/` layout | #20 |

---

## 21. Verified setup appendix — the known-good GB10 path as implemented

> **Golden rule: everything runs inside pinned containers. Never install torch on aarch64 with pip on the host — it silently becomes CPU-only.** The trainer and the image probe both fail loudly on a CPU-only torch.

**Order of operations on the machine**
1. Clone the trial branch; `uv sync --frozen`; `uv pip install huggingface-hub`.
2. Pull both images by digest.
3. `python3 scripts/rental/docker_runtime_setup.py` → must report `READY`; then `source artifacts/docker_runtime/docker_env.sh` in every terminal.
4. `scripts/rental/collect_image_pins.py` → reads real library versions from inside the images and writes a candidate freeze. Review it; use it via `FREEZE=…`.
5. `scripts/rental/materialise_checkpoint.py` → downloads the pinned FP8 snapshot and writes its hash manifest.
6. `scripts/rental/check_preparation.py` → no blockers.
7. Start `rental.live_status`; run `rental.orchestrate` under `track_command.py`.
8. Further training cells with `scripts/run_smoke.sh`; capacity sweep with `scripts/bench/run_benchmark.py`.
9. `scripts/rental/summarise_trial.py` → `docs/stage1_baseline.md`. Copy out. Delete the instance.

**Serving:** vLLM, FP8, flags from `configs/serving.yaml`. Do **not** set `CUTE_DSL_ARCH=sm_121a` on the default path (reported to hang; a newer community recipe disagrees — unresolved, needs a hardware test and an owner decision before use).

**Training:** Unsloth `FastModel` (not `FastLanguageModel`) for the MoE; router frozen and verified; 4-bit QLoRA by default; the project is imported from the mounted checkout, with no package installation inside the image. On unified-memory pressure the lifecycle drops the page cache where permitted and records when it is not.

**Reference figures (other people's units — to be replaced by ours):** serving ~44–85 tok/s single-stream, ~300 tok/s batched; LoRA ~450 tok/s stock to ~3,500 optimised.

---

## 22. Document index

| Read | For |
|---|---|
| **This brief** | Part I: design, decisions, true status, every stage. Part II: the recipe on one Spark |
| `OWNER_GUIDE_GB10_TRIAL.md` | The trial in plain English, and how to read results |
| `RENTAL_START_HERE.md`, `ENVERGE_SETUP.md`, `MEASUREMENTS_AND_TRACKING.md` | Exact commands, provider specifics, the tracker |
| `PENDING_HARDWARE_CHECKS.md` | Every claim still needing hardware evidence |
| `DECISIONS_TO_REVISIT.md` | Temporary choices and their triggers |
| `ARCHITECTURE.md`, `SONNET_COMPLETE_BUILD_PLAN.md` | Target code structure; per-stage definitions of done |
| `PRODUCT_ALIGNMENT_AND_SIX_DOMAIN_CURRICULUM.md`, `CURRENT_PRODUCT_SPEC.md` | Owner's product direction that this brief consolidates |
| `containers/vllm-gb10/PROVENANCE.md` | Evidence behind the image and flag choices |
| v1.1–v1.3 briefs, `STAGE_0_AND_1_EXACT.md`, handoff and readiness notes | History |

---

# PART II — THE RECIPE: how one Spark produces the model

Part I says what we are building and in what order. Part II says how it is actually done within the budget. Every number marked **(ref)** is someone else's measurement and is a placeholder until our trial replaces it; every number marked **(proposed)** is a starting value the owner must confirm before it is used as a gate. The formulas are the durable part.

## 23. The budget constraint, stated once

**OWNER CONSTRAINT:** the hardware budget buys **one DGX Spark**. Everything else must already exist or cost almost nothing.

| Allowed | Not available |
|---|---|
| One Spark (engine): serving, training, evaluation, verifier, storage | A second GPU or second Spark |
| The existing HP laptop as the lab (RAM upgrade £35–55) | Recurring cloud compute after the ~$20 trial |
| Free, open-source software and open model weights | Paid model APIs (also forbidden as judges by design) |
| Backup disk, network bits (~£150) | Paid datasets or labelling services |

Three consequences shape the whole recipe:
1. **One thing at a time.** Serving and training cannot overlap on one GPU with shared memory. The day is time-sliced (§24).
2. **Volume is the scarce resource.** The model learns only from verified attempts, and one Spark makes a limited number per day. Every design choice is judged by verified wins per token.
3. **The lab laptop, not the Spark, limits target supply.** Light container targets run in dozens; a Windows or AD environment runs one at a time. The optional 64 GB lab mini-PC (£150–300) is the only later hardware request, and only when heavy domains begin. Without it they still run — more slowly.

## 24. The daily rhythm

| Window | Hours (proposed) | What runs on the Spark |
|---|---|---|
| Day | 16 | Serving: agents attempt lab scenarios; verifier scores them; Loop A updates strategy |
| Night | 6 | Training (when a round is ready) or sealed evaluation of a candidate |
| Morning | 2 | Gate: read the logs, compare with the anchor, human approves or rejects |

Training does not happen every night. A generation is trained only when a round's worth of verified, diverse data exists (§27); other nights serve or evaluate.

## 25. The compute budget — the arithmetic that governs everything

**Serving (experience generation).**

> attempts per day = (output tokens/sec × serving seconds per day) ÷ output tokens per attempt
> verified unique wins per day = attempts × success rate × share surviving the diversity cap

Worked example with reference numbers — *replace with our trial's figures*:

| Input | Easy/medium tasks | Hard, long-context tasks |
|---|---|---|
| Batched output rate | 300 tok/s (ref) | ~150 tok/s (ref: decode falls with context) |
| Serving time | 16 h = 57,600 s | same |
| Output tokens per day | ≈ 17 million | ≈ 8.6 million |
| Output tokens per attempt (12 actions) | ~3,600 without reasoning traces; ~11,000 with (estimate) | ~8,000 / ~25,000 (estimate) |
| Attempts per day | ≈ 4,800 / ≈ 1,600 | ≈ 1,100 / ≈ 350 |
| At 10% success, half surviving the cap | ≈ 240 / ≈ 80 wins | ≈ 55 / ≈ 17 wins |

What this tells us before spending anything:
- **The 300-wins/day floor is reachable only on easy and medium tasks, and only narrowly.** On hard tasks one Spark yields tens of wins a day. This matches the earlier briefs' warning and makes the **~100-trajectory pilot rule the realistic route to the first generation** (§7.8, §40).
- **Reasoning traces cost roughly three times the volume.** The Instruct-vs-Thinking decision (D-2) is a volume decision as much as a quality one.
- **Success rate is the strongest lever we control** — through curriculum difficulty (§8) and Loop A — because it multiplies everything else.
- Prompt (input) tokens are processed much faster than output tokens and prefix caching removes most repeats, but long contexts still shrink how many agents fit at once (§5.2).

**Training.**

> training hours = (examples × average tokens per example × epochs) ÷ training tokens/sec ÷ 3,600

| Round | Tokens | At 450 tok/s (ref, stock) | At 3,460 tok/s (ref, optimised) |
|---|---|---|---|
| Pilot: 100 examples × 6,000 tokens × 3 epochs | 1.8 M | ≈ 1.1 h | ≈ 9 min |
| Small: 600 × 6,000 × 2 | 7.2 M | ≈ 4.4 h (one night) | ≈ 35 min |
| Full: 2,400 × 6,000 × 2 | 28.8 M | ≈ 18 h (three nights or a weekend) | ≈ 2.3 h |

The trial's `stage1_baseline.md` gives our real rate; `summarise_trial.py --round-tokens` does this sum. **A pilot fits in one evening even on the slow path** — so the first generation does not wait on training optimisation, while the 3-day cadence at full volume does.

**Evaluation.** 200 sealed tasks × 2 models (base and candidate) × ~4,000 output tokens ≈ 1.6 M tokens ≈ 1.5 h (ref). One night comfortably holds an evaluation.

**Memory.** Serving reserves most of the 128 GB for the model (~31 GB) and its cache, so nothing else uses the GPU while serving. 4-bit QLoRA training needs ~17 GB of weights plus working memory that grows with sequence length; bf16 needs ~61 GB of weights. Both fit only when the server is stopped — which the lifecycle already enforces.

**Storage (4 TB).** Models ≈ 92 GB per variant; each adapter is hundreds of megabytes; trajectories are text. Keep every log and golden anchor forever; keep the latest 10–20 adapters; prune old intermediate datasets only behind a trusted anchor.

## 26. Producing experience — the agent loop and the scenarios

- **Agent loop:** think → choose one allowed tool action → observe → adjust, with a hard action cap and context budget per attempt (8–16K for most; longer only for hard tasks). Actions are structured output checked against an allow-list before anything reaches the lab; every step is logged with provenance.
- **Scenario supply is the true bottleneck, and it is human-paced.** Volume and diversity come from *scenario families*: independently implemented targets, each with seeded variation (different routes, roles, data, configuration), each with its assurance contract (§8). A new hostname or seed alone is not a new skill.
- **Reaching the volume honestly** (restored from v1.1): (1) many parallel light containers with varied configurations; (2) difficulty kept winnable-but-hard; (3) count defensive wins too — they are cheaper to produce and verify; (4) the diversity cap enforced in code — once a family reaches its share, further wins are logged but held out of training; (5) on a shortfall, wait or run a smaller round flagged under-volume — never pad.
- **Refusals** (restored from v1.1): a safety-tuned model may decline offensive lab tasks. Handle in this order, without a stripped model: state the authorised-lab context → domain fine-tuning (the real fix) → prefer the base/thinking variant and instruction tuning → only then a light, targeted anti-refusal fine-tune — legitimate because the enforced scope gate, not the model's reluctance, is what keeps behaviour safe. Record refusal rate as a metric from the first run.
- **Loop A runs every day:** prompts, strategies and verified facts improve continuously and raise the success rate that §25 depends on.

## 27. The data recipe

1. **Only verified wins become training examples**, plus verified *corrections* of failures. Failed and unverifiable attempts are kept for analysis, never trained on.
2. **One example** = the scenario brief, the sequence of observations and actions that led to the verified outcome, and the paired defensive step where one exists — in the model's chat format.
3. **Train on what the agent wrote, not on what the environment said.** The loss covers the agent's own turns; observations are context. (The trial's smoke run does not mask this way; production must.)
4. **Every round contains:** new verified wins; **seed replay** of earlier verified data (proposed 20–30%) so old skills are not forgotten; general-ability canary material kept out of training for testing only.
5. **Deduplicate by scenario family and behaviour**, not by exact text. Cap any one family at 15% of the round.
6. **Screen anything external** as untrusted; never train directly on unvetted public data.
7. **Splits are fixed by family before training:** train / development / sealed. Tuning uses development only. The sealed set is never looked at during development.
8. Every dataset version is hashed and recorded with its composition.

## 28. The training recipe

- **Method:** LoRA on the frozen MoE with the router frozen; 4-bit QLoRA by default (§7.4). Start from `configs/training.yaml`: rank 16, alpha 32, learning rate 2e-4, linear schedule, attention and expert projections as targets.
- **First run is the pilot:** ~100 verified examples, 2–3 epochs, short sequences. Its job is to prove the loop end to end and to test the pilot rule — not to be good.
- **Watch while training:** training loss and development loss together (loss falling while development stalls = overfitting → stop early); gradient norm; expert-load balance and dead experts; refusal rate. Stop on any non-finite value.
- **Change one thing at a time** between runs, with a new run identifier, and record why.
- **If the MoE misbehaves** (unstable loss, expert collapse, canaries dropping): lower the learning rate → confirm the router is frozen → restrict targets to attention only → add clipping and warm-up. Smaller first runs on the same model replace the removed dense fallback.
- **GRPO only after an SFT generation has beaten the base** on the sealed set. Rewards come only from the assured verifier.

## 29. The evaluation and promotion recipe

- **Sealed set (proposed):** at least 200 web tasks across at least 10 scenario families the model has never trained on, mixing offensive, detection and remediation tasks, with patched and pre-satisfied controls. Below roughly 200 paired tasks a real 10-point improvement cannot be told from luck.
- **Comparison is paired:** base and candidate attempt the same tasks under the same settings; report the paired test, the confidence interval, and results per family (one family improving does not make a general gain).
- **Canaries:** a fixed general reasoning and coding set; a drop means the model is forgetting.
- **Promotion gate (proposed, to be pre-registered by the owner before the first evaluation):** candidate beats base on the sealed set with a paired test at p < 0.05 **and** no critical category regresses **and** false-positive rate is no worse **and** canaries fall by no more than 2 points **and** the owner approves. No LLM takes part in any of it.
- **Every use of the sealed set is recorded** in the acceptance ledger with the model identity. A set that has been used many times is no longer sealed; retire and replace it.

## 30. Serving the result

Preferred: the adapter served on the FP8 model (personas as adapters). If the trial shows that does not work correctly: merge the adapter into the full-precision weights and serve those, or merge and re-quantise to FP8 on the Spark. Choose by measured correctness first, then speed. Whichever path is chosen becomes part of the reviewed freeze.

## 31. When it is not learning — the diagnosis table (restored from v1.1)

| Symptom | Likely cause | First action |
|---|---|---|
| Training loss falls, benchmark flat | Overfitting or too little diverse data | Fewer epochs; check family shares; more seed replay |
| Loss unstable | Learning rate or router drift | Lower the rate; confirm router frozen |
| Expert-load collapse | MoE routing disturbed | Freeze/verify router; restrict targets |
| Benchmark drops right after a new data source or curriculum change | Data or curriculum, not the model | Revert that one change; re-run |
| Security score up, canaries down | Forgetting | More seed replay; lower rate; shorter run |
| Everything looks fine but scores are wrong | **The verifier** | Re-run the assurance suite before anything else |
| Verified/failed ratio jumps overnight | Verifier bug or data shift | Quarantine the day's data; audit |
| False positives rising | Reward shaping | Check the false-positive penalty |

Always compare a bad generation with the last golden anchor, roll back to the anchor, fix the one cause, and resume. Change external things one at a time.

## 32. The path to the model, in order — the checklist

1. **Trial** on the rented GB10; get our real serving and training rates; decide the purchase (Stage 1A).
2. **Re-run on the owned Spark**; connect the lab laptop (Stage 1B).
3. **Build the sealed web set first**, then the verifier service with its assurance suite (Stage 2A).
4. **Build 10+ web scenario families** and the agent loop; start Loop A.
5. **Compare Instruct and Thinking** on real tasks; pick one by wins per token (D-2).
6. **Measure wins per day** honestly (Stage 1.5); put our numbers into §25.
7. **Run the pilot:** ~100 verified examples → train → paired evaluation on the sealed set.
8. If the pilot beats the base: lower the bar per the pre-registered rule and run generation 2 on more data. If not: diagnose with §31, improve scenario diversity and success rate, try again within the D-3 rule.
9. **Promote only through the gate** (§29); register the generation; keep the anchor.
10. Only then: GRPO, the population, and the next domain — each new domain verifier-first.

**What this recipe can honestly deliver on one Spark:** a model that is measurably better than its base at the security tasks our lab can verify, improving in steps as the lab and verifier grow. Not general frontier reasoning, not unsupervised discovery of new attack classes, and not six mature domains by mid-2027.

## 33. Where the risk really is

| Risk | Why it matters on one Spark | What we do |
|---|---|---|
| Too few verified wins | Learning rate equals experience rate | Pilot rule; success-rate work; defensive wins; more families |
| Scenario building is slow | It is human-paced and solo | Web only until the proof; reuse family templates |
| A weak or leaky sealed set | Every claim rests on it | Build it first; enough tasks; ledger; retire when worn |
| Adapter serving fails on FP8 | Blocks deployment | Decision tree in §30, settled by the trial |
| 4-bit training fails on GB10 | Blocks the default method | bf16 fallback already wired |
| A confidently wrong verifier | Poisons everything silently | Assurance suite on every change; dual checks |
| Dates versus labour | One builder | Deliverables defined by evidence, not promises (D-5, D-6) |

---

# PART III — BUILDING THE WHOLE SYSTEM: every phase in detail, with realistic dates

Part I describes the system. Part II gives the recipe for one training generation on one Spark. Part III explains how the **complete system in all the briefs** — the agent population, both learning loops, the verifier, the curriculum, six domains, defence and recovery — is reached by repeatedly **training and fine-tuning on the Spark**, stage by stage, and when each piece can realistically exist.

## 34. The complete system, and how training on the Spark produces it

### 34.1 The system in one picture (in words)
Two machines. The **Spark** holds the model, the verifier's answer keys, the training code and all records. The **lab laptop** holds the targets and nothing valuable. They talk only through a narrow, logged gateway.

On the Spark, one copy of the model is served. Many **agents** — each just a saved configuration: a role, a prompt, allowed tools, a strategy — take turns using it. An agent is given a **scenario** by the **curriculum controller**, works on a lab target through the gateway, and its whole attempt is saved as a **trajectory**. The **verifier** — plain code, no AI — checks what really happened on the target and labels the attempt verified, failed, or unverifiable.

Two loops then learn from this:
- **Loop A (every day, no training):** which agent configurations, prompts and strategies work best; which verified facts are worth remembering. This makes the *same* model perform better.
- **Loop B (every few days, training on the Spark):** verified attempts become a dataset; the Spark fine-tunes a new **generation** of the model; a **sealed benchmark** the trainer has never seen decides whether it is better; a human approves; the **registry** stores it permanently. This makes a *better* model.

Around this sit the safety parts: the **authorisation gate** (what may be touched), the **lab state machine** (targets and malware never share the network path), the **candidate bank** (interesting but unprovable results wait there), and **rollback** (any generation can be restored).

### 34.2 What "fine-tuning produces the system" means — the generation ladder
The system is not built and *then* trained. Each stage adds the machinery for a new kind of verified experience, and the Spark turns that experience into the next generation of the model.

| Generation | Trained in | Trained on (all verified) | Method | What it should do better than its parent |
|---|---|---|---|---|
| G0 | — | nothing; the base Qwen3-30B-A3B | — | Baseline. Scored on the sealed set so every later claim has a comparison |
| G1 | Stage 2B | ~100 web lab wins (pilot) | SFT, 4-bit QLoRA | Proves the whole loop works; tests the pilot rule |
| G2–G3 | Stage 2B | Hundreds to low thousands of web wins + replay | SFT | **The proof:** beats G0 on the sealed web set |
| G4–G6 | Stage 3 | Web + web defence (detection, remediation, triage) + Linux, cumulative | SFT | Defence learned from the attacks; a second domain without forgetting web |
| G7+ | Stage 5a | The same domains | SFT, then **GRPO** (reinforcement learning on verifier rewards) | Better on hard multi-step tasks where SFT plateaus |
| later | Stage 5b | + Windows, then AD, then cloud, then mobile — each added, none removed | SFT + GRPO | One model competent across domains, measured per domain |

Rules that hold for every generation:
- **Training data is verified wins only**, plus replay of earlier verified data. Nothing the model merely claimed.
- **Recommended default: each generation is a fresh adapter trained from the base model on the cumulative curated dataset** (new wins plus a sampled replay of old ones). This keeps generations independent and reproducible and stops small errors compounding. Continuing from the previous adapter is the cheaper alternative once data is large; choose by measured result, one change at a time.
- **Round size is capped to what fits the night window** (§25); replay is sampled, not the whole history.
- **One main adapter per generation.** "Personas" are agent configurations first (Loop A). Separate role adapters are an optional later refinement, tried only if a measured gain justifies the extra training time.
- **A generation is never served to the agents until the gate passes and a human approves.** Once promoted, the agents use it — so the next round of experience comes from a stronger model. That is the recursion.

### 34.3 How the pieces map to the stages

| Piece of the system | Built in | First trained/used |
|---|---|---|
| Serving, training path, measurements | 1A | 1A (smoke only) |
| Two-machine link, lab state machine, authorisation tiers | 1B | 2A |
| Sealed benchmark, verifier service, assurance | 2A | 2A |
| Agent loop, trajectory store, dataset builder, registry | 2A | 2B |
| Curriculum controller (web) | 2B | 2B |
| Loop B: SFT, promotion gate, rollback | 2B | 2B |
| Defensive verifiers and tools; second domain; live ownership checks | 3 | 3 |
| Recovery verifier and immutable backups | 4 | 4 |
| Agent population (MAP-Elites), cooperation, speed approaches, GRPO | 5a | 5a |
| Windows, AD, cloud, mobile; malware detonation | 5b | 5b |
| Multi-tenant product, dashboard, accreditation | 6 | — |

---

## 35. Stage 0 — Pre-work (DONE)
**In plain words:** get organised so later work starts on firm ground.
**What exists:** the repository, shared data definitions with mandatory provenance, validated configuration files, automated checks on every change, the decision log, and exact pins for the model and container images.
**Left over:** the sealed-benchmark harness planned here was not built; it is the first task of Stage 2A.

## 36. Stage 1A — The hardware trial on a rented GB10 (NEXT)
**In plain words:** before paying ~£5,000, rent the same machine for a day and run the real cycle on it: load the model, answer questions, train a small add-on, reload it, deploy it, and save every measurement.

**Starts when:** the owner has written what "good enough" means (D-1), confirmed ~200 GB of disk with Enverge, tested copying a file off the instance, and booked the rental.

**What the Spark-class machine does here:** *serving* the FP8 model and measuring speed; *training* a small LoRA adapter twice (4-bit QLoRA, then bf16) to measure tokens per second and memory; *serving again* with the adapter attached. This is plumbing and measurement, not learning — the data is seven short examples.

**How it is done, step by step:**
1. Connect; inventory the machine; clone the trial branch.
2. Pull the two pinned container images.
3. Run the Docker setup script. Enverge's session is a locked-down container where the usual GPU flag fails, so the script finds the flags that work and saves them. It must say READY.
4. Probe the images for their real library versions; these replace the deliberate `FILL` placeholders in a reviewed copy of the freeze file.
5. Download the serving model and verify every file against the pinned fingerprint.
6. Start the live tracker; run the full lifecycle once under it (preflight → serve → measure → release memory → train → reload → serve with adapter → workload → export).
7. Run the bf16 comparison, then longer-sequence training cells; run the capacity benchmark.
8. Build the one-page baseline report; copy everything to your own machine; read it back; delete the instance; confirm billing stopped.

**How we know it worked:** the serving and training numbers exist for *our* run; the adapter reloads and its tensors match; memory is released between phases; the adapter-on-FP8 result is recorded either way; the evidence opens on your laptop; you record BUY, DO NOT BUY or RE-TEST.

**What can go wrong → what we do:**
- No GPU inside containers, or containers cannot see the project folder → stop in the first hour, keep the report, raise with Enverge. Cheap failure.
- vLLM cannot serve the FP8 MoE on this image → try the documented fallback image; if that fails it is a purchase-blocking finding.
- 4-bit training fails (the bitsandbytes library on this chip) → the bf16 run is the fallback and becomes the default if it fits and is fast enough.
- The adapter will not serve on the FP8 model → not purchase-blocking; decide between merged-weight and unquantised serving afterwards (§30).

**Effort and realistic date:** one day on the machine, a few days of preparation. **Realistic: completed by 30 November 2026**, if booked in the next two weeks.

**Hands over:** our real tokens-per-second for serving and training (these replace every reference figure in §25), a reviewed freeze with real versions, and the purchase decision.

## 37. Stage 1B — Lab foundation on the owned Spark
**In plain words:** set up the two real machines so the model can safely practise on targets.

**Starts when:** the Spark has arrived (UK stock; allow about a week) and the lab laptop has its 32 GB.

**What the Spark does here:** repeats the Stage 1A lifecycle on the owned unit — its system image may differ from the rental, so nothing is assumed to carry over — then serves the base model for the first lab rehearsals.

**What gets built, and why:**
- **Clean, isolated lab laptop:** wiped, fresh system, containers enabled, off the home network. Targets are deliberately vulnerable; they must not sit near anything valuable.
- **The private link (WireGuard):** an encrypted tunnel whose firewall lets the Spark reach one lab address and nothing else.
- **The lab gateway:** the single door into the lab. It accepts only defined requests, logs all of them, and refuses anything while the lab is in malware mode.
- **The lab state machine:** two modes — *serving targets* or *detonating malware* — that can never be on together, enforced in code with the tunnel down during detonation. Built now, even though malware work is Stage 5, so the safety boundary exists before it is needed.
- **The authorisation service:** three levels — read-only (automatic), sandbox (automatic inside the lab), production (needs a human-signed token). Lab addresses are owned by definition; the proof-of-ownership mechanism for outside targets is designed in but switched on in Stage 3.
- **Web targets as resettable containers:** each can be started, attacked, and returned to a known state, with its starting condition recorded so a win that was already true cannot be counted.

**How we know it worked:** the owned Spark reproduces the trial results; the tunnel reaches only the lab address; a test proves the tunnel is unreachable in malware mode; the authorisation service refuses out-of-scope and unsigned production requests; a target starts, is exercised by the existing lab worker over the link, and resets.

**What can go wrong → what we do:** results differ on the owned unit → re-pin against its system image before anything else. The 32 GB laptop is tight → keep to light web containers for now; heavy systems are not needed until Stage 5.

**Effort and realistic date:** 2–4 weeks. **Realistic: by 24 December 2026**, if the Spark is ordered by about 2 December.

**Hands over:** a safe place for agents to work, and a model served on hardware we own.

## 38. Stage 2A — The verifier and the loop (before measuring or training anything)
**In plain words:** build the judge, the exam, and the practice machinery. Nothing is trained in this stage — on purpose. A model trained before its judge exists has learned from unchecked claims.

**Starts when:** Stage 1B is done.

**What the Spark does here:** serves the base model (G0) all day for the agents; runs the first sealed-set evaluation to record G0's baseline; serves the Thinking variant for the model comparison.

**What gets built, in this order, and why the order matters:**
1. **The sealed web benchmark and its runner.** A set of web tasks the training side can never read: it can only submit a model and receive a score. Built first because every later claim of improvement is measured on it, and an exam written after seeing the student's answers is worthless. Target: 200+ tasks over 10+ families (§29). Alongside it, the **canaries** — a fixed general-ability test that reveals forgetting.
2. **The verifier service.** Small, plain-code checkers behind one interface:
   - *exploitation* — did the objective really fall, read from the target's true state, and was it not already true beforehand;
   - *detection* — does the rule catch the labelled attacks without flagging the benign traffic, with false positives penalised;
   - *remediation* — is the hole closed **and** is the service still working.
   Each has a second, independently written checker; a disagreement quarantines the data.
3. **The assurance suite** — the tests *of the verifier*: cases with known answers; deliberate traps (an already-compromised target, a "fixed" service that is actually broken, a mislabelled sample); the disagreement alarm; a version stamp on every verdict. It runs on every change and a failing verifier cannot be used.
4. **More web scenario families.** Ten or more independently built targets with seeded variation. This is slow, manual work and is the real limit on how much the model can learn; everything downstream depends on it.
5. **The agent loop and trajectory store.** Think → choose an allowed action → pass the authorisation gate → act through the lab gateway → observe → repeat, with an action cap. Every step is saved with who, what model, what scenario, and when.
6. **The dataset builder.** Turns verified trajectories into training sets: removes duplicates by behaviour, screens outside data, mixes in replay, and enforces the 15% family cap in code.
7. **The model registry.** Each generation stored with its adapter, dataset fingerprint, settings and scores, never overwritten; any one can be restored.
8. **The model comparison (D-2).** The same tasks run with Instruct and with Thinking; the verifier scores both; choose by verified wins per token.

**How we know it worked:** the assurance suite passes and blocks changes that break it; the sealed runner scores a model without exposing a single task; an agent completes a web task from first step to verified verdict on the real model; the dataset builder demonstrably enforces its rules; a stored generation can be restored; the model choice is recorded with its evidence.

**What can go wrong → what we do:**
- Scenario building takes longer than planned (likely) → the January milestone uses a smaller first slice, clearly labelled (see §47).
- The verifier is fooled by one of its own traps → that is the suite doing its job; fix before proceeding.
- The model refuses lab tasks → the refusal ladder in §26; record the refusal rate.
- The base model's success rate is very low → Loop A work on prompts and strategy, and easier Level 1–2 tasks, before any measuring.

**Effort and realistic date:** 2–3 months of solo work. **Realistic: a minimum slice by 10 January 2027; complete by end of February 2027.**

**Hands over:** a trustworthy judge, an unseen exam with G0's baseline score, and a working stream of verified experience.

## 39. Stage 1.5 — The measurement gate
**In plain words:** before betting on weight training, count honestly how much verified experience the rig produces.

**Starts when:** Stage 2A is complete and the owner has decided D-3 (what happens after failed rounds) and D-4 (how uniqueness is counted).

**What the Spark does here:** serves G0 for a measurement window of about a week while the agents work the web scenarios.

**How it is done:** count verified, unique, non-trivial wins per day with the family cap applied; record the success rate, tokens per attempt and tokens per win; put these into the §25 formulas; compare with the pre-registered bar (300 a day, no family above 15%). The tool prints a figure and a recommendation; the owner decides.

**The three possible outcomes — all valid:**
1. The bar is cleared → Loop B is switched on at full volume.
2. The bar is missed but there are 100+ verified examples → run the **pilot**. If the pilot beats G0 on the sealed set, the true bar was lower and is revised downward on that evidence. On one Spark this is the expected route.
3. Volume is too low even for a pilot → Loop A is the working engine while scenario supply and success rate are improved; measure again.

**Effort and realistic date:** 2–4 weeks. **Realistic: mid-March 2027.**

**Hands over:** our own numbers for the compute budget, and a recorded decision on Loop B.

## 40. Stage 2B — The proof: the first generations
**In plain words:** train the model on its own verified experience and find out, on an exam it has never seen, whether it got better. This is the result the whole project stands on.

**Starts when:** the Stage 1.5 decision is recorded. (The pilot may run earlier, as soon as 100 verified examples exist — that is the January milestone.)

**What the Spark does here — the first real fine-tuning:**
- **By day:** serves the current model; agents gather verified wins; Loop A improves strategy.
- **On training nights:** the server stops; the dataset builder produces the round; the Spark trains a new adapter (4-bit QLoRA or the precision chosen after the trial), router frozen; every training metric is logged.
- **On evaluation nights:** the candidate and G0 both sit the sealed set and the canaries.
- **In the morning:** the gate result is read; a human approves or rejects.

**What gets built:**
- **The trainer** as a proper component (the trial's smoke script is its prototype): loss on the agent's own turns only, full metric logging, checkpoints.
- **The promotion gate:** candidate must beat G0 on the sealed set with a paired statistical test, with no critical category worse, no rise in false positives, canaries within tolerance — then human approval. The exact thresholds are written down *before* the first evaluation (§29).
- **The rollback controller:** compare a bad generation's logs with the last good one, restore, fix one cause, resume.
- **The web curriculum controller:** raises difficulty as the success rate rises, steps back when prerequisites are missing, keeps a free-exploration share, logs every change.

**The sequence of generations:**
1. **G1 — the pilot.** ~100 verified examples, 2–3 epochs, about an hour of training. Purpose: prove the loop end to end and test the pilot rule.
2. **G2 — first full-method generation.** More data and families, replay included. Diagnose with §31 if it disappoints.
3. **G3 and on** — repeat, one change at a time, until a generation passes the gate or the D-3 rule is reached.

**How we know it worked:** a generation trains with a complete, reconstructable record; it is compared with G0 on the sealed set with paired statistics; it is stored and can be rolled back; and **either** it measurably beats G0 and is promoted, **or** the outcome is logged honestly and the D-3 rule applied. Both end Phase 1.

**What can go wrong → what we do:** loss falls but the exam does not improve → too little diverse data; build families, not epochs. Canaries fall → more replay, lower rate. Unstable training → the MoE fixes in §28. Scores look wrong though everything seems fine → suspect the verifier first.

**Effort and realistic dates:** **G1 by 15 January 2027** (tight; see §47). **The proof — a promoted generation or a logged outcome — by end of April 2027.**

**Hands over:** a model that is measurably better at verified web security work, and a loop that can repeat. **Phase 2 may not begin before this.**

---

## 41. Stage 3 — Defence, and the second domain
**In plain words:** teach the model to defend using the attacks it can now carry out, and add Linux without forgetting web.

**Starts when:** the Stage 2B proof holds.

**What the Spark does here:** the same daily rhythm, now training generations (G4–G6) on a wider mix: web attacks, the matching defensive tasks on the same scenarios, and Linux tasks — always with replay of earlier data so web skill is kept.

**What gets built, and why:**
- **Defensive tools the model reads rather than trusts:** network monitoring (Suricata, Zeek) and endpoint monitoring (Wazuh, Velociraptor) on the lab. Each attack the offensive agents run now also produces labelled telemetry — the attack manufactures the defender's ground truth.
- **Detection engineering:** agents write detection rules; the detection verifier scores them against that labelled telemetry. This is the cleanest task for later reinforcement learning because the score is exact.
- **Remediation:** agents propose fixes in the sandbox; the verifier requires hole closed *and* service alive.
- **Vulnerability prioritisation:** a local copy of the public vulnerability catalogues (no live internet) and a verifier that scores rankings against known versions.
- **Incident records and a response engine** obeying the three authorisation levels: nothing touches a production system without a human-signed token tied to that exact action, and the model never holds production credentials.
- **Live proof of ownership and the scope-breach playbook** — both required before any target outside the lab, even a pilot.
- **Linux in the curriculum:** light containers, Levels 1–2 first, each scenario with its verifier before it is used.

**How we know it worked:** each new verifier passes assurance before its data trains anything; the response engine cannot act on production without a token; an outside target without proof is refused; and a generation improves on the sealed benchmark across web and Linux with no canary regression.

**What can go wrong → what we do:** adding Linux lowers web scores → forgetting; raise the replay share and retrain. Telemetry is incomplete → those tasks are unevaluable, not passes.

**Effort and realistic dates:** 3–6 person-months. **Realistic: May to September 2027.** By the **30 June 2027** milestone: web defence tasks working and Linux at Levels 1–2 (§47).

**Hands over:** a model that attacks and defends on web and Linux, and the controls needed before any outside engagement.

## 42. Stage 4 — Recovery
**In plain words:** prove, with a check that cannot be argued with, that a damaged system has been put back exactly as it was.

**Starts when:** Stage 3 is done.

**What the Spark does here:** little training; recovery tasks join the dataset for later generations.

**What gets built:** backups that cannot be altered or deleted, held on credentials the AI side cannot reach; restore tests against snapshots; a deterministic recovery verifier that compares the restored system with the known-good state.

**How we know it worked:** the backups are provably out of the AI's reach; a restore is verified automatically; the evidence is recorded.

**Effort and realistic dates:** 1–2 person-months. **Realistic: October to November 2027.**

## 43. Stage 5a — The full recursive engine
**In plain words:** move from "one model, a few agents, supervised fine-tuning" to the full system: a large, varied population of agents, cooperation between them, and reinforcement learning — all still judged only by the verifier.

**Starts when:** the Stage 2B proof holds and Stage 3's verifiers exist. No reinforcement learning or evolution before that.

**What the Spark does here:**
- **By day:** serves one model to a large logical population — thousands of configurations taking turns, never thousands of models.
- **By night:** SFT rounds as before, and **GRPO rounds**. In GRPO the model makes a *group* of attempts at the same task; the verifier scores each; attempts better than the group's average are reinforced and worse ones discouraged. On a single GPU the practical form is: gather the groups by day through the fast server, compute the scores, apply the update at night. It is used only on tasks with exact, cheap verification (detection and remediation first).

**What gets built, and why:**
- **The agent population with MAP-Elites:** instead of keeping only the top scorers, keep the best agent *of each kind* (task category × strategy style). This preserves variety, which is what produces varied training data and avoids a blind spot.
- **Cooperation, chosen per task:** a shared workspace for a team on one hard target, or agents spread across many targets. Only through defined, logged channels; some agents are kept blind and a critic attacks shared conclusions, so the group does not talk itself into an error.
- **The three speed approaches,** each behind a switch and kept only if measured to help: sharing common work between agents; caching verified facts (a Loop A gain, not training); routing easy steps to a small disposable model.
- **Full six-group logging, golden anchors, retention and environment versioning,** so that any decline can be traced to the model, the data, the curriculum or the verifier.

**How we know it worked:** the population stays varied; cooperation leaves a complete record; each speed approach has a measurement behind it; GRPO generations pass the same gate as SFT ones; a deliberately degraded generation is rolled back and training resumes.

**What can go wrong → what we do:** GRPO learns to game a checker → that is a verifier defect; fix and extend the assurance traps before continuing. Group collection is too slow → fewer, harder tasks with smaller groups; keep SFT as the main engine.

**Effort and realistic dates:** 4–6 person-months. **Realistic: December 2027 to April 2028.**

## 44. Stage 5b — The remaining domains: Windows, Active Directory, cloud, mobile
**In plain words:** add the four heavier domains one at a time, each only after its verifier is assured, each added to — never replacing — what came before.

**For every domain, the same five steps:** (1) build the lab environments for Levels 1–2; (2) build and assure its verifiers; (3) gather verified experience; (4) train a generation with replay of all earlier domains; (5) pass the gate with no earlier domain regressing — then build Levels 3–5.

| Domain | Lab reality on the laptop | What the verifier reads | Realistic window |
|---|---|---|---|
| Windows | One heavy virtual machine at a time | Real account and privilege state; service state | Feb–Apr 2028 |
| Active Directory | Several machines together — the heaviest; needs the 64 GB lab mini-PC (£150–300) or runs very slowly | Directory state: group membership, tickets, privileges actually obtained | May–Jul 2028 |
| Cloud | Light containers emulating a provider offline; a real provider sandbox only where its behaviour matters, kept as separate evidence | Role and resource state in the emulated account | Aug–Sep 2028 |
| Mobile | Android emulator and owned apps; iOS at app level only | Data or secrets actually reached on the owned device/app | Oct–Dec 2028 |

**Malware detonation** is switched on in this stage, behind the state machine built in Stage 1B: no network or a fake one, snapshots restored after every run, and never while the tunnel is up.

**What the Spark does here:** training rounds grow because the dataset is cumulative; replay is sampled to keep each round inside the night window; per-domain scores are reported separately so one strong domain cannot hide a weak one.

**How we know it worked:** every domain has an assured verifier before any of its data trains; no earlier domain's score falls when a new one is added; detonation and the tunnel are never active together.

**Effort:** roughly 2–3 months per domain, solo.

## 45. Stage 6 — Commercial readiness (deferred)
Outside current work by owner decision. When reopened: separation between customers, customer data kept out of training by default, a full dashboard with approvals and audit trails, independent testing of the platform's own defences, encrypted and monitored weights, update and support processes, and insurance and accreditation before any paid outside testing. **Realistic: not before 2029, and a separate decision.**

---

## 46. What stays true at every stage
- The verifier for a task exists and is assured before that task trains anything.
- No AI in any verifier, gate or authorisation decision.
- Only verified wins are trained on; every round includes replay; the family cap is enforced in code.
- The sealed benchmark is unreadable by the training side, and every use of it is recorded.
- A human approves every promotion and every production action.
- The lab holds no model, answer keys or credentials; lab code imports nothing from the Spark side.
- Everything runs in pinned containers; every run can be reconstructed from its record.
- One change at a time; temporary choices go in the decision log with a trigger.

## 47. The realistic calendar

Assumptions: one builder working close to full time with AI assistance; the trial is booked within two weeks; the Spark is ordered promptly and arrives in about a week. Every date moves day for day with those. These are estimates to be re-planned at each gate, not promises.

| When | Milestone | What will honestly exist |
|---|---|---|
| by 30 Nov 2026 | Stage 1A | Our own GB10 numbers; purchase decided |
| by 24 Dec 2026 | Stage 1B | Owned Spark and lab laptop linked safely |
| by 10 Jan 2027 | Stage 2A, first slice | Verifier core with assurance; ~5 web families; agent loop; a first sealed set of ~80 tasks |
| **15 Jan 2027** — owner target | **G1, the pilot** | **A fine-tuned adapter trained on ~100 verified web wins, served on our stack, compared with the base model on the first sealed set.** The comparison is preliminary — 80 tasks cannot confirm a small gain — and will be labelled so. No slack in this date |
| end Feb 2027 | Stage 2A complete | 10+ families; 200-task sealed set; registry; model variant chosen |
| mid Mar 2027 | Stage 1.5 | Measured wins per day; Loop B decision |
| end Apr 2027 | **Stage 2B — the proof** | A promoted generation that beats the base on the full sealed set — or an honest logged result |
| **30 Jun 2027** — owner target | Stage 3 under way | **Web: attack and defence, Levels 1–4. Linux: Levels 1–2 with assured verifiers. The other four domains: specified with assurance contracts, not yet built or trained** |
| Sep 2027 | Stage 3 complete | Web + Linux, attack and defence; outside-target controls ready |
| Nov 2027 | Stage 4 | Verified recovery |
| Apr 2028 | Stage 5a | Population, cooperation, GRPO, full logging |
| Dec 2028 | Stage 5b | All six domains trained, each measured separately |
| 2029 | Stage 6 | Separate decision |

**On the two owner targets, plainly:**
- **15 January 2027 is achievable as a pilot generation with a preliminary comparison**, and only if November and December go to plan. A *confirmed* improvement belongs to the end-of-April proof.
- **30 June 2027 cannot be a six-domain product on one Spark with one builder.** Windows, AD and mobile each need a heavy lab and their own verifiers, and no domain may train before its verifier exists. What June can honestly hold is two domains working and four specified. The six-domain system is realistically the end of 2028.

**What would bring dates forward:** a second person building scenarios and verifiers in parallel (the true bottleneck is human, not the Spark); accepting Levels 1–2 only for the later domains; buying the lab mini-PC early so heavy environments do not queue. **What would not:** more training time, a second GPU, or skipping verifier assurance — the model learns only as fast as verified, varied experience arrives.

---

*End of v1.5. The verifier is the foundation, and its own correctness is assured, not assumed. Loop B is the goal, switched on by measured volume, not hope. Offensive-led in training, contained by design, honest in claim. The hardware is bought on evidence from our own run — and until that run happens, everything here is preparation.*
