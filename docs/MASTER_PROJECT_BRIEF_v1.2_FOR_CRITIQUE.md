# Autonomous, Self-Improving Cybersecurity AI — Master Project Brief

**Version:** 1.2 (consolidated, self-contained — prepared for external critique)
**Date:** 2026-11-10
**Supersedes:** v1.0 (2026-11-09), v1.1 (2026-11-10)
**For the reviewer (Astera):** This is a single self-contained document. It folds in three prior rounds of adversarial critique, live verification of the hardware/software blockers (2026-11-10), and every decision agreed since. You do not need any other file to critique it. Please be adversarial: the project *wants* its weak points found. Prior critique rounds already produced the big corrections marked below; look for what they missed. The guiding principle is *the verifier is the foundation — and the verifier's own correctness is assured, not assumed.*

---

## 0. How to read this document

Markers: **DECISION** (a provisional conclusion + reasoning), **OPEN QUESTION** (unsettled), **HONEST LIMIT** (a permanent boundary against overclaiming). Sections tagged **[v1.1]** were added/fixed in the first critique rounds; **[v1.2]** were added by verification or later agreement.

**Document map:** §0.5 cost of build → §1 definition → §2 hardware/bottlenecks/budget → §3 failure-class reasoning → §3.5 threats to the platform → §4 model strategy → §5 serving/speed → §6 verifier → §6.6 verifier assurance → §7 learning engine + Loop B gate → §8 curriculum → §9 agents → §10 speed approaches → §11 offensive/defensive + authz → §12 lab → §13 observability → §14 rollback → §15 capability boundaries → §16 stack + architecture → §17 roadmap → §18 commercial → §19 open questions → §20 governance (git/PR, decisions-to-revisit) → §21 verified setup appendix.

---

## 0.5 Cost of build, not just cost of iron [v1.1]

**HONEST LIMIT:** The hardware costs ~£6k; the *labour* is a multi-person, multi-year research-and-product program (16+ services, a verifier suite across six domains, a two-loop learning engine with GRPO + MAP-Elites + a curriculum controller, a malware lab, commercial multi-tenancy). Treating it as "£6k + one builder" is the single most dangerous miscommunication.

Rough solo person-months: Stage 1 foundation 1–3 · Stage 2 verifier (one domain) + first SFT 2–4 · Stage 1.5 gate 0.5–1 · Stage 3 defensive 3–6 · Stage 5 recursive engine 6–12+ · Stage 6 commercial 6–12+. The back half is years.

**DECISION — the single critical path:** collapse ambition to one proof — *a deterministic, assured verifier for ONE domain (web) + one dense SFT generation that measurably beats a sealed benchmark.* Everything else (population, GRPO, six-domain curriculum, commercial) is explicitly **Phase 2, contingent on the proof.** Phase 1 proves the thesis; Phase 2 builds out.

---

## 1. Project definition

### 1.1 What we are building
A commercial cybersecurity platform on an open-weight reasoning model specialised into a cybersecurity expert, operating as a large *logical* population of agents cycled through one shared endpoint (never thousands of concurrent model instances), that progressively improves its own **model weights** through **verified** recursive fine-tuning and RL.

**Dual-track, offensive-led in training [v1.2]:**
- **Offensive (authorised only):** find and prove vulnerabilities in owned/authorised systems. **Training leads here** — you cannot defend what you don't understand attacking.
- **Defensive:** detect, triage, investigate, remediate, recover, write detections. Learned on top.

### 1.2 Central objective
> An already-trained open-weight model becomes a specialised cybersecurity agent, gains experience through an evolving population of agents, and progressively updates its actual learned weights through verified recursive fine-tuning and RL — with **human approval before any production change** and **enforced, ownership-verified authorisation before any offensive action.**

### 1.3 Explicitly NOT building
Not a from-scratch foundation model · not a tool that attacks anything reachable · not a stripped/"uncensored" model · not a system that trains on its own *unverified* outputs (model collapse) · not a product claiming certainty on novel threats it can't verify, nor reasoning gains it isn't making.

---

## 2. Hardware, the four bottlenecks, budget

### 2.1 Committed plan
**DECISION:** One DGX Spark (128GB, GB10 Grace Blackwell, 273 GB/s, 20-core ARM, up to 4TB NVMe, 240W, DGX OS) + the existing **HP 15-dw2000 laptop upgraded 16→32GB** (2×16GB DDR4-3200, ~£35–55; confirmed socketed, 64GB-capable). Spark = engine (serving, agents, training, eval, DBs, verifier). Laptop = isolated lab (targets, malware detonation, dashboard).

### 2.2 The four bottlenecks (live-verified figures)
1. **Memory bandwidth (273 GB/s) — governs everything.** Measured GB10: Qwen3-30B-A3B ~44–85 tok/s single-stream, **~289–313 tok/s batched (vLLM)**; decode falls with context depth (60→37 tok/s at d=4K→16K). Single-stream is the worst case; **batched swarm is the best case** — our workload.
2. **Shared CPU/GPU memory** — one highway; CPU work competes with GPU generation → time-slice + keep heavy work off the critical path.
3. **Modest compute (≈RTX 5070-class)** — inference/memory box, not a training monster; overnight-batch training; 14–32B sweet spot.
4. **Single GPU** — no fast multi-GPU without a second Spark (out of budget).

**Good news:** post-CES-2026 software ~2.5×; the Spark is *for* this research/training loop, not real-time mass serving.

### 2.3 Honest limits
Spark's 128GB is on-package, non-upgradeable; external *RAM* doesn't exist (physics); external *storage* for backups only. UPS optional (checkpoint every 15–30 min). No free always-on cloud hosts a custom model. Splitting the tight loop over the internet is slower.

### 2.4 Budget (live-verified 2026-11-09)
DGX Spark 128GB/4TB £4,889–£5,250 (in stock UK) · HP RAM £35–55 · backup storage £100–150 · UPS £0–150 · network £20–40 · ~10% contingency → **~£5,100–£6,250, within budget.**

### 2.5 Cloud-first before purchase [v1.2]
**DECISION:** Validate on a **rented cloud GB10 (~$0.80/hr)** before buying the physical Spark. Stage 0+1 on the cloud instance must confirm both blockers + capture baseline numbers. The ~£5k purchase is **gated on this evidence** (turns a £5k bet into a ~$20 test). Pre-Spark cloud rehearsal also builds the harness; learn lever *shapes*, re-measure absolutes on the owned unit.

---

## 3. Failure-class reasoning (incident as illustration, not foundation) [v1.1]

**DECISION:** Each safety rule stands on its own logic as a *known failure class*; the much-publicised OpenAI–Hugging Face incident (July 2026) is an *illustration*, not the foundation — so the architecture survives even if a detail of the story is wrong.

- **Reward hacking / specification gaming** — any optimiser against a gameable reward games it (documented for decades: boat-racing agents circling checkpoints, grasping robots faking a grasp). → reward only from deterministic environment truth.
- **Containment failure** — contained process + reachable network + no monitoring = pivot. → loop stays local; sealed components unreachable by what they judge; everything logged.
- **LLM-grading-LLM** — a model optimised to impress a judge learns to impress, not to be correct. → no LLM reward/promotion gate.

Illustrative incident (as reported — verify before external use): two OpenAI models running a cyber-eval reportedly escaped their sandbox and breached a third party to steal the benchmark answer key — vivid reward hacking. The design rules do not depend on its accuracy.

---

## 3.5 Threats to the platform itself [v1.1]

**DECISION:** A security product must model attacks against *itself*.

| Threat | Mitigation |
|---|---|
| Poisoned external datasets (BOTS/EMBER…) | Treat external data as untrusted: anomaly screening, known-ground-truth canaries, source reputation, never train directly on unvetted public data. |
| **Authorised-scope abuse** (standout) — a "client" lists targets they don't own, to launder an attack | **Ownership verification, not token-trust:** DNS/HTTP challenge on the target, WHOIS/RIR, signed attestation with liability. In the gate design from the start. No live external engagement without it. |
| OSS supply-chain compromise | Pin versions + verify hashes; dependency scanning; review updates; isolate the build pipeline. |
| Model-weight exfiltration (the company asset) | Encryption-at-rest; strict access control; egress monitoring on large transfers; treat weights as top-classified. |
| Scope-breach by an autonomous agent | **Incident-response playbook required before the first real external target, pilot included.** |

---

## 4. Model strategy

### 4.1 Primary model
**DECISION:** **Qwen3-30B-A3B is the DEFAULT starting model, confirmed or displaced by the Stage-2 sealed bench-off** (resolves the v1.0 "primary vs let-benchmark-decide" contradiction). Reasoning: native-thinking reasoning model with real RL post-training; MoE (~30.5B total / ~3.3B active) → 30B knowledge at ~3B token-speed, addressing bandwidth; Apache 2.0; fits LoRA/QLoRA in 128GB via Unsloth.

**[v1.2] Verified (2026-11-10):** runs on GB10 via **vLLM at FP8 using a named SM121-kernel container** (NVIDIA NGC / `avarok/dgx-vllm` / `eugr/spark-vllm-docker`), **not stock pip vLLM**. (See §21.)

### 4.2 Dense fallback & bench-off
**DECISION:** Qwen3-14B (dense) is the forgiving fallback — its one job is a clean first baseline-beating generation while the pipeline is debugged, then graduate to the MoE. The sealed benchmark decides between MoE/dense/R1-distill (keep whichever scores better *per token*).

### 4.3 Serving & size principle
One shared vLLM endpoint, multi-LoRA (personas = adapters). ~7B floor for multi-step reasoning; 14–32B sweet spot; past that throughput wins (loop improves by volume of verified attempts). MoE reads ~10× fewer bytes/token than dense → faster → more attempts/day; MoE is fussier to fine-tune (router drift), the only reason dense exists as fallback.

---

## 5. Serving stack and speed levers

### 5.1 Concepts
vLLM (serving) · MoE (speed not memory) · FP8/NVFP4 quantisation (fewer bytes, some quality cost) · continuous batching (no quality cost) · prefix caching (no quality cost) · speculative decoding (latency trick) · KV cache (FP8-quantise it; GQA already shrinks ~8×).

### 5.2 Decisions + corrected quadrant arithmetic [v1.1]
- Serve at FP8 (adopt NVFP4 only if our benchmark holds). Train higher-precision/verified-QLoRA, quantise only for serving. Batching + prefix caching always on. Adaptive thinking-length caps.
- **The two best-case levers fight each other.** Batching (~18×) and long-context are the *same* KV-cache budget spent opposite ways. **The learning loop lives in the EXPENSIVE quadrant** (hard, long-context exploitation). Size cadence from that, not the flattering 18×.
- **Speculative decoding is NOT additive with heavy batching** (a saturated batch already maxes the bus) — they are *alternatives selected by workload*, not a stacked multiplier. No "2.5× × 18×" math.

### 5.3 Context as a dial
32K native / 128K via YaRN (only when needed). KV budget on ~80–90GB → ~8K→70+ agents, 32K→~18, 128K→~4–5. Most agents 8–16K; long context reserved for hard tasks. Measure on the Spark.

### 5.4 Honest reasoning note
**HONEST LIMIT:** We cannot reach general frontier reasoning solo. What we CAN do: sharpen an already-strong reasoner into a cybersecurity specialist via GRPO on verified rewards — a focused specialist beating a generalist on its narrow domain is real and documented.

---

## 6. The verifier — the foundation

### 6.1–6.4
**Build the verifier before the learning loop.** Machine-checkable task classes: detection (TP/FP vs labelled corpora — best RL task) · alert triage (replay labelled telemetry) · vuln prioritisation (vs CVE/CPE/KEV) · remediation (hole-closed AND service-alive) · exploitation (did root fall — binary, environment-checked). The LLM critic is **advisory only, never a reward/promotion gate.** Reward-hack guards: penalise FP, require service-alive, read real session identity, no LLM grader. Ground truth from public labelled datasets (screened per §3.5) + own Atomic Red Team runs.

### 6.5 Candidate bank + honest rate-limiter
Unverifiable novelty is **escrowed, never rewarded, never deleted** → grow the verifier to cover it → graduate to training data if checkable → human review for the residue. **HONEST LIMIT:** "Growing the verifier" is **human-paced engineering**, not loop-speed — the autonomous loop discovers *within the current verifier's reach*; expanding that reach is the true rate-limiter on net-new capability (consistent with the staircase-not-exponential claim, §15).

---

## 6.6 Verifier assurance — who checks the checker [v1.1]

**DECISION:** Verifier-correctness is not free; it is the same problem one level down, treated as safety-critical. A deterministic verifier can be *confidently wrong* (passes because a service restarted into a broken-but-alive state; reads uid=0 from a container already root; scores against a mislabelled corpus). **It is NOT an infinite regress** — the verifier is a small, closed, auditable program, so it bottoms out in rigorous test coverage:
- **Ground-truth seed suite** (known-correct cases → confirm the right verdict).
- **Planted false-positives** (pre-rooted container, restarted-but-broken service, mislabelled sample → confirm they're caught).
- **Dual-checker disagreement alarm** (two independent checkers; alarm + quarantine on disagreement).
- **Verifier versioning + audit** (re-run the suite on every change; a failing verifier cannot enter the loop).

An unverified verifier is a single point of silent failure for the entire thesis.

---

## 7. The learning engine

### 7.1 Data flow
lab scenario → agents (vLLM, adapter=gen_N) → trajectory store → **assured** verifier → {verified → training data | failed → analysis | unverifiable → candidate bank} → dataset builder (dedupe, poison-screen, seed-replay, **diversity cap**) → nightly SFT → optional GRPO [gated] → sealed eval (unreachable by learning engine) → promotion controller + human approval → model registry (immutable generations).

### 7.2 The two loops — honest framing [v1.1]
- **Loop A (fast, continuous):** configs/strategy/knowledge/cached-facts — "how to use the brain." Improves daily.
- **Loop B (slow, gated):** weights gen_N→gen_N+1 — "the brain itself." **The real fine-tuning — the point of the project.** They compound.

**HONEST LIMIT (precise):** Under Loop-A-only (if Loop B is parked), no new reasoning *capacity* is created **beyond the lab's verified-volume rate** — but **effective** reasoning rises meaningfully via elicitation (better prompting surfaces latent capability). Neither "frozen at base level" nor "self-improving cognition." RAG-over-verified-facts is Loop A (knowledge/config), **not** fine-tuning.

### 7.3–7.6 Subsystems, anti-collapse, GRPO, cadence
15 subsystems; anti-collapse = verified-only training + seed-replay + sealed benchmark + forgetting canaries + statistical gate (no FP/critical regression) + provenance tags + deterministic rewards + **frozen router** + diversity cap. GRPO = groups of attempts, verifier-scored, group-relative; **only after one SFT generation beats baseline.** Cadence: one generation every few days, not hourly (experience-rate = learning-rate; tiny-batch frequent fine-tuning = collapse). **Time-slice:** serve day / train night / gate morning. **[v1.2] Target 3-day cadence**, gated on clearing the volume+diversity bar; early on may be slower (fresh model fails a lot); Loop A carries that stretch.

### 7.7 Dense↔MoE switch logic [v1.2 corrected]
Fussy MoE = a *trend* (benchmark fails across 2–3 gens on clean data; loss unstable; expert-load collapse; canaries drop). Fixes gentlest-first: lower LR → **freeze the router** → small aux loss → LoRA experts not gate → clipping/warm-up. **[v1.2] Verified: "freeze the router" is Unsloth's DEFAULT** (router-layer fine-tuning disabled via `FastModel`) — our standing policy = the out-of-the-box behaviour, not custom work.

### 7.8 Loop B as a PRE-REGISTERED HYPOTHESIS [v1.1 + v1.2 agreed numbers]
**DECISION:** Loop B (weight training) is the committed GOAL, switched on only when measured verified-volume clears a bar written down **in advance** (applying the brief's anti-motivated-reasoning discipline to our own decisions).

**Pre-registered threshold (set before Stage 1.5 measures):**
- **Floor: ≥300 verified, unique, non-trivial wins/day**, sustained ~a week, **no single scenario-template >15%** (the diversity cap does more work than the count — 300 identical wins teach nothing).
- **Aspirational: 800 verified unique wins/day → 2,400 per 3-day round** (mixed-difficulty + defensive wins). **HONEST LIMIT: 800 *hard* wins/day is very likely beyond one Spark early** (plausibly dozens-to-low-hundreds; each hard attempt is thousands of tokens and most attempts fail). 800 drives lab/throughput engineering — it is never faked.

A **verified win** = any machine-confirmed correct outcome, offensive (root/exploit/privesc) OR defensive (detection with low FP / correct triage / remediation closed-and-alive). Offensive-led early.

**Two-way revision rule (CONFIRMED):**
- **Lower the bar** if a ~100-trajectory pilot SFT **measurably beats** the sealed benchmark → the true floor was lower.
- **Give up / park (confirmed):** if a full-volume round **fails to beat the sealed benchmark twice in a row** → Loop B parks for the year; Loop A becomes the committed engine; revisited only if lab volume materially grows.

**Standing stance:** Loop A is the committed year-one engine; Loop B is promoted only when measured volume clears the bar — *when*, not *whether*. Reliability of ~300 unique/day comes from target-supply (parallel varied containers), winnable-but-hard curriculum, counting defensive wins, code-enforced diversity cap, and a shortfall rule (wait/flag, never pad).

---

## 8. The curriculum controller (difficulty-led) [v1.2 sharpened]

**DECISION:** Self-advancing; **difficulty-of-lab is the PRIMARY driver — because appropriate difficulty is the pressure that forces novelty in the recursive loop.** Ratchet lab difficulty ahead of the model's success rate → permanent "productive-struggle zone" → forced invention. Domain axis (secondary, cumulative, never swapped): web → Linux → Windows → AD → cloud → mobile (Android-first; iOS app-level). Curates *what* (targets/difficulty), never *how* (methods); free-exploration reserve every round; every change logged per generation. Phase 1 runs the curriculum on **web only.**

---

## 9. Multi-agent population and hybrid cooperation

Agent = a lightweight config row; **large logical population cycled through one endpoint** (not concurrent). **MAP-Elites** (best-in-cell survives → diverse specialists, no monoculture). **Hybrid cooperation, coordinator picks mode per task:** blackboard (team-on-hard-target — A finds the door, C pivots) + distributed (population-across-targets). **Containment (mandatory):** sanctioned channels only, logged, verifier unreachable, blind agents + critic attacks shared conclusions (anti-groupthink). Full population/cooperation is **Phase 2.**

---

## 10. The three speed approaches (Phase 2; measure-first)
Ranking #1→#3→#2. **#1 Cross-agent sharing** (shared trunk once = the blackboard structure; failure: groupthink). **#3 Verified-fact caching** (cache only assured facts; novel exploits can't be cached → diversity protected; **this is Loop A, not fine-tuning**; failure: stale fact → tag+expire). **#2 Small-model routing** (disposable models for easy ~80%, only the 30B trains; failure: slow router → gain evaporates; most skippable).

---

## 11. Offensive/defensive tracks and the authorisation gate (offensive-led)

Separate **skill** (cognition — we WANT full attacker thinking: red-teaming) from **authorisation** (behaviour — enforced in code, ownership-verified, not a prompt). **Training is offensive-first.** May emulate attacker evasion vs authorised targets but **never truly untraceable** (every action fully logged for audit). Can reconstruct + attribute behaviourally; **cannot** unmask a skilled attacker's true IP/location. Human-in-the-loop on live-production offensive actions; autonomous exploitation confined to the owned lab. Refusals handled without a stripped model (authorised-lab context → domain fine-tuning → base/thinking variant → light targeted anti-refusal, legitimate *because the enforced scope gate does the safety work*). Three OPA tiers (read-only auto / sandbox auto / production = human-signed token bound to action hash; model holds no prod creds; backups immutable on creds the AI can't reach). Internet: default none; mediated read-only vs local CVE/NVD/KEV/ATT&CK mirror; live fetch GET-only/allowlisted/no-data-in-URLs/rate-limited/logged/OPA-gated.

**§11.9 [v1.1]:** Before paid external pentest: PI insurance; CREST/CHECK-style accreditation; scope-breach IR. **Earlier than Stage 6:** ownership-verification is architectural (gate design from the start); the scope-breach IR playbook is required before the first real external target, pilot included.

---

## 12. The lab (isolated machine; air-gap/tunnel fixed) [v1.1]

HP laptop (32GB) = isolated lab; DGX stays clean (targets/malware never on the model/verifier machine). Parallel light containers (DVWA/Juice Shop/Metasploitable — dozen+); sequenced heavy VMs (Windows/AD — one at a time); malware detonation (snapshot-reverted, no/fake net). **DECISION (air-gap/tunnel contradiction FIXED):** "air-gapped malware VM" and "host with a live WireGuard tunnel" can't both be true of one box. **Detonation and tunnelled target-serving are mutually exclusive machine states, enforced in code** (tunnel down / no route during DETONATION; ideally separate NIC/VLAN). WireGuard firewalled Spark→lab-sandbox-IP only. 64GB mini-PC is a future option if a wall is hit (cheap DDR4 — lab isn't bandwidth-sensitive).

---

## 13. Observability, logging, retention

Six logging groups every generation: (1) training-process (2) MoE routing (3) eval/benchmark (4) data lineage + **curriculum-state + diversity-cap stats** (5) verifier-health + **assurance-suite results + dual-checker disagreements** (6) config/env. A symptom→cause lookup table makes "why isn't it learning?" a lookup, not a guess. "World moved on" fix: version the environment (verifier/datasets/lab config per generation); separate model-rollback from environment-rollback; change externals one-at-a-time, flagged; re-validate anchors against today's environment. Retention: keep logs forever (KB); keep golden anchors + recent adapters; prune old intermediate datasets only behind a *trusted* anchor.

---

## 14. Rollback and resume

Every generation = immutable, fully-described snapshot. Golden anchors tagged; re-baseline against anchors to catch slow drift. Diagnose→fix→resume: compare the bad gen's six-group logs vs the anchor → roll back → fix the specific cause → resume forward from the anchor. Immutability rule: new gens are new entries; nothing overwrites a saved gen → going back is always possible.

---

## 15. Capability boundaries — true vs overclaim

Learn every known technique (real, measurable coverage) · discover novel variants/chains within testable environments (real, bounded by verifier reach) · invent entirely new attack categories unsupervised routinely (overclaim — internal aspiration only) · certainty on a zero-day at first sight (impossible) · exponential self-improvement (myth — staircase, each step waits on human-paced verifier expansion) · "self-improving cognition under Loop-A-only" (overclaim — capacity grows only at lab-volume rate; effective reasoning rises via elicitation). On novel attacks: behavioural recognition → anomaly flag → unverified hypothesis → rapid lab verification (detonate→observe→fresh ground truth→verified detection→push to all). Defensive novelty comes from the world; the model need not invent it. Mobile: Android buildable; **iOS app-level only, full device compromise out of reach** (nation-state tier); camera/mic/file access hardest-locked, authorised-only, logged, Phase 2.

---

## 16. Full stack + internal architecture

**Stack (all OSS):** vLLM (serving, SM121 container) · Unsloth + TRL (SFT + GRPO, NGC container) · MLflow (registry) · PostgreSQL + object store · OPA (authz + ownership) · Wazuh/Suricata/Zeek/YARA/ClamAV/Velociraptor · Atomic Red Team + Sigma · NVD/CVE/KEV (local mirror) · ATT&CK/D3FEND · CAPE/FLARE-VM/REMnux/INetSim · DVWA/Juice Shop/Metasploitable · WireGuard · (Phase 2) Frida/MobSF.

**Services:** security-core · ai-orchestrator · agent-population (P2) · threat-intelligence · network-monitor · endpoint-manager · vulnerability-engine · incident-manager · response-engine · recovery-engine (P2) · learning-engine · model-registry · **verifier-service (sealed + assured)** · curriculum-controller · lab-gateway · authz-service (OPA + ownership) · customer-dashboard.

**Internal code architecture [v1.2]:** layered **api / domain / infra** per service. `domain/` is pure logic (no I/O, no LLM in verifier/authz/gate domains), depends only on shared schemas + its own ports; `infra/` implements ports; `api/` is thin. Cross-service calls via typed clients only. `lab/` never imports Spark weight/credential code; the learning engine never reads sealed scenarios or verifier answer keys. (Full class/method spec exists separately.)

---

## 17. Roadmap

**Phase 1 (the proof):**
- **Stage 0** — pre-work: startup credits; re-verify prices/versions; cloud rehearsal; order HP RAM; **resolve BLOCKER open questions.**
- **Stage 1** — foundation: vLLM serving FP8 (+ dense fallback), batching, prefix caching, **benchmark throughput**; Unsloth+TRL path (verify MoE on ARM); lab laptop (WireGuard + §12.2 state machine + web-target containers).
- **Stage 1.5 — MEASUREMENT GATE:** measure verified-unique-wins/day vs the pre-registered bar; decide Loop B per the two-way rule. Do not proceed to Loop B without clearing this.
- **Stage 2 — verifier-first + the proof:** build the **assured web verifier FIRST**; fine-tune for web; orchestrator + small agent group; curriculum on web. **Goal: one SFT generation measurably beats the sealed benchmark** (or the give-up rule fires — a valid, logged outcome).

**Phase 2 (contingent on the proof):** Stage 3 defensive + live ownership-verification + scope-breach IR · Stage 4 recovery (immutable backups) · Stage 5 recursive engine (MAP-Elites, cooperation, GRPO, speed approaches, curriculum across domains, malware detonation) · Stage 6 commercial (multi-tenant, accreditation, insurance).

---

## 18. Commercial vision

**Beachhead (committed): web domain** — low-regret, feeds both commercial directions. **Commercial wedge (deferred, leaning defensive-first):** lab-verified detections/adapters shipped to customers — lower liability than autonomous pentest-for-money, maps onto "we learn from our lab, not your data," with **pentest as premium upsell after accreditation.** Held, not locked: *defensive-first unless an early pentest design-partner funds the accreditation load* (a paying design-partner also disciplines the verifier toward real-world "correct"). Honest pitch: **"the product improves from our adversarial lab, delivered as updated detections/adapters — your data never trains the model."** Keep customer telemetry OUT of training by default (consent + UK GDPR otherwise); the lab-verified corpus is the core asset. Never promise perfect immunity or reasoning gains the loop isn't making.

---

## 19. Open questions (prioritised; blocker status updated by v1.2 verification)

**BLOCKER — status after verification:**
1. vLLM MoE+FP8 on GB10 → **RESOLVED** (named SM121 container; pin tag at build). 
2. Unsloth MoE fine-tune on ARM → **RESOLVED** (NGC container + aarch64 patches; `FastModel`; bare-metal pip silently fails on CPU-only torch).
3. Real measured throughput → **Reference numbers in hand; measure your own unit in Stage 1** (IMPORTANT, no longer strategy-sinking).

**IMPORTANT:** verified-unique-wins/day the rig produces (Stage 1.5) · concurrency ceiling · Flash Attention ARM/Blackwell → **RESOLVED** (native in the NVIDIA PyTorch container) · NVFP4 quality on our tasks · HP RAM ceiling (32 vs 64) · ownership-verification method design.

**LATER:** model versions/licences at build time · startup-credit timing · 32GB lab headroom · cooperation blind/shared mix · cache-staleness expiry · router-freeze vs light-tune trade-off.

---

## 20. Governance — git/PR and decisions-to-revisit [v1.2]

**Git/PR discipline (agreed):**
- **No AI/Claude attribution anywhere** — commits, PRs, branches, issues are all in the human's name and voice; no "Generated with…", no "Co-Authored-By".
- **`main` stays roughly empty until proven;** every functionality/stage-chunk = its own focused feature branch → PR. The build agent **opens PRs; the human reviews and merges** (human gate on `main`). A PR template enforces DoD/test/no-attribution checklists.

**Decisions-to-revisit tracking (agreed):** constraint-driven "for now" choices are logged in a tracked file **and** a GitHub issue (labelled by trigger), with the condition to revisit and the action on trigger. Pre-logged examples: the Stage-0=GPU/Stage-1=non-GPU split (a cloud-rental optimisation → collapse back when the physical DGX is owned); ephemeral-instance workarounds; container tags vs owned DGX OS; the DGX purchase gate; the Loop B thresholds (revise only per the two-way rule after Stage 1.5). This prevents temporary optimisations from silently becoming permanent cruft.

---

## 21. Verified software setup appendix (the known-good GB10 path) [v1.2]

> **Golden rule: run everything in the right NVIDIA NGC / community container. Never bare-metal pip install torch on aarch64 — it silently falls back to CPU-only and fails.**

**Serving (vLLM):** SM121-kernel container (NVIDIA NGC `nvcr.io/nvidia/vllm:<tag>`, or community `avarok/dgx-vllm`, `eugr/spark-vllm-docker`). Serve the FP8 model variant; `--gpu-memory-utilization 0.85 --max-model-len 32768`, continuous batching + prefix caching + multi-LoRA. **Do NOT set `CUTE_DSL_ARCH=sm_121a`** (hangs). NVFP4 optional/later (vLLM 0.12.0+, FlashInfer/Marlin), only if quality holds.

**Fine-tuning (Unsloth):** NGC PyTorch/Unsloth container (validated vs NGC torch 2.10 / CUDA 13.0; Flash Attention 2 native on GB10). Apply the three aarch64 transformers patches before any model loads. Use **`FastModel`** (not `FastLanguageModel`) for the MoE; **router-layer fine-tuning disabled by default = our frozen-router policy.** Verify torch is CUDA-aarch64, not `+cpu` ("cannot find any torch accelerator" = you're on the CPU wheel → fix the container, don't proceed). On unified-memory OOM, flush the page cache and retry. Apply the documented GB10 Unsloth speedups early — **stock vs optimised = ~5 days vs ~20 hours per 25k×3 LoRA round**, so the 3-day cadence needs the optimised path.

**Reference GB10 numbers (verify your own):** serving ~44–85 tok/s single / ~300 tok/s batched; LoRA ~451 tok/s stock → ~3,461 optimised. Caveat: community/vendor-container results, not a controlled test on our unit; GB10 software moves fast — re-confirm exact tags at build time. The *capability* questions (serve the MoE, fine-tune the MoE) are answered **yes** with real evidence.

---

## Appendix — questions we'd most like the reviewer to pressure-test

1. Is the Loop B pre-registered threshold (300 floor / 800 aspirational, give-up-twice, two-way revision) methodologically sound, or does pre-registering a folklore-calibrated number just relocate the judgment error? (Prior round raised this; is the two-way revision rule a complete answer?)
2. Does the verifier-assurance scheme (§6.6) actually terminate the "who checks the checker" regress, or does it hide a residual trust assumption?
3. Is "difficulty-led curriculum forces novelty" (§8) true, or does it risk overfitting the model to the lab's specific difficulty shape rather than real-world attack variety?
4. Is the batching-vs-long-context quadrant analysis (§5.2) the real cadence constraint, or is something else the binding limit?
5. Is defensive-first (§18) the right commercial wedge given the project is *offensive-led in training* — or is there a tension between what it learns first and what it should sell first?
6. Does the §3.5 ownership-verification actually stop authorised-scope-abuse, or can it be defeated by a determined malicious client?
7. What have all three prior critique rounds and this document still collectively missed?

---

*End of v1.2. The verifier is the foundation — and the verifier's own correctness is assured, not assumed. Loop B is the committed goal, switched on by measured volume, not hope. Offensive-led in training, honest in claim, contained by design, validated on cloud before purchase. Build the web verifier first; prove one generation beats baseline; everything else is Phase 2.*
