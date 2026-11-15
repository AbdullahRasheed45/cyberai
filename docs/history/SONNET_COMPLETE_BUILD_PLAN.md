# Complete Build Plan for Sonnet — All Stages (0–6)

**Purpose:** The full end-to-end implementation plan for the Autonomous Cybersecurity AI platform, covering every stage from pre-work to commercial readiness. This supersedes the Phase-1-only `SONNET_BUILD_INSTRUCTIONS.md` by extending it through Phase 2. Read `MASTER_PROJECT_BRIEF_v1.1.md` and `BRIEF_v1.2_CORRECTIONS_AND_SETUP.md` first — this document tells you *how and in what order to build everything*.

**How to use this document:** Build strictly in stage order. Each stage has: Goal, Prerequisites, Build steps, and a Definition-of-Done (DoD) checklist. **Do not start a stage until the prior stage's DoD is fully checked.** Phase 1 (Stages 0–2) proves the thesis; Phase 2 (Stages 3–6) builds out, and is gated on the Stage-2 proof holding.

---

## PRIME DIRECTIVES (apply to every stage)

1. **Verifier-first.** Never build a component that trains or is scored before its verifier exists and passes its assurance suite (brief §6, §6.6).
2. **Phase gate is real.** Stages 3–6 do not begin until the Stage-2 proof (one SFT generation beats a sealed benchmark) holds, OR the give-up rule has fired and Loop-A-primary is the committed engine. Either is a valid, logged outcome.
3. **Deterministic gates.** No LLM in any verifier, gate, or authorisation decision.
4. **Everything logged + versioned** (six logging groups, brief §13); every run reproducible.
5. **Measure, don't assume.** Write measurement harnesses; never hardcode throughput.
6. **Fail loud.** Verifier disagreement, missing ground truth, CPU-only-torch, or gate failure → stop and surface.
7. **Machine isolation is physical.** `lab/` code never imports weight/credential-holding Spark code; the sealed benchmark is unreachable by the learning engine; the §12.2 detonation/tunnel mutual-exclusion is enforced in code.
8. **Run on the known-good platform path** (Appendix in v1.2): NGC/SM121 containers, aarch64 patches, `FastModel` for the MoE, verify torch is CUDA-aarch64 not +cpu.

---

## REPOSITORY STRUCTURE (full, all stages)

```
cyberai/
├── README.md · pyproject.toml · Makefile · .env.example
├── docker-compose.yml              # Spark-side services
├── docker-compose.lab.yml          # lab (laptop) services — SEPARATE
├── containers/
│   ├── vllm-gb10/                  # SM121 vLLM container pin + serve entrypoint
│   └── unsloth-ngc/                # NGC Unsloth container + aarch64 patches
├── configs/
│   ├── models.yaml · serving.yaml · training.yaml
│   ├── curriculum.yaml · loopB_gate.yaml
│   ├── authz_policy/*.rego
│   └── retention.yaml
├── libs/ {common, schemas, clients}
├── services/
│   ├── verifier_service/           # Stage 2 (BUILD FIRST)
│   ├── ai_orchestrator/            # Stage 1–2
│   ├── security_core/              # Stage 2–3
│   ├── authz_service/              # Stage 1 (OPA + ownership verification)
│   ├── lab_gateway/                # Stage 1 (WireGuard + §12.2 state machine)
│   ├── model_registry/             # Stage 2 (MLflow)
│   ├── learning_engine/            # Stage 2 (SFT) → Stage 5 (GRPO, population)
│   ├── curriculum_controller/      # Stage 2 (web) → Stage 5 (all domains)
│   ├── threat_intelligence/        # Stage 3
│   ├── network_monitor/            # Stage 3 (Suricata/Zeek)
│   ├── endpoint_manager/           # Stage 3 (Wazuh/Velociraptor)
│   ├── vulnerability_engine/       # Stage 3 (NVD/CVE/KEV)
│   ├── incident_manager/           # Stage 3
│   ├── response_engine/            # Stage 3 (OPA-gated)
│   ├── agent_population/           # Stage 5 (MAP-Elites)
│   ├── recovery_engine/            # Stage 4
│   └── customer_dashboard/         # Stage 2 minimal → Stage 6 full
├── lab/ {targets, detonation, state_manager, agent_runner}
├── verifiers/ {web, linux, windows, ad, cloud, mobile, registry, */assurance}
├── benchmarks/ {sealed, canaries}
├── datasets/ {seed, builder}
├── scripts/ {measure_throughput, stage15_gate, ...}
└── tests/ {unit, integration, assurance}
```

---

# PHASE 1 — THE PROOF (Stages 0–2)

## STAGE 0 — Pre-work (before hardware)

**Goal:** De-risk and prepare so Stage 1 starts on a known-good path.

**Build steps:**
1. **Resolve the (now-verified) setup path.** Record the exact container tags (vLLM SM121; Unsloth NGC) and the aarch64 patch set from v1.2 Appendix B. Pin them in `containers/`.
2. **Pre-Spark cloud rehearsal** (free cloud, small model): build and debug `benchmarks/sealed` harness, `scripts/measure_throughput.py`, and the orchestrator agent loop on a tiny model. Learn lever *shapes* only — absolute numbers won't transfer.
3. **Scaffold the repo** (structure above), `libs/common` + `libs/schemas`, CI (lint + unit + assurance gates).
4. **Apply for startup credits** (NVIDIA Inception etc.) — weeks of lead time.
5. **Order HP RAM** (2×16GB DDR4-3200); confirm ceiling via `wmic memphysical get maxcapacityex`.

**DoD:**
- [ ] `libs/schemas` frozen (Trajectory, Verdict, DatasetVersion, TrainingRun, EvalResult, GenerationRecord, AuthzRequest/Decision) with mandatory provenance.
- [ ] CI runs unit + assurance test stubs.
- [ ] Container tags + aarch64 patch set pinned in `containers/`.
- [ ] Sealed-benchmark harness + measurement harness run on a tiny model in free cloud.

---

## STAGE 1 — Foundation (on the Spark + lab)

**Goal:** Reliable local inference + training path + secure two-machine infra, with measured numbers.

**Prerequisites:** Stage 0 DoD; Spark + 32GB laptop in hand.

**Build steps:**
1. **Serving (vLLM, SM121 container):** serve `Qwen3-30B-A3B-FP8` + the dense fallback (`Qwen3-14B`). Continuous batching + prefix caching on, multi-LoRA enabled. **Confirm post-CES software (~2.5×).** Do NOT set `CUTE_DSL_ARCH=sm_121a`.
2. **Training path (Unsloth NGC container):** apply aarch64 transformers patches; `FastModel` loads Qwen3-30B-A3B; run a tiny LoRA smoke-test → confirm loss decreases, adapter writes, **torch is CUDA-aarch64 not +cpu.** Apply the optimised-speedup config early (5-day→20-hour difference).
3. **Measure throughput** (`scripts/measure_throughput.py`): serving tok/s at batch sizes 1/8/32 and context 8K/16K/32K; training step time. Record as the Stage-1 baseline.
4. **Lab laptop:** wipe + fresh OS + Docker/KVM; isolate from home LAN.
5. **lab_gateway + WireGuard:** firewalled Spark→lab-sandbox-IP only; narrow API; all traffic logged.
6. **§12.2 state_manager:** hard mutual-exclusion state machine (TARGET_SERVING XOR DETONATION); enforce tunnel-down + no-route during DETONATION. (Phase 1 uses TARGET_SERVING only; build the machine now.)
7. **authz_service (OPA):** three tiers + scope rule + **ownership-verification hook** (lab IPs owned by allowlist; external-target ownership proof stubbed for Phase 2 but the architecture present).
8. **Lab targets (web):** DVWA, Juice Shop, Metasploitable-web as containers; fresh-spin + destroy/recreate revert; pre-state snapshot for the "not-already-root" check.

**DoD:**
- [ ] vLLM serves Qwen3-30B-A3B FP8 on the Spark; measured batched tok/s recorded.
- [ ] Unsloth tiny LoRA smoke-test passes on real GPU (not CPU-only torch).
- [ ] Training speedup config applied; LoRA step time recorded.
- [ ] WireGuard reaches only the lab sandbox IP; nothing else on the subnet.
- [ ] state_manager test proves tunnel unreachable during DETONATION.
- [ ] authz_service denies out-of-scope and production-without-token.
- [ ] Web target containers spin up, are attacked, and revert.

---

## STAGE 1.5 — MEASUREMENT GATE (before committing to Loop B)

**Goal:** Measure what the rig actually produces, and decide Loop B against the pre-registered bar.

**Build steps:**
1. Run the orchestrator + web targets + verifier for a measurement window.
2. `scripts/stage15_gate.py`: count **verified, unique, non-trivial wins/day** (apply the diversity cap). Compare against `configs/loopB_gate.yaml`:
   ```yaml
   floor_verified_unique_per_day: 300
   max_template_share: 0.15
   aspirational_per_day: 800
   revision_rule:
     lower_bar_if: "~100-trajectory pilot SFT measurably beats the sealed benchmark"
     give_up_if: "a full-volume round fails to beat the sealed benchmark twice in a row"
     give_up_action: "park Loop B for the year; Loop A becomes committed engine"
   ```
3. Print the measured figure + recommended decision (switch Loop B on / lower bar per pilot / park). **Human confirms** — do not auto-decide.

**DoD:**
- [ ] A measured verified-unique-wins/day figure is logged.
- [ ] A recommended decision vs the pre-registered bar is produced and human-confirmed.
- [ ] If volume is low: Loop A is confirmed as the committed engine (valid outcome); Loop B build waits.

---

## STAGE 2 — Verifier-first + first generation (THE PROOF)

**Goal (critical path):** an assured **web** verifier + one SFT generation that **measurably beats the sealed benchmark**.

**Prerequisites:** Stage 1.5 cleared (Loop B switched on, or bar revised per pilot evidence).

**Build steps (strict order):**
1. **verifier_service + verifiers/web:** exploitation (real session `uid=0`, not-already-root), detection (TP/FP vs labelled corpora, FP penalised), remediation (hole-closed AND service-alive via real health check).
2. **verifiers/web/assurance (§6.6 — do not skip):** ground-truth seed suite · planted false-positives (pre-rooted container, restarted-but-broken service, mislabelled sample) · dual-checker disagreement alarm · verifier versioning. Must pass in CI before any verifier is usable.
3. **Trajectory store** (Postgres + object store, provenance-tagged) + **ai_orchestrator** full agent loop (think→tool→observe→adjust, adaptive think caps, through authz→lab_gateway).
4. **datasets/builder:** dedupe + external-data poison-screen + seed-replay + **diversity cap enforced in code** + composition/diversity stats on each DatasetVersion.
5. **model_registry (MLflow):** immutable generations, golden-anchor tagging, lineage, rollback info.
6. **benchmarks/sealed** (separate service, learning engine cannot read scenarios) + **canaries** (general reasoning/coding).
7. **learning_engine (SFT only; GRPO stubbed):** Unsloth `FastModel` SFT LoRA, **router frozen (Unsloth default)**, full Group-1/2 metrics logged; promotion controller (sealed bench + canaries + statistical gate + no FP regression + human approval); rollback controller (diagnose→fix→resume).
8. **curriculum_controller (web only):** difficulty tiers; ratchet difficulty to success rate; free-exploration reserve; log curriculum state per generation.
9. **Wire the full loop** and run ≥1 full generation.

**DoD (the proof):**
- [ ] Web verifier assurance suite passes fully in CI.
- [ ] Orchestrator drives a full web attempt → verified verdict end-to-end.
- [ ] Dataset builder enforces seed-replay + diversity cap + poison screen.
- [ ] SFT generation runs (frozen router) with full metrics logged + reconstructable.
- [ ] Sealed benchmark scores a candidate without the learning engine reading scenarios.
- [ ] Registry stores an immutable generation; rollback restores it.
- [ ] **One SFT generation measurably beats the sealed benchmark** — OR the give-up rule fires (logged, Loop-A-primary committed). **Either outcome ends Phase 1.**

**→ GATE: Do not start Phase 2 until this DoD holds.**

---

# PHASE 2 — BUILD-OUT (Stages 3–6; contingent on the Stage-2 proof)

## STAGE 3 — Controlled defensive capabilities

**Goal:** reliably investigate and propose defensive actions, all sandbox-tested, with human approval for production.

**Build steps:**
1. **Defensive tool integration (AI interprets, doesn't blindly trust):** `network_monitor` (Suricata/Zeek), `endpoint_manager` (Wazuh/Velociraptor). Agents consume + correlate their output.
2. **vulnerability_engine:** NVD/CVE/KEV **local mirror** (no raw internet); prioritisation verifier (score vs CVE/CPE/KEV on configured hosts).
3. **threat_intelligence:** feed enrichment from local mirrors.
4. **detection-engineering** agents producing Sigma/Suricata/YARA → scored by the detection verifier.
5. **remediation** agents → remediation verifier (hole-closed AND service-alive) in sandbox.
6. **incident_manager:** investigation lifecycle + evidence records (`security_core`).
7. **response_engine (OPA-gated):** read-only autonomous; sandbox autonomous; **production = human-signed token bound to action hash**, model holds no prod creds.
8. **Ownership-verification LIVE** (§3.5): activate the real ownership-proof mechanism (DNS/HTTP challenge, WHOIS/RIR, signed attestation) before any external target. **Scope-breach IR playbook written now** (before first external/pilot engagement — not Stage 6).
9. Curriculum adds the **Linux** domain (cumulative; retain web share).

**DoD:**
- [ ] Each new domain/task class has an assured verifier before it trains.
- [ ] Detection/remediation/vuln verifiers pass assurance.
- [ ] response_engine enforces tiers; production needs a signed token.
- [ ] Ownership-verification blocks an external target lacking proof.
- [ ] Scope-breach IR playbook documented.
- [ ] A generation improves on the sealed benchmark across web+Linux without canary regression.

---

## STAGE 4 — Recovery

**Goal:** independently verifiable recovery.

**Build steps:**
1. **recovery_engine:** integrate **immutable/append-only backups** on credentials the AI stack cannot reach.
2. Restoration testing against snapshots; integrity verification; recovery-evidence records.
3. Recovery verifier: restored system matches known-good state (deterministic).

**DoD:**
- [ ] Backups are immutable and unreachable by the AI stack.
- [ ] A restore is verified against known-good state deterministically.
- [ ] Recovery evidence is logged + reconstructable.

---

## STAGE 5 — Recursive learning + evolution (the full engine)

**Goal:** agent strategies AND model weights improve through evaluated generations, across domains.

**Prerequisites:** Stage-2 proof held (one SFT generation beat baseline). **No RL/evolution before this.**

**Build steps:**
1. **agent_population (MAP-Elites):** genome = config; archive indexed by behaviour descriptors (task category × strategy style); best-in-cell survives.
2. **Hybrid cooperation (§9.4):** blackboard (team-on-hard-target) + distributed (population-across-targets); coordinator picks mode; **sanctioned channels only, logged; blind agents + critic (anti-groupthink).**
3. **Speed approaches (#1→#3→#2):** cross-agent sharing (= blackboard structure) · verified-fact caching (cache only assured facts, tag+expire — Loop A, not fine-tuning) · small-model routing (disposable, only the 30B trains). Each behind a flag, **measured on the Spark** before relying on it.
4. **RL engine (GRPO):** groups of attempts per task, verifier-scored, above/below-group-average; **only after SFT beat baseline.** Rewards only from assured deterministic verifiers.
5. **Full six-group logging** (§13) incl. verifier-assurance (Group 5) + diversity-cap stats (Group 4).
6. **Golden-anchor registry + rollback/resume** (§14): tag anchors; re-baseline against anchors; diagnose→fix→resume.
7. **Retention policy** (`configs/retention.yaml`, §13.4): keep logs forever; keep anchors + recent adapters; prune old intermediate datasets behind trusted anchors only.
8. **Environment versioning** ("world moved on" fix): verifier/datasets/lab config versioned per generation; change externals one-at-a-time, flagged; re-validate anchors against today's environment.
9. **Curriculum across domains:** Windows → AD → cloud → **mobile (Android-first; iOS app-level only)**. Each new domain cumulative, only after succeeding at the current difficulty frontier; each needs its verifier + assurance first.
10. **Malware detonation activated** in `lab/detonation/` (the §12.2 state machine already gates it — detonation and tunnel never co-live).

**DoD:**
- [ ] MAP-Elites preserves diverse specialists (no monoculture).
- [ ] Cooperation runs through sanctioned, logged channels with blind agents + critic.
- [ ] Each speed approach measured on the Spark; kept only if it genuinely helps.
- [ ] GRPO runs with verifier-only rewards, after SFT-beats-baseline.
- [ ] Each new domain has an assured verifier before it trains.
- [ ] Detonation never co-lives with the tunnel (state-machine test).
- [ ] Golden anchors + rollback/resume demonstrated (degrade → roll back → resume forward).

---

## STAGE 6 — Commercial readiness

**Goal:** a deployable dual-track product.

**Build steps:**
1. **Multi-tenant separation** + privacy/access control; **keep customer telemetry OUT of training by default** (consent + UK GDPR otherwise). The lab-verified corpus is the core asset.
2. **customer_dashboard (full):** alerts, reports, admin, approvals, audit trails.
3. **Audit/reporting**; independent security testing of the platform itself (§3.5 threats: poisoned data, scope-abuse, supply-chain, weight-exfiltration mitigations verified).
4. **Install/update + deployment/support** processes.
5. **§11.9 for pentest-as-a-service:** professional indemnity insurance; CREST/CHECK-style accreditation; scope-breach IR (already drafted in Stage 3) productionised.
6. **Commercial wedge:** defensive-first (lab-verified detections/adapters shipped to customers), pentest as premium upsell after accreditation. Pitch: "the product improves from our adversarial lab, delivered as updated detections/adapters — your data never trains the model."

**DoD:**
- [ ] Tenant separation + access control + audit trails in place.
- [ ] Platform-self threat mitigations (§3.5) independently tested.
- [ ] Weights encrypted-at-rest + egress-monitored.
- [ ] Accreditation/insurance/IR complete before any paid external pentest engagement.
- [ ] Deployment + update + support processes documented.

---

## CROSS-CUTTING REQUIREMENTS (every stage)

- Config via YAML + env; no magic numbers.
- Structured logging into the six groups; every run reproducible.
- Assurance tests (verifier §6.6) run in CI and block merge.
- No LLM in any gate/verifier/authorisation decision.
- Hard dependency boundary: `lab/` never imports weight/credential code; `learning_engine` never reads sealed scenarios or verifier answer keys.
- Secrets only from env/secret store; weights encrypted-at-rest with access control + egress monitoring (§3.5).
- Spark-side vs lab-side docker-compose never merged.
- Run on the known-good GB10 path (v1.2 Appendix): NGC/SM121 containers, aarch64 patches, `FastModel`, torch-is-CUDA-not-CPU.

---

## MASTER DEFINITION OF DONE

**Phase 1 complete when:** the Stage-2 proof holds (one SFT generation beats the sealed benchmark) or the give-up rule has fired with Loop-A-primary committed — either way, logged and honest.

**Phase 2 complete when:** Stages 3–6 DoDs all hold — a dual-track product with assured verifiers per domain, contained recursive learning, immutable recovery, platform-self-security tested, and (for paid pentest) accreditation/insurance/IR in place.

---

*Build the verifier first and assure it. Measure before betting on Loop B. Prove one generation beats baseline on web before anything else. Keep the machines isolated, the gates deterministic, and every claim honest. Everything in Phase 2 waits for the Phase-1 proof.*
