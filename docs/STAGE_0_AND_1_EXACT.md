# Stage 0 + Stage 1 — Exact Line-by-Line Runbook

**Follow this top to bottom.** Every command and file is given exactly. Two parts:
- **PART A — OFF-GPU PREP** (do on any normal/cheap machine; do NOT pay for the Spark for this). Scaffold, schemas, configs, commit to git.
- **PART B — ON-SPARK SESSION** (the paid cloud DGX Spark; ~$0.80/hr). Runs only GPU-needing steps, ordered to prove the two blockers and capture numbers fast.

**Golden rules for a rented, ephemeral Spark:**
- The instance is disposable. **Everything you want to keep must be in git (code) or scripted to re-download (models/containers).**
- Do PART A first, commit, THEN start the paid instance and `git clone`.
- Commit after every working step.

---

# PART A — OFF-GPU PREP (no Spark, no cost)

## A0. Prerequisites on your dev machine
- Install: `git`, `python3.11+`, `uv` (`pip install uv`) or `poetry`, and a GitHub/GitLab account.
- Create an empty private repo named `cyberai` on GitHub. Copy its SSH/HTTPS URL.

## A0b. Git identity + GitHub labels (do this before the first commit)
```bash
# Commit AS YOU — never any AI attribution (see GIT_WORKFLOW.md)
git config user.name  "Your Name"
git config user.email "you@example.com"
# Authenticate GitHub as you:
gh auth login            # or add an SSH key / token
# Create the revisit labels (after the remote exists, step A13):
#   gh label create revisit-on-dgx --color FBCA04 --description "Revisit when the physical DGX is owned"
#   gh label create purchase-gate --color 0E8A16 --description "Gates the DGX purchase decision"
#   gh label create revisit-on-measurement --color 1D76DB --description "Revisit after Stage 1.5 measurement"
```

## A1. Create the project and folders
```bash
mkdir cyberai && cd cyberai
git init
mkdir -p docs libs/common libs/schemas libs/clients \
         services/verifier_service services/ai_orchestrator services/authz_service \
         services/lab_gateway services/model_registry services/learning_engine \
         services/curriculum_controller \
         lab/targets lab/detonation lab/state_manager lab/agent_runner \
         verifiers/web/assurance benchmarks/sealed benchmarks/canaries \
         datasets/seed datasets/builder scripts tests/unit tests/integration tests/assurance \
         configs/authz_policy containers/vllm-gb10 containers/unsloth-ngc
```

## A2. Copy the design docs + governance files into place
Put these in `cyberai/docs/`:
- `MASTER_PROJECT_BRIEF_v1.1.md`
- `BRIEF_v1.2_CORRECTIONS_AND_SETUP.md`
- `SONNET_COMPLETE_BUILD_PLAN.md`
- `STAGE_0_AND_1_EXACT.md` (this file)
- `diagram-master-comprehensive.drawio`

Put these at the repo **root** (not docs/):
- `CLAUDE.md` (Claude Code reads this automatically)
- `GIT_WORKFLOW.md`
- `DECISIONS_TO_REVISIT.md`
- `.github/pull_request_template.md`

This whole runbook (Part A) should be done on a feature branch, e.g. `git switch -c stage-0/scaffold`, and opened as a PR for the human to merge (see `GIT_WORKFLOW.md`). Do NOT commit straight to `main`.

## A3. Write `pyproject.toml` (repo root)
```toml
[project]
name = "cyberai"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
  "pydantic>=2.7",
  "pyyaml>=6.0",
  "structlog>=24.1",
  "httpx>=0.27",
  "psycopg[binary]>=3.1",
  "mlflow>=2.14",
  "pytest>=8.0",
]

[tool.pytest.ini_options]
testpaths = ["tests"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

## A4. Write `.env.example` (repo root)
```bash
# --- copy to .env and fill in; NEVER commit .env ---
POSTGRES_DSN=postgresql://cyberai:changeme@localhost:5432/cyberai
MLFLOW_TRACKING_URI=http://localhost:5000
VLLM_BASE_URL=http://localhost:8000/v1
VLLM_MODEL=Qwen/Qwen3-30B-A3B-Instruct-2507-FP8
LAB_GATEWAY_URL=http://10.10.0.2:8080
WIREGUARD_LAB_IP=10.10.0.2
HF_TOKEN=            # HuggingFace token for model download
```

## A5. Write `.gitignore` (repo root)
```
.env
__pycache__/
*.pyc
.venv/
models/
*.log
mlruns/
data/
```

## A6. Write `libs/schemas/__init__.py` (the frozen core types)
```python
from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class Outcome(str, Enum):
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"
    UNVERIFIABLE = "UNVERIFIABLE"


class Provenance(BaseModel):
    scenario_id: str
    verifier_version: str | None = None
    generating_adapter: str
    timestamp: datetime
    lab_target_id: str | None = None


class TrajectoryStep(BaseModel):
    action: str            # e.g. "tool_call" | "reason" | "final"
    content: str
    tool_name: str | None = None
    tool_result: str | None = None


class Trajectory(BaseModel):
    id: str
    agent_config_id: str
    adapter_id: str                      # gen_N
    domain: str                          # "web" in Phase 1
    difficulty_tier: int
    task_class: str                      # "exploitation" | "detection" | "remediation" | ...
    steps: list[TrajectoryStep]
    raw_output: str
    started_at: datetime
    finished_at: datetime
    provenance: Provenance               # MANDATORY — no trajectory without provenance


class Verdict(BaseModel):
    trajectory_id: str
    task_class: str
    outcome: Outcome
    detail: dict[str, Any] = Field(default_factory=dict)   # e.g. {"uid":0} or {"tp":95,"fp":2}
    verifier_name: str
    verifier_version: str
    checked_at: datetime
    dual_checker_agreement: bool | None = None


class DatasetVersion(BaseModel):
    id: str
    hash: str
    composition: dict[str, int]          # {"verified_new":.., "seed_replay":.., "<source>":..}
    diversity_stats: dict[str, float]    # per-template share
    created_at: datetime
    provenance: list[Provenance]


class TrainingRun(BaseModel):
    id: str
    base_model: str
    adapter_in: str | None
    adapter_out: str
    config: dict[str, Any]
    dataset_version_id: str
    metrics: dict[str, Any]              # loss curves, grad-norm, LR, expert-load
    started_at: datetime
    finished_at: datetime


class EvalResult(BaseModel):
    candidate_adapter: str
    benchmark_version: str
    overall_score: float
    per_category: dict[str, float]
    fp_rate: float
    canary_scores: dict[str, float]
    confidence_interval: tuple[float, float]
    per_task: list[dict[str, Any]]


class AuthzRequest(BaseModel):
    target: str
    scope_token: str | None = None
    ownership_proof: dict[str, Any] | None = None
    tier: str                            # "read_only" | "sandbox" | "production"
    action_hash: str | None = None


class AuthzDecision(BaseModel):
    allow: bool
    reason: str
```

## A7. Write `libs/common/__init__.py` (logging + provenance + ids)
```python
from __future__ import annotations
import uuid
from datetime import datetime, timezone
import structlog

# Six logging groups as explicit categories (brief §13)
LOG_GROUPS = ("training", "routing", "eval", "data_lineage", "verifier_health", "config_env")

def get_logger(service: str):
    return structlog.get_logger(service=service)

def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"

def now() -> datetime:
    return datetime.now(timezone.utc)
```

## A8. Write the serving config `configs/serving.yaml`
```yaml
# vLLM serving on GB10 — see docs/BRIEF_v1.2 Appendix B1
model: "Qwen/Qwen3-30B-A3B-Instruct-2507-FP8"
dtype: "auto"            # FP8 variant
gpu_memory_utilization: 0.85
max_model_len: 32768
enable_prefix_caching: true
enable_chunked_prefill: true
# multi-LoRA enabled at serve time via --enable-lora
# DO NOT set CUTE_DSL_ARCH=sm_121a (hangs on GB10)
```

## A9. Write the training config `configs/training.yaml`
```yaml
# Unsloth FastModel on GB10 — see docs/BRIEF_v1.2 Appendix B2
model_name: "unsloth/Qwen3-30B-A3B"
max_seq_length: 2048       # raise for long-context hard tasks
load_in_4bit: true         # QLoRA
full_finetuning: false
lora_rank: 16
lora_alpha: 32
# Router-layer fine-tuning is DISABLED BY DEFAULT in Unsloth = our frozen-router policy. Do not re-enable.
gradient_checkpointing: true
packing: true              # sequence packing — part of the 5-day→20-hour speedup
learning_rate: 1.0e-5
warmup_steps: 20
max_grad_norm: 1.0
```

## A10. Write the Loop B gate config `configs/loopB_gate.yaml`
```yaml
# PRE-REGISTERED. Do not edit after measuring (brief §7.8).
floor_verified_unique_per_day: 300
max_template_share: 0.15
aspirational_per_day: 800
revision_rule:
  lower_bar_if: "a ~100-trajectory pilot SFT measurably beats the sealed benchmark"
  give_up_if: "a full-volume round fails to beat the sealed benchmark twice in a row"
  give_up_action: "park Loop B for the year; Loop A becomes committed engine"
```

## A11. Write a smoke-test `tests/unit/test_schemas.py`
```python
from datetime import datetime, timezone
from libs.schemas import Trajectory, Provenance, TrajectoryStep, Outcome, Verdict

def test_trajectory_requires_provenance():
    p = Provenance(scenario_id="s1", generating_adapter="gen_0", timestamp=datetime.now(timezone.utc))
    t = Trajectory(id="t1", agent_config_id="a1", adapter_id="gen_0", domain="web",
                   difficulty_tier=1, task_class="exploitation",
                   steps=[TrajectoryStep(action="final", content="done")],
                   raw_output="done", started_at=datetime.now(timezone.utc),
                   finished_at=datetime.now(timezone.utc), provenance=p)
    assert t.provenance.generating_adapter == "gen_0"

def test_verdict_roundtrip():
    v = Verdict(trajectory_id="t1", task_class="exploitation", outcome=Outcome.VERIFIED,
                detail={"uid": 0}, verifier_name="web.exploitation", verifier_version="1.0",
                checked_at=datetime.now(timezone.utc))
    assert Verdict.model_validate_json(v.model_dump_json()).outcome == Outcome.VERIFIED
```

## A12. Write the `Makefile` (repo root)
```makefile
.PHONY: install test lint serve-smoke train-smoke bench
install:
	uv venv && uv pip install -e .
test:
	uv run pytest -q
lint:
	uv run python -m py_compile libs/schemas/__init__.py libs/common/__init__.py
serve-smoke:
	bash scripts/serve_smoke.sh
train-smoke:
	bash scripts/train_smoke.sh
bench:
	uv run python scripts/measure_throughput.py
```

## A13. Run the off-GPU tests, commit to a branch, open a PR (human merges)
```bash
uv venv && uv pip install -e .
uv run pytest -q          # test_schemas must pass
git switch -c stage-0/scaffold 2>/dev/null || git switch stage-0/scaffold
git add -A
git commit -m "stage-0: repo scaffold, schemas, configs, governance docs"   # NO AI attribution
git branch -M main 2>/dev/null || true
git remote add origin <YOUR_REPO_URL> 2>/dev/null || true
git push -u origin stage-0/scaffold
# create the revisit labels now that the remote exists:
gh label create revisit-on-dgx --color FBCA04 --description "Revisit when the physical DGX is owned" || true
gh label create purchase-gate --color 0E8A16 --description "Gates the DGX purchase decision" || true
gh label create revisit-on-measurement --color 1D76DB --description "Revisit after Stage 1.5" || true
# open the PR AS YOU; the HUMAN reviews and merges (Claude Code does not merge):
gh pr create --fill --base main
# then open the pre-logged revisit issues from DECISIONS_TO_REVISIT.md:
gh issue create --title "DGX purchase gate" --body "See DECISIONS_TO_REVISIT.md P-001." --label purchase-gate
gh issue create --title "Revisit: Stage 0/1 GPU split" --body "See DECISIONS_TO_REVISIT.md R-001." --label revisit-on-dgx
gh issue create --title "Revisit: ephemeral-instance workarounds" --body "See DECISIONS_TO_REVISIT.md R-002." --label revisit-on-dgx
gh issue create --title "Revisit: container tags vs owned DGX OS" --body "See DECISIONS_TO_REVISIT.md R-003." --label revisit-on-dgx
gh issue create --title "Revisit: Loop B gate thresholds after Stage 1.5" --body "See DECISIONS_TO_REVISIT.md M-001." --label revisit-on-measurement
```
`main` stays empty until the human merges this first PR. Everything else lands via its own stage branch + PR.

**PART A DoD:**
- [ ] `uv run pytest -q` passes (schemas round-trip; provenance mandatory).
- [ ] Repo pushed to git with docs/ + CLAUDE.md.
- [ ] All configs written. **Nothing above needed a GPU — you paid $0 so far.**

---

# PART B — ON-SPARK SESSION (paid; prove the blockers + measure)

> Start the cloud DGX Spark NOW. Work in this exact order — the GPU-only steps come first so your money proves the two blockers and captures numbers. Target: finish B1–B6 in the first few hours.

## B0. First thing on the instance
```bash
# clone your repo
git clone <YOUR_REPO_URL> && cd cyberai
cp .env.example .env    # edit .env: set HF_TOKEN, keep localhost URLs
# confirm the GPU is visible
nvidia-smi              # must show GB10; if not, STOP — wrong instance
uname -m                # must print: aarch64
```

## B1. Write the model-download script `scripts/download_model.sh` and run it
```bash
cat > scripts/download_model.sh <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
: "${HF_TOKEN:?set HF_TOKEN in .env}"
mkdir -p models
pip install -q "huggingface_hub[cli]"
huggingface-cli download Qwen/Qwen3-30B-A3B-Instruct-2507-FP8 \
  --local-dir models/qwen3-30b-a3b-fp8 --token "$HF_TOKEN"
EOF
chmod +x scripts/download_model.sh
set -a; source .env; set +a
./scripts/download_model.sh    # ~30GB; persist models/ to a volume if the provider offers one
```

## B2. Pull the SM121 vLLM container and write the serve script
> Use a known-good SM121 image (v1.2 Appendix B1). Try the NVIDIA NGC image first; fall back to a community SM121 image. **Pin whichever works** into `containers/vllm-gb10/IMAGE.txt`.
```bash
# Try, in order, until one pulls and serves (record the winner):
docker pull nvcr.io/nvidia/vllm:25.10-py3 || true
# community fallbacks (verify current tags at build time):
# docker pull avarok/dgx-vllm-nvfp4-kernel:v22
# (eugr/spark-vllm-docker — build per its README)

cat > scripts/serve_smoke.sh <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
IMAGE="$(cat containers/vllm-gb10/IMAGE.txt)"
docker run --rm --gpus all --ipc=host -p 8000:8000 \
  -v "$PWD/models/qwen3-30b-a3b-fp8:/model" \
  "$IMAGE" \
  vllm serve /model --served-model-name qwen3 \
  --gpu-memory-utilization 0.85 --max-model-len 32768 \
  --enable-prefix-caching --enable-chunked-prefill
EOF
chmod +x scripts/serve_smoke.sh
echo "nvcr.io/nvidia/vllm:25.10-py3" > containers/vllm-gb10/IMAGE.txt   # edit to the winner
```
Start the server (in one terminal):
```bash
bash scripts/serve_smoke.sh
```
In a second terminal, confirm it answers (**BLOCKER #1 proof**):
```bash
curl -s http://localhost:8000/v1/chat/completions \
 -H 'Content-Type: application/json' \
 -d '{"model":"qwen3","messages":[{"role":"user","content":"Say OK"}]}' | head
```
→ A valid completion = **vLLM serves Qwen3-30B-A3B FP8 on GB10. Blocker #1 CONFIRMED on your unit.** Record the winning image in `containers/vllm-gb10/IMAGE.txt`, commit.

## B3. Measure serving throughput `scripts/measure_throughput.py`
```bash
cat > scripts/measure_throughput.py <<'EOF'
import time, json, httpx
URL = "http://localhost:8000/v1/chat/completions"
def one(prompt, max_tokens=128):
    t0 = time.time()
    r = httpx.post(URL, json={"model":"qwen3","messages":[{"role":"user","content":prompt}],
                              "max_tokens":max_tokens}, timeout=120)
    dt = time.time()-t0
    out = r.json()
    n = out.get("usage",{}).get("completion_tokens", max_tokens)
    return n/dt
if __name__ == "__main__":
    single = one("Explain TCP in 100 words.")
    print(json.dumps({"single_stream_tok_s": round(single,1)}))
    # crude batch proxy: fire N concurrent
    import concurrent.futures as cf
    with cf.ThreadPoolExecutor(max_workers=32) as ex:
        t0=time.time(); list(ex.map(lambda _: one("Explain DNS.",64), range(32))); dt=time.time()-t0
    print(json.dumps({"batch32_wall_s": round(dt,1)}))
EOF
uv run python scripts/measure_throughput.py | tee stage1_serving_numbers.json
git add -A && git commit -m "Stage 1: vLLM serving confirmed + throughput measured on GB10"
```
Expect roughly ~44–85 tok/s single-stream and much higher aggregate batched (reference: ~300 tok/s). **Record your actual numbers** — they set cadence/concurrency downstream.

## B4. Unsloth training smoke-test (BLOCKER #2 proof)
> Run inside the NGC Unsloth container with aarch64 patches (v1.2 Appendix B2). Write a tiny LoRA run on ~20 toy examples and confirm loss decreases + adapter writes + **torch is CUDA not +cpu.**
```bash
cat > scripts/train_smoke.py <<'EOF'
# Runs INSIDE the unsloth NGC container. Confirms MoE LoRA works on GB10.
import torch
assert torch.cuda.is_available(), "FAIL: torch has no CUDA accelerator (CPU-only wheel). Fix container."
print("torch CUDA OK:", torch.version.cuda)
from unsloth import FastModel
model, tok = FastModel.from_pretrained(
    model_name="unsloth/Qwen3-30B-A3B",
    max_seq_length=2048, load_in_4bit=True, full_finetuning=False,
)
# router-layer fine-tuning disabled by default = frozen router (our policy)
from trl import SFTTrainer, SFTConfig
from datasets import Dataset
data = Dataset.from_list([{"text": f"Q: ping {i}? A: pong {i}"} for i in range(20)])
trainer = SFTTrainer(model=model, tokenizer=tok, train_dataset=data,
    args=SFTConfig(max_steps=5, per_device_train_batch_size=1,
                   gradient_accumulation_steps=1, learning_rate=1e-5,
                   logging_steps=1, output_dir="out_smoke"))
res = trainer.train()
print("TRAIN LOSS FINAL:", res.training_loss)
model.save_pretrained("out_smoke/adapter")
print("ADAPTER SAVED OK")
EOF

cat > scripts/train_smoke.sh <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
# Use the NGC Unsloth container (pin the tag that works into containers/unsloth-ngc/IMAGE.txt)
IMAGE="$(cat containers/unsloth-ngc/IMAGE.txt)"
docker run --rm --gpus all --ipc=host -v "$PWD:/work" -w /work "$IMAGE" \
  bash -lc "pip install -q --no-cache-dir unsloth unsloth_zoo trl datasets && \
            python scripts/train_smoke.py"
EOF
chmod +x scripts/train_smoke.sh
echo "nvcr.io/nvidia/pytorch:25.11-py3" > containers/unsloth-ngc/IMAGE.txt  # edit to the working NGC tag
bash scripts/train_smoke.sh 2>&1 | tee stage1_train_smoke.log
```
→ "torch CUDA OK", decreasing loss, "ADAPTER SAVED OK" = **Unsloth MoE LoRA works on GB10. Blocker #2 CONFIRMED on your unit.**
- If you see **"cannot find any torch accelerator"**: you're on the CPU-only wheel → the container/patches are wrong (v1.2 B2). Fix before continuing; do NOT proceed.
Commit:
```bash
git add -A && git commit -m "Stage 1: Unsloth MoE LoRA confirmed on GB10 (not CPU-only)"
```

## B5. Measure a real LoRA step time (cadence input)
Bump `max_steps` to ~50 in `scripts/train_smoke.py`, rerun `scripts/train_smoke.sh`, and record seconds/step from the log. This feeds the 3-day-cadence math (reference: stock ~5 days vs optimised ~20 hours per 25k×3 round). Commit the number.

## B6. Capture the Stage-1 baseline and push
```bash
cat > stage1_baseline.md <<EOF
# Stage 1 measured baseline (our unit)
- Serving image: $(cat containers/vllm-gb10/IMAGE.txt)
- Training image: $(cat containers/unsloth-ngc/IMAGE.txt)
- Single-stream tok/s: (from stage1_serving_numbers.json)
- Batch32 wall s: (from stage1_serving_numbers.json)
- LoRA seconds/step: (from stage1_train_smoke.log)
- Blocker #1 (vLLM MoE+FP8): CONFIRMED
- Blocker #2 (Unsloth MoE LoRA): CONFIRMED
EOF
git add -A && git commit -m "Stage 1 baseline recorded" && git push
```

## B7. (If time remains in the 24h) Lab + infra scaffolding
Only after B1–B6 are committed, start the non-GPU-critical Stage-1 infra you can also do off-Spark later:
- `lab/state_manager/` — the §12.2 TARGET_SERVING XOR DETONATION state machine (code + a test asserting the tunnel is unreachable during DETONATION).
- `services/authz_service/` — OPA policies (3 tiers + scope + ownership-verification hook).
- `services/lab_gateway/` — WireGuard config + narrow API; refuses calls in DETONATION.
- `lab/targets/` — DVWA / Juice Shop / Metasploitable container definitions + revert script.
These don't need the GPU, so if the clock is running low, **commit B1–B6, tear down the instance to stop billing, and do B7 off-GPU.**

---

## END-OF-SESSION CHECKLIST (before you tear down the paid instance)
- [ ] `containers/vllm-gb10/IMAGE.txt` and `containers/unsloth-ngc/IMAGE.txt` hold the WORKING tags.
- [ ] `stage1_serving_numbers.json`, `stage1_train_smoke.log`, `stage1_baseline.md` committed + pushed.
- [ ] Both blockers confirmed on your unit.
- [ ] Everything pushed to git (the instance is about to vanish).
- [ ] `models/` either on a persistent volume or re-downloadable via `scripts/download_model.sh`.

**When all boxes are ticked, Stage 1's hardware-critical work is DONE and proven on your own unit.** Next: ask for the **Stage 2 exact runbook** (the web verifier + its assurance suite — the foundation), which is mostly off-GPU and cheap to build.

---

*Pay the Spark only for B1–B6. Prove the blockers, grab the numbers, commit, tear down. Everything else is cheap off-GPU work.*
