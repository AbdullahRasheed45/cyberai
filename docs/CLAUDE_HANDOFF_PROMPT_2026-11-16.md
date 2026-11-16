# Prompt to paste into the next coding session

I have completed an offline remediation pass on my repository for the original
29 review findings and six follow-up defects. The existing-code defects have
regression-tested fixes; requirements for unbuilt components were corrected in
the versioned brief. This does **not** mean the entire platform is implemented or
that deployment/GPU/security checks have passed.

Read in order:
1. AGENTS.md and GIT_WORKFLOW.md.
2. docs/MASTER_BRIEF_v2.3.md, completely.
3. docs/WORKFLOW_RECONCILIATION_2026-11-16.md,
   docs/REVIEW_FIX_LEDGER_2026-11-16.md and docs/HANDOFF_2026-11-16.md.
4. Actual changes in the focused detector, lab-protocol and v2.3 workflow/documentation
   branches/PRs; inspect current git status and tests rather than trusting summaries.

The detector now varies consistent event-field values instead of forcing predicate
truth; the negation cheat and impossible-branch false rejection have regressions.
The worker terminates on attempted-action exhaustion, bounded/partial input failures
and EOF; SSH rehearsal shares the actual workload transport and validates expected
worker identity/protocol. Earlier v2.2 checks: 354 passed, 8 skipped. Final v2.3 checks: 368 passed,
8 skipped in a clean locked environment; see the current handoff. Skips, CPU mocks and local subprocesses are not hardware evidence.

Use the ledger to distinguish CODE, SPEC and OPEN items. Do not say all runtime
blockers are passed. The generic kit, sealed launcher/server/account controls,
registry publisher, graduation/revocation engine and full learning gate remain
future implementation tasks with corrected acceptance contracts. Real SSH/network/
VM isolation and GB10 runs remain unexecuted.

Preserve product-only, offensive-first authorized labs, independent deterministic
verification, both learning loops, six easy-to-hard domains, one Spark/32GB lab,
Qwen3-30B-A3B MoE, reasoning and the measured variant comparison. Owner targets
remain 15 January 2027 and 30 June 2027; changes need explicit approval. Keep all
unresolved D-1 through D-9 decisions explicit; do not infer approval of a pilot
exception, architecture replacement, parking-policy change or altered milestones.

Continue concrete stage-appropriate preparation, not another broad architecture
rewrite. Reproduce any suspected regression and fix it narrowly. Use the existing
protocol1 worker for trial SSH deployment; the kit worker is unbuilt. Keep evidence
and the handoff current, preserve older versions and useful/unrelated changes,
follow branch/PR rules and report exactly what ran. Do not rent compute, purchase,
merge or deploy production without my explicit authorization for that action.

The v2.3 pass also fixes timing, remote handshake, configuration propagation,
base/adapted workflow records, reporting, cooperative concurrency/cleanup, deadline
reserve and snapshot-manifest validation. The core concept remains unchanged.
Use the latest handoff for final check counts; do not present old counts as new.

Read v2.3 §22 for the owner-requested strengthening techniques. They preserve
the core concept and are staged proposals, not completed features. End your
report with concrete next actions and explicit remaining hardware/policy gates.
