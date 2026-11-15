# Brief v1.2 — Verified Corrections + Software Setup Appendix

**Date:** 2026-11-10
**Status:** Layers on top of `MASTER_PROJECT_BRIEF_v1.1.md`. Incorporates live verification (2026-11-10) of the three BLOCKER open questions (§19). Apply these corrections to the brief; the appendix is the known-good setup path so the build points at working configurations instead of discovering failures the hard way.

---

## Part A — The three BLOCKERs are RESOLVED (verified on real GB10 hardware)

All three Stage-0 BLOCKER open questions are now answered **yes** against current public evidence from people running this exact hardware. They move from "unknown, could sink the model strategy" to "known-working, needs the right container + setup." **The model strategy (Qwen3-30B-A3B MoE, FP8 serving, Unsloth fine-tuning) stands.**

### BLOCKER #1 — vLLM serves Qwen3-30B-A3B at FP8 on GB10 → CONFIRMED
- Works today on real DGX Spark (GB10, SM121, ARM64) via **community/NVIDIA Docker images with prebuilt SM121 kernels** — NOT stock pip vLLM.
- Measured: ~289–313 tok/s batched under vLLM; ~44–85 tok/s single-stream; FP8 ≈ doubles throughput vs BF16.
- **Correction to §4.1/§16:** name the known-good path explicitly (see Appendix B1). Stock vLLM out-of-the-box will not have the SM121 kernels.

### BLOCKER #2 — Unsloth fine-tunes the MoE on ARM/GB10 → CONFIRMED (with setup friction)
- Unsloth officially supports Qwen3 MoE (30B-A3B, 235B-A22B) via `FastModel` (not `FastLanguageModel`). LoRA/QLoRA runs verified on real GB10 hardware (loss decreases, loadable adapter + metadata written, eval/export complete).
- **Must run inside the NVIDIA NGC container with aarch64 transformers patches.** A bare-metal `pip`/`uv` install on aarch64 **silently resolves to CPU-only torch** and aborts with "cannot find any torch accelerator." This is the single biggest setup trap — see Appendix B2.
- **Correction to §7.7:** "freeze the router" is **Unsloth's DEFAULT** (router-layer fine-tuning disabled by default), not something we must implement. Our standing policy = the out-of-the-box behaviour. Less work than v1.1 implied.

### BLOCKER #3 — Real measured throughput → REFERENCE NUMBERS in hand (still verify your own unit)
Reference figures from real GB10 units (yours still needs its own Stage-1 measurement, but these de-risk planning):

| Metric | Measured on real GB10 |
|---|---|
| Qwen3-30B-A3B decode, single stream (FP8) | ~44–85 tok/s |
| Qwen3-30B-A3B decode, **batched (vLLM)** | **~289–313 tok/s** |
| Decode vs context depth | 60 → 53 → 44 → 37 tok/s at d=4K/8K/16K |
| LoRA training, **stock** Unsloth (25k×3) | ~451 tok/s → **~5 days** |
| LoRA training, **optimised** (25k×3) | ~3,461 tok/s → **~20 hours** |

**Planning consequences:**
- Batched ~300 tok/s confirms the swarm thesis (single-stream slow, batching recovers it).
- **Training optimisation is NOT optional:** stock-vs-tuned is ~5 days vs ~20 hours per LoRA round. The 3-day cadence target (§7.6) is achievable **only** on the optimised training path → invest in the Unsloth speedup early (Stage 1).

**Honest caveat:** these are community/vendor-container results, not a controlled test on your unit; GB10 software moves fast, so re-confirm exact container tags at build time. The *capability* questions are answered; the *exact versions* are a Stage-1 pin.

---

## Part B — Verified software setup appendix (the known-good path)

> **Golden rule for the GB10/ARM64 platform: run everything inside the right NVIDIA NGC / community container. Never bare-metal pip install torch on aarch64 — it silently falls back to CPU-only and fails.**

### B1 — Serving (vLLM) on GB10
- Use a **SM121-kernel container**, one of:
  - NVIDIA NGC vLLM container (`nvcr.io/nvidia/vllm:<tag>`) — pin the tag at build time.
  - Community images with prebuilt SM121 wheels: `avarok/dgx-vllm` / `eugr/spark-vllm-docker` (verify current tag).
- Model: `Qwen/Qwen3-30B-A3B-Instruct-...-FP8` (FP8 variant).
- Key serve flags (confirm against the container's vLLM version): `--gpu-memory-utilization 0.85`, `--max-model-len 32768`, continuous batching + prefix caching on, multi-LoRA enabled.
- **Do NOT** set `CUTE_DSL_ARCH=sm_121a` (reported to cause hangs on GB10).
- NVFP4 (optional, later): landed in vLLM 0.12.0, Blackwell/SM121 MoE kernels via FlashInfer/Marlin — only adopt if your benchmark shows quality holds (§5.2). FP8 is the Phase-1 default.

### B2 — Fine-tuning (Unsloth) on GB10
- Run inside the **NVIDIA NGC PyTorch/Unsloth container** (validated against NGC's torch 2.10 on CUDA 13.0). Flash Attention 2 is available natively in the NVIDIA PyTorch container on GB10.
- Apply the **three aarch64 transformers patches** required before any model loads (bypass the kernel fetch that doesn't exist for GB10's platform).
- Use `FastModel` (NOT `FastLanguageModel`) for the MoE:
  ```python
  from unsloth import FastModel
  model, tokenizer = FastModel.from_pretrained(
      model_name="unsloth/Qwen3-30B-A3B",
      max_seq_length=2048,          # raise for long-context hard tasks
      load_in_4bit=True,            # QLoRA; load_in_8bit=True or full_finetuning=True also supported
      full_finetuning=False,
  )
  # Router-layer fine-tuning is DISABLED BY DEFAULT (= our frozen-router policy, §7.7). No extra work.
  ```
- **Trap to avoid:** verify `torch` is the CUDA aarch64 build, not `torch==2.10.0+cpu`. If a run aborts with "cannot find any torch accelerator," you are on the CPU wheel — fix the container/env, do not proceed.
- **UMA note:** on unified-memory OOM, flush the page cache and retry (DGX Spark shares CPU/GPU memory — §2.2 bottleneck #2).
- **Optimisation (do early):** the stock→optimised path is ~5 days→~20 hours per LoRA round. Apply the documented GB10 Unsloth speedups (sequence packing, the lossless-speedup kernels/config) so the 3-day cadence is reachable.

### B3 — Versions to pin at build time (Stage 0/1)
| Component | Known-good reference (verify current) |
|---|---|
| Driver / CUDA | 580.x / CUDA 13.0+ (DGX OS 7.x) |
| vLLM | SM121 container build (e.g. 0.26.x+ with SM121 kernels) |
| transformers | the exact version the Unsloth container pins (patched for aarch64) |
| unsloth / unsloth_zoo | latest (MoE via FastModel) |
| bitsandbytes | aarch64 wheel (>=0.49.0) |
| torch | CUDA aarch64 build (NOT +cpu) |

### B4 — The three corrections to apply to the brief text
1. **§4.1 / §16 (serving):** "vLLM at FP8 on GB10 via a named SM121 container (NVIDIA NGC / avarok / eugr), not stock pip vLLM."
2. **§7.7 / §16 (training):** "Unsloth MoE fine-tune confirmed on GB10 **inside the NGC container with aarch64 transformers patches**; bare-metal pip silently fails on CPU-only torch. Router-freeze is Unsloth's **default** (`FastModel`), not custom work."
3. **§2.2 / §7.6 (throughput/cadence):** "Reference GB10 numbers: ~300 tok/s batched serving; LoRA round ~5 days stock → ~20 hours optimised. The 3-day cadence requires the optimised training path — invest in the Unsloth speedup in Stage 1."

### B5 — Updated §19 open-question status
- #1 vLLM MoE+FP8 on GB10 → **RESOLVED** (named container; pin tag at build).
- #2 Unsloth MoE on ARM → **RESOLVED** (NGC container + aarch64 patches; FastModel).
- #3 Real throughput → **Reference numbers in hand; still measure your own unit in Stage 1** (remains IMPORTANT, no longer a strategy-sinking BLOCKER).
- #6 Flash Attention ARM/Blackwell → **RESOLVED** (native in the NVIDIA PyTorch container on GB10).

Net: the Stage-0 BLOCKERs that could have forced a model-strategy change are cleared. Stage 1 still *measures* on your unit, but it is now confirming a known-good path, not exploring an unknown one.
