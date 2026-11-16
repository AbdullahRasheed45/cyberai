# ARCHITECTURE.md — Internal Code Structure (src/, modules, classes)

**Purpose:** This specifies the *internal* software architecture — the `src/` layout inside each service, every module, every key class with its responsibility, main method signatures, and dependencies. Claude Code builds to this spec so every service has the same clean shape. This is the skeleton; per-stage runbooks fill in the implementations.

**Chosen style:** **layered — `api / domain / infra`** per service. Full class + key-method + dependency detail.

**Reading order:** §1 principles → §2 shared libs → §3 the service template → §4 per-service breakdowns → §5 dependency rules → §6 class index.

---

## 1. Architectural principles (apply to every service)

- **Three layers per service:**
  - `api/` — transport: FastAPI routes, request/response handling. Thin. No business logic.
  - `domain/` — the core: pure logic classes, no I/O, no framework imports. Unit-testable in isolation.
  - `infra/` — adapters to the outside world: DB, HTTP clients, file I/O, message queues, container/process control.
  - `models.py` — pydantic DTOs for this service (import shared types from `libs/schemas`).
  - `config.py` — typed config load for this service.
  - `__main__.py` — entrypoint (`python -m services.<name>`).
- **Dependency direction (strict):** `api → domain → (ports)`; `infra` implements ports; nothing in `domain` imports `infra` or `api`. Domain depends only on `libs/schemas`, `libs/common`, and abstract ports it defines.
- **Ports & adapters where it matters:** domain defines an abstract interface (a "port", e.g. `TrajectoryRepo`), infra provides the concrete adapter (`PostgresTrajectoryRepo`). This keeps domain testable with fakes.
- **No LLM in domain logic of verifier/authz/gates.** Those domains are deterministic.
- **Everything typed.** Pydantic for DTOs, `Protocol`/`ABC` for ports, full type hints.

---

## 2. Shared libraries (`libs/`)

### `libs/schemas/` (already written in Stage 0)
The frozen cross-service DTOs: `Trajectory`, `TrajectoryStep`, `Provenance`, `Verdict`, `Outcome`, `DatasetVersion`, `TrainingRun`, `EvalResult`, `AuthzRequest`, `AuthzDecision`, `GenerationRecord`. These are the lingua franca; services import them, never redefine them.

### `libs/common/` (already written in Stage 0)
- `get_logger(service)` — structured logging bound to the six log groups.
- `new_id(prefix)`, `now()` — id/time helpers.
- `provenance.py` — `stamp(obj, **fields) -> Provenance` helper.
- `LOG_GROUPS` — the six logging categories.

### `libs/clients/` (typed clients for inter-service calls)
One small client class per service that others call. Each wraps `httpx` and returns `libs/schemas` types.
- `class VerifierClient:` `verify(trajectory: Trajectory) -> Verdict`
- `class AuthzClient:` `authorize(req: AuthzRequest) -> AuthzDecision`
- `class LabGatewayClient:` `run_payload(target, payload) -> LabResult`; `target_state() -> LabState`
- `class RegistryClient:` `register(run: TrainingRun)`, `get_generation(id) -> GenerationRecord`, `rollback(to_id)`
- `class SealedBenchClient:` `evaluate(adapter_id) -> EvalResult`  *(submit-and-score only; cannot read scenarios)*
- `class ServingClient:` `chat(messages, adapter_id, max_tokens) -> str`  *(wraps the vLLM OpenAI endpoint)*

---

## 3. The service template (every service follows this)

```
services/<name>/
├── __init__.py
├── __main__.py            # entrypoint: builds infra adapters, injects into domain, starts api
├── config.py              # typed config (reads configs/*.yaml + env)
├── models.py              # service-local DTOs (+ re-export libs/schemas types used)
├── api/
│   ├── __init__.py
│   └── routes.py          # FastAPI router; calls domain services; no logic
├── domain/
│   ├── __init__.py
│   ├── ports.py           # abstract interfaces (Protocol/ABC) the domain needs
│   └── <core modules>.py  # the actual logic classes
└── infra/
    ├── __init__.py
    └── <adapters>.py      # concrete implementations of ports (db, clients, io)
tests/unit/test_<name>_*.py
tests/integration/test_<name>_*.py
```

**Wiring (dependency injection) in `__main__.py`:** construct infra adapters → pass them into domain classes (which accept ports in their `__init__`) → mount the api router → run. This is how domain stays pure and testable.

---

## 4. Per-service internal structure

> Build order follows the stages. Phase-1 services are fully specified; Phase-2 services give the class skeleton to build to when reached.

### 4.1 `verifier_service` (Stage 2 — BUILD FIRST)

```
services/verifier_service/
├── api/routes.py
├── domain/
│   ├── ports.py
│   ├── base.py
│   ├── registry.py
│   └── assurance.py
└── infra/
    ├── target_inspector.py
    └── corpus_store.py
```

**`domain/base.py`**
- `class CheckContext(BaseModel)` — everything a checker needs: `task_class`, `target_handle`, `pre_state`, `post_state`, `artifacts` (rule text, fix script, etc.).
- `class BaseChecker(ABC)` — the port every checker implements.
  - `name: str`, `version: str`
  - `@abstractmethod def check(self, ctx: CheckContext) -> Verdict`
  - `def _verdict(self, outcome, detail) -> Verdict` (helper, stamps name/version/time)

**`domain/` checkers (each a `BaseChecker` subclass):**
- `class ExploitationChecker(BaseChecker)` — reads **real** session identity; VERIFIED only if `post_state.uid == 0` AND `pre_state.uid != 0` (not-already-root). `check(ctx) -> Verdict` with `detail={"uid":..,"pre_uid":..}`.
- `class DetectionChecker(BaseChecker)` — runs a rule against labelled corpora; `detail={"tp":..,"fp":..,"fn":..,"tn":..}`; VERIFIED gated on TP high AND FP within bound (FP penalised).
- `class RemediationChecker(BaseChecker)` — VERIFIED only if `vuln_recheck == closed` AND `service_health == alive`. `detail={"hole_closed":bool,"service_alive":bool}`.
- `class VulnPrioritisationChecker(BaseChecker)` — scores a ranking vs CVE/CPE/KEV on configured hosts.

**`domain/registry.py`**
- `class CheckerRegistry` — maps `task_class -> BaseChecker`.
  - `register(checker: BaseChecker, *, primary: bool)`
  - `get(task_class) -> BaseChecker`
  - `get_dual(task_class) -> tuple[BaseChecker, BaseChecker]` (primary + independent)

**`domain/assurance.py` (§6.6 — the heart)**
- `class AssuranceSuite`
  - `run_seed_suite(checker) -> AssuranceReport` (known-ground-truth cases must return expected verdicts)
  - `run_planted_false_positives(checker) -> AssuranceReport` (pre-rooted container, restarted-but-broken service, mislabelled sample must be CAUGHT)
  - `run_dual_checker(task_class, ctx) -> DualResult` (alarm on disagreement)
  - `certify(checker) -> bool` (all must pass before the checker is usable)
- `class AssuranceReport(BaseModel)` — pass/fail per case, details.
- `class DualResult(BaseModel)` — `agree: bool`, both verdicts.

**`domain/ports.py`**
- `class TargetInspector(Protocol)` — `session_identity(handle) -> dict`; `service_health(handle, check) -> bool`; `vuln_present(handle, check) -> bool`.
- `class CorpusStore(Protocol)` — `labelled(name) -> list[LabelledItem]`.

**`infra/`**
- `class LabTargetInspector(TargetInspector)` — reads real state via the lab_gateway (through `LabGatewayClient`).
- `class FileCorpusStore(CorpusStore)` — loads labelled malicious/benign corpora from disk/object store.

**`api/routes.py`**
- `POST /verify` → `VerdictService.verify(trajectory)` which: builds `CheckContext` (via inspector), runs primary + dual checker, stamps version, returns `Verdict`. Sealed: no endpoint exposes answer keys.

**Dependencies:** domain → `libs/schemas`, `libs/common`, its own ports. infra → `libs/clients.LabGatewayClient`. **Never** imports learning_engine.

---

### 4.2 `ai_orchestrator` (Stage 1–2)

```
services/ai_orchestrator/
├── api/routes.py
├── domain/
│   ├── ports.py
│   ├── agent.py
│   ├── loop.py
│   ├── tools.py
│   └── cooperation.py      # Phase 2 (stub interface in Phase 1)
└── infra/
    ├── serving_adapter.py
    ├── tool_adapters.py
    └── trajectory_writer.py
```

**`domain/agent.py`**
- `class AgentConfig(BaseModel)` — `id`, `role`, `system_prompt`, `tool_allowlist`, `temperature`, `adapter_id`, `think_cap`.
- `class Agent` — holds a config; `build_prompt(task) -> messages`.

**`domain/loop.py` (the think→tool→observe→adjust loop)**
- `class AgentLoop`
  - `__init__(self, serving: ServingPort, tools: ToolInvoker, authz: AuthzPort, writer: TrajectoryWriter)`
  - `run(agent: Agent, task: Task) -> Trajectory` — the loop: decode → parse action → (if tool) authorize+invoke → feed result back → repeat until `final` or `think_cap`.
  - `_parse_action(text) -> Action` ; `_step_cap` enforcement.

**`domain/tools.py`**
- `class Tool(Protocol)` — `name`; `invoke(args) -> str`.
- `class ToolInvoker` — holds allowed tools per agent; `invoke(agent, name, args) -> str` (checks allowlist first).
- Concrete tools (infra-backed): `NmapTool`, `LabShellTool` (via lab_gateway), `CveMirrorLookupTool`.

**`domain/ports.py`**
- `ServingPort` — `chat(messages, adapter_id, max_tokens) -> str`.
- `AuthzPort` — `authorize(req) -> AuthzDecision`.
- `TrajectoryWriter` — `write(trajectory) -> None`.

**`domain/cooperation.py` (Phase 2 — interface only in Phase 1)**
- `class Blackboard` — shared workspace: `read()`, `write(finding)`.
- `class CooperationCoordinator` — `pick_mode(task) -> Mode`; runs blackboard vs distributed. (Stub: Phase 1 returns a single-agent mode.)

**`infra/`**
- `class VllmServingAdapter(ServingPort)` — wraps `ServingClient`.
- `class ToolAdapters` — concrete tool impls calling lab_gateway / mirror.
- `class PostgresTrajectoryWriter(TrajectoryWriter)`.

**`api/routes.py`** — `POST /run_task {agent_config_id, task}` → `AgentLoop.run(...)` → returns trajectory id; async-friendly.

---

### 4.3 `authz_service` (Stage 1)

```
services/authz_service/
├── api/routes.py
├── domain/
│   ├── ports.py
│   ├── policy.py
│   └── ownership.py
└── infra/
    ├── opa_adapter.py
    └── ownership_adapters.py
```

**`domain/policy.py`**
- `class PolicyDecisionService`
  - `__init__(self, opa: PolicyEngine, ownership: OwnershipVerifier)`
  - `decide(req: AuthzRequest) -> AuthzDecision` — tier rules + scope check + (for external targets) ownership verification + (for production) signed-token-bound-to-action-hash check.
- `class Tier(str, Enum)` — `READ_ONLY | SANDBOX | PRODUCTION`.

**`domain/ownership.py` (§3.5 — the standout)**
- `class OwnershipVerifier(Protocol)` — `verify(target, proof) -> bool`.
- `class OwnershipProof(BaseModel)` — method + payload (DNS/HTTP challenge, WHOIS, attestation).

**`domain/ports.py`**
- `PolicyEngine(Protocol)` — `evaluate(input: dict) -> dict` (OPA).

**`infra/`**
- `class OpaAdapter(PolicyEngine)` — calls the OPA server with `.rego` policies from `configs/authz_policy/`.
- `class DnsChallengeVerifier(OwnershipVerifier)`, `class HttpChallengeVerifier(OwnershipVerifier)`, `class AllowlistVerifier(OwnershipVerifier)` (lab IPs owned by definition).

**`api/routes.py`** — `POST /authorize {AuthzRequest}` → `PolicyDecisionService.decide` → `AuthzDecision`.

---

### 4.4 `lab_gateway` (Stage 1) — lives on the LAB machine

```
services/lab_gateway/           # deployed to laptop; see lab/ for runners
├── api/routes.py
├── domain/
│   ├── ports.py
│   └── gateway.py
└── infra/
    ├── wireguard.py
    └── runner_adapter.py
```

**`domain/gateway.py`**
- `class LabGateway`
  - `__init__(self, state: StateManagerPort, runner: RunnerPort)`
  - `run_payload(target, payload) -> LabResult` — **refuses if state == DETONATION**; else dispatches to runner.
  - `target_state() -> LabState`.
- `class LabState(str, Enum)` — `TARGET_SERVING | DETONATION`.
- `class LabResult(BaseModel)` — raw output + captured state for the verifier.

**`domain/ports.py`** — `StateManagerPort` (`current() -> LabState`), `RunnerPort` (`execute(target, payload) -> LabResult`).

**`infra/`** — `class WireguardInfra`, `class AgentRunnerAdapter(RunnerPort)`. (The actual runner + state machine live under `lab/`, §4.10.)

---

### 4.5 `model_registry` (Stage 2)

```
services/model_registry/
├── api/routes.py
├── domain/
│   ├── ports.py
│   ├── registry.py
│   └── rollback.py
└── infra/
    └── mlflow_adapter.py
```

**`domain/registry.py`**
- `class ModelRegistry`
  - `register(run: TrainingRun, eval: EvalResult) -> GenerationRecord`
  - `get(generation_id) -> GenerationRecord`
  - `tag_golden_anchor(generation_id)`
  - `list_anchors() -> list[GenerationRecord]`
  - `current_serving_adapter() -> str`
- `class GenerationRecord(BaseModel)` — adapter_id, base, dataset_version_id, config, eval, expert_load, provenance, lineage, parent_id, is_golden_anchor. **Immutable** (new records only; never overwrite).

**`domain/rollback.py`**
- `class RollbackController`
  - `rollback_to(generation_id)` — restore as serving adapter.
  - `diagnose(bad_id, anchor_id) -> DiagnosisReport` — compares six-group logs.
  - `resume_from(anchor_id)`.

**`infra/mlflow_adapter.py`** — `class MlflowRegistry(...)` implements the ports against MLflow.

---

### 4.6 `learning_engine` (Stage 2 SFT → Stage 5 GRPO)

```
services/learning_engine/
├── api/routes.py
├── domain/
│   ├── ports.py
│   ├── dataset_builder.py
│   ├── trainer.py
│   ├── grpo.py            # Phase 2 (stub in Phase 1)
│   ├── promotion.py
│   └── gate.py
└── infra/
    ├── unsloth_adapter.py
    └── dataset_io.py
```

**`domain/dataset_builder.py`**
- `class DatasetBuilder`
  - `build(verified: list[Trajectory]) -> DatasetVersion` — dedupe → poison-screen (external) → seed-replay mix → **diversity cap (no template >15%)** → stats.
  - `_dedupe`, `_poison_screen`, `_apply_diversity_cap`, `_mix_seed_replay`.
- `class DiversityCap` — `enforce(items, max_share) -> (kept, held_back)`.

**`domain/trainer.py`**
- `class SftTrainer`
  - `__init__(self, backend: TrainingBackend)`
  - `train(dataset: DatasetVersion, base_adapter: str, config: dict) -> TrainingRun` — router frozen (Unsloth default), full metrics logged.
- `TrainingBackend(Protocol)` — `fit(dataset, config) -> metrics`.

**`domain/gate.py`**
- `class PromotionGate`
  - `evaluate(candidate_adapter) -> GateResult` — sealed benchmark + canaries + statistical test + no FP/critical-category regression.
  - `class GateResult(BaseModel)` — `pass_: bool`, reasons, eval: EvalResult.

**`domain/promotion.py`**
- `class PromotionController`
  - `run_generation(verified) -> GenerationOutcome` — build dataset → train → gate → (await human approval) → register or reject.

**`domain/grpo.py` (Phase 2 stub)**
- `class GrpoTrainer` — groups of attempts, verifier-scored, group-relative advantage. Interface only in Phase 1.

**`infra/unsloth_adapter.py`** — `class UnslothBackend(TrainingBackend)` — `FastModel`, NGC container, aarch64, frozen router by default.

**Hard rule:** learning_engine depends on `SealedBenchClient` (submit-and-score) but **cannot read** sealed scenarios or verifier answer keys.

---

### 4.7 `curriculum_controller` (Stage 2 web → Stage 5 all domains)

```
services/curriculum_controller/
├── api/routes.py
├── domain/
│   ├── difficulty.py
│   ├── domains.py
│   └── controller.py
└── infra/
    └── success_rate_source.py
```

- `class DifficultyLadder` — `current_tier()`, `should_raise(success_rate) -> bool`, `raise_tier()`.
- `class DomainSchedule` — cumulative domain order (web→linux→windows→ad→cloud→mobile); `active_domains()`, `can_add_next(success_rate) -> bool`, `add_next()`.
- `class CurriculumController`
  - `next_scenario_spec() -> ScenarioSpec` — difficulty-led: picks difficulty from success rate, domain from schedule, + free-exploration reserve.
  - `record_outcome(verdict)` — updates success rate; logs curriculum state per generation.
- `class ScenarioSpec(BaseModel)` — domain, difficulty_tier, target_template, is_free_exploration.

---

### 4.8 `benchmarks/sealed` (Stage 2) — SEPARATE SERVICE

```
benchmarks/sealed/
├── api/routes.py          # ONLY: POST /evaluate {adapter} -> EvalResult
├── domain/
│   └── evaluator.py       # runs hold-out scenarios; scenarios NOT exposed
└── infra/
    └── scenario_store.py  # private; no read endpoint
```
- `class SealedEvaluator` — `evaluate(adapter_id) -> EvalResult`. Scenarios live here and are unreachable from learning_engine. Rotate hold-outs over time.

---

### 4.9 Phase-1 lighter services (stubs now, filled in their stage)

- `security_core` (Stage 2–3): `domain/case.py` (`class Case`, `class Evidence`), `infra/` Postgres store. `CaseService.open/append/close`.
- `customer_dashboard` (Stage 2 minimal): a thin read API + approval endpoint; full UI in Stage 6.

---

### 4.10 `lab/` (on the laptop — not a service, but structured)

```
lab/
├── state_manager/
│   ├── machine.py          # class LabStateMachine: TARGET_SERVING <-> DETONATION, mutually exclusive
│   └── enforcement.py      # brings tunnel down / blocks routes on DETONATION
├── agent_runner/
│   └── runner.py           # class AgentRunner: execute(target, payload) -> LabResult
├── targets/
│   ├── web/                # DVWA, Juice Shop, Metasploitable compose + revert
│   └── registry.py         # class TargetRegistry: spin_up / revert / pre_state
└── detonation/             # Phase 2: class DetonationSandbox (gated by state machine)
```
- `class LabStateMachine` — `state()`, `to_target_serving()`, `to_detonation()` (each enforces the other is torn down); `assert_tunnel_down_if_detonation()`.
- **Hard rule:** `lab/` imports NOTHING from Spark-side services that hold weights/creds.

---

### 4.11 Phase-2 services (class skeleton to build to when reached)

- `agent_population`: `domain/genome.py` (`class Genome` = AgentConfig + descriptors), `domain/map_elites.py` (`class MapElitesArchive`: `place(genome, score, descriptors)`, `best_in_cell`, `cells()`), `domain/selection.py`.
- `network_monitor` / `endpoint_manager` / `vulnerability_engine` / `threat_intelligence`: each `domain/<x>.py` with an interpreter class consuming tool output (Suricata/Zeek/Wazuh/Velociraptor/NVD) → structured findings.
- `incident_manager`: `domain/lifecycle.py` (`class Incident`, state machine).
- `response_engine`: `domain/actions.py` (tiered actions, OPA-gated), `domain/approval.py` (signed-token).
- `recovery_engine`: `domain/recovery.py` (`class RecoveryVerifier`: restored == known-good).

---

## 5. Dependency rules (enforced)

1. `domain/` imports only: `libs/schemas`, `libs/common`, its own `ports.py`. Never `infra/`, never `api/`, never another service directly.
2. Cross-service calls go through `libs/clients/` (typed), never direct imports.
3. `infra/` implements `domain/ports.py` interfaces; `__main__.py` wires them.
4. `lab/*` never imports Spark-side weight/credential code.
5. `learning_engine` never imports `benchmarks/sealed` internals or verifier answer keys — only `SealedBenchClient.evaluate`.
6. No LLM import inside `verifier_service/domain`, `authz_service/domain`, or any gate.
7. All public domain methods are typed and unit-tested with fake ports.

---

## 6. Class index (quick reference — what lives where)

| Class | Service / module | Role |
|---|---|---|
| `BaseChecker`, `ExploitationChecker`, `DetectionChecker`, `RemediationChecker` | verifier_service/domain | deterministic verdicts |
| `AssuranceSuite`, `DualResult` | verifier_service/domain/assurance | §6.6 check-the-checker |
| `CheckerRegistry` | verifier_service/domain | task_class → checker |
| `AgentLoop`, `Agent`, `AgentConfig` | ai_orchestrator/domain | think→tool→observe loop |
| `ToolInvoker`, `Tool` | ai_orchestrator/domain | gated tool use |
| `Blackboard`, `CooperationCoordinator` | ai_orchestrator/domain (P2) | cooperation |
| `PolicyDecisionService`, `Tier` | authz_service/domain | authorisation |
| `OwnershipVerifier`, `OwnershipProof` | authz_service/domain | §3.5 ownership |
| `LabGateway`, `LabState` | lab_gateway/domain | gated lab ingress |
| `LabStateMachine` | lab/state_manager | §12.2 mutual exclusion |
| `ModelRegistry`, `GenerationRecord` | model_registry/domain | immutable generations |
| `RollbackController` | model_registry/domain | diagnose→rollback→resume |
| `DatasetBuilder`, `DiversityCap` | learning_engine/domain | dataset + diversity cap |
| `SftTrainer`, `GrpoTrainer` (P2) | learning_engine/domain | training |
| `PromotionGate`, `PromotionController` | learning_engine/domain | gate + generation run |
| `SealedEvaluator` | benchmarks/sealed/domain | sealed scoring |
| `CurriculumController`, `DifficultyLadder`, `DomainSchedule` | curriculum_controller/domain | difficulty-led curriculum |
| `MapElitesArchive`, `Genome` (P2) | agent_population/domain | quality-diversity |

---

*Build every service to this shape: thin api, pure domain, adapter infra, ports between them. Verifier domain first. Keep domain free of I/O and LLMs. The per-stage runbooks give the full method bodies; this gives the skeleton they hang on.*
