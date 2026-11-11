# GB10 serving — operating this setup

This is the operating doc for `scripts/gb10_serve.sh` and friends. It
supersedes nothing in `docs/STAGE_0_AND_1_EXACT.md` — that runbook's own
heredoc scripts remain valid if you run them literally — but it is a more
configurable, more checked version of the same Part B2/B3 work, built per
a later task that specifically asked us not to assume the runbook's example
flags remain valid and to verify current compatibility first.

**Read `containers/vllm-gb10/PROVENANCE.md` first.** It records what was
actually verified (with sources and dates) versus what is still an
unreviewed claim or a community forum report. This doc assumes you've read
the caveats there, especially:
- GB10/sm_121 has **no merged upstream vLLM support** (PR #31740 closed,
  unmerged) — both candidate images are workarounds, not an officially
  supported path.
- **Multi-LoRA on the FP8 MoE primary model is unverified** and is refused
  by default (`configs/serving.yaml: require_lora_fp8_verified: false`).
- An unresolved contradiction exists between our own prior guidance ("do
  not set `CUTE_DSL_ARCH=sm_121a`") and the community's current (2026-10)
  recommended path for a newer MoE kernel backend. The default config here
  stays on the conservative side and does **not** set that variable.

## Prerequisites

Run on the GB10 host itself (rented cloud instance or an owned DGX Spark —
see `docs/EXECUTION_ENVIRONMENTS.md`), not on the Windows dev machine:
- Docker with NVIDIA Container Toolkit (`--gpus all` must work).
- `.env` populated from `.env.example` (`HF_TOKEN` if you hit rate limits;
  both configured models are public as of 2026-11-11, so it is not
  required for access).
- This repo cloned, `uv sync` run.

## Commands

```bash
# 1. Host-level checks — architecture, GPU visibility, memory, cache dir, image pin.
bash scripts/gb10_serve.sh preflight-host

# 2. In-container checks — torch/CUDA visibility, compute capability,
#    captures the INSTALLED image's actual `vllm serve --help` (self-documents
#    the real CLI surface instead of trusting our assumptions).
bash scripts/gb10_serve.sh preflight-container

# 3. See the exact command that would run, without running it:
bash scripts/gb10_serve.sh render primary
bash scripts/gb10_serve.sh render dense_fallback --lora

# 4. Start (detached). First model load is slow (minutes) — don't mistake
#    "not answering yet" for broken; use smoke-test once, then watch logs.
bash scripts/gb10_serve.sh start primary

# 5. Status / logs / stop
bash scripts/gb10_serve.sh status
bash scripts/gb10_serve.sh logs
bash scripts/gb10_serve.sh stop

# 6. Functional smoke test (liveness -> readiness -> real inference):
bash scripts/gb10_serve.sh smoke-test gb10_cloud hardware

# 7. Throughput measurement (typed, labelled evidence — see
#    libs/schemas.EvidenceRecord):
uv run python scripts/measure_throughput.py --host-env gb10_cloud --evidence hardware

# 8. If anything looks wrong: dump a full evidence bundle
bash scripts/gb10_serve.sh diagnose
```

`start`/`render` take `primary` (Qwen3-30B-A3B FP8) or `dense_fallback`
(Qwen3-14B dense) and an optional `--lora`. `--lora` against `primary` is
**refused** unless `configs/serving.yaml`'s `require_lora_fp8_verified` is
flipped to `true` — and that should only happen after a real hardware
correctness check, not merely "the server didn't crash" (see PROVENANCE.md
for why: a same-family quantized-MoE + LoRA combination produced garbage
output in community testing).

## If the official NGC image fails preflight

`containers/vllm-gb10/IMAGE.txt` pins the primary attempt
(`nvcr.io/nvidia/vllm:26.10-py3`, official NVIDIA NGC). If
`preflight-container` or an actual serve attempt hits a
`NotImplementedError: No compiled cutlass_scaled_mm for compute capability:
121`-shaped error, that confirms the sm_121 CUTLASS gap documented in
PROVENANCE.md applies to this image too. Fall back to the image pinned in
`containers/vllm-gb10/FALLBACK_IMAGE.txt` (`eugr/spark-vllm-docker`'s
image) — **re-resolve its digest first**, since it is a floating `:latest`
tag (`docker manifest inspect --verbose eugr/spark-vllm:latest`), and record
the new digest + the date in PROVENANCE.md before relying on it.

## What "pending hardware checks" means here

See `docs/PENDING_HARDWARE_CHECKS.md` for the exact list. In short: nothing
in this setup has been run against a real GPU as of 2026-11-11. Every
script above has been validated on the Windows dev machine (syntax, pure
Python unit tests, a mocked HTTP integration test) — see
`DECISIONS_TO_REVISIT.md` R-004/R-005.
