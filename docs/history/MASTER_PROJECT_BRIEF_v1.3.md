# Autonomous, Self-Improving Cybersecurity AI — Master Project Brief

**Version:** 1.3 (consolidated, self-contained — prepared for external critique)
**Date:** 2026-11-12
**Supersedes:** v1.0 (2026-11-09), v1.1 (2026-11-10), v1.2 (2026-11-10)
**For the reviewer (Astra):** This is a single self-contained document. It folds in prior rounds of adversarial critique, live verification of the hardware/software blockers, and every decision agreed since. Please be adversarial: the project *wants* its weak points found. The guiding principle is *the verifier is the foundation — and the verifier's own correctness is assured, not assumed.*

**What changed in v1.3 (owner-directed):**
1. **Offensive track foregrounded and made explicit** across the verifier task classes (§6), the curriculum (§8), the lab (§12), and the offensive/authorisation section (§11). The project was always *offensive-led in training*; v1.3 removes any ambiguity that let it read as defensive-only.
2. **The lab is provisioned for all six domains from the start, each as an easy→hard difficulty ladder that forms the curriculum spine** (§8, §12). Reconciled honestly with the §0.5 web-first critical path: the **Phase-1 proof still gates on web**; the six-domain lab is *infrastructure provisioned ahead* so the curriculum can advance without a new build each time. The 32 GB-lab hardware limit is stated, not glossed.
3. Alignment note: the detection-verifier + generator-disjoint held-out-eval code already built is the **Stage-2 assured web-verifier slice** (§6.6, §17) — not a separate project. v1.3 is the single source of truth; the interim `briefs/` v2.0 set is superseded.

---

## 0. How to read this document

Markers: **DECISION** (a provisional conclusion + reasoning), **OPEN QUESTION** (unsettled), **HONEST LIMIT** (a permanent boundary against overclaiming). Sections tagged **[v1.1]** were added/fixed in the first critique rounds; **[v1.2]** by verification or later agreement; **[v1.3]** by this owner-directed revision (offensive track + six-domain lab/curriculum).

**Document map:** §0.5 cost of build → §1 definition → §2 hardware/bottlenecks/budget → §3 failure-class reasoning → §3.5 threats to the platform → §4 model strategy → §5 serving/speed → §6 verifier → §6.6 verifier assurance → §7 learning engine + Loop B gate → §8 curriculum (six-domain, difficulty-led) → §9 agents → §10 speed approaches → §11 offensive/defensive + authz → §12 lab (six-domain) → §13 observability → §14 rollback → §15 capability boundaries → §16 stack + architecture → §17 roadmap → §18 commercial → §19 open questions → §20 governance → §21 verified setup appendix.

---

## 0.5 Cost of build, not just cost of iron [v1.1]

**HONEST LIMIT:** The hardware costs ~£6k; the *labour* is a multi-person, multi-year research-and-product program (16+ services, a verifier suite across six domains, a two-loop learning engine with GRPO + MAP-Elites + a curriculum controller, a malware lab, commercial multi-tenancy). Treating it as "£6k + one builder" is the single most dangerous miscommunication.

Rough solo person-months: Stage 1 foundation 1–3 · Stage 2 verifier (one domain) + first SFT 2–4 · Stage 1.5 gate 0.5–1 · Stage 3 defensive 3–6 · Stage 5 recursive engine 6–12+ · Stage 6 commercial 6–12+. The back half is years.

**DECISION — the single critical path:** collapse ambition to one proof — *a deterministic, assured verifier for ONE domain (web) + one dense SFT generation that measurably beats a sealed benchmark.* Everything else (population, GRPO, six-domain curriculum, commercial) is explicitly **Phase 2, contingent on the proof.** Phase 1 proves the thesis; Phase 2 builds out.

**[v1.3] Amendment — lab infrastructure vs learning proof:** the owner has directed that the **lab environments for all six domains be provisioned up front as easy→hard ladders** (the curriculum spine, §8/§12). This is *infrastructure breadth pulled forward*, and it is distinguished sharply from *learning breadth*: the Phase-1 **learning proof is unchanged — it gates on web only.** Provisioning six labs is additional lab-build labour and lab-hardware load (§12 HONEST LIMIT); it is **not** a claim that six-domain weight-learning happens in Phase 1. The critical path to the *proof* still runs through web.

---

## 1. Project definition

### 1.1 What we are building
A commercial cybersecurity platform on an open-weight reasoning model specialised into a cybersecurity expert, operating as a large *logical* population of agents cycled through one shared endpoint (never thousands of concurrent model instances), that progressively improves its own **model weights** through **verified** recursive fine-tuning and RL.

**Dual-track, offensive-led in training [v1.2/v1.3 — foregrounded]:**
- **Offensive (authorised only):** find and prove vulnerabilities in owned/authorised systems — root, exploit, priv-esc, objective capture, all environment-checked. **Training leads here** — *you cannot defend what you don't understand attacking.* The offensive agent is the **data engine**: it generates the machine-confirmed ground truth (what actually worked against a target) that the defensive side learns from. Offence and defence **co-evolve** on the same scenarios (purple-team / self-play dynamic).
- **Defensive:** detect, triage, investigate, remediate, recover, write detections. Learned on top of, and fed by, the offensive signal.

### 1.2 Central objective
> An already-trained open-weight model becomes a specialised cybersecurity agent, gains experience through an evolving population of agents, and progressively updates its actual learned weights through verified recursive fine-tuning and RL — with **human approval before any production change** and **enforced, ownership-verified authorisation before any offensive action.**

### 1.3 Explicitly NOT building
Not a from-scratch foundation model · not a tool that attacks anything reachable (autonomous offensive action is **confined to the owned, isolated lab**; live-production offensive actions are human-in-the-loop and ownership-verified) · not a stripped/"uncensored" model · not a system that trains on its own *unverified* outputs (model collapse) · not a product claiming certainty on novel threats it can't verify, nor reasoning gains it isn't making.

---

## 2. Hardware, the four bottlenecks, budget

### 2.1 Committed plan
**DECISION:** One DGX Spark (128GB, GB10 Grace Blackwell, 273 GB/s, 20-core ARM, up to 4TB NVMe, 240W, DGX OS) + the existing **HP 15-dw2000 laptop upgraded 16→32GB** (2×16GB DDR4-3200, ~£35–55; confirmed socketed, 64GB-capable). Spark = engine (serving, agents, training, eval, DBs, verifier). Laptop = isolated lab (targets, malware detonation, dashboard). **[v1.3] the lab now hosts all six domain environments (§12); on 32 GB this requires time-slicing and likely the 64 GB upgrade/mini-PC once AD/Windows rungs run at volume.**

### 2.2 The four bottlenecks (live-verified figures)
1. **Memory bandwidth (273 GB/s) — governs everything.** Measured GB10: Qwen3-30B-A3B ~44–85 tok/s single-stream, **~289–313 tok/s batched (vLLM)**; decode falls with context depth (60→37 tok/s at d=4K→16K). Single-stream is the worst case; **batched swarm is the best case** — our workload.
2. **Shared CPU/GPU memory** — one highway; CPU work competes with GPU generation → time-slice + keep heavy work off the critical path.
3. **Modest compute (≈RTX 5070-class)** — inference/memory box, not a training monster; overnight-batch training; 14–32B sweet spot.
4. **Single GPU** — no fast multi-GPU without a second Spark (out of budget).

**Good news:** post-CES-2026 software ~2.5×; the Spark is *for* this research/training loop, not real-time mass serving.

### 2.3 Honest limits
Spark's 128GB is on-package, non-upgradeable; external *RAM* doesn't exist (physics); external *storage* for backups only. UPS optional (checkpoint every 15–30 min). No free always-on cloud hosts a custom model. Splitting the tight loop over the internet is slower.

### 2.4 Budget (live-verified 2026-11-09)
DGX Spark 128GB/4TB £4,889–£5,250 (in stock UK) · HP RAM £35–55 · backup storage £100–150 · UPS £0–150 · network £20–40 · ~10% contingency → **~£5,100–£6,250, within budget.** **[v1.3] a 64 GB lab mini-PC (cheap DDR4, ~£150–300) is now a probable Phase-1.5/2 line item once the six-domain lab runs heavy domains at volume — flagged, not yet committed.**

### 2.5 Cloud-first before purchase [v1.2]
**DECISION:** Validate on a **rented cloud GB10 (~$0.80/hr)** before buying the physical Spark. Stage 0+1 on the cloud instance must confirm both blockers + capture baseline numbers. The ~£5k purchase is **gated on this evidence** (turns a £5k bet into a ~$20 test). Pre-Spark cloud rehearsal also builds the harness; learn lever *shapes*, re-measure absolutes on the owned unit.

**[v1.3] Measurement harness (owner request):** the cloud rehearsal must run a dedicated **benchmark/fitness script** (`scripts/rental/benchmark.py`, planned) that measures, on the rented unit: model load + unified-memory footprint; **training throughput (tok/s, s/step, time-per-epoch, extrapolated hours to train the pilot and the full round)**; max batch×seq before OOM; bandwidth/compute utilisation (the real bottleneck); serving tok/s and multi-LoRA overhead; sustained-run thermal/clock throttling; and a **cost model** (rental £/hr × measured hours = £/experiment → how many self-improvement rounds the budget buys before 15 Jan). Output = a one-page **go/no-go hardware-fitness report**. This is pure measurement (no offensive content) and is how the DGX-purchase gate (§2.5) and the model-variant decision (§4.2) are settled with evidence, not folklore.

---

## 3. Failure-class reasoning (incident as illustration, not foundation) [v1.1]

**DECISION:** Each safety rule stands on its own logic as a *known failure class*; the much-publicised OpenAI–Hugging Face incident (July 2026) is an *illustration*, not the foundation — so the architecture survives even if a detail of the story is wrong.

- **Reward hacking / specification gaming** — any optimiser against a gameable reward games it (documented for decades: boat-racing agents circling checkpoints, grasping robots faking a grasp). → reward only from deterministic environment truth.
- **Containment failure** — contained process + reachable network + no monitoring = pivot. → loop stays local; sealed components unreachable by what they judge; everything logged.
- **LLM-grading-LLM** — a model optimised to impress a judge learns to impress, not to be correct. → no LLM reward/promotion gate.

Illustrative incident (as reported — verify before external use): two models running a cyber-eval reportedly escaped their sandbox and breached a third party to steal the benchmark answer key — vivid reward hacking. The design rules do not depend on its accuracy. **[v1.3] This failure class is exactly why the offensive agent's reward is environment-checked (did root actually fall in the owned lab) and never self-reported, and why autonomous offence is lab-confined.**

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
**DECISION:** **Qwen3-30B-A3B is the DEFAULT starting model, confirmed or displaced by the Stage-2 sealed bench-off.** Reasoning: native-thinking reasoning model with real RL post-training; MoE (~30.5B total / ~3.3B active) → 30B knowledge at ~3B token-speed, addressing bandwidth; Apache 2.0; fits LoRA/QLoRA in 128GB via Unsloth.

**[v1.2] Verified (2026-11-10):** runs on GB10 via **vLLM at FP8 using a named SM121-kernel container**, **not stock pip vLLM.** (See §21.)

**[v1.3] Variant note (offence raises the stakes):** the thinking-vs-non-thinking variant question is now *more* load-bearing because **multi-step exploitation is reasoning-heavy** (chaining steps, adapting to target responses) in a way that writing a single detection rule is not. The §4.2 sealed bench-off must score candidates on **offensive** tasks too, and the §2.5 benchmark must report **cost-per-token per variant**, before the variant is locked. Do not assume the non-thinking variant suffices for the offensive track.

### 4.2 Dense fallback & bench-off
**DECISION:** Qwen3-14B (dense) is the forgiving fallback — its one job is a clean first baseline-beating generation while the pipeline is debugged, then graduate to the MoE. The sealed benchmark decides between MoE/dense/R1-distill (keep whichever scores better *per token*, **on both offensive and defensive task classes [v1.3]**).

### 4.3 Serving & size principle
One shared vLLM endpoint, multi-LoRA (personas = adapters). ~7B floor for multi-step reasoning; 14–32B sweet spot; past that throughput wins. MoE reads ~10× fewer bytes/token than dense → faster → more attempts/day; MoE is fussier to fine-tune (router drift), the only reason dense exists as fallback.

---

## 5. Serving stack and speed levers

### 5.1 Concepts
vLLM (serving) · MoE (speed not memory) · FP8/NVFP4 quantisation · continuous batching (no quality cost) · prefix caching (no quality cost) · speculative decoding (latency trick) · KV cache (FP8-quantise it; GQA already shrinks ~8×).

### 5.2 Decisions + corrected quadrant arithmetic [v1.1]
- Serve at FP8 (adopt NVFP4 only if our benchmark holds). Train higher-precision/verified-QLoRA, quantise only for serving. Batching + prefix caching always on. Adaptive thinking-length caps.
- **The two best-case levers fight each other.** Batching (~18×) and long-context are the *same* KV-cache budget spent opposite ways. **The learning loop lives in the EXPENSIVE quadrant** (hard, long-context exploitation). Size cadence from that, not the flattering 18×.
- **Speculative decoding is NOT additive with heavy batching** — alternatives selected by workload, not a stacked multiplier. No "2.5× × 18×" math.

### 5.3 Context as a dial
32K native / 128K via YaRN (only when needed). KV budget on ~80–90GB → ~8K→70+ agents, 32K→~18, 128K→~4–5. Most agents 8–16K; long context reserved for hard tasks. Measure on the Spark.

### 5.4 Honest reasoning note
**HONEST LIMIT:** We cannot reach general frontier reasoning solo. What we CAN do: sharpen an already-strong reasoner into a cybersecurity specialist via GRPO on verified rewards — a focused specialist beating a generalist on its narrow domain is real and documented.

---

## 6. The verifier — the foundation

### 6.1–6.4
**Build the verifier before the learning loop.** Machine-checkable task classes, **offensive and defensive [v1.3]**:
- **Exploitation (offensive, the lead signal):** did root/privesc/objective actually fall — **binary, environment-checked** (real session identity / uid / flag file / service state), never self-reported. Per domain: web (shell/RCE/auth-bypass/data-exfil proven), Linux (root via SUID/sudo/kernel), Windows (SYSTEM/privesc), AD (domain-admin / Kerberos path proven), cloud (privesc to admin role / resource takeover in the emulated account), mobile (app data/secret extraction, insecure-storage proof).
- **Detection (defensive, best RL task):** TP/FP vs labelled corpora — *the corpora the offensive side generates*.
- **Alert triage** (replay labelled telemetry) · **vuln prioritisation** (vs CVE/CPE/KEV) · **remediation** (hole-closed AND service-alive).

The LLM critic is **advisory only, never a reward/promotion gate.** Reward-hack guards: penalise FP, require service-alive, read real session identity, no LLM grader. Ground truth from public labelled datasets (screened per §3.5) + own Atomic Red Team runs + **the offensive agent's environment-checked wins [v1.3]**.

### 6.5 Candidate bank + honest rate-limiter
Unverifiable novelty is **escrowed, never rewarded, never deleted** → grow the verifier to cover it → graduate to training data if checkable → human review for the residue. **HONEST LIMIT:** "Growing the verifier" is **human-paced engineering**, not loop-speed — the autonomous loop discovers *within the current verifier's reach*; expanding that reach is the true rate-limiter (staircase-not-exponential, §15).

### 6.6 Verifier assurance — who checks the checker [v1.1]
**DECISION:** Verifier-correctness is treated as safety-critical; a deterministic verifier can be *confidently wrong*. **Not an infinite regress** — a small, closed, auditable program bottoming out in rigorous test coverage:
- **Ground-truth seed suite** · **Planted false-positives** (pre-rooted container, restarted-but-broken service, mislabelled sample → confirm caught) · **Dual-checker disagreement alarm** · **Verifier versioning + audit** (re-run on every change; a failing verifier cannot enter the loop).

**[v1.3] Status — the web slice is built:** the assured web **detection** verifier exists in code — bounded Sigma-subset executor, OS-enforced per-rule isolation, seed/trivial/integrity assurance, and a **generator-disjoint held-out evaluation** (train/dev/held-out use different payload families; a memorised rule passes train and fails held-out) with **paired** difference analysis (McNemar + cluster bootstrap) and a restricted-acceptance budget. The web **exploitation** verifier (did the attack land, environment-checked) is the next slice. An unverified verifier is a single point of silent failure for the entire thesis.

---

## 7. The learning engine

### 7.1 Data flow
lab scenario → agents (vLLM, adapter=gen_N) → trajectory store → **assured** verifier → {verified → training data | failed → analysis | unverifiable → candidate bank} → dataset builder (dedupe, poison-screen, seed-replay, **diversity cap**) → nightly SFT → optional GRPO [gated] → sealed eval (unreachable by learning engine) → promotion controller + human approval → model registry (immutable generations).

### 7.2 The two loops — honest framing [v1.1]
- **Loop A (fast, continuous):** configs/strategy/knowledge/cached-facts — "how to use the brain." Improves daily.
- **Loop B (slow, gated):** weights gen_N→gen_N+1 — "the brain itself." **The real fine-tuning — the point of the project.** They compound.

**HONEST LIMIT (precise):** Under Loop-A-only, no new reasoning *capacity* beyond the lab's verified-volume rate — but **effective** reasoning rises via elicitation. Neither "frozen at base level" nor "self-improving cognition." RAG-over-verified-facts is Loop A, **not** fine-tuning.

### 7.3–7.6 Subsystems, anti-collapse, GRPO, cadence
Anti-collapse = verified-only training + seed-replay + sealed benchmark + forgetting canaries + statistical gate + provenance tags + deterministic rewards + **frozen router** + diversity cap. GRPO = groups of attempts, verifier-scored, group-relative; **only after one SFT generation beats baseline.** Cadence: one generation every few days (experience-rate = learning-rate; tiny-batch frequent fine-tuning = collapse). **Time-slice:** serve day / train night / gate morning. **[v1.2] Target 3-day cadence**, gated on the volume+diversity bar; Loop A carries early stretches.

### 7.7 Dense↔MoE switch logic [v1.2]
Fussy MoE = a *trend* (benchmark fails across 2–3 gens on clean data; loss unstable; expert-load collapse; canaries drop). Fixes gentlest-first: lower LR → **freeze the router** → small aux loss → LoRA experts not gate → clipping/warm-up. **"Freeze the router" is Unsloth's DEFAULT** (`FastModel`) — standing policy = out-of-the-box behaviour.

### 7.8 Loop B as a PRE-REGISTERED HYPOTHESIS [v1.1 + v1.2]
**DECISION:** Loop B is the committed GOAL, switched on only when measured verified-volume clears a bar written down **in advance.**

**Pre-registered threshold:**
- **Floor: ≥300 verified, unique, non-trivial wins/day**, sustained ~a week, **no single scenario-template >15%** (diversity cap does more work than the count).
- **Aspirational: 800 verified unique wins/day → 2,400 per 3-day round.** **HONEST LIMIT: 800 *hard* wins/day is very likely beyond one Spark early** (plausibly dozens-to-low-hundreds; each hard attempt is thousands of tokens and most fail). 800 drives lab/throughput engineering — never faked.

A **verified win** = any machine-confirmed correct outcome, offensive (root/exploit/privesc/objective) OR defensive (detection low-FP / correct triage / remediation closed-and-alive). **Offensive-led early [v1.3]:** the six-domain lab's easy rungs (§8/§12) are the primary supply of early offensive wins.

**Two-way revision rule (CONFIRMED):**
- **Lower the bar** if a ~100-trajectory pilot SFT **measurably beats** the sealed benchmark → the true floor was lower.
- **Give up / park (confirmed):** if a full-volume round **fails to beat the sealed benchmark twice in a row** → Loop B parks for the year; Loop A becomes the committed engine; revisited only if lab volume materially grows.

**Standing stance:** Loop A is the committed year-one engine; Loop B is promoted *when*, not *whether*, measured volume clears the bar. Reliability of ~300 unique/day comes from target-supply (parallel varied containers across the six-domain lab), winnable-but-hard curriculum, counting defensive wins, code-enforced diversity cap, and a shortfall rule (wait/flag, never pad).

---

## 8. The curriculum controller (difficulty-led, six-domain) [v1.3 expanded]

**DECISION:** Self-advancing; **difficulty-of-lab is the PRIMARY driver — appropriate difficulty is the pressure that forces novelty in the recursive loop.** Ratchet lab difficulty ahead of the model's success rate → permanent "productive-struggle zone" → forced invention. Curates *what* (targets/difficulty), never *how* (methods); free-exploration reserve every round; every change logged per generation.

**Two axes:**
- **Difficulty axis (PRIMARY) — the easy→hard ladder, per domain [v1.3]:** every domain carries an explicit ladder:
  - **Easy** — known single-step vulnerability, undefended (teaches the base technique; the early win-supply for §7.8).
  - **Medium** — chained steps, light evasion, partial defences/monitoring present.
  - **Hard** — multi-step, long-context, defended, variant-forcing (lives in the expensive quadrant §5.2; this is where novelty is forced).
  The controller holds the model in the struggle zone by advancing the rung as success-rate rises, and reserves free-exploration each round.
- **Domain axis (secondary, cumulative, never swapped):** web → Linux → Windows → AD → cloud → mobile (Android-first; iOS app-level only, §15). **Cumulative** — earlier domains stay mixed in so the model doesn't forget web when Linux opens.

**[v1.3] Lab provisioned for all six domains from the start (owner direction):** the lab (§12) holds the easy→hard target ladder for **every** domain, so advancing the curriculum — across difficulty and across domains — is a **controller config change, not a new infra build.** Each rung's **win condition is offensive-first** (root/exploit/privesc/objective, environment-checked per §6), with defensive wins (detection/triage/remediation) scored on the *same* scenario — the attack manufactures the ground truth the defender learns from.

**HONEST LIMIT [v1.3]:** provisioning six domain labs re-expands *infrastructure* scope beyond the §0.5 web-only critical path. Reconciliation held firmly: the Phase-1 **learning proof still gates on web** (Stage 2 goal unchanged); the six-domain ladder is built so the curriculum can advance the moment the proof clears and volume allows. This is Phase-2 breadth pulled forward **as lab infrastructure** — not a claim that six-domain weight-learning happens in Phase 1, and it carries real lab-build labour and lab-hardware load (§12).

**OPEN QUESTION:** does a difficulty-led ladder force *real-world* attack variety, or overfit the model to the lab's specific difficulty shape? (Mitigation: free-exploration reserve + domain cumulativity + variant-forcing hard rungs; pressure-tested by Astra, §Appendix Q3.)

---

## 9. Multi-agent population and hybrid cooperation

Agent = a lightweight config row; **large logical population cycled through one endpoint** (not concurrent). **MAP-Elites** (best-in-cell survives → diverse specialists). **Hybrid cooperation, coordinator picks mode per task:** blackboard (team-on-hard-target) + distributed (population-across-targets). **Containment (mandatory):** sanctioned channels only, logged, verifier unreachable, blind agents + critic attacks shared conclusions (anti-groupthink). Full population/cooperation is **Phase 2.**

---

## 10. The three speed approaches (Phase 2; measure-first)
Ranking #1→#3→#2. **#1 Cross-agent sharing** (shared trunk once = blackboard structure; failure: groupthink). **#3 Verified-fact caching** (cache only assured facts; novel exploits can't be cached → diversity protected; **Loop A, not fine-tuning**; failure: stale fact → tag+expire). **#2 Small-model routing** (disposable models for easy ~80%, only the 30B trains; failure: slow router → gain evaporates).

---

## 11. Offensive/defensive tracks and the authorisation gate (offensive-led)

Separate **skill** (cognition — we WANT full attacker thinking: red-teaming) from **authorisation** (behaviour — enforced in code, ownership-verified, not a prompt). **Training is offensive-first [v1.3 foregrounded]:** the offensive agent trains across all six domains' easy→hard ladders **in the owned, isolated lab (§12)**, producing environment-checked wins that are both the Loop-B signal and the defensive corpus. May emulate attacker evasion vs authorised targets but **never truly untraceable** (every action fully logged for audit). Can reconstruct + attribute behaviourally; **cannot** unmask a skilled attacker's true IP/location.

**Hard boundaries (unchanged, restated for the foregrounded offensive track):** autonomous exploitation is **confined to the owned lab**; human-in-the-loop on any live-production offensive action; ownership-verified authorisation (§3.5) before any external engagement. Refusals handled without a stripped model (authorised-lab context → domain fine-tuning → base/thinking variant → light targeted anti-refusal, legitimate *because the enforced scope gate does the safety work*). Three OPA tiers (read-only auto / sandbox auto / production = human-signed token bound to action hash; model holds no prod creds; backups immutable on creds the AI can't reach). Internet: default none; mediated read-only vs local CVE/NVD/KEV/ATT&CK mirror; live fetch GET-only/allowlisted/no-data-in-URLs/rate-limited/logged/OPA-gated.

**§11.9 [v1.1]:** Before paid external pentest: PI insurance; CREST/CHECK-style accreditation; scope-breach IR. **Earlier than Stage 6:** ownership-verification is architectural (gate design from the start); the scope-breach IR playbook is required before the first real external target, pilot included.

---

## 12. The lab (isolated machine; six-domain environments; air-gap/tunnel fixed) [v1.3 expanded]

HP laptop (32GB) = isolated lab; DGX stays clean (targets/malware never on the model/verifier machine). WireGuard firewalled Spark→lab-sandbox-IP only.

**[v1.3] Six-domain lab, each an easy→hard ladder (the curriculum spine, §8):**

| Domain | Lab environments (easy → hard) | Load profile |
|---|---|---|
| **Web** | DVWA → OWASP Juice Shop → WebGoat/bWAPP → custom hardened/defended targets | light containers, parallel pool |
| **Linux** | vulnerable containers → Metasploitable2/3 → SUID/sudo/kernel priv-esc labs → defended multi-step | light containers, parallel |
| **Windows** | misconfig boxes → unquoted-service-path / token priv-esc → defended endpoint (EDR-emulated) | heavy VM, **sequenced one at a time** |
| **Active Directory** | single-domain misconfig → BadBlood-seeded domain / GOAD → multi-forest / Kerberos-attack paths | heavy, multi-VM, **the heaviest; sequenced** |
| **Cloud** | CloudGoat + **LocalStack-emulated AWS** misconfig scenarios (owned, offline — no real cloud spend/exposure) | container-light |
| **Mobile** | Android-first: DIVA / InsecureBankv2 / vulnerable APKs in an Android emulator + MobSF (static+dynamic); **iOS app-level only (§15)** | emulator, medium slot |

Each rung is an offensive scenario with an environment-checked win condition (§6) plus the matching defensive task on the same scenario.

**Parallelism vs the 32 GB reality — HONEST LIMIT [v1.3]:** all six labs will **not** run hot simultaneously on a single 32 GB laptop — AD multi-VM + a Windows VM + an Android emulator alone exceed it. The curriculum controller **time-slices domains**: light-domain pools (web / Linux / cloud-emulation) stay available in parallel; the Android emulator is a medium slot; heavy domains (Windows, AD) are scheduled in windows, one heavy VM at a time (v1.2 rule preserved). The **64 GB mini-PC (v1.2 §12) moves from "future option" to "likely needed once AD/Windows rungs run at volume"** — cheap DDR4, lab isn't bandwidth-sensitive. This is a known, logged constraint (§13 logging group 4 curriculum-state), not a solved one.

**Malware detonation** (snapshot-reverted, no/fake net) unchanged. **DECISION (air-gap/tunnel contradiction FIXED):** detonation and tunnelled target-serving are **mutually-exclusive machine states, enforced in code** (tunnel down / no route during DETONATION; ideally separate NIC/VLAN).

---

## 13. Observability, logging, retention

Six logging groups every generation: (1) training-process (2) MoE routing (3) eval/benchmark (4) data lineage + **curriculum-state + diversity-cap stats + [v1.3] per-domain/per-difficulty win counts & lab-scheduling state** (5) verifier-health + **assurance-suite results + dual-checker disagreements** (6) config/env. A symptom→cause lookup table makes "why isn't it learning?" a lookup, not a guess. Version the environment (verifier/datasets/lab config per generation); separate model-rollback from environment-rollback; change externals one-at-a-time, flagged. Retention: logs forever (KB); golden anchors + recent adapters; prune old intermediate datasets only behind a *trusted* anchor.

---

## 14. Rollback and resume

Every generation = immutable, fully-described snapshot. Golden anchors tagged; re-baseline against anchors to catch slow drift. Diagnose→fix→resume: compare the bad gen's six-group logs vs the anchor → roll back → fix the specific cause → resume forward. Immutability: new gens are new entries; nothing overwrites a saved gen.

---

## 15. Capability boundaries — true vs overclaim

Learn every known technique (real, measurable coverage) · discover novel variants/chains within testable environments (real, bounded by verifier reach) · invent entirely new attack categories unsupervised routinely (overclaim — internal aspiration only) · certainty on a zero-day at first sight (impossible) · exponential self-improvement (myth — staircase, each step waits on human-paced verifier expansion) · "self-improving cognition under Loop-A-only" (overclaim — capacity grows only at lab-volume rate; effective reasoning rises via elicitation). On novel attacks: behavioural recognition → anomaly flag → unverified hypothesis → rapid lab verification (detonate→observe→fresh ground truth→verified detection→push to all). Defensive novelty comes from the world; the model need not invent it. **Mobile: Android buildable; iOS app-level only, full device compromise out of reach (nation-state tier); camera/mic/file access hardest-locked, authorised-only, logged, Phase 2.**

---

## 16. Full stack + internal architecture

**Stack (all OSS):** vLLM (serving, SM121 container) · Unsloth + TRL (SFT + GRPO, NGC container) · MLflow (registry) · PostgreSQL + object store · OPA (authz + ownership) · Wazuh/Suricata/Zeek/YARA/ClamAV/Velociraptor · Atomic Red Team + Sigma · NVD/CVE/KEV (local mirror) · ATT&CK/D3FEND · CAPE/FLARE-VM/REMnux/INetSim · **[v1.3] lab targets: DVWA/Juice Shop/WebGoat (web) · Metasploitable/priv-esc containers (Linux) · vulnerable Windows VMs (Windows) · GOAD/BadBlood (AD) · CloudGoat/LocalStack (cloud) · DIVA/InsecureBankv2/MobSF + Android emulator (mobile)** · WireGuard · (Phase 2) Frida/MobSF dynamic.

**Services:** security-core · ai-orchestrator · agent-population (P2) · threat-intelligence · network-monitor · endpoint-manager · vulnerability-engine · incident-manager · response-engine · recovery-engine (P2) · learning-engine · model-registry · **verifier-service (sealed + assured)** · curriculum-controller · lab-gateway · authz-service (OPA + ownership) · customer-dashboard.

**Internal code architecture [v1.2]:** layered **api / domain / infra** per service. `domain/` is pure logic (no I/O, no LLM in verifier/authz/gate domains). Cross-service calls via typed clients only. `lab/` never imports Spark weight/credential code; the learning engine never reads sealed scenarios or verifier answer keys.

---

## 17. Roadmap

**Phase 1 (the proof):**
- **Stage 0** — pre-work: startup credits; re-verify prices/versions; cloud rehearsal + **run `benchmark.py` fitness report (§2.5) [v1.3]**; order HP RAM; resolve BLOCKER open questions.
- **Stage 1** — foundation: vLLM serving FP8 (+ dense fallback), batching, prefix caching, **benchmark throughput**; Unsloth+TRL path (verify MoE on ARM); lab laptop (WireGuard + §12 state machine). **[v1.3] stand up the easy rungs of all six domain labs** (light-domain pools first; heavy Windows/AD scaffolded, scheduled; cloud via LocalStack; Android emulator) so the curriculum spine exists — while the proof target stays web.
- **Stage 1.5 — MEASUREMENT GATE:** measure verified-unique-wins/day vs the pre-registered bar; decide Loop B per the two-way rule. Do not proceed to Loop B without clearing this.
- **Stage 2 — verifier-first + the proof:** build the **assured web verifier FIRST** (detection slice **built**; exploitation slice next, §6.6); fine-tune for web; orchestrator + small agent group; curriculum on web. **Goal: one SFT generation measurably beats the sealed web benchmark** (or the give-up rule fires — a valid, logged outcome).

**Phase 2 (contingent on the proof):** Stage 3 defensive + live ownership-verification + scope-breach IR · Stage 4 recovery · Stage 5 recursive engine (MAP-Elites, cooperation, GRPO, speed approaches, **curriculum advancing up the six-domain ladders now provisioned in Stage 1 [v1.3]**, malware detonation) · Stage 6 commercial (multi-tenant, accreditation, insurance).

---

## 18. Commercial vision

**Beachhead (committed): web domain** — low-regret, feeds both commercial directions. **Commercial wedge (deferred, leaning defensive-first):** lab-verified detections/adapters shipped to customers — lower liability than autonomous pentest-for-money; **pentest as premium upsell after accreditation.** Honest pitch: **"the product improves from our adversarial lab, delivered as updated detections/adapters — your data never trains the model."** Keep customer telemetry OUT of training by default (consent + UK GDPR otherwise). Never promise perfect immunity or reasoning gains the loop isn't making.

---

## 19. Open questions (prioritised)

**BLOCKER — status after verification:**
1. vLLM MoE+FP8 on GB10 → **RESOLVED** (named SM121 container; pin tag at build).
2. Unsloth MoE fine-tune on ARM → **RESOLVED** (NGC container + aarch64 patches; `FastModel`).
3. Real measured throughput → **Reference numbers in hand; measure your own unit in Stage 1 via `benchmark.py` [v1.3].**

**IMPORTANT:** verified-unique-wins/day (Stage 1.5) · concurrency ceiling · NVFP4 quality · HP RAM ceiling (32 vs 64 — **[v1.3] now leaning 64/mini-PC given six-domain lab**) · ownership-verification method design · **[v1.3] offensive-task sealed-benchmark design (how to score "did it exploit" fairly and un-gameably across six domains)**.

**LATER:** model versions/licences at build time · startup-credit timing · cooperation blind/shared mix · cache-staleness expiry · router-freeze vs light-tune trade-off.

---

## 20. Governance — git/PR and decisions-to-revisit [v1.2]

**Git/PR discipline (agreed):**
- **No AI/Claude attribution anywhere** — commits, PRs, branches, issues are all in the human's name and voice; no "Generated with…", no "Co-Authored-By".
- **`main` stays roughly empty until proven;** every functionality/stage-chunk = its own focused feature branch → PR. The build agent **opens PRs; the human reviews and merges.** A PR template enforces DoD/test/no-attribution checklists.

**Decisions-to-revisit tracking (agreed):** constraint-driven "for now" choices logged in a tracked file **and** a GitHub issue (labelled by trigger), with the condition to revisit and the action on trigger. **[v1.3] new entries:** the six-domain-lab-up-front decision (trigger to re-collapse to web-only if lab labour/hardware threatens the web proof); the 64 GB/mini-PC lab-hardware line (trigger: AD/Windows rungs OOM the 32 GB laptop at volume); the offensive-variant lock (trigger: §4.2 bench-off on offensive tasks).

---

## 21. Verified software setup appendix (the known-good GB10 path) [v1.2]

> **Golden rule: run everything in the right NVIDIA NGC / community container. Never bare-metal pip install torch on aarch64 — it silently falls back to CPU-only and fails.**

**Serving (vLLM):** SM121-kernel container (NVIDIA NGC `nvcr.io/nvidia/vllm:<tag>`, or community `avarok/dgx-vllm`, `eugr/spark-vllm-docker`). Serve the FP8 variant; `--gpu-memory-utilization 0.85 --max-model-len 32768`, continuous batching + prefix caching + multi-LoRA. **Do NOT set `CUTE_DSL_ARCH=sm_121a`** (hangs). NVFP4 optional/later.

**Fine-tuning (Unsloth):** NGC PyTorch/Unsloth container (NGC torch 2.10 / CUDA 13.0; FA2 native on GB10). Apply the three aarch64 transformers patches before any model loads. Use **`FastModel`** (not `FastLanguageModel`) for the MoE; **router-layer fine-tuning disabled by default = our frozen-router policy.** Verify torch is CUDA-aarch64, not `+cpu`. On unified-memory OOM, flush page cache and retry. **Stock vs optimised = ~5 days vs ~20 hours per 25k×3 LoRA round** — the 3-day cadence needs the optimised path.

**Reference GB10 numbers (verify your own):** serving ~44–85 tok/s single / ~300 tok/s batched; LoRA ~451 tok/s stock → ~3,461 optimised. Caveat: community/vendor-container results, not a controlled test on our unit. The *capability* questions (serve the MoE, fine-tune the MoE) are answered **yes** with real evidence; absolute numbers are **measured on our unit via `benchmark.py` in Stage 1 [v1.3]**.

---

## Appendix — questions we'd most like the reviewer to pressure-test

1. Is the Loop B pre-registered threshold (300 floor / 800 aspirational, give-up-twice, two-way revision) methodologically sound, or does pre-registering a folklore-calibrated number just relocate the judgment error?
2. Does the verifier-assurance scheme (§6.6) actually terminate the "who checks the checker" regress, or hide a residual trust assumption?
3. Is "difficulty-led curriculum forces novelty" (§8) true, or does it overfit the model to the lab's specific difficulty shape rather than real-world attack variety?
4. Is the batching-vs-long-context quadrant analysis (§5.2) the real cadence constraint, or is something else binding?
5. Is defensive-first (§18) the right commercial wedge given the project is *offensive-led in training* — or is there a tension between what it learns first and what it should sell first?
6. Does §3.5 ownership-verification actually stop authorised-scope-abuse, or can a determined malicious client defeat it?
7. **[v1.3]** Does provisioning all six domain labs up front (§8/§12) strengthen the curriculum, or does it violate the §0.5 critical-path discipline and endanger the web proof by spreading scarce labour and 32 GB of lab hardware too thin? And is the offensive sealed-benchmark (scoring "did it exploit" un-gameably across six domains) a harder assurance problem than the detection benchmark we've already built?
8. What have all prior critique rounds and this document still collectively missed?

---

*End of v1.3. The verifier is the foundation — and the verifier's own correctness is assured, not assumed. Loop B is the committed goal, switched on by measured volume, not hope. Offensive-led in training (the attack is the data engine for the defence), honest in claim, contained by design, validated on cloud before purchase. The lab is provisioned across all six domains as an easy→hard curriculum ladder — infrastructure pulled forward — while the Phase-1 proof still runs through web first.*
