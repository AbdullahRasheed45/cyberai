> Subsequent runnable-workflow fixes and current authority: `MASTER_BRIEF_v2.3.md`
> and `WORKFLOW_RECONCILIATION_2026-11-16.md`. The rows below preserve the v2.2
> remediation record; SPEC/OPEN rows have not become implemented by this update.

# Review remediation ledger — 16 November 2026

Scope: original findings 1–29 and follow-up N1–N6. This ledger distinguishes code
repairs from corrected requirements for **unbuilt** components. A SPEC entry does
not mean its future implementation or machine-level test has passed. v2.2 is the
current coherent specification; v2.0/v2.1 are preserved for exact comparison.

| Finding | Concrete remediation | Evidence / remaining execution |
|---|---|---|
| 1 | §6/T5a.5 separate checker admission and original-evidence adjudication; individual evidence/checker-hash verdicts, mixed-cluster test; no Boolean promotion flag. | SPEC: graduation engine unbuilt. |
| 2 | §4.1/T2A.11 root-owned argument-free launcher, fixed cwd, isolated interpreter, complete frozen dependencies, bounded stdin IDs. | SPEC: install/cwd/module/env attacks must run on Linux. |
| 3 | §4.3 sealed inference namespace/permissioned socket, no shared engine server or hidden-port assumption; deny client/admin access. | SPEC: real-account/server isolation unexecuted. |
| 4 | §4.4 external observer, separate credentials, no fork/closure secrecy claim, bounded byte-only IPC, externally retained final commitment. | SPEC: target-RCE/chain rewrite/truncation/substitution suite required. |
| 5 | §5/§7.1 explicit claim event; principal/resource/policy/state/delivery binding; shadow checks referenced event rather than first match. | SPEC: generic verifier unbuilt. |
| 6 | T3.5 separates crash/fault/harness/timeout/OOM/control/novelty, pins compiler/runtime, replay/patch controls; §15 measures overhead. | SPEC: native domain unbuilt. |
| 7 | T3.5 names a runtime report adapter, explicitly untrusted by itself; corroboration and ordinary-abort/forged-text controls; unsupported cases UNVERIFIABLE. | SPEC: runtime hooks/classifier unbuilt, no new sanitizer pass claimed. |
| 8 | §5 versioned discriminated evidence contracts; trusted nonce; exact replay blobs/ground-truth inputs; judge identity signature consistent. | SPEC: schema-2 models/migrations unbuilt. |
| 9 | Detector 0.4.0 replaces predicate forcing with consistent field-value counterfactuals, joint assignments and explicit work/deadline caps. | CODE: original positive-identifier, negation, impossible-branch and joint-field regressions. Finite development assurance only. |
| 10 | §7.1/T3.2 clean-state variant replay and business-result/protected-state matrix; special-case/dummy200/disable-all controls. | SPEC: kit remediation oracle unbuilt; current narrow reference is not a general patch oracle. |
| 11 | §11.2 feasible integer allocation, >=7 families, bounded search/work limits, explicit bootstrap zero-old-replay, later replay shortage fails. | SPEC: production dataset builder unbuilt. |
| 12 | §11.3 group-level estimand/inference, dependency assumptions, immutable IDs, multiple-look/comparison correction, effect and multifamily condition. | SPEC: proposed numbers need D-7; full gate unbuilt. |
| 13 | T2A.14/T2B.4 complete variant lineage, development-only selection, identity-bound baseline replacement/reuse and parent+anchor comparisons. | SPEC: variant comparison and full gate unexecuted. |
| 14 | C3/C12/T2A.10/12/14/16 behavior/implementation diversity, matched budgets, all-attempt total cost, unseen implementation vs class distinction. | SPEC: no seed-diversity or reasoning-equivalence claim. |
| 15 | §6 immutable verdict/graduation/revocation events; authoritative projection and transitive dataset/generation/anchor taint; no invented attempt row. | SPEC: store/lineage engine unbuilt. |
| 16 | §6/§7.3 no-signal human intake; independent negatives/metamorphic/blinded validation; advisory triage cannot suppress intake. | SPEC: checker-growth path unbuilt. |
| 17 | §7.3/T2A.7 privileged assurance bootstrap separate from scheduling; installed certificate binds all content/config/checker/suite hashes. | SPEC: admission implementation unbuilt. |
| 18 | Current worker caps raw input, counts all attempts, terminates with evidence at16, partial/idle/session deadlines, duplicate-key rejection; client caps response allocation. Kit §5 additionally specifies all generic field/token budgets. | CODE for protocol1: oversized/partial/duplicate/flood regressions. SPEC for future generic tools. |
| 19 | §4.1/2 signed-by-authority approval inbox rather than name; capability tiers; secure registry ingestion and one lifecycle broker with recovery. | SPEC: broker/registry/authz engine unbuilt. |
| 20 | §12 pre-capture sandbox profile, forbidden mounts/socket/egress, pins, free backend, MCP allow-list and sensitive artifact lifecycle. | SPEC: rea not adopted or executed. |
| 21 | T3.3 per-family RO/RW mounts, namespace/internal privilege and external observer; incompatible profiles refused. | SPEC: Linux family profiles unbuilt. |
| 22 | T1B.4 denies non-lab and production until T3.4 exists; scope/action/address/expiry/nonce/human authority and disclosure boundary specified. | SPEC: no new outside-target allowance implemented. |
| 23 | Shared SSH argv, existing worker forced-command mode, expected-host/scenario checks; setup failures recorded; §9 correct deployment command. | CODE: local subprocess/unit checks. Actual pinned-key SSH/firewall/VM isolation still UNEXECUTED. |
| 24 | §11.1 exact pilot dependency exception, includes dataset/sealed/registry/masks, seven families, descriptive evaluation and no promotion bypass. | OPEN D-5; normal stage order applies until explicit approval. |
| 25 | §15 complete measured occupancy, clock/token semantics, failed-N cost and defined dimensional formula; §16 no invented speed/calendar certainty. | SPEC: numeric GPU measurements remain absent. |
| 26 | 32GB-only proposed AD budget with host reserve; no extra builder/hardware assumed; provider/iOS semantics unsupported until available. Owner targets unchanged. | SPEC: resource profile must be measured; D-6 remains OPEN. |
| 27 | T2B.1 all-role token masks; T5a.5 same-conditioning DPO; optional GRPO disabled pending complete policy/logprob/KL/zero-variance contract. | SPEC: these engine training paths unbuilt. Existing smoke is not their validation. |
| 28 | §18–20 implemented/specified distinction, no perfect/free/frontier comparison; source/build/debug/reproduce and human triage prerequisites. | SPEC: capability claims remain hypotheses until measured. |
| 29 | §0/§17 and decisions preserve M-001/R-009/R-011 authority, approved vs proposed changes and owner milestones. | Owner decisions remain OPEN, not falsely closed. |
| N1 | Non-lab denial cannot be overridden by caller-written scope/name/disclosure flag. | SPEC: fail-closed T1B.4/T3.4. |
| N2 | Registry-owned new inodes, no-follow regular-file ingestion, approved hash verification, no moved engine-owned trees. | SPEC: race/link/open-handle tests required. |
| N3 | Impossible incidental branch retains behavioral verdict; negation retains actual Boolean semantics. | CODE: regression fails before correction and passes after. |
| N4 | Original adjudication/exact replay/fresh generalization are distinct executions; only actual corresponding verified trajectories eligible. | SPEC: no synthesized attempt-equivalent rows. |
| N5 | Shadow verifies the explicitly claimed event, not first matching event; repeated/background event tests mandatory. | SPEC: future verifier test contract. |
| N6 | Runtime report interface explicitly named, provenance bounded, no signal-to-class inference, unsupported native cases unverified. | SPEC: native adapter/classifier must be implemented and demonstrated before training. |

## Actual offline execution evidence

- All three initial detector reproductions failed under the old code; new tests
  passed after consistent-value counterfactual implementation. A fourth test proves
  work-budget exhaustion cannot become VERIFIED.
- Targeted detector/evaluation/acceptance run: 104 passed, 1 optional skip before
  adding the fourth regression; all four new regressions subsequently passed.
- Worker negative tests failed under old code for oversize/partial-line/forced
  command/budget termination; corrected worker plus existing workflow/rehearsal
  suites: 38 passed.
- Full repository run after both code fixes: **354 passed, 8 skipped**.
  Skipped tests are environment/optional checks, not evidence of a pass.
- No compute rented, no hardware purchased, no merges, no production deployment.
  No real SSH, host isolation, native sanitizer adapter or GB10 inference/training
  execution is represented by these CPU/subprocess tests.

## Review handoff acceptance

Read the code diffs and this ledger, not just the v2.2 assertions. The immediate
code defects are repaired offline and the reviewed task-contract contradictions
are replaced. The future platform remains unbuilt. Do not turn SPEC or OPEN rows
into implementation-complete claims. A claim that "all runtime blockers passed"
would be false. See `HANDOFF_2026-11-16.md` for the exact next actions.
