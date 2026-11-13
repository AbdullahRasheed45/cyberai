# Execution environments

This project's code runs across three physically and logically separate
machines. Which host a piece of work belongs on is not a style choice — it
is a safety boundary (CLAUDE.md PRIME DIRECTIVE #7, brief §12). This doc
says what each host is for, what may run there, and what must never cross
between them.

## 1. Windows development machine (this machine, today)

- **What it is:** the day-to-day editor/CI-authoring machine. No GPU, no
  CUDA, no Docker assumed available.
- **What runs here:** repository scaffolding, typed schemas and config
  validation (`libs/`), unit tests, lint/format, documentation, CI workflow
  authoring, non-GPU service domain logic (pure functions, no I/O).
- **What does NOT run here:** vLLM serving, Unsloth/TRL fine-tuning, anything
  claiming a measured throughput or training-loss number. A bare-metal pip
  install of `torch` on a non-Linux/non-aarch64 host proves nothing about the
  GB10 path (CLAUDE.md directive #8) — don't try to approximate it here.
- **Evidence kind this host can produce:** `EvidenceKind.LOCAL` only
  (`libs/schemas.EvidenceKind`). Never `HARDWARE`.

## 2. ARM64 GB10 host (rented cloud today; a future owned DGX Spark)

- **What it is:** the aarch64 Grace Blackwell box that serves and trains the
  model. Today this is a **rented, ephemeral** cloud instance (~$0.80/hr);
  see `DECISIONS_TO_REVISIT.md` R-001/R-002/R-003 for what changes once the
  physical unit is owned.
- **What runs here:** `docs/STAGE_0_AND_1_EXACT.md` Part B — vLLM serving
  (FP8, SM121 container), the Unsloth + TRL LoRA smoke test, throughput
  measurement. Only inside the pinned NGC/community containers — never a
  bare-metal pip install of `torch` (silently becomes CPU-only on aarch64).
- **What does NOT run here:** the lab's targets/malware, WireGuard's lab-side
  endpoint, anything holding ownership-verification secrets for a live
  client. Weights and credentials belong here and only here.
- **Evidence kind this host can produce:** `EvidenceKind.HARDWARE` with
  `HostEnvironment.GB10_CLOUD` (or `GB10_OWNED` once purchased) — the only
  results that may be cited as confirming a brief §19 BLOCKER.
- **Ephemeral discipline:** everything worth keeping is in git or scripted
  to re-download (`scripts/download_model.sh`); the instance itself is
  disposable.

## 3. Isolated HP lab laptop (lab machine)

- **What it is:** the physically separate, air-gapped-by-default machine
  that hosts targets (DVWA/Juice Shop/Metasploitable now; Windows/AD/malware
  detonation later). See brief §12 and `docs/ARCHITECTURE.md` §4.10/§4.4.
- **What runs here:** `lab/` target containers, the lab state machine
  (`TARGET_SERVING` XOR `DETONATION`, never both), `lab_gateway`'s lab-side
  runner.
- **What must NEVER be on this machine:** model weights, verifier answer
  keys, or any credential the AI agent could reach. `lab/` code never
  imports Spark-side weight/credential code (CLAUDE.md directive #7,
  `docs/ARCHITECTURE.md` §5 rule 4).
- **Network boundary:** WireGuard, firewalled Spark → lab-sandbox-IP only,
  and torn down whenever the lab is in `DETONATION` state — enforced in
  code, not just policy.
- **Evidence kind this host can produce:** `EvidenceKind.HARDWARE` with
  `HostEnvironment.LAB_LAPTOP`.

## Cross-cutting rules

- A PR's "Hardware evidence" section (see `.github/pull_request_template.md`)
  must say which of these three hosts — or CI, or none — actually produced
  each claim in it. See `libs/schemas.EvidenceRecord` for the typed shape.
- Secrets (`HF_TOKEN`, DSNs, the WireGuard lab IP) live in `.env`
  (git-ignored); `.env.example` holds safe placeholders only. Never put a
  real secret in a `configs/*.yaml` file — those are validated and committed.
- Non-secret policy belongs in `configs/*.yaml`, loaded through
  `libs/common.load_yaml_config` against a model in `libs/schemas.config`,
  never read ad hoc or hardcoded (CLAUDE.md: "config in YAML + env; no magic
  numbers in code").
