# Product alignment and six-domain lab curriculum

12 November 2026. Owner clarification following the full reread of MASTER_PROJECT_BRIEF_v1.2_FOR_CRITIQUE(1).md.

## Authority and scope

The actual v1.2 brief is the product baseline. Later owner instructions retain a working fine-tuned model target of 15 January 2027 and a six-domain product target of 30 June 2027. These are targets, not outcomes established by passing infrastructure tests.

This addendum concerns the PRODUCT ONLY. Commercial positioning, customer segments, pricing, accreditation strategy and defensive-first sales arguments are outside the current discussion and must not drive architecture or training priority.

The brief already makes training offensive-led in §§1.1 and 11. The detection-heavy implementation was a partial infrastructure slice, not the intended entire product. Preserve that work as a component and restore the complete learning workflow.

## Product definition

A Qwen3-30B-A3B-family reasoning model powers a logical population of security agents through one shared serving endpoint. In owned/authorised labs, agents investigate security properties, plan bounded tests, demonstrate weaknesses and record environment evidence. Corresponding defensive tasks detect activity, investigate it, remediate its cause and verify recovery. Assured deterministic verifiers decide which outcomes are established. Verified experience supports gated model-weight updates.

The workflow is: scenario -> offensive investigation -> environment-verified outcome -> defensive detection/remediation -> independent retest -> provenance-tagged experience -> candidate weight update -> sealed evaluation -> promotion or rejection.

Offensive-first is the learning priority, not a rule that defensive verifiers must wait until offensive capability is complete. Build both sides of the verifier and telemetry path early. Detection-only rule generation is insufficient as the first complete offensive workflow.

Keep autonomous offensive execution inside owned labs; live external action follows the brief's enforced authorisation and human approval gates. Sealed verifiers, answer keys, promotion controls, model weights and privileged credentials are unreachable from target environments. Model self-reports are never ground truth.

## Preserve the actual architecture

- One shared endpoint; agents are configurations/trajectories, not many simultaneous full model copies.
- Qwen3-30B-A3B remains the default family, selected/confirmed by the brief's controlled task-quality/token-cost comparison. A non-thinking Instruct-2507 pin is an integration candidate, not a silently accepted permanent replacement for native reasoning.
- Preserve the optimized v1.2 serving/training route; measure runtime compatibility and absolute speed on actual GB10 before purchase.
- Preserve verifier-first implementation, assurance fixtures, dual-check disagreement quarantine and immutable verifier versions.
- Loop A improves orchestration, strategy, retrieval and verified facts without changing weights.
- Loop B trains candidate adapters/weights on curated verified experience. Maintain replay, diversity constraints, frozen-router policy, forgetting canaries, sealed evaluation, immutable generations and rollback.
- Introduce GRPO only after an SFT generation demonstrates held-out gain, as the brief requires.
- Full MAP-Elites population and cooperation remain staged after the first proof. Do not quietly remove them from the product, or make implementing all of them a prerequisite for the first working fine-tune.
- Keep the api/domain/infra separation and typed service boundaries. No LLM decision inside deterministic authorisation/verifier/promotion logic.

## Six-domain lab: available curriculum, staged activation

Maintain manifests and a staged target inventory for all six domains. This does not claim all environments already exist or can run concurrently. The web proof remains first; the curriculum grows cumulatively across Linux, Windows, AD, cloud and mobile. Starting to specify all six labs now does not make mature six-domain capability a January requirement.

The lab host remains separate from the Spark engine, following §12. Given the planned 32GB laptop, use measured resource profiles and scheduling: light containers may run together, heavy Windows/AD/mobile environments may require separate batches. An AD task requiring several communicating hosts must run its required topology together; do not pretend independent single-VM runs reproduce that scenario. If the topology does not fit, record the limitation and adjust the lab allocation before claiming coverage. Spark cloud access does not by itself supply the separate target lab.

Cloud labs have two evidence categories: local emulation for early controlled tasks, and actual provider sandbox verification where provider semantics are essential. Do not treat emulator success as equivalent to real IAM/provider behaviour. Mobile begins with owned Android apps and emulators; retain the brief's later, bounded iOS app-level scope.

| Domain | Level 1: fundamentals | Level 2: single weakness | Level 3: multi-step | Level 4: realistic constraints | Level 5: unseen generalisation |
| --- | --- | --- | --- | --- | --- |
| Web | Map routes, roles and trust boundaries | Demonstrate one seeded access/input/session flaw | Connect multiple application weaknesses | Stateful workflows, limited visibility and legitimate background requests | Withheld application families/implementations, including patched controls |
| Linux | Map users, permissions, services and process boundaries | Demonstrate a seeded permission or service weakness | Connect low-privilege access and a bounded privilege-boundary failure | Mixed services, restricted capabilities and normal administrative noise | Withheld configurations and service combinations |
| Windows | Map accounts, services, permissions and event sources | Demonstrate a seeded service/permission weakness | Connect access with a controlled privilege-boundary failure | Endpoint controls, changed configurations and normal user activity | Withheld host images and configuration families |
| Active Directory | Understand identities, groups, trusts and domain services | Demonstrate one seeded identity/delegation/configuration failure | Validate a bounded multi-host identity path | Segmentation, constrained accounts and service dependencies | Withheld directory topologies and privilege relationships |
| Cloud | Map resources, principals and permission boundaries | Demonstrate one seeded IAM/storage/workload exposure | Connect permissions and workloads within the sandbox | Guardrails, varied policy conditions and legitimate workload activity | Withheld policy/resource structures; provider-specific validation where needed |
| Mobile | Map owned app components, storage, permissions and API trust | Demonstrate a seeded app-level storage/component/API flaw | Connect app and backend trust failures | Release-like builds, stateful workflows and restricted visibility | Withheld apps/builds and app-backend combinations |

These are task specifications, not executable attack recipes. Concrete target images/tools are selected from the brief and pinned after compatibility checks. Harder means greater reasoning, state, composition or uncertainty; it does not mean moving outside authorised scope.

## Every scenario needs an assurance contract

A versioned scenario manifest should record:
- domain, family/template, level, prerequisite skills and allowed actions;
- image/topology identifiers, seeds and resource requirements;
- ownership/scope, target boundary and reset procedure;
- starting identity/privileges and baseline security state;
- hidden success predicate and two independent evidence paths where applicable;
- required telemetry and how unavailable observations are classified;
- offensive goal and the corresponding defensive task;
- patched/non-vulnerable controls, service-health checks and negative cases;
- trajectory provenance and split assignment.

Never reward a system for finding a condition that setup had already satisfied. Examples: a preprivileged session, a pre-existing marker, a broken service mistaken for a fix, or absent telemetry mistaken for a clean request. A task without a trustworthy verifier can enter the candidate bank, not rewarded training data.

Defensive counterparts are measured separately: the attack may succeed while detection fails; a patch may block the attack while breaking the service. Preserve both verdicts. Full workflow success requires the appropriate component conditions, not an average that hides a critical failure.

## Curriculum progression and coverage

Use difficulty as the primary progression axis, preserving the brief's intent, but do not assert that increasing difficulty forces genuine novelty. Treat that as an empirical hypothesis.

Advance on predeclared performance over varied development scenarios and independent validation variants; do not train or tune against sealed acceptance data. The controller must also regress to easier tasks when failures show missing prerequisites. Keep easier replay tasks, earlier-domain canaries, a free-exploration reserve and a small allocation to unfamiliar variants.

Do not silently convert a provisional success-rate target into ground truth. Log task availability, attempts, verified outcomes, failure/unevaluable categories, novelty relative to existing trajectories, template shares, tokens and runtime. Deduplicate by scenario/behaviour, not only exact strings. Rotating a hostname or seed is not automatically a unique skill win.

All six domains remain in the curriculum inventory; activation and resource scheduling can be sequential. Report not-yet-built labs as not built. Report one working scenario as narrow scenario coverage, not domain mastery. A cross-domain final level is appropriate only after prerequisites and its entire authorised topology are verifiable.

## Recursive weight improvement: evidence before promotion

1. Freeze current model/environment/verifier versions.
2. Generate authorised lab trajectories with the current model.
3. Verify outcomes independently; quarantine disagreements and unverified hypotheses.
4. Curate train/dev experience with provenance, deduplication, diversity limits and replay.
5. Train a candidate SFT adapter; measure actual training configuration and token volume.
6. Compare current/base and candidate on aligned unseen tasks, plus forgetting/critical-regression checks.
7. Promote only through the brief's gate; otherwise retain the prior generation and diagnose.
8. Repeat using the promoted generation only after an actual gain is established.

Each cycle need not improve. A model reasoning eloquently about a failed action is not a verified win. Keep failed trajectories for analysis; only use corrections as supervised targets after independent verification. Reward and promotion must not be assigned by an LLM critic.

The 300/day floor, 800/day aspiration, template cap and ~100-trajectory pilot revision rule in §7.8 remain recorded provisional hypotheses, not universal scientific thresholds. Do not pad counts to reach them.

There is a real policy conflict: §7.8 says two unsuccessful full-volume generations park Loop B for a year, while the later owner requirement commits to a working fine-tuned model by January. Do not silently pick one or announce weight learning optional. Record a proposed explicit amendment: two failures trigger diagnosis and suspension of automatic promotion; continue controlled first-SFT research toward January. Reconcile that amendment in the project's decision record before treating it as approved policy.

Likewise, the brief treats the full six-domain/recursive product as later-phase work while later owner dates target June. Preserve the six-domain product direction, but define reviewable per-domain acceptance depth and measured dependencies rather than claiming every research subsystem will be mature by that date.

## Hardware trial must represent this product

Retain the cloud-before-purchase gate. Trial data should include representative offensive tool trajectories and defensive/retest records, not only short SQLi-rule targets or ping/pong. Measure useful training tokens, actual sequence lengths, steps, memory/headroom, loading/compilation overhead, serving under long context and batching, adapter deployment and end-to-end verified tasks per unit time.

The current smoke is ten steps at a 2048-token model sequence limit. It is not the production training benchmark. The current inference post_stream path mixes monotonic and epoch clocks when computing wall time; fix that before relying on results. Expand only the measurement paths needed for the purchase decision, not an endless configuration search.

The 24-hour rental is for critical platform/purchase evidence and real trial training. It does not demonstrate mature offensive/defensive capability across six domains or recurring learning gains. The actual target lab must be available alongside compute.

## Immediate repository work

Use this addendum with the actual v1.2 brief and updated CODEX_PROJECT_HANDOFF_2026-11-12.md. Preserve existing verifier and rental code. Repair the concrete Round-18 evaluation-boundary issues, add the first assured offensive web workflow with its defensive/retest counterpart, and define resource-aware manifests for the six-domain curriculum. Stage implementation rather than building all targets simultaneously. Keep commercial topics outside this product task.
