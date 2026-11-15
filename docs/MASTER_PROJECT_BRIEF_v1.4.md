# Autonomous, Self-Improving Cybersecurity AI — Master Project Brief

**Version:** 1.4 (consolidated, self-contained)
**Date:** 2026-11-15
**Supersedes:** v1.3 (2026-11-12) as the single current brief. v1.1/v1.2/v1.3 are kept in `docs/` as history.
**Status of this document:** prepared for owner sign-off. Where it records an owner decision it says so and cites the decision log; where something is unresolved it is marked **OPEN**. Nothing here claims a result that has not been produced.

**The one-paragraph position.** We are turning an open-weight model (Qwen3-30B-A3B) into a cybersecurity specialist that improves its own weights only from machine-verified experience. The design has not changed since v1.2. What has changed is that the repository now contains a tested, end-to-end *trial pipeline* for the hardware decision, a narrow assured verifier, and a first owned-lab workflow — and **nothing has yet run on a GPU**. The next step is a single authorised ~24-hour trial on a rented GB10; its measured results decide the ~£5k DGX Spark purchase.

**What changed in v1.4**
1. **Owner decisions folded in:** Qwen3-30B-A3B MoE **only** (dense fallback removed); **4-bit QLoRA** is the training default with bf16 as a measured comparison; the trial runs on **Enverge** (a sandboxed container, not bare metal); product-only scope; delivery targets 15 January 2027 and 30 June 2027.
2. **Status made true to the code** (§17A): every "built" claim was checked against the repository. Two v1.3 claims are corrected — the web evaluation is *not* generator-disjoint, and the planned `benchmark.py` became a different, larger thing (§2.6).
3. **The trial is specified end to end** (§2.5–2.7, §21): what runs, what is measured, what decides the purchase, and what the trial cannot tell us.
4. **Every stage (0–6) written out** with goal, entry condition, work and definition of done (§17), **nine recommended changes** to carry the project forward (§0.1), and a single list of every open decision with its owner (§19).

## 0.1 Recommended changes to carry the project forward

These are the author's recommendations after auditing the repository against the earlier briefs. They are applied in the roadmap (§17) and marked **[REC-n]**. Each needs owner approval, and none removes a gate.

| # | Recommendation | Why |
|---|---|---|
| REC-1 | **Split Stage 2 and move its first half before the measurement gate.** The order becomes 1A → 1B → 2A (verifier, sealed set, agent loop) → 1.5 (measure) → 2B (first generation). Build the **sealed web acceptance set first** | The original order measured verified wins/day before the verifier, agent loop and benchmark it depends on existed — circular. It also left "verifier-first" without a sealed set, which blocks every learning claim |
| REC-2 | **Split Stage 1 into 1A (hardware trial on a rental) and 1B (lab foundation on owned hardware)** | Different entry conditions, costs and owners; the purchase decision sits between them |
| REC-3 | **Add an explicit adapter-serving decision after the trial** (adapter on FP8, merged weights, or unquantised serving) | Adapter-on-quantised-MoE serving is unproven anywhere; the plan must not assume it |
| REC-4 | **Define the 15 January deliverable as a measured comparison, not a promised gain** | A gain cannot be guaranteed; an honest, verifiable deliverable can |
| REC-5 | **Define the 30 June target by per-domain depth** | Six domains at depth conflicts with the labour estimates; breadth at Levels 1–2 with verifiers is achievable and keeps the six-domain direction |
| REC-6 | **Adopt heavy infrastructure only when a stage needs it** (the registry starts as hashed, immutable directories; MLflow and PostgreSQL later) | Unused dependencies were already removed; less surface before the proof |
| REC-7 | **Replace the year-long parking rule with diagnose-and-suspend-promotion** (§7.8, D-3) | The park contradicts the January commitment; suspension keeps the safety intent |
| REC-8 | **Give the removed dense model's debugging role to small first runs on the same MoE**, with bf16 as the precision fallback | The dense fallback is gone by owner decision; its "forgiving first baseline" role still needs an answer |
| REC-9 | **Supply representative training data for the trial** if at all possible | Seven short examples prove the pipeline but cannot forecast training cost, which is the purchase question |

Markers: **DECISION** (settled, with reasoning) · **OWNER DECISION** (settled by the owner on the date given) · **OPEN** (unsettled) · **HONEST LIMIT** (a permanent boundary against overclaiming) · **STATUS** (what exists today).

**Document map:** §0.1 recommended changes → §0.5 cost → §1 definition → §2 hardware, trial, purchase gate → §3 failure classes → §3.5 threats to the platform → §4 model → §5 serving → §6 verifier → §7 learning engine → §8 curriculum → §9 agents → §10 speed approaches → §11 offensive/defensive + authorisation → §12 lab → §13 observability → §14 rollback → §15 capability boundaries → §16 stack and code architecture → §17 status and roadmap → §18 commercial (deferred) → §19 open decisions → §20 governance → §21 verified setup appendix → §22 document index.

---

## 0.5 Cost of build, not just cost of iron

**HONEST LIMIT:** The hardware costs ~£6k. The *labour* is a multi-person, multi-year research-and-product programme: 16+ services, a verifier suite across six domains, a two-loop learning engine, a malware lab. Treating it as "£6k and one builder" is the most dangerous miscommunication available.

Rough solo person-months: Stage 1 foundation 1–3 · Stage 1.5 gate 0.5–1 · Stage 2 verifier (one domain) + first SFT 2–4 · Stage 3 defensive 3–6 · Stage 5 recursive engine 6–12+ · Stage 6 commercial 6–12+.

**DECISION — one critical path.** Collapse ambition to one proof: *a deterministic, assured verifier for ONE domain (web) plus one SFT generation that measurably beats a sealed benchmark.* Everything else — population, GRPO, six-domain learning, commercial — is Phase 2 and contingent on that proof.

**Six-domain lab vs the proof.** The owner has directed that the product keeps all six domains and that their curricula be specified now. This is *inventory and infrastructure*, not *learning breadth*: the Phase-1 learning proof still gates on web only (§8, §12).

**OPEN (owner) — targets vs the estimates above.** The owner's targets are a working fine-tuned model by **15 January 2027** and a six-domain product by **30 June 2027**. These are targets, not demonstrated feasibility; against the person-month estimates they are aggressive. §17 (Stage 2B) states what "working fine-tuned model" can honestly mean by January. The six-domain June target needs per-domain acceptance depth defined before it can be planned (§19 D-6).

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
Instruct-2507 does not produce reasoning traces. Earlier briefs required a *native-reasoning* model, and multi-step exploitation is reasoning-heavy. `Qwen3-30B-A3B-Thinking-2507` exists in the same family (same MoE-only decision). The planned comparison — task quality, latency and token cost on offensive and defensive tasks — has not been run, and the current pin must not be read as settling it. It belongs after the trial, at the first evaluation that has real tasks (§17, Stage 2A).

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

## 17. Status and roadmap — every stage

Recommended changes from §0.1 are applied below and marked **[REC-n]**. Each stage lists its goal, entry condition, work, definition of done (DoD) and state today.

### 17A. Status at 15 November 2026

| Stage | In one line | State |
|---|---|---|
| 0 Pre-work | Scaffold, schemas, governance | **Done** (merged to `main`) |
| 1A Hardware trial | Serve, train, deploy and measure on a rented GB10 | **Prepared and tested offline; not yet run** |
| 1B Lab foundation | Two-machine link, lab state machine, web targets | One target built; link not started |
| 2A Verifier and loop | Sealed web set, verifier service, agent loop, more scenarios | Components only (§6.4) |
| 1.5 Measurement gate | Verified wins/day vs the pre-registered bar | Not started |
| 2B The proof | One SFT generation vs the sealed web benchmark | Not started |
| 3–6 | Defensive, recovery, recursive engine, commercial | Not started; gated on 2B |

Validation of what exists: lint clean; 327 tests pass on Linux as CI runs them, plus 38 PyTorch-dependent checks run separately on CPU; the trial's container commands and the Docker setup script were rehearsed against a real Docker daemon without a GPU; preflight's checkpoint rules were checked against the real pinned model configuration. **None of this is GPU evidence.**

Repository: five stacked pull requests (#8 → #11 → #10 → #13 → #15), all mergeable, awaiting owner review. The trial does not need them merged; it clones the top branch.

---

## PHASE 1 — THE PROOF

### Stage 0 — Pre-work — DONE
**Goal:** start on a known path.
**Delivered:** repository scaffold, frozen cross-service schemas with mandatory provenance, typed configuration, CI (lint, format, tests, no-secrets check), governance files, image and model pins.
**Carried forward:** the sealed-benchmark harness the original plan placed here was not built; it becomes the first item of Stage 2A [REC-1].

### Stage 1A — Hardware trial on a rented GB10 — NEXT [REC-2]
**Goal:** decide the purchase on our own measurements.
**Entry:** the owner has written the acceptance criteria (D-1), confirmed about 200 GB of disk, rehearsed getting results off the instance, and authorised the rental.
**Work (about 24 hours; runbooks: `OWNER_GUIDE_GB10_TRIAL.md`, `RENTAL_START_HERE.md`):**

| Hours | Work | Stop condition |
|---|---|---|
| 0–2 | Inventory; pull images; **measure Docker settings (must be READY)**; probe images and resolve version pins; download and hash the model; preparation check | No working GPU mode, containers cannot see the checkout, or CUDA/bf16 missing → export evidence and end |
| 2–5 | First full lifecycle (2048 tokens, batch 1, 30 steps, 4-bit QLoRA) | — |
| 5–11 | bf16 comparison cell; then 4096- and 8192-token cells (4096 × batch 2 only with headroom) | Out of memory → record; do not retry blindly |
| 11–15 | Review adapter-serving result; capacity benchmark sweep | — |
| 15–19 | Representative-data run if supplied; live lab workflow only if already rehearsed | — |
| 19–21 | One diagnosed re-run | — |
| 21–24 | Build `stage1_baseline.md`; copy everything out; read it back off-instance; delete the instance; confirm billing stopped | — |

**DoD:**
- [ ] vLLM serves the FP8 MoE model on GB10; latency and throughput recorded.
- [ ] LoRA training runs on the GPU (not CPU torch); tokens/sec, seconds/step and peak memory recorded for 4-bit QLoRA and for bf16.
- [ ] Adapter saved, reloaded in a fresh process, and verified.
- [ ] Adapter-on-FP8 serving attempted; outcome recorded either way.
- [ ] Memory released between serving and training.
- [ ] Evidence bundles and `stage1_baseline.md` verified on the owner's machine.
- [ ] **Owner records BUY / DO NOT BUY / RE-TEST against D-1.**

**After the trial, before anything else:** replace research claims with measured ones (`PROVENANCE.md`, `PENDING_HARDWARE_CHECKS.md`); calibrate the pre-measurement thresholds (R-007); settle precision (R-008) and the attention backend (R-005); commit a reviewed freeze with real library versions; and **decide how adapters will be served** if adapter-on-FP8 failed — merged weights or unquantised serving [REC-3].

### Stage 1B — Lab foundation, on owned hardware [REC-2]
**Goal:** a secure two-machine setup that can host targets.
**Entry:** Spark purchased (or a second authorised rental) and the 32 GB lab laptop available.
**Work:** re-run the Stage 1A pipeline on the owned unit (R-003); wipe and isolate the lab laptop; rehearse the existing lab worker over SSH between the two machines; WireGuard, firewalled engine → lab only; the lab state machine (target-serving XOR detonation, tunnel down during detonation — built now, used later); authorisation service with three tiers and a lab-address allow-list (external ownership proof stubbed, architecture present); web targets as resettable containers with pre-state capture.
**DoD:**
- [ ] The owned unit reproduces the Stage 1A results.
- [ ] The tunnel reaches only the lab address; nothing else on the subnet.
- [ ] A state-machine test proves the tunnel is unreachable during detonation.
- [ ] The authorisation service denies out-of-scope and production-without-token requests.
- [ ] Web targets start, are exercised, and revert to a known state.

### Stage 2A — Verifier and loop, before any measurement or training [REC-1]
**Goal:** everything that produces and judges experience exists and is assured before volume is measured or a model is trained.
**Why the order changed:** the original plan measured verified wins/day (Stage 1.5) before the verifier, agent loop and sealed benchmark that the measurement depends on were built (Stage 2). That is circular. Splitting Stage 2 removes the contradiction without changing any gate.
**Entry:** Stage 1B DoD.
**Work, in strict order:**
1. **Sealed web acceptance set and runner** — fresh, restricted scenarios the learning side cannot read; submit-and-score only; usage recorded in the acceptance ledger. Forgetting canaries alongside.
2. **`verifier_service`** in the target layout, with `detection_verifier` as its core (R-011): exploitation, detection and remediation checkers for web; the full assurance suite (seed truths, planted false positives, dual-checker disagreement, versioning) passing in CI.
3. **More web scenario families** with independent implementations, so that volume and diversity are real rather than one scenario repeated (R-006).
4. **Agent loop** (think → tool → observe) through authorisation and the lab gateway; **trajectory store** with mandatory provenance.
5. **Dataset builder:** dedupe, poison screen, seed replay, diversity cap enforced in code.
6. **Model registry:** immutable generations with lineage and rollback. Start as a hash-manifested directory; adopt MLflow only when it earns its weight [REC-6].
7. **Model comparison (D-2):** Instruct vs Thinking on real offensive and defensive tasks, scored by the verifier — quality, latency, token cost.

**DoD:**
- [ ] The assurance suite passes in CI and blocks merge when it fails.
- [ ] The sealed set scores a candidate without the learning side reading scenarios.
- [ ] The loop drives a full web attempt to a verified verdict, end to end, on the real model.
- [ ] The dataset builder enforces replay, diversity cap and screening.
- [ ] The registry stores a generation immutably; rollback restores it.
- [ ] The model variant is chosen on evidence and recorded.

### Stage 1.5 — Measurement gate
**Goal:** measure what the rig really produces; decide Loop B against the pre-registered bar.
**Entry:** Stage 2A DoD; owner decisions D-3 and D-4 made.
**Work:** run the loop for a measurement window; count verified, unique, non-trivial wins/day with the diversity cap applied; compare with `configs/loopB_gate.yaml`; print the figure and a recommendation. **The owner confirms; nothing auto-decides.**
**DoD:**
- [ ] A measured wins/day figure is logged with its diversity statistics.
- [ ] A recommendation against the bar is produced and owner-confirmed.
- [ ] If volume is low, Loop A is confirmed as the working engine (a valid outcome) and the pilot rule (§7.8) governs whether a first SFT is still attempted.

### Stage 2B — The proof
**Goal:** one SFT generation measured against the sealed web benchmark.
**Entry:** Stage 1.5 decision recorded.
**Work:** SFT with the frozen-router policy and the settled precision, full metrics logged; promotion gate (sealed score, canaries, paired statistical test, no false-positive regression, human approval); rollback controller; web-only curriculum controller with a difficulty ratchet and free-exploration reserve; at least one full generation run. First runs are small and cheap on the same MoE — short sequences, pilot-sized data — which takes over the debugging role the removed dense model had [REC-8].
**DoD:**
- [ ] A generation trains with every metric logged and the run reconstructable.
- [ ] The candidate is compared with the base model on the sealed set, with paired statistics.
- [ ] The registry holds the generation; rollback is demonstrated.
- [ ] **Either** the generation measurably beats the base on the sealed set, **or** the outcome is logged and the D-3 rule is applied. Both end Phase 1 honestly.

**→ GATE: Phase 2 does not start until Stage 2B's DoD holds.**

**The 15 January 2027 deliverable [REC-4].** Achievable and verifiable by that date: *an adapter trained on verified web-lab experience, served on the project's own stack, with a measured comparison against the base model on the sealed web set* — whatever the comparison shows. A gain cannot be promised in advance; finding out is the purpose of the gate. Owner to confirm (D-5).

---

## PHASE 2 — BUILD-OUT (contingent on Stage 2B)

Rule for every stage below: **each new domain or task class gets an assured verifier before it trains.**

### Stage 3 — Controlled defensive capabilities; second domain
**Goal:** reliably investigate and propose defensive actions, sandbox-tested, with human approval for production.
**Entry:** Stage 2B DoD.
**Work:** defensive tool integration in which the model interprets tool output rather than trusting it (network and endpoint monitoring); a vulnerability engine on a local CVE/KEV mirror with a prioritisation verifier; detection-engineering agents scored by the detection verifier; remediation agents scored on hole-closed-and-service-alive; incident lifecycle and evidence records; a response engine with the three policy tiers (production needs a human-signed token; the model holds no production credentials); **live ownership verification and the scope-breach playbook, before any external target**; the curriculum adds **Linux**, cumulatively.
**DoD:**
- [ ] Detection, remediation and prioritisation verifiers pass assurance.
- [ ] Response tiers are enforced; a production action is impossible without a signed token.
- [ ] Ownership verification blocks an external target lacking proof.
- [ ] The scope-breach playbook is written.
- [ ] A generation improves on the sealed benchmark across web + Linux with no canary regression.

### Stage 4 — Recovery
**Goal:** independently verifiable recovery.
**Entry:** Stage 3 DoD.
**Work:** immutable, append-only backups on credentials the AI stack cannot reach; restoration tests against snapshots; a deterministic recovery verifier (restored state equals known-good).
**DoD:**
- [ ] Backups are immutable and unreachable by the AI stack.
- [ ] A restore is verified deterministically against known-good state.
- [ ] Recovery evidence is logged and reconstructable.

### Stage 5 — Recursive learning and evolution; remaining domains
**Goal:** agent strategies and model weights both improve across evaluated generations and domains.
**Entry:** the Stage 2B proof held. **No RL or evolution before this.**
**Work:** an agent population with MAP-Elites; hybrid cooperation through sanctioned, logged channels with blind agents and a critic; the three speed approaches, each behind a flag and kept only if measured to help; GRPO with verifier-only rewards; full six-group logging; golden anchors with rollback and resume; a retention policy; environment versioning; the curriculum across **Windows → AD → cloud → mobile**, each cumulative and verifier-first; malware detonation activated behind the state machine. Lab hardware grows here (a 64 GB mini-PC) when heavy environments run at volume.
**DoD:**
- [ ] Diverse specialists are preserved (no monoculture).
- [ ] Cooperation runs only through sanctioned, logged channels.
- [ ] Each speed approach is measured; unhelpful ones are removed.
- [ ] GRPO runs on verifier rewards only.
- [ ] Every new domain has an assured verifier before training.
- [ ] Detonation never coexists with the tunnel (tested).
- [ ] Degrade → roll back → resume is demonstrated.

**The 30 June 2027 six-domain target [REC-5].** Against the labour estimates in §0.5, six domains at depth by June is not credible for one builder. A target that is both honest and useful: *all six domains present with at least Levels 1–2 backed by assured verifiers and working lab environments, web and one further domain at Levels 3–4, and the recursive loop demonstrated on web.* Owner to set the depth (D-6).

### Stage 6 — Commercial readiness (deferred; outside current scope)
**Goal:** a deployable product.
**Work when reopened:** tenant separation and access control; customer telemetry out of training by default; dashboard, audit and reporting; independent security testing of the platform's own threat mitigations; weights encrypted at rest with egress monitoring; install, update and support processes; insurance and accreditation before any paid external testing.
**DoD:**
- [ ] Tenant separation and audit trails are in place.
- [ ] The platform's own security is independently tested.
- [ ] Accreditation, insurance and incident response are complete before paid external engagements.

### Cross-cutting, every stage
Configuration in YAML and environment, no magic numbers · every run reproducible · assurance tests block merge · no LLM in any gate, verifier or authorisation decision · `lab/` never imports engine code; the learning engine never reads sealed scenarios · secrets only from the environment · containers only on GB10, never host-installed torch.

**Phase 1 is complete** when Stage 2B's DoD holds. **Phase 2 is complete** when Stages 3–5 hold at the depth set in D-6; Stage 6 is a separate decision.

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
| D-5 | Definition of the 15 January deliverable (§17, Stage 2B) | Now |
| D-6 | Per-domain acceptance depth for the 30 June six-domain target | Before Stage 3 planning |

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
| **This brief** | The design, decisions, true status and plan |
| `OWNER_GUIDE_GB10_TRIAL.md` | The trial in plain English, and how to read results |
| `RENTAL_START_HERE.md`, `ENVERGE_SETUP.md`, `MEASUREMENTS_AND_TRACKING.md` | Exact commands, provider specifics, the tracker |
| `PENDING_HARDWARE_CHECKS.md` | Every claim still needing hardware evidence |
| `DECISIONS_TO_REVISIT.md` | Temporary choices and their triggers |
| `ARCHITECTURE.md`, `SONNET_COMPLETE_BUILD_PLAN.md` | Target code structure; per-stage definitions of done |
| `PRODUCT_ALIGNMENT_AND_SIX_DOMAIN_CURRICULUM.md`, `CURRENT_PRODUCT_SPEC.md` | Owner's product direction that this brief consolidates |
| `containers/vllm-gb10/PROVENANCE.md` | Evidence behind the image and flag choices |
| v1.1–v1.3 briefs, `STAGE_0_AND_1_EXACT.md`, handoff and readiness notes | History |

---

*End of v1.4. The verifier is the foundation, and its own correctness is assured, not assumed. Loop B is the goal, switched on by measured volume, not hope. Offensive-led in training, contained by design, honest in claim. The hardware is bought on evidence from our own run — and until that run happens, everything here is preparation.*
