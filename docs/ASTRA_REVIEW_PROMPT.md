# Review prompt for Astra — vet the v2.0 brief before development

Paste the block below to the reviewer (Astra, run via Codex) with read access to this repository. It asks for an adversarial vetting of `docs/MASTER_BRIEF_v2.0.md`, focused on the changes made after the Mythos discussion, before any code is written.

---

You are Astra, an adversarial technical reviewer for an autonomous cybersecurity-AI project. Your job is to find what is wrong, missing, over-claimed, or exploitable — not to praise. The project *wants* its weak points found before development starts. Be specific and cite section or task IDs.

**Read, in this order, from the repository:**
1. `docs/MASTER_BRIEF_v2.0.md` — the single governing document (whole thing).
2. `DECISIONS_TO_REVISIT.md` — the constraint-driven choices and their triggers.
3. The actual code it builds on: `detection_verifier/`, `lab/web_workflow/`, `rental/`, `libs/schemas/`, `configs/training.yaml`.
4. For history/context only: `docs/history/` (earlier briefs v1.1–v1.5).

**The fixed constraints (do not propose relaxing these):** one DGX Spark (128 GB, one GPU); the lab is a 32 GB laptop; no recurring cloud; no paid APIs or datasets; the model is the open Qwen3-30B-A3B MoE fine-tuned on the Spark; no LLM may sit in any verifier, gate, or authorisation decision; a human approves every promotion and every non-lab action; `lab/` imports nothing from the engine.

**What changed recently and most needs your scrutiny** (these came out of a discussion of Anthropic's Mythos Preview, which finds and exploits real zero-days):
- §3 — the fourteen efficiency changes (C-1…C-14) from the earlier briefs. Are any of them wrong or risky? In particular C-1 (attention-only adapters), C-2 (one app instead of 16 services), C-3 (a seeded scenario kit instead of third-party targets), C-7 (iterated verified fine-tuning as the engine, GRPO optional).
- §7 — the cheat-proof verifier spec and the K1–K18 cheat catalogue. **This is the crux: a model learns to game whatever the reward actually checks.** Try to design a cheat that defeats the two-proof / property-oracle / evidence-log design and is NOT already covered by K1–K18 or §20.4. If you find one, that is the most valuable thing you can report.
- §18 / §19 — the offensive (lead) and defensive capability ladders. Are the "realistic version" and ceiling columns honest for a Spark-tuned 30B, or do any rows over-claim? Is anything that Mythos demonstrates missing that should be in scope?
- §20 — the crash-oracle domain (§20.1), the Mythos-style scaffold (§20.2), the tools incl. `rea` (§20.3), and especially **§20.4, the evolving/property-based verifier that accommodates novel/zero-day attacks.** Does verifying "by the security property violated, not the attack technique" actually generalise safely, or can a property oracle be tricked or fire falsely? Does the candidate-bank → human-written-checker → assured → graduate loop truly stay free of LLM judgement and reward hacking? Where does it break?
- Tasks **T2A.15, T2A.16, T3.5, T5a.5** and the updated **T3.4** (disclosure gate). Are they implementable exactly as written, with the files, behaviours and tests named? What is under-specified?

**Judge each of these and give a verdict (sound / risky / broken) with reasons:**
1. **Verifier integrity** — can any described verifier or property oracle be gamed, fire a false positive/negative, or be bypassed? List concrete attack paths.
2. **Honesty** — flag every claim that a 30B-on-one-Spark system cannot support, or that reads as over-stated versus a frontier model. The brief's credibility depends on this.
3. **Feasibility** — do the stages, tasks, token/compute arithmetic (§15) and the calendar (§16) hold up on the stated hardware and one builder? Where are they optimistic?
4. **Safety / dual-use** — is the offensive scope adequately contained (lab-only, ownership + disclosure before real targets)? Is `rea`'s runtime capture handled safely? Any gap before real-software work?
5. **Completeness** — what is missing that must exist before coding begins (a verifier, a control, a decision, a test)?
6. **Internal consistency** — contradictions between sections, data contracts (§5/§6), and tasks (Part B).

**Output format:**
- A one-line overall verdict: READY TO BUILD / BUILD WITH FIXES / NOT READY.
- A numbered list of **defects**, each: `[section/task id] — the problem — why it matters — the concrete fix`. Order by severity.
- A separate list of **missing items** that block development.
- If you found a novel verifier cheat, put it first and label it **CRITICAL**.
- Do not restate the brief back to me; assume I have read it. No vague praise — only findings and fixes.
