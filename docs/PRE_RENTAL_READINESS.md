# Pre-rental readiness — 12 November 2026

**NOT READY for the requested training/product purchase trial.** Reviewed the actual scaffold/foundation/serving branches, product alignment, handoff and proposed v1.3. The historical v1.2 critique brief and Round-18 archive/code are absent. No GPU result exists in this checkout. The handoff's historical test counts are not current execution evidence.

## Concrete blockers

1. Obtain/import the actual Round-18 implementation and evidence. No `rental/`, training/save/fresh-reload scripts, acceptance controller, web export or complete workflow is present. Do not reconstruct them from narrative summaries and call the defects fixed.
2. Runbook B4 is illustrative, not an implemented, pinned training stack. Training-image digest, runtime dependencies, exact model snapshot, explicit LoRA attachment and fresh-process adapter effect/deployment must be wired and checked offline before billing. The handoff lists candidate identities; those are not locally verified runtime assets.
3. No executable assured offensive web task, defensive counterpart, independent retest or separate target-lab enforcement exists. Arrange the lab and prove resets, telemetry, tunnel restrictions and target ownership before billing.
4. Representative training-token accounting, CUDA memory sampling, steady-state step timing, training timeout/cleanup and export receipts are not implemented. Serving measurement now reports actual tokens, per-request wall time, aggregate throughput, warm-up, failures and total runtime, but explicitly labels loading/device memory and streaming TTFT/decode as unmeasured. Do not call this a complete fitness benchmark.
5. Owner inputs needed: acceptable training-round duration and representative dataset size/context mix, verified external storage/export destination and capacity, separate lab access, and provider billing/teardown semantics. No numerical purchase threshold has been invented.

## Offline preparation and exclusions

Before billing: obtain missing sources; resolve evaluator defects or exclude learning claims; freeze train/dev separately from a fresh restricted acceptance set; acceptance must never select training targets. All six Round-18 issues in the handoff remain OPEN and excluded from purchase/learning evidence. Define the January web objective, prepare verified task trajectories and negative controls, pin assets, cache where permitted, test command forwarding with fake executables, and verify export/restore checksums to the selected destination.

Representative records must preserve scenario/template ID, initial privileges/state, bounded offensive action and observation, independent success evidence, defensive action, retest and service health, telemetry completeness, verifier/model versions and split. Such records are not currently available as verified training data. Do not synthesize successful outcomes to fill the benchmark.

Training matrix, once the missing runner is restored: prioritize sequence 2048/batch 1, 4096/batch 1, 8192/batch 1; then 4096/batch 2 only with measured headroom. Use 5 warm-up and 25 measured optimizer steps as a provisional measurement budget, recording actual non-padding tokens, microbatch/accumulation, completed optimizer steps, synchronized CUDA timing, peak allocated/reserved and host memory. Stop on OOM; preserve failure logs; no blind retry. These are proposed workloads, not executable or measured results.

## Available commands

From repo root, on development machine:

```bash
uv sync --frozen
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
uv run python scripts/gb10/render_serve_args.py --variant primary --format json
uv run python scripts/gb10/render_serve_args.py --variant dense_fallback --format json
```

Only AFTER explicit rental authorisation, on GB10 Linux with uv/Docker/NVIDIA runtime installed:

```bash
mkdir -p evidence/gb10
set -o pipefail
timeout 120 bash scripts/gb10_serve.sh preflight-host 2>&1 | tee evidence/gb10/host.log
timeout 1800 bash scripts/gb10_serve.sh preflight-container 2>&1 | tee evidence/gb10/container.log
timeout 120 bash scripts/gb10_serve.sh start primary
# After loading, with logs retained separately:
timeout 90 bash scripts/gb10_serve.sh smoke-test gb10_cloud hardware primary
timeout 1800 uv run python scripts/measure_throughput.py --host-env gb10_cloud --evidence hardware --batch-size 4 --max-tokens 128 --warmup-requests 2 --out evidence/gb10/serving.json
docker logs cyberai-vllm-gb10 > evidence/gb10/server.log 2>&1
bash scripts/gb10_serve.sh stop
```

The start command detaches: its timeout DOES NOT bound server lifetime or billing. Set a provider deadline independently and stop/remove the container explicitly. Stopping Docker does not terminate the rental. The serving image and both model revisions are pinned; their runtime compatibility is UNEXECUTED. The FP8 primary's LoRA combination remains refused by default pending correctness evidence. Training and complete-workflow commands cannot honestly be supplied until the absent runner is restored.

## Prioritized 24-hour schedule (conditional; do not book yet)

| Hours | Work and stop condition |
|---|---|
| 0–2 | Hardware/architecture/driver/storage checks; pull frozen assets; capture identities and loading overhead. Wrong host/incompatible image: stop, export and end rental. |
| 2–5 | Baseline serve; warm-up separately; context/concurrency measurements; capture actual token counts and device/host memory. Bound debugging to this window. |
| 5–11 | Stop serving; verify memory released; representative training matrix and save. This phase is blocked by missing runner/data. |
| 11–15 | Fresh-process reload, adapter state/effect checks, serving deployment of the actual trained MoE adapter. Incompatibility is a failed purchase requirement, not a successful smoke. |
| 15–19 | Complete offensive → independent outcome → defensive action → retest workflow on separate lab; any evaluator disagreement quarantines the record. |
| 19–21 | One bounded rerun of a diagnosed failure or sustained measurement; never consume export reserve. |
| 21–24 | Export adapter/configs/data hashes/logs/failures, verify destination receipts and restore; stop workloads and terminate rental through provider; confirm billing stopped. |

## Purchase decision

Require real GB10 serving, representative train/save/fresh-reload and actual adapter deployment, bounded end-to-end lab execution, sufficient measured memory/storage headroom, and verified evidence export. Compare measured useful tokens/second and total round time including load/warm-up/eval/export against the owner's accepted workload/cadence. Successful infrastructure is not evidence of held-out learning gain or six-domain mastery. Any missing/failed required result means no positive purchase recommendation. No purchase or further rental is authorised by this report.

Offline evidence: 27 tests passed on Windows outside sandbox localhost restrictions, including two regression tests first observed failing for token-count fabrication. No CUDA, Docker networking or real container invocation was executed here. Bash lifecycle verification remains required; Python mocks do not certify it.
