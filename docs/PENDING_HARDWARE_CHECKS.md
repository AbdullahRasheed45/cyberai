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
| 7 | ~~Dense fallback (Qwen3-14B) serves end to end~~ | removed: MoE only (R-009) | — |
| 8 | ~~Multi-LoRA on the dense fallback~~ | removed: MoE only (R-009) | — |
| 9 | Multi-LoRA on the FP8 primary (expected unverified / at risk) | only after deliberately flipping `require_lora_fp8_verified: true` *and* doing a real correctness check (not just "it started") | if correct: flip the flag for real and log the change in `DECISIONS_TO_REVISIT.md`; if garbage output (as community reports suggest): leave refused, record the confirmed failure in `PROVENANCE.md` |
| 10 | Unsloth + TRL training path (brief's other Stage 1 blocker) | `docs/STAGE_0_AND_1_EXACT.md` Part B4/B5 | out of scope for this task — tracked separately |
| 11 | WireGuard / lab state machine | out of scope for this task (lab laptop, not GB10) — see `docs/EXECUTION_ENVIRONMENTS.md` | tracked separately |
| 12 | Real benchmark-harness sweep (8K/16K/32K × concurrency) | `uv run python scripts/bench/run_benchmark.py --host-env gb10_cloud --evidence hardware --out-json ... --out-report ...` | `BenchmarkReport.harness_test == false`, `evidence == "hardware"`, points cover every configured bucket/length-pair/concurrency combo that fit `max_model_len` |
| 13 | Inter-chunk vs inter-token granularity confirmed | inspect a real run's `inter_chunk_latencies_s` count vs `actual_completion_tokens` for a single request | if counts differ, update `docs/BENCHMARK_HARNESS.md`'s caveat from "assumed" to "confirmed multi-token chunking" |
| 14 | Recommended operating configuration computed from real data | same command as #12 | `recommended_operating_configuration` is non-null for at least one context bucket; `recommendation_pending_reason` is gone for that bucket |
| 15 | Prefix-cache hit/miss heuristic checked against real telemetry | compare the TTFT heuristic in #12's report against vLLM's `/metrics` cache-hit gauges, if exposed on the running image | note in `PROVENANCE.md` whether `/metrics` exposes a usable signal on this image, so the heuristic-only caveat can be upgraded or confirmed as the only option |

| 16 | Rental lifecycle end to end (the path the trial actually runs) | `RENTAL_START_HERE.md` §7: `track_command.py ... -- uv run python -m rental.orchestrate` | `receipt.json` status `COMPLETED`; releases `confirmed`; `reload_result.json` passed; `workload_result.json` present. Its vLLM launches use the same `configs/serving.yaml` engine flags and attention backend as rows 4–6, so a pass there also exercises #5. |
| 17 | LoRA on the FP8 MoE primary, via the rental lifecycle | phase `start_lora` → `verify_adapter_identity` → workload | adapter served and producing a parseable response is evidence toward #9; it does NOT by itself flip `require_lora_fp8_verified` — that still needs the correctness review in #9 |
| 19 | Docker runtime flags in the provider sandbox | `python3 scripts/rental/docker_runtime_setup.py` | `status: READY`; a GPU mode shows GB10; mounts read+write; loopback port reachable (R-010) |
| 20 | 4-bit QLoRA vs bf16 training throughput | first lifecycle (qlora_4bit) + `TRAIN_PRECISION=bf16` cell | both `train_meta.json` files present; compare `steady_state_tok_s` (R-008) |
| 18 | Calibrate lifecycle thresholds | first completed run of #16 | see `DECISIONS_TO_REVISIT.md` R-007 / issue #16 |

See `DECISIONS_TO_REVISIT.md` R-005 (serving choices) and R-007 (lifecycle thresholds) for the tracked follow-up issues.
