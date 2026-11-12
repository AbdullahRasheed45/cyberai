# Serving benchmark harness

`scripts/bench/run_benchmark.py` measures the **serving endpoint's**
throughput/latency/capacity trade-offs — context length × concurrency ×
batching — against synthetic, seeded, non-sensitive workloads.

**This is NOT the sealed cybersecurity capability benchmark**
(`benchmarks/sealed/`, `docs/ARCHITECTURE.md` §4.8), which scores whether a
model generation is better at security tasks. This harness never touches
that benchmark's scenarios, scoring, or answer keys. It answers a different
question: *how much serving capacity does this endpoint actually have, and
under what configuration?*

## What it measures

- **Sweep axes:** input length, output length, and concurrency, within
  representative 8K/16K/32K context-budget buckets (`configs/benchmark.yaml`
  — a bucket or length pair that doesn't fit the serving config's
  `max_model_len` is **skipped and reported**, never silently clipped).
- **Per-request:** time-to-first-token (TTFT), inter-chunk latency (see
  caveat below), end-to-end latency, errors, timeouts.
- **Per sweep point:** error rate, timeout rate, single-request output
  tok/s (only meaningful at concurrency=1), aggregate output tok/s (the
  batching-sensitive number), latency percentiles (p50/p90/p99), memory
  telemetry before/after.
- **Prefix-cache hit/miss:** a heuristic only — the generic OpenAI-compatible
  endpoint has no definitive per-request hit/miss flag, so this compares
  TTFT on a cold (first) issue of a prompt against sequential repeats of
  the identical prompt.
- **Multi-LoRA adapter switching:** exercised only if
  `configs/benchmark.yaml: lora_adapters_to_exercise` is non-empty and
  `configs/serving.yaml: enable_lora` is true; otherwise explicitly
  reported as skipped, with why — never silently omitted.
- **Memory telemetry:** `/proc/meminfo` (system) + `nvidia-smi` (GPU),
  both best-effort — a run where neither is available still completes, with
  `MemorySnapshot.source == "unavailable"` rather than crashing.

## Caveats (read before trusting a number)

- **Inter-chunk, not strictly inter-token, latency.** vLLM may batch more
  than one token into a single SSE chunk; this harness measures gaps
  between *content-bearing SSE events*, which is inter-token latency only
  if the server streams exactly one token per chunk. `docs/GB10_SERVING.md`
  / `PROVENANCE.md` has not confirmed vLLM's chunking granularity on GB10.
- **Synthetic prompt length is an approximation**, not an exact token
  count: `libs/common/benchmark_domain.synthetic_prompt` sizes text by a
  words-per-token heuristic (no tokenizer download required to run this
  harness). The server's own reported `usage.prompt_tokens` /
  `usage.completion_tokens` are the authoritative counts recorded per
  request — compare the two if precise length control matters.
- **Batching results are never multiplied together.** Two concurrency
  levels are two separate measured points, shown side by side; brief §5.2
  explains why they are not a stacked multiplier (same KV-cache budget,
  spent two different ways).
- **`ignore_eos: true`** is sent on every request (a vLLM OpenAI-server
  extension) so the model generates the full requested output length
  instead of stopping early at EOS — otherwise output-throughput numbers
  would be contaminated by how "talkative" the synthetic prompt happens to
  make the model.

## Harness tests vs real measurements

Every report has `harness_test: bool`. **A `harness_test=true` report is
proof the harness's own accounting/bounding/error-handling works — it is
never a GPU performance result**, regardless of what the numbers inside it
look like, and `scripts/bench/run_benchmark.py` refuses to combine
`--harness-test` with `--evidence hardware`. The rendered Markdown report
puts this in its own banner at the top.

```bash
# Harness self-test against a controlled/mock endpoint (what CI runs):
uv run python scripts/bench/run_benchmark.py \
    --benchmark-config configs/benchmark.harness-test.yaml \
    --host 127.0.0.1 --port <mock-port> --served-model-name qwen3 \
    --host-env ci --evidence mocked --harness-test \
    --out-json /tmp/report.json --out-report /tmp/report.md
```

See `tests/integration/test_run_benchmark_harness.py` for the fake
streaming server this runs against, and what it proves (successful sweep,
server errors captured not crashed on, timeouts enforced, the request
budget never exceeded, the hardware/harness-test combination refused).

## Running a real measurement

Only once an authorised GB10 (or lab) endpoint is actually serving:

```bash
uv run python scripts/bench/run_benchmark.py \
    --host-env gb10_cloud --evidence hardware \
    --out-json evidence/bench/$(date -u +%Y%m%dT%H%M%SZ).json \
    --out-report evidence/bench/$(date -u +%Y%m%dT%H%M%SZ).md
```

(Host/port/served-model-name default to whatever `configs/serving.yaml`
says; override with `--host`/`--port`/`--served-model-name` if needed.)

Bounds (`max_requests_total`, `max_runtime_s`, per-point
`requests_per_point`/`warmup_requests_per_point`) are enforced both when
the sweep plan is built AND while it runs — a point that would blow the
budget mid-run stops the sweep early rather than overrunning it, and the
report says so (`truncated`, `truncation_reason`).

## Recommended operating configuration

Computed (`libs/common/benchmark_domain.recommend_configuration`) **only**
from `evidence=HARDWARE` points with zero errors/timeouts, per context
bucket, ranked by aggregate output tok/s (optionally bounded by
`configs/benchmark.yaml: sla_p99_e2e_latency_s`). On any other run —
including every harness test — `recommended_operating_configuration` is
`None` and `recommendation_pending_reason` says why. **As of 2026-11-12,
no real hardware run has occurred, so this recommendation is pending** —
see `docs/PENDING_HARDWARE_CHECKS.md`.
