# Pending hardware checks — GB10 serving

Nothing in `containers/vllm-gb10/` or `scripts/gb10*` has been run against
a real GPU as of 2026-11-11. This was built and validated entirely on a
Windows dev machine (no GPU, no Linux, no `--gpus all`), per the working
rule not to rent paid resources without explicit authorisation. This is the
exact list of what a real GB10 session must still confirm, each one mapped
to a `libs.schemas.EvidenceRecord` this repo's own scripts already know how
to produce — running the check **is** filling in the record, not inventing
a new report format.

Do not cite any row below as confirmed until it has actually been run and
its `EvidenceRecord.evidence` field is `HARDWARE`.

| # | Check | Command | What "pass" looks like |
|---|---|---|---|
| 1 | GB10 host confirmed, arch/driver/memory sane | `bash scripts/gb10_serve.sh preflight-host` | exits 0; no FAIL lines |
| 2 | Official NGC image: GPU visible, CUDA available, correct compute capability | `bash scripts/gb10_serve.sh preflight-container` | `torch_cuda` check passes, reports `compute_capability: "12.1"` |
| 3 | Official NGC image: sm_121 CUTLASS gap present or absent | same as #2, inspect for `NotImplementedError: No compiled cutlass_scaled_mm for compute capability: 121` | if it appears, fall back to `FALLBACK_IMAGE.txt` (see `docs/GB10_SERVING.md`) and record that this gap is confirmed, not just reported by third parties |
| 4 | vLLM serves the FP8 primary model end to end | `scripts/gb10_serve.sh start primary` then `scripts/gb10_serve.sh smoke-test gb10_cloud hardware` | smoke-test's `EvidenceRecord.passed == true`, `evidence == "hardware"` |
| 5 | `TRITON_ATTN` actually used / no attention-backend crash | inspect `scripts/gb10_serve.sh logs` during #4 for backend-selection errors | no FlashInfer "Unsupported architecture" / attention crash in the log |
| 6 | Throughput baseline (single-stream + batched) | `uv run python scripts/measure_throughput.py --host-env gb10_cloud --evidence hardware` | a real `ServingThroughputResult`, replaces the brief's reference numbers with ours |
| 7 | Dense fallback (Qwen3-14B) serves end to end | `scripts/gb10_serve.sh start dense_fallback` then `smoke-test` | same as #4, for the fallback model |
| 8 | Multi-LoRA on the dense fallback (expected to work) | `scripts/gb10_serve.sh render dense_fallback --lora` then start + smoke-test with a real adapter once one exists (Stage 2+) | inference smoke test passes with the adapter attached |
| 9 | Multi-LoRA on the FP8 primary (expected unverified / at risk) | only after deliberately flipping `require_lora_fp8_verified: true` *and* doing a real correctness check (not just "it started") | if correct: flip the flag for real and log the change in `DECISIONS_TO_REVISIT.md`; if garbage output (as community reports suggest): leave refused, record the confirmed failure in `PROVENANCE.md` |
| 10 | Unsloth + TRL training path (brief's other Stage 1 blocker) | `docs/STAGE_0_AND_1_EXACT.md` Part B4/B5 | out of scope for this task — tracked separately |
| 11 | WireGuard / lab state machine | out of scope for this task (lab laptop, not GB10) — see `docs/EXECUTION_ENVIRONMENTS.md` | tracked separately |

See `DECISIONS_TO_REVISIT.md` R-005 for the tracked follow-up issue.
