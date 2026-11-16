# Owner guide: what the rental will establish

Current: 16 November 2026. `MASTER_BRIEF_v2.3.md` governs the product.
Use `RENTAL_START_HERE.md` for exact commands. No GPU run is claimed here.

## The purpose

Rent one actual GB10/DGX Spark for an explicitly authorized, bounded trial before
buying hardware. Measure model loading, first-token latency, decode speed,
aggregate throughput, shared memory, representative training and the complete
train -> save -> fresh-process reload -> adapter deployment -> workflow path.
A successful training command is not proof that security capability improved.

The core concept is unchanged: offensive-first authorized lab experience,
independent deterministic verification, defensive correction/retest, provenance,
Loop A strategy/fact improvement and Loop B actual model-weight improvement,
sealed evaluation and human-approved promotion. Six domains remain the product
target. Population/cooperation follow the first web learning proof.

## What is actually ready offline

The repository has a narrow resettable web authorization lab, fixed allowed
agent actions, verifier controls, a controller-applied defensive patch/retest,
reference trajectory export, serving/training preparation and live tracking.
The reference suite covers success, failure, pre-satisfied, patched and noisy
long-context cases. It does not demonstrate the model discovering a vulnerability
or writing a patch. Long benign activity is context load, not attack-chain diversity.

Recent fixes address model-wait versus partial-input timing, matching remote-worker
checks, custom training-config forwarding, failure/action accounting, base-versus-
adapter workflow records, concurrent-run protection, interruption cleanup and the
tracker's deadline/export reserve. See `WORKFLOW_RECONCILIATION_2026-11-16.md`.

The generic kit, protected sealed evaluator, secure registry/promotion engine,
production dataset allocator and repeated learning loop are still unbuilt. These
are later-stage requirements, not hidden passes or reasons to redesign the trial.

## The model and machines

Qwen3-30B-A3B MoE remains the family. The current pinned Instruct-2507 base serves
as FP8; training loads its lineage-matched base using 4-bit QLoRA and attention-only
adapters by default. bf16 and all-target adapters are controlled comparisons.
The reasoning requirement and Instruct/Thinking comparison remain; switching
variants requires complete pins, a matched baseline and owner approval.

Weights and adapters stay on the Spark, never the lab laptop. The separate 32 GB
Windows laptop hosts the lab inside an isolated disposable VM, with no host
folders, credentials or Docker socket exposed. SSH connects to the restricted
controller account inside that environment. SSH alone does not isolate Windows.
No host wipe, malware execution or arbitrary target execution is authorized.

Provider details are hypotheses to check against the allocated instance:
`ENVERGE_SETUP.md` covers GPU Docker and an already-compatible native environment.
Do not improvise an ARM64 Torch installation. A container sandbox is not evidence
that the future sealed-account security controls can be deployed there.

## Before paying

1. Freeze the reviewed checkout and development data; run the offline checks and
   reference commands in the start guide. Older branches omit recent fixes.
2. Set up the isolated lab and verify its SSH host key, expected hostname,
   forced-command restrictions and egress/controller boundaries. Local subprocess
   tests do not establish those machine properties.
3. Choose durable export storage and rehearse copy plus independent hash readback.
   An export folder on the rented filesystem is staging, not durable storage.
4. Write the workload criteria: context/concurrency, acceptable latency, training
   tokens/round and maximum full-round duration, memory headroom and required
   adapter-serving behavior. These values are still an owner decision (D-1).
5. Confirm repository access, provider stop/billing procedure and available storage.
   Pre-stage images/weights only where possible before billing. Compatibility
   requiring the allocated GPU cannot honestly be pre-approved offline.

The representative web trial requires the lab. A detection-only hardware diagnostic
can measure speed without it, but cannot establish offensive-workflow readiness.
The current long reference is only one workflow shape; broader representativeness
must be decided from the intended workload, not asserted from its length.

## During the authorized 24 hours

- Hours 0–2: provider inventory, storage/export, pinned-image probes and downloads;
  stop early on incompatibility.
- Hours 2–5: baseline serving and web workflow, single-request versus aggregate rates.
- Hours 5–11: first 2048/b1/30-step train-save-reload path; compare bf16 and all-target
  only one at a time, then 4096/8192 and 4096/b2 if measured headroom permits.
- Hours 11–19: actual adapter serving/workflow, control cases and complete cost.
- Hours 19–21: one diagnosed rerun if useful; preserve failures.
- Hours 21–24: export everything, independent readback, container cleanup and owner
  termination through the provider. Confirm billing stopped.

The tracker reserves three hours plus cleanup grace before RENTAL_STOP_UTC. It
cannot stop provider billing. Direct commands outside it do not inherit that cap.
Use fresh run IDs, source the measured Docker environment in every terminal and
never run raw serving/training concurrently with a locked lifecycle.

## What to read during and after the trial

The loopback dashboard (`python -m rental.live_status`) shows phases, logs, host
RAM/swap, supported GPU counters, steps/tokens/loss and request failures. Access it
through an authorized SSH tunnel; do not expose it publicly. An assistant needs
actual authorized session access to inspect it; no automatic remote monitoring is
established by creating a dashboard.

Read `receipt.json`, `orchestration.json`, `inference_measurements.json`,
`train_meta.json`, `reload_result.json`, base and adapter `workload_result.json`,
console logs and `export_result.json`. The summary script shows both web outcomes
and their token/action/runtime cost. Missing data remains missing.

Tokens/sec is not a direct DRAM-bandwidth measurement. CPU mocks are not GB10
results. A failed model workflow is a result to preserve, not a hardware failure
by definition. A matched development improvement is not a sealed learning gain.

## Versioning and next action

The trial must use a reviewed full commit from the current stacked feature PRs,
not minimal main or the older stage-1 branch. No merge is required to clone that
commit. Follow the current handoff for the stack order. Earlier briefs and evidence
remain preserved. D-1 through D-9 retain their explicit unresolved status.

The fixes preserve the core concept and make its execution/evidence more reliable.
They do not turn the future platform into completed code or authorize rental.
