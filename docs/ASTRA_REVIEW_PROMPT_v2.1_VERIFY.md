# Review prompt for Astra — verify the v2.1 fix pass against your own NOT READY review

Paste the block below to the reviewer (Astra, run via Codex) with read access to this repository.
This is a **follow-up, adversarial** review: it asks Astra to check its own prior findings against
what was actually changed, not to re-review the brief from scratch. The goal is a scorecard —
how many of the 29 findings are genuinely fixed — plus anything the fix pass got wrong or broke.

---

You are Astra. On 15 November 2026 you reviewed `docs/MASTER_BRIEF_v2.0.md` for this project and
returned an overall verdict of **NOT READY**, with 29 numbered defects (4 marked CRITICAL) and a
verdict (sound/risky/broken) on all 14 of the brief's efficiency changes (C-1…C-14), of which only
C-5, C-13 and C-14 came back fully **sound**. A fix pass has now been done in response. Your job
this time is **not** to re-review the brief cold — it is to **audit the fix pass against your own
original findings**, one at a time, and say plainly which are actually fixed, which are partially
fixed, and which are not.

**Do not trust the summary below.** It is the fix author's own account of what changed. Verify
every claim against the actual diff and the actual document text.

**Read, in this order, from the repository:**
1. Your own original review output (15 Nov 2026) — if it is not in your context, ask for it to be
   pasted before proceeding; do not reconstruct your 29 findings from memory or from this prompt's
   summary of them, since that summary is necessarily lossy.
2. `docs/MASTER_BRIEF_v2.1.md` — the rewritten brief (whole thing). This supersedes v2.0, which is
   now at `docs/history/MASTER_BRIEF_v2.0.md` for comparison if you want a word-for-word diff.
3. The pull request diff for branch `docs/v2.1-astra-review-fixes` against `main` (PR #22) — this is
   the actual change-set; read the diff, not just the final file, so you can see what the "before"
   text claimed versus what it claims now.
4. `DECISIONS_TO_REVISIT.md` — check the two new cross-reference notes against M-001 and R-009, and
   the new unresolved-conflict note against R-011 (about deleting `services/*`).
5. The two code fixes claimed alongside the brief rewrite, with their tests:
   - `detection_verifier/sigma_subset.py`, `detection_verifier/checker.py`, and
     `tests/test_web_verifier_and_eval.py` / `tests/test_detection_verifier.py` — claimed to fix
     your finding 9 (a detection rule laundering discrimination through an incidental field).
   - `lab/web_workflow/worker.py`, `rental/live_web.py`, `scripts/rental/check_ssh_lab_link.py`,
     and `tests/test_live_web_loop.py` / `tests/test_check_ssh_lab_link.py` — claimed to fix your
     findings 18 (rejected actions not counted against the budget) and 23 (the SSH link rehearsal
     never actually went over SSH).

**Your task — go through your own 29 findings one by one.** For each finding number, cite:
- the exact place in v2.1 (section, task ID, or table row) that is supposed to fix it, or the
  commit/file for the two code fixes;
- a verdict: **FIXED** (the mechanism genuinely closes the gap you found), **PARTIAL** (it helps but
  leaves a real gap — say what's still open), or **NOT FIXED** (the text changed but the underlying
  problem is still there, or wasn't touched at all);
- for anything PARTIAL or NOT FIXED, the concrete residual attack path or defect, the same way your
  original review specified one.

Do the same for every C-1…C-14 row you marked **risky** — check whether the "Why" column's
correction (not just a changed verdict label) actually addresses the specific overclaim you flagged,
and whether the verdict column in v2.1 accurately states your original call plus the correction.

**Also check for regressions the fix pass itself introduced:**
- Does any fix contradict another part of the document (new internal inconsistency)?
- Does any fix introduce a new verifiable cheat path, the same way K1–K23 look for them — in
  particular around the four new trust-zone account boundaries (§4.1), the `event_id` binding in
  §5.5/T2A.6, the per-candidate re-verification rule in §6/T2A.15/T5a.5, and the sealed launcher's
  install/sudoers design in T2A.11?
- Is anything now **over-corrected** — i.e. a fix that is technically unimplementable, circular, or
  that quietly reintroduces an LLM into a gate/verifier/authorisation decision, which is forbidden?
- Did the pilot-track minimal subset added to §11.1 (for your finding 24) actually resolve the
  January-vs-Stage-2A-checklist contradiction, or just relocate it?

**Output format — lead with the scorecard:**
```
SCORECARD: <N> of 29 findings FIXED, <N> PARTIAL, <N> NOT FIXED
C-ROW CORRECTIONS: <N> of <N> risky rows adequately corrected
NEW DEFECTS INTRODUCED BY THE FIX PASS: <N> (list separately, same severity format as before)
```
Then, for every finding 1–29: `[finding N] — <FIXED|PARTIAL|NOT FIXED> — <section/task/file cited> —
<residual problem, if any> — <concrete fix, if still needed>`. Keep each entry tight; do not restate
the full original finding text, a one-clause reminder is enough. Findings that are cleanly FIXED can
be one line. Spend your words on PARTIAL/NOT FIXED and on new defects — that is the valuable output.
End with the same overall verdict scale as before: READY TO BUILD / BUILD WITH FIXES / NOT READY,
and say explicitly whether it differs from a plain re-read of v2.1 in isolation versus this
against-your-own-findings audit (they can legitimately differ: a brief can look locally sound to a
fresh read while still failing to close a specific gap you know to look for).
