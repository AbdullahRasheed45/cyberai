# Autonomous self-improving cybersecurity product — master brief v2.2

Version 2.2 · 16 November 2026 · specification correction, not implementation evidence.

This is the current consolidated product/build specification. v2.0 remains in
`docs/history/MASTER_BRIEF_v2.0.md`; v2.1 remains at `docs/MASTER_BRIEF_v2.1.md`.
Neither is silently edited. This version replaces contradictory task contracts,
not just their explanatory notes. `REVIEW_FIX_LEDGER_2026-11-16.md` maps the 29
original findings and six follow-up defects to requirements and actual evidence.

Status vocabulary: **implemented** means code exists; **tested offline** means
the named checks executed locally; **hardware-unverified** means no such claim
may be made; **specified** means future work, not a working capability;
**OPEN** means owner approval/input is required before the affected work.

## 0. Authority, scope and order

The owner's latest instructions prevail. Product only. Offensive-first learning
in owned, authorised labs, then defensive correction and independent verification.
Both Loop A (strategy/tool use) and actual Loop B (model-weight updates) remain.
All six domains remain: web, Linux, Windows, AD, cloud and mobile, easy to hard,
activated within measured memory/time budgets. Qwen3-30B-A3B MoE is the default
family; preserve reasoning and the planned Instruct/Thinking comparison.

The targets remain **15 January 2027** for a working fine-tuned model and
**30 June 2027** for the six-domain product. Neither delivery is proved feasible
by this document. Do not substitute two domains for six, or a smoke run for a
verified learning result, without explicit owner approval. Do not claim an
alternative 2028 schedule is a measured necessity. Estimate remaining engineering
effort and critical paths after the trial. No second builder, extra lab machine,
recurring cloud, paid API or paid dataset is assumed.

Stage order applies. The January pilot exception in §11 is **OPEN D-5** and is
the only proposed exception; it does not declare Stage 2A complete. Unapproved
C-2/R-011 architecture changes remain proposals, not authority to delete services.
Follow `GIT_WORKFLOW.md`: focused branch/PR, normal configured human authorship,
no attribution trailers, owner merges. Never rent, buy, merge or deploy production
without the owner's explicit authorization for that action.

## 1. Product and invariants

Agents attempt tasks; independent deterministic code verifies results; only
eligible verified trajectories train; train/save/fresh-reload/deploy/evaluate;
a human approves every promotion. Repeated improvement is a hypothesis to test,
not a property guaranteed by filtered fine-tuning. No LLM decides authorization,
verdicts, assurance admission, dataset eligibility, gates or promotion.

Sealed content is inaccessible to learning. Lab code imports only standard library
and `lab`, never engine/rental/sealed. No model, engine credentials or sealed
material persists on the target machine. Treat all target output as untrusted.
Everything has pinned identity, provenance and real token/time/memory accounting.
Missing evidence fails closed. A crash is not automatically an exploit or a win.

## 2. Hardware, models and pins

One Spark, one GPU, 128 GB shared memory; one 32 GB lab laptop. Benchmark serving
and training serially, with resource release checked between them. Keep actual
runtime flags and model/image identities in the existing validated YAML/freeze.
Do not install host torch on aarch64; use the pinned container path and probe CUDA.

Current serving identity: `Qwen/Qwen3-30B-A3B-Instruct-2507-FP8`
@ `5a5a776300a41aaa681dd7ff0106608ef2bc90db`.
Training base: `unsloth/Qwen3-30B-A3B-Instruct-2507`
@ `41d47883cd854ab6d119fb7cba6e9ed3511886e2`; verify lineage file hashes.
Serving image: `nvcr.io/nvidia/vllm@sha256:ecd885a6fa671552021eb2bef16773110ebfa4eb5e24e4a2831bf0f4808ddfea`.
Training image: `docker.io/unsloth/unsloth@sha256:c3a52373be71e968310d06a99fee54b0006f34dd847ead1bd63709a0d41a3220`.
These are repository pins, not evidence they work on this GPU. 4-bit QLoRA,
attention-only LoRA and frozen router remain defaults; bf16/all-target comparisons
are measured cells. Thinking requires its own reviewed commit/tokenizer/weight
lineage pins before execution. No automatic model substitution.

## 3. Efficiency decisions and their actual limits

| ID | Direction | Required qualification / acceptance |
|---|---|---|
| C-1 | Attention-only default | 13,369,344 versus 843,841,536 adapter parameters at the reviewed dimensions; expert token exposure does not prove inability to learn. Compare quality and complete runtime, not speed alone. |
| C-2 | Proposed single application | OPEN R-011: retain capability boundaries in §4; no deletion/migration until owner resolves it. Network services are not automatically secure either. |
| C-3 | Seeded scenario kit | Structural variation is not semantic novelty; ground truth needs independent admission. Measure behavior/implementation diversity and a separate unseen-class track. |
| C-4 | Generic bounded tools | Future kit only; implement every protocol/session bound in §5 before use. Current worker remains five-action protocol 1. |
| C-5 | Report wins/day from first admitted loop | Reporting does not authorize training or waive dependencies. |
| C-6 | 100-example pilot experiment | Not sufficient-data proof. Require feasible allocation across at least seven families, bootstrap rule §11, and owner pilot approval. |
| C-7 | Iterated verified/rejection-sampled SFT | Main weight-learning procedure; not equivalent to on-policy RL or guaranteed to improve. Optional GRPO remains gated on a complete algorithm and measured benefit. |
| C-8 | Small quality-diversity table | Measure retained behavioral variety and gain over a single configuration. Routing is a resource trade-off, not an impossibility. |
| C-9 | Restricted SSH; defer detonation link controls | Every earlier untrusted/native/runtime-capture task requires its own admitted sandbox before execution. No deferred safety dependency. |
| C-10 | Synthetic telemetry first | D1 validates only its synthetic schema; D5 needs separate real-tool semantics and corpora. |
| C-11 | Target recovery plus operational backup | Different requirements: T3.2 tests target restoration; T3.6 tests registry/store/dataset disaster recovery. |
| C-12 | Instruct working default; compare Thinking | No assumed 3× token factor or reasoning-equivalence claim. Report success and complete cost separately at matched budgets; preserve reasoning canaries. |
| C-13 | Evaluate exact served artifact | Identity includes base, tokenizer/template, quantization, adapter, flags and software. Matched parent and anchor baselines required. |
| C-14 | Probes replace unsupported setup assumptions | Keep any image-specific patches proved necessary; no invented library versions or GPU results. |

## 4. Trust boundaries and execution

### 4.1 Accounts and immutable installations

Spark: `engine` learns/serves and owns staging; `sealed` owns exam runtime/data;
`registry` owns published artifacts and serving pointer; root/admin owns executable
installations and lifecycle broker. Lab: trusted controller and restricted target
UIDs; `labsealed` is inaccessible to normal `lab`. Distinct PIDs alone are not
isolation. No engine Docker-group/root access that bypasses these boundaries.
Validate effective group membership, mounts, sockets, ptrace/proc access and sudo
rules on the real unit; account diagrams are not assurance evidence.

T2A.11 installs a root-owned `/opt/cyberai-sealed/bin/evaluate` launcher and its
complete dependency tree/interpreter, including frozen agent, labclient and verifier
copies. No live imports, configs or executable paths from the engine checkout.
Sudoers permits only `engine ALL=(sealed) NOPASSWD: /opt/cyberai-sealed/bin/evaluate`
with **no command arguments**, `env_reset`, no `SETENV`, and a root-controlled PATH.
The launcher immediately changes to its protected directory, sanitizes environment,
closes inherited descriptors, and execs its pinned interpreter with `-I` and an
absolute installed entry point. Reject all unrecognized environment/input fields.
Read one bounded JSON request on stdin containing a generation ID, fixed set ID
and experiment ID. Resolve IDs under trusted manifests; never accept arbitrary
paths, Python modules, shell text, model URLs or server flags.

Install the registry publisher with the same launcher discipline. Human approval
comes from a root/registry-controlled approval inbox, never an engine-written
name. Approval records bind action, generation manifest hash, scope, expiry and
one-use nonce. Verify ownership/permissions and consume atomically. Training or
evaluation completion never grants promotion authority.

### 4.2 Registry ingestion and GPU lifecycle

Publisher copies bounded regular-file content from staging into **new** registry-owned
inodes. Reject symlinks, hardlinks, devices, path traversal and unsafe adapter
formats; resolve using directory descriptors/no-follow semantics. Verify the copied
bytes against the approved manifest; source changes cannot change published bytes.
Source file ownership, open handles and chmod cannot grant engine write access to
destination files. Never rename an engine-owned tree into the trusted registry.
Publish an immutable manifest and use temp/fsync/rename plus directory fsync for
SERVING. Record a verified audit event before reporting success.

One root-owned lifecycle broker holds an exclusive OS lock across resource use,
not just startup. Every serve/train/sealed-eval/promote path uses it. Engine can
request only validated operations, not run arbitrary privileged containers. Record
operation ID/PID/artifact; after crash reconcile actual processes/GPU allocation
before reclaiming a stale operation. Do not unlink a live lock. Container-existence
checks are diagnostics, never exclusion. Registry proposals can be registered as
candidates before approval; only published serving-pointer changes need approval.

### 4.3 Sealed inference and imports

Stop engine inference before a sealed window. Start a sealed-owned inference
server in a network namespace reachable only by sealed's runner/proxy, or behind
a permission-controlled Unix socket. An undisclosed loopback port is insufficient.
No engine-readable logs, temp files, metrics, administrative endpoints or inherited
descriptors. Test connection attempts and server mutation as engine. Pin and verify
the exact candidate bytes before loading. The agent solving exam tasks may use an
LLM client; verifier/gate/authz modules may not. Frozen sealed runner dependencies
are not a live engine import. Never install exam families in this public checkout.

### 4.4 Target isolation and evidence

Controller launches targets through a trusted sandbox launcher as a distinct UID
with bounded CPU/memory/PIDs/files, isolated filesystem/network and no controller
mounts, credentials or sockets. Do not fork a secret-holding parent and assume
closures are secret. A target necessarily contains its planted application data;
RCE may read that data but may not alter observer truth or evidence. Native/RCE
families require externally observed violation proofs, not an assertion of HTTP
exfiltration inferred from a target-authored IPC message.

HTTP requests pass through the controller's observer; actual bounded response
bytes delivered to the tool are hashed/logged outside the target. Use bounded
byte messages; never unpickle target messages (`Connection.recv` prohibited).
Externally retain a session manifest plus authenticated final trace count/digest
before verification. Reject recomputed chains, deleted suffixes, substituted sessions
and incomplete commitments. Hiding filenames is not a protection mechanism.

## 5. Versioned data contracts

T2A.1 implements strict, extra-forbid schema version 2 models and valid/invalid
fixtures. Evidence with unknown kind/version/field, duplicate keys, absent ground truth or missing
commitment is UNVERIFIABLE, not a loss silently eligible for training.

### 5.1 Scenario and brief

ScenarioSpec: `domain`, `family`, `family_version`, `family_code_sha256`,
`config_sha256`, `level`, `seed`, `case` (vulnerable/patched_control/pre_satisfied),
`split` (train/dev/sealed). Seed fixes structure, not secrets. TaskBrief: protocol,
session ID, public objective, starting identity, tool schemas and explicit budgets.
Admission certificate binds family/code/config/checker/assurance hashes. Never
schedule on a mutable version integer alone. Sealed specs never enter engine storage.

### 5.2 Actions and observations

Kit Action: `thought` (<=400 characters), `tool`, strict tool-specific `args`.
Web request: method allow-list; path-only <=512 bytes, no scheme/host/control
characters/backslash, percent-decode/recheck, no redirect following; query <=1024
bytes; <=8 headers, each <=512 bytes, total <=2048; only Cookie/Authorization/
Content-Type; body <=4096 bytes. Finish: `claim` <=256 UTF-8 bytes and `event_id`.
The model's event reference is untrusted and validated against committed evidence.

Kit input line <=8192 bytes **including newline**, bounded before JSON decoding;
nesting <=4, <=64 objects, duplicate keys refused. Read/partial-line deadline 10s;
request deadline 10s; session wall time 300s; total prompt+completion tokens <=32768
by default. Configured smaller task budgets win. Every generation/retry/denial
spends the appropriate token/action budget. Each model call consumes one attempted
action; malformed-output corrective retry consumes another. On exhaustion emit
terminal evidence and close: no unlimited grace finish loop. EOF is terminal.

Kit response reads at most 4097 body bytes before truncating to 4096, bounded
headers and a 16384-byte observation line, with a read deadline. Trusted evidence
is separate: content-addressed bounded replay blobs hold necessary exact request/
response bytes. Never first allocate an unbounded body and then truncate it.

Current rental worker is **protocol 1**, not the generic kit: <=8192-byte input,
16 attempts, 10s idle/partial-line deadline, 300s session deadline; terminal records
on EOF/timeout/oversize/budget; five actions only. Its client bounds response lines
to 1 MiB to preserve explicitly labelled long activity traces. These different
budgets are versioned contracts, not proof of generic-tool implementation.

### 5.3 Evidence common envelope

Evidence is a discriminated union on `objective_kind`: capture/tamper/crash.
Common fields: `schema_version`, `attempt_id`, `session_id`, ScenarioSpec,
controller/target/code/config/policy/admission hashes, start/end monotonic durations
and UTC correlation timestamps, before/after health and pre-satisfied state,
action/token counts, failure category, trace manifest (count/final digest/commitment),
and replay blob manifest. Missing required evidence returns UNVERIFIABLE.

Every event has session/event/sequence/request IDs; actual authenticated principal
and credential-context hash; resource ID and ownership/entitlement decision under
a versioned independent ground-truth policy; pre/post state hashes/versions;
request blob/hash; delivered-response blob/hash/status/byte count; target instance
identity; causal parent event IDs; and integrity-chain predecessor. Preserve exact
query/body/headers in protected replay storage, with secret-aware access controls.
Do not infer identity from a different cookie parser than the application uses:
compare actual app authentication context with the independent entitlement model;
ambiguity/disagreement quarantines, never awards a win.

### 5.4 Objective-specific evidence and verdicts

Capture: trusted expected-secret commitment, claim hash, claimed event ID and
controller-observed canary delivery bound to that principal/resource/session/event.
Tamper: trusted **expected nonce hash**, claim hash and before/after protected-field
hashes, actual state transition and entitlement; require all three nonce hashes
equal and a forbidden transition after start. A model-selected arbitrary value fails.
Crash: target/harness/compiler/instrumentation hashes/options, input blob/hash,
supervisor wait status, termination origin (target/harness/supervisor), timeout/OOM
flags, independently corroborated fault site/class, replay and patched-control
results. Runtime report text or a signal alone cannot establish this record.

Verdict: ID, attempt/evidence hashes, checker version/hash, outcome VERIFIED/FAILED/
UNVERIFIABLE, offensive/defensive sub-outcomes, primary/shadow event IDs, reasons,
verification time and superseded verdict ID. `judge(evidence, attempt_id)` requires
matching identities. Ordinary failed attempts have no training eligibility.

### 5.5 Trajectory, dataset and generation

Training JSONL contains complete messages and token spans with role/source IDs;
metadata includes attempt/evidence/verdict hashes, family/behavior/implementation
identity, split, generation and replay source. Tool outputs remain user/tool roles,
never assistant targets. Dataset manifest lists exact authoritative verdict events,
hashes, allocation, exclusions and dedup decisions.

Generation manifest binds parent, frozen anchor, base repo/commit/file hashes,
tokenizer/template hash, precision/target set, adapter hashes, dataset hash,
trainer/container/software identities and measured runtime/token/memory history.
Evaluation identity additionally binds serving quantization/flags/agent settings,
checker/canary/set manifests. Human approval is a separate trusted record, not a
mutable `approved_by` field asserted by engine.

## 6. Append-only storage and graduation

T2A.8 implements immutable completed attempts, append-only steps and append-only
verdict, candidate, checker-admission, graduation, revocation and audit events.
Dataset/item manifests reference verdict IDs and evidence hashes. Candidate status
and current verdict are rebuildable projections, not mutable authority. Publish
explicit SQL migrations/views and transaction/concurrency tests in that task.

Authoritative verdict = latest valid event for the attempt under the current
admitted checker, with explicit supersession/revocation precedence. An old positive
may never reappear because the latest event was filtered out. A revocation taints
dependent datasets/generations/anchors recursively; suspend automatic use, report,
and require human selection of an unaffected generation. Never rewrite history.

Checker admission is one transaction; candidate adjudication is another. A cluster
is a review index only. Reverify **every candidate's original immutable evidence**
with the new admitted checker. Store a new candidate-specific verdict and event,
bound to evidence/checker hashes and replay result. Do not trust a sticky Boolean
flag. Mixed clusters must graduate only individually verified members.

Exact replay restores the original equivalent state and secret/nonce commitments
inside protected evidence custody. If required replay cannot be reconstructed,
return UNVERIFIABLE. Fresh blinded instances test checker generalization separately:
fresh secrets require a new executed trajectory and its own attempt/verdict. Never
copy a failed original trajectory into an invented successful attempt-equivalent row.

No-signal hypotheses have an explicit human-invoked intake (`reason`, original
attempt ID, evidence manifest) even if no oracle fired. Statuses escrowed/
inconclusive/dismissed/graduated are event-derived; none grants reward by itself.
Advisory LLM triage may reorder/annotate but cannot discard intake, suppress checks,
change verdicts or influence eligibility. Preserve all bounded attempts for audit.

## 7. Verifier assurance and cheat controls

### 7.1 Offensive and defensive decisions

Primary checks expected claim/nonce and pre/post conditions. Shadow independently
checks the committed forbidden event for the **claimed event ID**, not the first
matching event in the session. Both validate binding to session/principal/resource/
policy/state/delivery and must identify the same causal event. Separate logic and
mutation controls are required; shared evidence does not make checks independent
by assertion. Claim correct without event, background-only events, credential/parser
disagreement and missing delivery are quarantined. Pre-satisfied never trains.

Defensive REMEDIATED requires clean equivalent-state replay, fresh credentials and
identifiers, multiple attack variants, original exploit regression and a legitimate
business-use matrix checking real results and protected state, not HTTP 200/health
alone. Include special-case patch, dummy-200, disable-all and hidden-data-loss controls.

### 7.2 Required cheat suite

Retain K1–K18: guessing, claim-only, pre-satisfied, legitimate-route leakage,
vandalism, evidence edits, target escape, text injection, fake lab messages, parsing,
memorized replay, exam leakage/exhaustion, disabled-feature patch, incidental rules,
broken generators, shared-checker bugs and container breakout. K19 adds mixed-cluster
graduation; K20 malicious module/cwd/environment injection; K21 sealed inference
connection/log/admin access; K22 target RCE/observer IPC escape; K23 forged sanitizer
output combined with exit 0, ordinary nonzero, assertion/abort and unrelated signal.
All are required controls, not a claim that their future implementations exist.

Additional controls: whole-chain rewrite/truncation/session substitution; same-event
identity switching/background traffic/repeated successful reads; wrong nonce; unsafe
staging links/races/open handles; approval forgery/replay/expiry; concurrent lifecycle
starts/crash recovery; fresh-instance trajectory substitution; duplicate/oversize/
partial lines and invalid floods. Each maps to a named failing test before its fix.

### 7.3 Family and checker admission

Every family/declared level ships public-tool reference exploit, benign business
walk and patched/pre-satisfied controls. Test at least 50 development seeds plus
the shared cheats. Freeze independently designed negatives/metamorphic cases and a blinded fresh
validation manifest before candidate-specific checker fitting; the owner reviews
the evidence. This is a test-design separation, not a second-builder dependency.
Checker-development examples alone cannot certify correctness.
Revisions run old and new controls. Human checker review is not replaced by an LLM.

Bootstrap uses an admin-only assurance runner, absent from forced-command options;
it drives the same core/protocol logic without scheduling/training privileges.
After assurance, atomically install a certificate bound to code/config/checker/
suite hashes under controller-protected ownership. Worker verifies those hashes
on load and refuses changed content even with unchanged version number.

Existing detector 0.4.0 uses finite, bounded incidental field-value counterfactuals
from the current development corpus and rule literals, including missing/unseen
values and joint assignments; it preserves Boolean semantics. Budget/deadline
exhaustion fails evaluation closed. The legacy metric name
`fp_burden_incidental_blind` now reports this counterfactual burden. It does not
prove generalization to every string, template or production telemetry distribution.
Candidate detection targets additionally require independent development variants
that preserve behavior while changing context and invert behavior while retaining
context. Acceptance data must never select training targets.

## 8. Stage 1A — existing GB10 rental preparation

Implemented offline; **not executed on GB10**. Follow `OWNER_GUIDE_GB10_TRIAL.md`,
`RENTAL_START_HERE.md` and `ENVERGE_SETUP.md`, subject to their actual probes.

| Task | Required operation/evidence |
|---|---|
| T1A.1 | Owner-approved booking only; clone reviewed trial commit, provider probe, frozen dependencies. |
| T1A.2 | Pull pinned images; runtime setup; source measured Docker environment in each shell. |
| T1A.3 | Probe image/CUDA/bf16/library versions and save the measured freeze; CPU torch stops execution. |
| T1A.4 | Materialize verified model checkpoint; configure stop/export/storage/workload/pilot and run preparation checker. |
| T1A.5 | Track lifecycle and live status; 30-step 2048-token attention/QLoRA cell, 5 warm-up steps. |
| T1A.6 | Prioritized one-variable cells: bf16, all-target adapters, 4096, 8192, then 4096/batch2 only with measured headroom. Long offensive/defensive trajectories are development-only. |
| T1A.7 | Measure actual processed tokens, steady-state step time, decode latency separately from aggregate throughput, prefill, failures, load/warm-up, memory and complete lifecycle. |
| T1A.8 | Summarize/export artifacts and adapter; read back/check hashes off-instance before owner stops billing. |
| T1A.9 | Owner records BUY/DO NOT BUY/RE-TEST against predeclared workload criteria. |
| T1A.10 | Commit actual pins/results and revise defaults only from evidence; no GPU-passed labels beforehand. |
| T1A.11 | Save/train/fresh-process reload and FP8+adapter deployment; compare same prompts before/after. If unsupported, record failure and test approved merged bf16/requantized paths. |

First-hour stop conditions: GPU unavailable, storage/cache mounts unusable, pinned
images/model cannot run, evidence export not available. Download/load overhead
counts against 24 hours. No promised training speed or download completion time.

## 9. Stage 1B — two-machine foundation

Entry: actual owned/rented authorized access and trial evidence, not assumed purchase.
T1B.1 reproduces the trial on the owned unit if purchased. T1B.2 installs the lab
inside an isolated VM/disposable environment on the 32 GB laptop, with no host
drive/credential mounts and no destructive Windows wipe. Record RAM/CPU/disk budget
and host reserve. T1B.3 configures dedicated restricted SSH keys, verified host key,
deny egress/firewall and a separate deployment authority. No Docker socket to targets.

Current workload forced command must start the **existing** protocol-1 worker:

```text
command="cd /home/lab/cyberai && exec /usr/bin/python3 -m lab.web_workflow.worker --from-ssh",restrict ssh-ed25519 <DEDICATED_PUBLIC_KEY>
```

Use `restrict` plus server forwarding restrictions and verify on the installed
OpenSSH version. Worker accepts only empty original command or the exact existing
client command `python3 -m lab.web_workflow.worker`; refuses arbitrary commands.
Do not install the unbuilt kit worker as this trial's forced command.

T1B.4 authorization is deterministic and **lab-only** for the current product path.
READ_ONLY permits only explicit admitted read operations; SANDBOX allows admitted
session tools; PRODUCTION and non-lab targets deny until T3.4 is implemented/admitted.
A caller-provided name, scope object or disclosure YAML row never overrides denial.
T1B.5 rehearses the exact deployed worker via the shared SSH argv:

```bash
LAB_SSH_HOST=cyberai-lab LAB_EXPECTED_HOSTNAME='REPLACE_WITH_VERIFIED_LAB_HOSTNAME' uv run python scripts/rental/check_ssh_lab_link.py --out artifacts/link_rehearsal.jsonl
```

Pinned host-key authentication, configured expected hostname, scenario/protocol,
worker commit and actual remote transcript must match. Run deployed forced-command
negative tests (shell/forwarding/alternate worker), controller/target isolation and
network-egress tests separately. A link rehearsal is not a sandbox-isolation pass.

## 10. Stage 2A — specified; do not claim implemented

| Task | Files/behavior and mandatory acceptance |
|---|---|
| T2A.1 | Strict schema-2 models/fixtures in libs/schemas/scenario.py; packages/import-boundary tests. No deletion of services while R-011 OPEN. |
| T2A.2 | lab/kit/core.py and trusted launcher implement §4.4/§5: separated target/observer, byte-only IPC, external trace commitment, exact replay custody; RCE/edit/truncation/substitution controls. |
| T2A.3 | lab/kit/tools.py/worker.py implement every §5 bound, admission certificate verification, automatic terminal evidence, URI/redirect escape suite; new protocol distinct from current worker. |
| T2A.4 | Ten web families: idor_read, idor_write, missing_function_auth, sqli_filter, path_traversal, mass_assignment, predictable_token, unsigned_token, internal_fetch, business_logic. Level1 direct, level2 discovery, level3 two-step chain, level4 decoys/background with bounded resources; level5 separate sealed variants. Each has independent ownership/business-state truth and all controls. |
| T2A.5 | engine/labclient: explicit local-test/SSH transports, session identity, bounded reads/deadlines, process cleanup and crash/timeout tests; deployed forced-command integration separate. |
| T2A.6 | engine/verifier/checks.py/verdict.py: judge(evidence, attempt_id), exact envelope validation, claimed-event causal proofs, trusted nonce and business-matrix retest; complete truth tables and mutation tests. |
| T2A.7 | Protected assurance bootstrap/certificates §7.3; new unadmitted family can be assured but not scheduled; modified code with unchanged version is refused. |
| T2A.8 | engine/store migrations, event projections and lineage §6; revocation/latest-verdict/transaction tests; forbid sealed inserts. |
| T2A.9 | engine/agents: bound every completion/retry/denial/action/token/wall time, real API usage; no function signature mismatch; scripted complete drives all positive/negative controls. |
| T2A.10 | engine/report: attempts, unique behavioral wins, success, full prompt/completion/action/runtime/occupancy cost, refusal heuristic labelled heuristic; no wins-only efficiency ranking. |
| T2A.11 | Trusted sealed installation, dependency freeze, ledger and private labsealed path §4; malicious module/cwd/env/socket/server-mutation tests as engine. Pilot: 3 families/80 tasks, descriptive only. Full gate: >=10 independently justified family groups/200 tasks; keep immutable task/group IDs private. |
| T2A.12 | Dataset allocation §11.2; authoritative eligible verdicts, behavioral/implementation dedup, no held-out selection; infeasible input terminates usefully. |
| T2A.13 | Candidate registration and secure publisher §4.2; immutable manifests, one-use human approval, lock and crash recovery; race/link/open-handle/forged-approval tests. |
| T2A.14 | Compare Instruct/Thinking on a frozen **development** manifest, same budgets/cases/order, separate success and all-cost metrics; reasoning canaries. No sealed feedback selects variant/training targets. Owner selects; atomically freeze serving/training/tokenizer/template lineage, invalidate incompatible baselines and capture a new matched anchor. |
| T2A.15 | Pure property signals consume explicit trusted evidence/ground-truth arguments; automatic signalled-candidate escrow plus human no-signal intake; per-candidate adjudication/replay/revocation §6. No candidate rewards. |
| T2A.16 | Advisory ranking/best-of-N/triage, bounded total cost for all N; cannot suppress intake, alter verdicts or eligibility. No LLM filter before acceptance. |

Full exit: all tasks/admission controls, ten families at declared levels, real model
attempts through stored verdicts, protected sealed baseline/registry/report and
identity-bound variant choice. Offline mocks do not satisfy deployed-machine checks.

## 11. Pilot, dataset allocation and Stage 2B

### 11.1 Pilot dependency exception — OPEN D-5

If explicitly approved, the pilot may precede full Stage 2A and the later volume
decision. Required first: Stage1B safety; T2A.1–3; >=7 T2A.4 families admitted at
levels1–2; T2A.5–10; T2A.11 pilot sealed runner/isolation; **T2A.12**; T2A.13 minimum
secure candidate registration/publisher/rollback/lifecycle; fixed Instruct identity
and matched baseline; T2A.15 escrow; T2B.1 mask/reload checks. T2A.14 variant comparison,
T2A.16 scaffold and remaining levels may wait; D-2 explicitly freezes Instruct for
this pilot until the approved comparison. No manual promotion bypass. Without D-5
approval, normal full-stage prerequisites apply. A pilot result is preliminary and
does not authorize automatic promotion or certify recursive learning improvement.

### 11.2 Dataset algorithm — proposed thresholds require D-7

100 examples, >=7 families, minimum5 each, per-family cap15%, replay25%.
First dataset has **zero old replay**, explicitly recorded bootstrap=true; never
fabricate old data. Later rounds require replay from earlier verified, non-revoked
datasets. If replay unavailable, fail; any temporary exception needs preapproval.

For a requested integer size N: family maximum=floor(.15*N), old count=floor(.25*N)
(except bootstrap), new=N-old. Eligible inventory must satisfy minima, maxima and
new/old availability simultaneously. Solve deterministic integer allocation over
(family, source), with a fixed seeded ordering, bounded finite dynamic programming
and explicit work cap; no repeated drop-until-empty loop. Search N downward from
max_examples to100 only; if none feasible, fail with missing inventory/constraints.
Sample within allocation deterministically by behavior/implementation coverage,
then frozen cost tie-breaks. Do not count route renaming as a new behavior. Tests:
five-family refusal, feasible seven-family100 allocation, seven-family insufficient
inventory refusal, bootstrap, rounding, replay shortage, deterministic selection,
revoked/latest-verdict exclusion and bounded termination. Dev variants select
targets; sealed/challenge evaluation never does.

### 11.3 Training and gate tasks

T2B.1 (`engine/train/sft.py`, specified): tokenize complete Qwen chat templates with
role boundaries, generate assistant-only label spans, and mask **all** system/user/
tool/padding tokens to -100. Do not rely on two substring delimiters. Test every
token for system messages between assistant turns, tool calls, quoted delimiter
text, padding, truncation through each role and missing assistant content. Split
development by behavior/implementation before training; log actual nonpadding
processed tokens and supervised tokens separately. Holdout never selects acceptance.
Keep finite weights/router/dtype/identity guards and save/fresh-reload checks.

T2B.2 pilot: eligible dataset -> stop serving under broker -> train -> save ->
fresh-process reload -> register candidate -> deploy exact artifact -> descriptive
sealed comparison and canaries. Record complete loading/warm-up/preprocess/save/
reload/deploy/eval occupancy as well as steady-state step/token measurements.

T2B.3 gate: predeclare task manifest, implementation-family dependence groups,
estimand (equal-weight group mean paired success gain), >=10 justified independent
groups, practical minimum gain (proposed5 percentage points), >=3 improving groups,
family regression <=10 points, canary drop <=2 points, detection FP nonincrease.
Primary inference is one-sided exact grouped sign-flip randomization under its declared
exchangeability/independence assumptions, <=20 groups; missing justification or a
larger design needs an approved protocol before use. Seeds are not independent
units by assertion. Task McNemar is diagnostic only. With <=12 sealed scoring
invocations per version, compare candidate to both parent and frozen anchor at
alpha=.05/(12*2) per comparison; ledger every invocation **before** execution,
including failures. No unbudgeted peeks, family significance fishing or post-hoc
threshold changes. Pilot80/3-family results are descriptive, not this full gate.

T2B.4 runs protected evaluation; baseline reuse requires exact set/task, base,
tokenizer/template, adapter, serving, agent, checker and protocol identities.
Any variant/config change needs a new matched baseline. Sealed runner retains
paired task/group vectors privately and exports an integrity-protected aggregate
report bound to candidate/parent/anchor hashes. No scenario prompts/answers reach
engine. Gate reports; trusted human approval publishes. No model votes.

T2B.5 curriculum: per-family easy-to-hard windows and proposed thresholds in YAML;
only admitted versions/levels; current zero-attempt families get explicit bootstrap
sampling; 10% bounded free exploration, control cases and earlier-domain replay.
Resource scheduler reserves host memory and refuses an unfittable lab topology.
T2B.6 day/night/eval/morning all use the single lifecycle broker and crash recovery.
T2B.7 subsequent generations compare to promoted parent **and** fixed anchor;
revocation/rollback propagates through lineage before any continued learning.

## 12. Later stages — specified, not implemented or guaranteed

Phase2 waits for the Stage2B proof, not simply a completed smoke adapter. An
unsuccessful pilot remains a result, not proof. Existing parking policy M-001
continues until D-3 is approved; no automatic year-long suspension amendment.

T3.1 detection uses independent development counterfactuals and honest synthetic
schema scope, never blanket overfit immunity. T3.2 remediation/recovery implements
the legitimate business matrix and exact restored-state checks. T3.3 Linux ships
per-family sandbox profiles: exact RO/RW mounts, UID namespaces, permitted internal
privilege transition and external supervisor observation. A sudo exercise may use
namespaced internal root; never host root. If a needed transition is incompatible
with the outer hardening, refuse that family until a safe profile is admitted.
Reading a flag hash alone is not evidence of the privileged read.

T3.4 outside actions remain disabled until its complete gate exists: owner-written
scope binds exact target/assets/resolved addresses, actions/hashes, authorization
evidence, expiry, one-use nonce and disclosure policy; human approves every action.
DNS/HTTP challenges are supporting control evidence, not authorization to test.
Validate redirects/rebinding at connection time and use a dedicated restricted
transport. Offline inspection of an owned software copy is distinct from contacting
a maintainer's live service. Disclosure and scope-breach playbooks are prerequisites.

T3.5 native targets: pin compiler/options/binary/harness and supervisor. Use ASan/
UBSan with explicit tested halt/abort settings; account for runtime/memory overhead.
Classify target defect/harness defect/assertion/ordinary exit/timeout/OOM/report/
exploitability separately. **No generic signal-to-bug-class mapping.** Implement a
named sanitizer report adapter using pinned runtime report hooks (ASan reporting
callbacks/query interface) to a bounded dedicated channel, not target stderr.
This channel is still target-process-originated and cannot by itself authenticate
a defect. Generated-family verification additionally requires the independently
specified fault site/property, clean replay, matching supervisor evidence and
patched controls. Unsupported UBSan/runtime classification stays UNVERIFIABLE.
For novel real-software crashes, escrow pending human-written admitted checker;
never award memory-corruption/control-flow/novelty credit from a report alone.
Control-flow influence needs its own observed-control acceptance test. Test forged
diagnostics plus ordinary nonzero/abort/unrelated signals, harness faults and OOM.

**T3.6 operational recovery:** consistent store/WAL snapshot, dataset/adapter/registry
manifests, integrity checks, encrypted off-device copy to owner-controlled durable
storage, retention and clean restore drill. Lost/corrupt disks must restore lineage,
revocations, approval history and serving pointer without inventing sealed data.
Sealed backup has separate keys/access and never enters the engine backup. Owner
selects durable destination before claiming recovery ready; no recurring cloud assumed.

T5a.1 measures table diversity/gain; T5a.2 optional GRPO is disabled until a written
algorithm fixes behavior-policy hash, sampling groups, stored per-token logprobs,
reference/KL policy, clipping/importance correction, reward normalization and zero-
variance handling (skip update), off-policy staleness rejection and matched-SFT
baseline. T5a.3 cooperation/caching/routing need measured gains, not assumed memory
impossibility. T5a.4 preserves full logging/anchors. T5a.5 separately admits human-
written checkers and individually adjudicates original candidates per §6; mixed
clusters, original/fresh replay and revocation tests mandatory. Optional DPO pairs
share byte/token-identical conditioning prefix; pair alternative continuations
from a common decision point, not full sessions with different tool observations.
Drop unpairable trajectories. Mask tool/system content; gate resulting artifacts.

Stage5b adds Windows/AD/cloud/mobile one admitted easy-to-hard slice at a time.
Starting **proposed**, unmeasured 32GB AD profile: host reserve8GB, DC4GB, member4GB,
client4GB, controller2GB, 10GB unallocated headroom; no other domain VMs concurrently.
Measure committed memory, reset/runtime and paging; refuse overload. Reduce lab
complexity/parallelism, not isolation. No 64GB purchase or second builder assumed.
Cloud emulation evidence excludes untested provider-specific semantics. Android
emulator/owned apps first; iOS unsupported until a free owned compliant environment
exists. No paid API/dataset/provider dependency is implied.

T5b.6 detonation requires independently tested serve-targets XOR detonate link
state machine, restored snapshots and no external route. `rea` runtime capture may
not wait for that task's controls: before any capture install a digest-pinned
disposable sandbox with no controller/host mounts, credentials, Docker socket or
egress, RO root plus bounded scratch, resource/time limits, reviewed tool allow-list
and pinned dependencies. Use a free backend such as Ghidra; disable unused MCP tools.
Capture artifacts are sensitive, access-controlled, encrypted on export and purged
by retention policy. Never run untrusted binaries on controller or engine.

## 13. Standing acceptance and evidence discipline

Run appropriate tests plus repository-wide Ruff/format/pytest checks before PR
completion. Future task tests named above are requirements, not existing passes.
Every hardware/deployed-security check has unit/host identity, commit/pin manifest,
UTC timestamp, command, result and exported artifact hash. Mock/CPU evidence is
explicitly separate. Do not mark Round18 evaluation defects fixed by assurance
language; only a concrete regression and actual result closes an implementation bug.

## 14. Configuration

Existing serving/training/lab/curriculum YAML remains the runtime source. Future
gate/dataset/engine policies have strict schemas and immutable run snapshots.
Every proposed number in this document requires D-7 before first scored use.
Changing a threshold after observing acceptance results requires a new protocol/set,
not quietly editing the freeze. Resource/protocol limits are explicit defaults,
never hidden magic numbers scattered across callers.

## 15. Measurement and compute accounting

Use monotonic clocks for elapsed durations; UTC only for correlation. Report prompt,
completion, processed nonpadding and supervised tokens separately. Single-request
latency/TTFT/decode speed and aggregate throughput are different measurements.
Include failures and every best-of-N attempt. Record peak/resident memory, KV cache,
OOM, loading, warm-up, reset/tool/verification wait and serialization overhead.

attempts/day = observed completed attempts / observed serving-window seconds *
available serving seconds, **only for the measured workload/concurrency mix**.
Eligible wins/day additionally measures verification/dedup/allocation survival.
Round occupancy = startup/load/quantization + preprocessing + measured training
steps + save + fresh reload + deployment + sealed evaluation + release/export.
Steady-state step time is not round occupancy. Use measured distributions and
workload assumptions; no hardcoded hour-per-pilot, 80–240 wins/day or 3× reasoning
factor. One GPU serializes phases. No invented download bandwidth estimate.

## 16. Calendar and milestone acceptance

Before rental: offline fixes, reference trajectories, pins/scripts, export rehearsal,
owner workload/stop criteria. During authorized24h: first-hour access/storage/GPU
probe; baseline serving/workflow; baseline train-save-reload-deploy; prioritized
one-variable cells; end-to-end evaluation and export, with stop/export reserve.
Actual start/stop times and model-download duration are measured, not promised.

January working-model acceptance: pinned trained adapter, actual reload/deployment,
complete workflow and matched baseline with honest preliminary outcome; statistical
learning improvement is a separate full gate. June remains six-domain owner target;
write effort/dependency ranges for each domain after initial admitted families and
the trial, identify critical-path slack/risks and seek an explicit scope/date decision
if incompatible. Do not assume day-for-day schedule slips or a second builder.

## 17. Open owner decisions

| ID | Decision before affected action |
|---|---|
| D-1 | Purchase criteria: representative workloads, minimum acceptable latency/throughput/round occupancy/memory, adapter-serving requirement; no rental authorization inferred. |
| D-2 | Instruct remains pinned pending measured development comparison; choosing Thinking requires owner-approved full identity/lineage and baseline replacement. |
| D-3 | Keep M-001 until owner decides parking versus controlled research amendment. |
| D-4 | Approve behavior/implementation diversity definition; seed count alone is insufficient. |
| D-5 | Approve/reject §11 pilot prerequisite exception; no implicit approval of changed January/June deliverables. |
| D-6 | Resolve measured scope/date feasibility within one-builder/32GB constraints; no extra hardware/person assumed. |
| D-7 | Approve dataset/bootstrap/gate/repeated-look/curriculum thresholds before measurement. |
| D-8 | Resolve C-2 against R-011 before deleting services or building that engine layout. |
| D-9 | Confirm actual access, lab identity, durable evidence/backup destination and retention. |

## 18. Offensive capability ladder (all kit extensions specified, not measured)

O1 web authorization/injection/logic: existing narrow fixed-action IDOR reference;
generic kit unbuilt. O2 chaining: demonstrated final objective plus each causal
step, not narrative. O3 crash discovery: independently corroborated fault, not mere
signal. O4 PoC/exploitability: executable reachability/control proof under a distinct
oracle; no frontier-parity claim. O5 N-day instances: unseen implementations and
known-class checks. O6 reverse engineering: source/navigation/build/debug/reproduce
tooling and independent issue triage, before any capability claim. O7 crypto-use:
narrow forged-token/distinguisher property check; no general cryptanalysis claim.
O8 recon: coverage against independently validated ground truth, not generated
route count as real-world coverage. Scope is authorized lab only until T3.4.
Reasoning quality and each capability ceiling are measured hypotheses, not inferred
from parameter count or resemblance to a frontier-model scaffold.

## 19. Defensive ladder

D1 synthetic detection rules with finite assurance; D2 dedup/triage/severity only
against declared lab labels, not general real-world severity; D3 patching preserves
business functionality; D4 target restoration and separate operational backup;
D5 real monitoring-tool interpretation needs separately validated schemas/corpora.
Offensive-first experience feeds these capabilities; no comparative superiority claim.

## 20. Evolving properties, scaffold and novel findings

Property oracles generalize only over what the instrumentation actually observes
and the assured ground truth models. Authz, integrity, delivery and native fault
properties need their own negative controls. Differential disagreement may be an
implementation difference, not a vulnerability. Unsupported observations escrow.
Candidate bank -> human checker -> independent assurance -> individual original-
evidence adjudication -> eligible verified trajectory; fresh-instance validation
is a separate experiment. No cluster-wide promotion or LLM admission decisions.
Model ranking/reflection/best-of-N are agent techniques, not proof of equivalent
frontier methodology or capability. Complete source/build/debug/reproduce tooling
and independent human issue triage before real-software findings are claimed.

## 21. References and actual next action

Read `REVIEW_FIX_LEDGER_2026-11-16.md`, `HANDOFF_2026-11-16.md` and the trial runbooks.
The owner/next coding agent should verify the focused PRs and offline evidence,
resolve the open decisions, then execute only explicitly authorized hardware checks.
This document closes specification contradictions; it does not instantiate the
future kit, sealed installation, registry, graduation engine or a six-domain product.
