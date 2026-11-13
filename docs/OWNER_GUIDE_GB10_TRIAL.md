# Owner's guide to the GB10 trial — plain English

13 November 2026. This explains, without jargon where possible, what the trial is
for, what was changed to make it work, what you need to do, and how to read the
results. The exact command reference is `RENTAL_START_HERE.md`; this guide tells
you *why* each step exists. A glossary is at the end.

---

## 1. What the trial is for

You want to know whether a DGX Spark (about £5,000) can do the job **before** you buy
one. So you rent the same machine (Enverge, about $0.85 an hour) for up to 24 hours
and run the real workload on it:

1. **Serve** the AI model (load it and answer questions) and measure how fast.
2. **Train** it (teach it with a small LoRA "add-on") and measure how fast.
3. **Save, reload and deploy** that add-on, and check it actually works.
4. **Export** all the measurements somewhere safe before the rental ends.

The answer you get is about the *machine*: speed, memory, and whether the software
works on it. It does **not** prove the model got smarter at security work — that
needs proper training data and evaluation later.

## 2. The model, in plain terms

- **Only one model family: Qwen3-30B-A3B ("MoE").** It has 30 billion parameters but
  only about 3 billion are active for each word, so it is fast for its size. The smaller
  backup model (Qwen3-14B) has been removed, as you asked.
- **"Instruct-2507" is the right version.** "2507" means July 2025 — that is the
  release date, not a deadline. I checked Hugging Face on 13 November 2026: there is
  no newer ("January") release of this model. Instruct-2507 is the model for your
  **15 January 2027** fine-tune target. (There is also a "Thinking-2507" version that
  reasons step by step; comparing the two is a separate decision for later.)
- **Two copies of the same model are used:**
  - For **answering** (serving): the official *FP8* copy — a compressed version that is
    faster and smaller (~31 GB download).
  - For **training**: the full-quality copy (~61 GB download), from which the add-on is
    trained. Both come from the same original weights, so the add-on fits the FP8 copy.

## 3. How training works now (your precision decision)

- **Default: 4-bit QLoRA.** While training, the model's main weights are squeezed to
  4 bits (about 17 GB instead of 61 GB) and frozen; only a small add-on (the LoRA
  adapter) is trained. This leaves lots of free memory for longer texts. It is
  not FP8 training and not bf16 training, as you asked.
- **bf16 is a comparison only.** One extra training run uses full-quality bf16
  weights (`TRAIN_PRECISION=bf16`). If it is clearly faster (more tokens per second)
  and still fits in memory, you can switch to it later. FP8 training is not used.
- The add-on trained either way is used on the FP8 serving copy.

## 4. What Enverge's machine is like, and how that is handled

You confirmed: Enverge gives a **real GB10**, but you log in **inside a locked-down
container**, not the bare machine, and you are **not an administrator (root)**.
Docker works inside that container, but the usual way of giving a container the GPU
(`--gpus all`) **fails** there.

What I built for this:

- **One place decides all Docker settings** (`rental/docker_runtime.py`). Every
  container the project starts — serving, training, the checks — asks it which flags
  to use.
- **A setup script tests the real machine** (`scripts/rental/docker_runtime_setup.py`).
  You run it once after downloading the two container images. It:
  1. tries the three known ways of giving a container the GPU and keeps the one that
     shows a GB10;
  2. checks shared-memory and memory-limit settings the locked-down container may refuse;
  3. checks a container can **read and write your project folder** (if not, nothing
     can work — it stops and says so);
  4. checks a server inside a container can be reached from your session.
  It saves the answers to `artifacts/docker_runtime/docker_env.sh`. You load them with
  `source artifacts/docker_runtime/docker_env.sh` — **in every new terminal window**.
- Things that need administrator rights (clearing the memory cache) are tried, and if
  refused they are simply recorded as "not permitted"; the run carries on.
- I rehearsed this script on your laptop's Docker (no GPU there): the folder read/write
  and network checks worked; the GPU part can only be confirmed on the Spark.

## 5. What I fixed so the trial would not fail for the wrong reasons

Before these fixes, several things would probably have broken a perfectly good run:

| Problem | What would have happened | Fix |
|---|---|---|
| The server was given only 4 minutes to start | Loading a 30B model can take longer, so the run would have been killed | Waits up to 30 minutes, but gives up at once if the server crashes |
| Server error messages were deleted when the server was removed | If serving failed you would not know why | Server messages are saved to a file live and kept in the results |
| One slow request during the speed test stopped everything | The run would end before training ever started | Slow/failed requests are recorded as results; only a dead server stops the run |
| Memory readings on GB10 show "N/A" | The "memory was freed" check could never work | Reads the machine's shared memory instead, and says so in the results |
| The reload check demanded near-identical numbers across two different calculation paths | A correct add-on would probably have been rejected | Weights must still match exactly; outputs must pick the same answer and be closer to the trained model than to the untrained one |
| Training settings in the config file were ignored | What ran was not what the file said | The trainer now reads `configs/training.yaml` |
| The training container tried to install the project from the internet | Could fail on network/permissions | Uses the project folder directly; prints progress live |
| Serving ignored the GB10 settings researched earlier | Untested defaults on the rental | Serving uses `configs/serving.yaml` everywhere |
| A side branch with the benchmark tool had been left behind | The rental would not have had it | Merged in |

All of this is covered by automated tests: **313 pass** (plus 22 extra checks that need
the PyTorch library, run separately). None of it has run on a GPU yet — that is what the
trial is for.

## 6. The live tracker (how the run is watched)

A small web page runs **on the Spark** and refreshes every 2 seconds. It shows:

- **Lifecycle phase** — which step the run is on (e.g. "waiting for the server").
- **Server logs** — the model server's own messages (loading progress, errors).
- **Hardware** — free memory (the important number on this machine), and GPU usage
  if the locked-down container lets us read it.
- **Training progress** — seconds per step, words (tokens) processed per second, loss.
- **Requests** — each test question's speed and any errors.

You view it from your laptop through an SSH "tunnel" (command in section 8). I can
monitor the same information if I have access to a terminal on the Spark (or you paste
me its output); I cannot reach the machine on my own.

## 7. Before you book — your checklist

1. **Storage:** ask Enverge how much disk you get. You need roughly **200 GB**
   (31 GB + 61 GB model downloads, two large container images, results).
2. **Getting results out:** Enverge storage is **deleted** with the instance. Decide
   how you will copy results to your laptop (normally `scp`, see section 8 step 12)
   and test it with a small file in the first hour.
3. **Deadline:** decide when the rental must stop (e.g. 24 hours after start), and set
   a reminder. Only deleting the instance in Enverge's portal stops billing.
4. **Your yardstick:** decide what "fast enough" means for you before looking at the
   numbers (for example, "one training round on my data must finish within X hours").
5. **GitHub access on the Spark:** the repository is private. Have your GitHub login
   or a deploy key ready; never paste a token into a command.
6. **Optional:** a Hugging Face token (`HF_TOKEN`) makes the big downloads less likely
   to be slowed down. Not required.

## 8. On the day — step by step

Each step says what it does. Exact commands are also in `RENTAL_START_HERE.md`.

1. **Connect** with the SSH command Enverge gives you.
2. **Get the code:**
   `git clone --branch stage-1/live-web-rental-readiness https://github.com/AbdullahRasheed45/cyberai.git && cd cyberai`
3. **Inventory the machine** (installs nothing):
   `python3 scripts/rental/provider_probe.py --out artifacts/enverge_initial_probe.json`
4. **Install the small project tools:** `uv sync --frozen && uv pip install huggingface-hub`
   (if `uv` is missing, install it from https://docs.astral.sh/uv/).
5. **Set where things go** (replace the example paths/time):
   ```bash
   export WORKLOAD_DOMAIN=detection TRAIN_MODE=pilot PILOT_DATA=data/platform_pilot.jsonl
   mkdir -p data && uv run python scripts/rental/make_pilot.py --domain detection --out "$PILOT_DATA"
   export MODEL_PATH=$HOME/models/qwen3-fp8 EVIDENCE_EXPORT_DIR=$HOME/trial-export
   mkdir -p "$MODEL_PATH" "$EVIDENCE_EXPORT_DIR"
   export RENTAL_STOP_UTC='2026-11-20T18:00:00Z'   # your real deadline
   ```
6. **Download the two container images** (big; takes a while):
   `uv run python -c 'import subprocess,yaml; c=yaml.safe_load(open("scripts/rental/FREEZE.yaml")); [subprocess.run(["docker","pull",c[k]],check=True) for k in ("vllm_image","unsloth_image")]'`
7. **Find the working Docker settings (Enverge-specific):**
   `python3 scripts/rental/docker_runtime_setup.py` → must say `"status": "READY"`.
   Then `source artifacts/docker_runtime/docker_env.sh`. If it says `BLOCKED`, stop and
   send me `artifacts/docker_runtime/docker_runtime.json`.
8. **Check what's inside the images:** `timeout 1800 uv run python scripts/rental/collect_image_pins.py`
   then `export FREEZE=artifacts/image_pin_collection/FREEZE.image-versions.yaml`.
   This fills in the exact library versions (they say `FILL` until now — on purpose).
9. **Download the serving model:** `uv run python scripts/rental/materialise_checkpoint.py`,
   then `uv run python scripts/rental/check_preparation.py` (should list no blockers).
10. **Start the tracker** in a second terminal (remember to `source` the docker file
    there too): `uv run python -m rental.live_status --root artifacts --runs runs --port 8765`.
    From your laptop: `ssh -N -L 8765:127.0.0.1:8765 <your Enverge SSH address>`, then open
    http://127.0.0.1:8765.
11. **Run the full trial once** (first terminal):
    ```bash
    export RUN_ID=hardware_s2048_b1
    export TRAIN_MAX_SEQ_LENGTH=2048 TRAIN_MAX_STEPS=30 TRAIN_BATCH_SIZE=1
    export TRAIN_GRAD_ACCUM=1 TRAIN_MEASURE_WARMUP_STEPS=5
    uv run python scripts/rental/track_command.py --out artifacts/tracked_$RUN_ID.json \
      --timeout 21600 -- uv run python -m rental.orchestrate
    ```
    Then the **bf16 comparison** and longer-text training runs (section 8 of
    `RENTAL_START_HERE.md`), each with a new `RUN_ID`.
12. **Copy everything out, then delete the instance.** From your laptop, for example:
    `scp -r <your Enverge SSH address>:~/cyberai/artifacts ./trial_artifacts` and the
    same for `runs` (adapters and training logs). Check the files opened on your laptop.
    Then delete the instance in the Enverge portal and confirm billing stopped.

## 9. What happens during one full run (step 11)

| Phase | Plain meaning | Typical worry |
|---|---|---|
| preflight | Checks it is really a GB10, the images and model files are exactly the pinned ones | A wrong or corrupted download stops the run here — cheap |
| start/wait base | Loads the FP8 model into the server | Can take many minutes; server logs show progress |
| measure | Speed test: single questions, then many at once, short and long texts | Slow results are recorded, not fatal |
| stop base | Shuts the server, checks memory was given back | Memory must return before training |
| train | Trains the add-on in 4-bit QLoRA, then reloads it in a fresh process and checks it | Out-of-memory or library errors show in the tracker log |
| start/wait LoRA | Loads the server again with the trained add-on attached | **Key test**: add-ons on FP8 MoE models are not proven on this hardware; failure here is an important finding, not a bug |
| workload | Asks the add-on model a security task and checks the answer automatically | A wrong answer is fine here — this tests plumbing, not skill |
| export | Packs every result with checksums and copies it to the export folder | Always runs, even after a failure |

## 10. How to read the results

Open these after a run (in `artifacts/run_<RUN_ID>/` and `runs/<RUN_ID>/`):

- `receipt.json` — overall result: `COMPLETED` or which step failed and why.
- `inference_measurements.json` — answering speed: time to first word (`ttft_s`),
  words per second for one user (`decode_tok_s_mean`) and for many at once
  (`aggregate_output_tok_s`), and any failures.
- `train_meta.json` — training speed: **`steady_state_tok_s`** (tokens per second — the
  main number for your QLoRA vs bf16 decision), seconds per step, peak memory,
  and the precision used.
- `reload_result.json` — `PASSED` with `logit_match: exact` (perfect) or
  `kernel_tolerant` (fine; small rounding differences between calculation methods).
- `workload_result.json` — what the trained model answered.
- `*.console.log` — the server's own messages, especially if something failed.

**What a good outcome looks like:** every phase completed; memory released between
phases; training speed you consider acceptable; the add-on loads on the FP8 server.
**A failure is still useful evidence** — it tells you what would go wrong on the
machine you were about to buy. Keep everything.

## 11. What is still open (honestly)

- Nothing has run on a GPU yet. Every fix above is tested offline only.
- Unknown until the trial: whether the add-on can be served on the FP8 MoE model;
  whether 4-bit training works on GB10 with the pinned libraries (bf16 is the
  comparison either way); the exact library versions; real speeds.
- The small training file used in the trial proves the pipeline, not real training
  cost. For a realistic speed forecast, add your own verified training examples.
- Policy questions for you (in `CURRENT_PRODUCT_SPEC.md`): the "park Loop B after two
  failures" rule versus the January deadline; Instruct vs Thinking model comparison.

## 12. GitHub: branches and pull requests

The code is a **stack** of branches, each building on the one before. Review and merge
in this order (each PR's base is the previous branch):

| PR | Branch | What it adds |
|---|---|---|
| #8 | stage-1/foundation → **main** | Typed configs, lint/test setup |
| #11 | gb10-serving → stage-1/foundation | GB10 serving scripts + benchmark tool |
| #10 | stage-1/pre-rental-readiness → gb10-serving | Rental measurement fixes |
| #13 | stage-1/round18-rental-integration → pre-rental-readiness | Verifier, web workflow, rental harness |
| #15 | stage-1/live-web-rental-readiness → round18 | Live web lab, tracker, and all of today's hardening |

You do not need to merge anything to run the trial: the Spark clones the
`stage-1/live-web-rental-readiness` branch directly. Decisions made "for now" are in
`DECISIONS_TO_REVISIT.md` with matching GitHub issues (#16–#19 are new today).

## Glossary

- **GB10 / DGX Spark** — NVIDIA's desktop AI computer; CPU and GPU share 128 GB of memory.
- **Unified memory** — CPU and GPU use the same memory, so "GPU memory used" is read
  from the whole machine.
- **MoE (mixture of experts)** — a model made of many small "experts"; only a few work
  on each word, which makes it fast.
- **Serving** — running the model so it can answer requests (here with **vLLM**).
- **LoRA adapter** — a small trainable add-on; the big model stays frozen.
- **QLoRA (4-bit)** — LoRA training while the frozen model is compressed to 4 bits.
- **bf16 / FP8** — number formats: bf16 is full training quality; FP8 is compressed,
  used here only for serving.
- **Tokens/sec** — roughly words processed per second; the main speed measure.
- **TTFT** — time to first token: how long before the first word appears.
- **Container / Docker** — a sealed box holding exactly the right software versions.
- **Docker-in-Docker / sandbox** — Enverge's setup: your session is itself a container,
  with Docker running inside it.
- **Pinned / digest / commit** — exact fingerprints of an image or model version, so
  nothing changes silently.
