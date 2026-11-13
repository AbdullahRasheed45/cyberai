# Rental measurements and tracking

Current instrumentation; no actual GB10 measurements have been executed.

Validation: a full offline run passed 234 tests with 2 optional skips. Subsequent
viewer loss-display/export changes passed 16 focused checks, and the final live
API test passed 3 checks. JavaScript syntax, Python lint/format and compilation
were checked. HTTP/API behavior is exercised; no real GB10 dashboard readings or
automated browser-rendering claim is made.

## Live dashboard and assistant access

Run the read-only dashboard from the checkout on the Spark, using the selected
environment's Python:

```bash
python3 -m rental.live_status --root artifacts --runs runs --port 8765
```

It binds **127.0.0.1 only**. From your laptop, use a second SSH connection with
the provider's actual username, hostname and key options:

```bash
ssh -N -L 8765:127.0.0.1:8765 user@INSTANCE.ssh.enverge.dev
```

Open http://127.0.0.1:8765 on the laptop. If the provider relay does not permit
port forwarding, inspect the same live files over the working SSH shell instead;
do not expose the dashboard publicly to bypass the relay.

The browser refreshes every two seconds and shows:
- Current command state, elapsed time, exit/failure status and sample age.
- Host available RAM/swap, disk headroom and supported GPU memory/utilization,
  temperature, power and clock readings.
- Training step progress, actual tokens, tokens/sec and seconds/step chart.
- Trainer-reported loss, learning rate and other emitted training-log metrics,
  labelled with their actual logged step rather than a guessed current value.
- Recent inference request input/output token counts, latency and request rate.
- Deterministic low-RAM, missing-telemetry, stale-sample and failure signals.

Claude/Codex can use the read-only JSON feed from a shell on the Spark:

```bash
curl --fail http://127.0.0.1:8765/api/state
tail -n 30 artifacts/tracked_train.log
tail -n 5 runs/YOUR_RUN_ID/step_measurements.jsonl
```

This requires that the assistant has authorised access to that SSH session or
you provide its output. Creating the tracker does not automatically connect an
assistant or keep it monitoring after a conversation ends. There is no remote
mutation/control API. The JSON feed also includes the bounded console-log tail
for each tracked command whose log stays under the artifact root.

Start tracked commands in another terminal using the wrapper below. It publishes
atomic state snapshots while running and appends full sample history to
`.samples.jsonl`. The snapshot keeps the last 120 samples; the dashboard keeps
recent request/step windows. Raw history stays in files. Inference request files
are written as requests finish under `<tracker_name>_requests/`. Exact token usage
is authoritative only when the server reports it; chunk counts are never called
tokens. Hardware samples update approximately once a second plus query overhead.

For on-the-spot tuning: capture the baseline, inspect logs and measurements,
change one setting (context, concurrency, batch or accumulation), use a fresh
run ID and compare the same workload. Record the reason and result in the run
notes. A signal suggests where to investigate; it is not automatic proof of a
bandwidth/compute bottleneck. Do not tune against sealed acceptance scenarios.
This preparation does not authorise purchases, deployment or paid session launch.

The live viewer exposes operational data without authentication on loopback;
keep it there and use SSH. Never put credentials in arguments, logs or snapshots.

| Measurement | Recorded evidence |
|---|---|
| Input/output tokens | inference per-request prompt/completion counts from server usage; no requested-max substitution |
| Reasoning tokens | retained when reported; otherwise unknown; visible decode speed withheld when reasoning cannot be separated |
| Time to first visible content | streamed single-request TTFT; not internal reasoning-start time |
| Decode/output speed | streamed decode estimate and end-to-end request rate; aggregate successful output tokens divided by batch wall time separately |
| Context and concurrency | cold/primed request matrix; actual prompt usage; per-request results/errors |
| Model loading/startup | command logs, phase timestamps and trainer load_runtime_s; preserve serving stdout manually or via tracker |
| Training tokens | actual non-padding and supervised tokens, microbatches, consumed sequence histogram; repeated batches counted as processed, not unique data |
| Training speed | synchronized optimizer-step durations; warm-up excluded steady-state time and actual tokens/sec |
| Training memory | allocated/reserved CUDA peaks; per-completed-step allocated/reserved readings |
| Training failures | completed-step JSONL persists before later failures; command logs preserve exceptions/OOMs |
| Download setup | download_result.json records snapshot bytes and download/cache/hash elapsed time, not invented network speed |
| Host and GPU samples | command tracker: host available RAM/swap, free disk, GPU memory/utilization/temperature/power/clocks when nvidia-smi exposes them |
| Provenance | model revisions, runtime versions, data hash, run ID, configuration and environment inventory |
| Agent workflow | actions, actual API usage, runtime, verified outcomes and failure categories |
| Export | manifest hashes, missing evidence and destination readback receipt |

## Track an entire command on either provider path

The standard-library tracker runs with the selected Python environment. Use a new
output filename per command; it refuses to overwrite prior evidence. Example for
the admitted Docker path after setup:

```bash
python3 scripts/rental/track_command.py --out artifacts/tracked_lifecycle.json --timeout 21600 -- uv run python -m rental.orchestrate
```

Provider existing-environment training (only after ENVERGE_SETUP.md admission):

```bash
python3 scripts/rental/track_command.py --out artifacts/tracked_train.json --timeout 21600 -- python3 scripts/smoke_train.py
python3 scripts/rental/track_command.py --out artifacts/tracked_reload.json --timeout 3600 -- python3 scripts/smoke_reload.py
```

Run reload only when training succeeded. Track download similarly:

```bash
python3 scripts/rental/track_command.py --out artifacts/tracked_download.json --timeout 10800 -- python3 scripts/rental/materialise_checkpoint.py
```

Each creates live `.json` telemetry, `.samples.jsonl` history and `.log` combined stdout/stderr. For live progress,
use another terminal: `tail -f artifacts/tracked_train.log`. Set unbuffered Python
output (`PYTHONUNBUFFERED=1`) if you need immediate Python log visibility.
Tracker records UTC timestamps and monotonic elapsed duration, exit code, timeout,
selected non-secret configuration and periodic samples. It does not capture the
full environment. Do not put tokens/passwords in command arguments or print them.

The wrapper's logs/JSON finish after the wrapped Docker lifecycle exports, so
copy them separately with all artifacts after it completes. They are not silently
claimed to be inside that earlier bundle. Save provider inventory, selected freeze,
extra training-matrix outputs and dataset hash as well.

## Limits and pre-rental gates

- Direct DRAM bandwidth (GB/s), kernel-level prefill, GPU routing/expert balance,
  and every allocator transient are not covered by these counters. Timing curves
  expose bandwidth-sensitive behavior but are not direct bandwidth measurements.
- Metrics are sampled, not continuous extrema. Unsupported NVIDIA fields or absent
  tools are reported unavailable. On unified memory, include host RAM/swap evidence.
- Windows host RAM via /proc is unavailable; run the tracker on Linux Spark for it.
- Wrapper sampling slightly perturbs timing; use the same sampling setup when
  comparing cells and preserve synchronized trainer step measurements separately.
- A tracker timeout does not terminate detached Docker containers or provider
  billing. Inspect/stop the trial's containers and delete the provider instance
  after confirmed export. Windows process-tree termination is not guaranteed.
- A host/kernel crash can interrupt the final JSON. Console logs and completed
  training-step JSONL are partial evidence, not a completed run.

Before billing: freeze the checkout/data profiles, choose acceptable workload
cadence, prepare SSH public key/account/repository access and export destination.
Actual provider access, custom GPU Docker versus compatible existing stack, storage
and driver compatibility still require inspecting Enverge's allocated machine.
No tracker can remove that uncertainty before access exists.
