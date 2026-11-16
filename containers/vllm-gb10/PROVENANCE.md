# GB10/SM121 serving — compatibility research (2026-11-11)

This records what was actually verified today, with sources, so the choices
in `docker-compose.yml` / `configs/serving.yaml` can be checked rather than
trusted. **None of this has been run on a real GB10 host yet** (see
`docs/PENDING_HARDWARE_CHECKS.md`). CLAUDE.md directive #8 names "NGC/SM121
containers" as the known-good path; this doc is the verification that
directive asked for, and it surfaces real uncertainty the original brief
didn't have in hand.

## Headline finding: GB10/sm_121 is not merged upstream

**vllm-project/vllm#31740** ("feat: Add SM121/GB10 (DGX Spark) Blackwell-class
GPU support") is the PR that would have made vLLM officially recognise
sm_121 (extends `SCALED_MM_ARCHS`/`FP4_ARCHS`/`MLA_ARCHS` to `12.1f`/`12.1a`,
fixing `NotImplementedError: No compiled cutlass_scaled_mm for compute
capability: 121`). **Status: closed, unmerged** (auto-closed stale,
2026-11-01). It never shipped in any vLLM release.
https://github.com/vllm-project/vllm/pull/31740

Consequence: a plain upstream vLLM build's CUTLASS FP8 kernels do **not**
cover sm_121. Community images (eugr, Avarok) exist specifically to patch
around this gap, not out of general enthusiasm.

The PR's own backend-compatibility matrix (author's claim, not independently
reviewed):

| Backend | sm_121 status |
|---|---|
| TRITON_ATTN | **Works — primary attention backend** |
| TRITON_MLA | Works |
| FlashInfer attention | Claimed "works" (SM75–SM121) — author's claim only |
| FlashInfer MLA | SM100-only, falls back to TRITON_MLA |
| CUTLASS MLA | SM100-only |
| FlashMLA Sparse | SM90/100-only |

A reviewer on that PR thread, **eugr** (maintainer of the most-used
community image, see below), reported that FlashInfer's TRT-LLM attention
path (`TllmGenFmhaRunner`) raised "Unsupported architecture" on his GB10
build, and that his build fell back to `TRITON_ATTN`. That is real-world
corroboration, not just the author's claim.

**Decision:** default `attention_backend: "TRITON_ATTN"` in
`configs/serving.yaml`, applied via the `VLLM_ATTENTION_BACKEND` env var
(the mechanism vLLM has used historically for this — no confirmed stable
`--attention-backend` CLI flag was found for the versions in play; verify
against the actual installed image's `vllm serve --help`, which
`scripts/gb10/preflight.sh` captures automatically into the evidence log).

Also directly relevant — **vLLM issue #29424** ("MoE LoRA for quantized
models"), closed "not planned" (2026-05-20), comment from classicsong
(2025-11-26): *"Qwen-30b-a3b-fp8 only works with triton fp8 kernel. It does
not work with CUTLASS kernel."* — same CUTLASS-gap story, for exactly our
model. https://github.com/vllm-project/vllm/issues/29424

## Multi-LoRA + FP8 MoE: explicitly NOT verified — report this, don't paper over it

The task that produced this doc requires reporting unsupported
model/quantisation/LoRA combinations explicitly. Here is the one that
matters most for us:

- Issue #29424's own compatibility table marks FP8 "✅ supported" with
  **`qwen3-30b-a3b-fp8` named as the test model** — i.e. our exact model.
- But the issue was closed "not planned", meaning that table was never
  backed by a merged, maintained implementation.
- A real attempt at the *same family* of problem — LoRA on a quantized MoE
  model (AWQ, not FP8, but the same quantized-MoE LoRA code path) — is
  recorded in the thread (Receiling, 2026-01-07, using
  `QuantTrio/Qwen3-30B-A3B-Thinking-2507-AWQ` + a dummy LoRA adapter):
  **"all garbage outputs."** No resolution is recorded.

**Conclusion:** multi-LoRA serving of the FP8-quantized Qwen3-30B-A3B MoE
model is an **unsupported combination as of 2026-11-11** — not proven
broken, but proven *unverified*, with a documented failure in a closely
related configuration. `configs/serving.yaml` encodes this as
`require_lora_fp8_verified: false`, and `scripts/gb10/render_serve_args.py`
**refuses** to add `--enable-lora`/adapter flags to the FP8 primary model's
serve command unless that flag is explicitly flipped after a real,
hardware-run correctness check (not just "it didn't crash").

The dense bf16 Qwen3-14B fallback has **no such restriction** — ordinary
multi-LoRA on an unquantized model is a mainstream, well-supported vLLM
path, and `require_lora_fp8_verified` does not gate it.

## Candidate images (digests independently verified 2026-11-11 via `docker manifest inspect` / `docker buildx imagetools inspect` from this machine — metadata only, no image pulled/run)

| Image | Arch | Digest (as of 2026-11-11) | Notes |
|---|---|---|---|
| `nvcr.io/nvidia/vllm:26.10-py3` | linux/arm64 | `sha256:ecd885a6fa671552021eb2bef16773110ebfa4eb5e24e4a2831bf0f4808ddfea` | Official NVIDIA NGC, multi-arch, "Latest" tag (published 2026-10-29). Catalog page explicitly names DGX Spark in an OOM troubleshooting note ("clean the memory cache: `sync && echo 3 > /proc/sys/vm/drop_caches`"), so NVIDIA targets this hardware — but the catalog page makes **no explicit sm_121 kernel claim**, and PR #31740 above shows the public sm_121 fix never merged upstream. Whether NGC backports it internally is **unconfirmed**. |
| `eugr/spark-vllm:latest` | linux/arm64 | `sha256:5e59cb7efe08a99b023925a185c971c5a31868d8261b755c33d9911c3b9389aa` | Community (eugr/spark-vllm-docker, MIT, "not affiliated with NVIDIA"), 2.5k GitHub stars, most-referenced path on the NVIDIA DGX Spark developer forum ("vLLM official docker doesn't work on Spark"). Builds vLLM from source with GB10-specific patches (sm_121 routing, FlashInfer B12X variant). Actively maintained (changelog entries through 2026-10). **No fixed version pin on `:latest`** — see "Reproducibility gap" below. |
| `avarok/vllm-dgx-spark:v11` | linux/arm64 | `sha256:246723e9a74163e7828716c1587d6c5208a9cf0dc8d1195cbd33f68234b1024b` | Community (Avarok-Cybersecurity/dgx-vllm). License is **contradictory between the GitHub repo (MIT badge vs an in-README "Apache 2.0" claim) and the HF card (apache-2.0)** — unresolved, flag before any commercial use. NVFP4/Nemotron-focused; **not validated against Qwen3-30B-A3B** in anything fetched. Smaller community (128 stars). |
| `avarok/dgx-vllm-nvfp4-kernel:v22` | linux/arm64 | `sha256:89e92470389f837a6ce4bf6e3b9674e733b2cc0e09b250c32c7d731342c41dd1` | Same project, different tag line; pinned to vLLM `v0.16.0rc2` (commit `3b30e6150`) per its own "software stack" table. Same license caveat as above. |

**Decision:**
- **Primary attempt on the actual GB10 session:** `nvcr.io/nvidia/vllm:26.10-py3` (the official artifact CLAUDE.md directive #8 asks for) — run `scripts/gb10/preflight.sh` first; if it hits the `cutlass_scaled_mm`/sm_121 `NotImplementedError` signature, that confirms the gap applies here too.
- **Documented fallback:** `eugr/spark-vllm:latest`, re-pinned to a specific digest *at the time it's actually used* (not the digest above, which will go stale the moment eugr publishes a new build) — this is the path the community and the PR #31740 thread itself point to as actually working with FP8 MoE models on GB10.
- **Not adopted as primary:** both Avarok tags — unresolved license status and no validation against our model.

### Reproducibility gap this leaves open

`eugr/spark-vllm:latest` is a floating tag with no numbered release visible
in what was fetched (the GitHub repo has a Tags tab and 684 commits on
`main`, but no fetched page showed a release number or a per-build digest
history). **Pinning `latest`'s digest today does not guarantee it is
reproducible later** — if this path is actually used, re-resolve and record
the digest at use time, and prefer `./build-and-copy.sh --use-wheels` (a
documented eugr flag that builds from precompiled wheels, "never compiles
missing wheels") over a silent `docker pull :latest` where possible.

## The CUTE_DSL_ARCH contradiction (flag for a human decision, not resolved here)

`docs/STAGE_0_AND_1_EXACT.md` / CLAUDE.md directive #8 both say: **"DO NOT
set `CUTE_DSL_ARCH=sm_121a` (hangs on GB10)."** That was the best
information available when the brief was written.

eugr's current (2026-10-07 changelog: *"B12X is now part of Flashinfer!"*)
B12X recipes **explicitly set `CUTE_DSL_ARCH=sm_121a`** as part of a newer,
faster MoE kernel path (`B12X_MLA_SM120_UNIFIED=1`, `--moe-backend b12x`).

This is a live, unresolved contradiction between our own prior guidance and
the most current community evidence. **This doc does not resolve it.**
`configs/serving.yaml`'s default path does **not** set `CUTE_DSL_ARCH`,
staying on the conservative/documented-safe side. The B12X path is not
wired into `docker-compose.yml`'s default profile; enabling it requires a
human decision plus a real hardware test, logged as its own entry if taken
(see `DECISIONS_TO_REVISIT.md`).

## Model identity (verified via the public Hugging Face Hub API, 2026-11-11 — `curl https://huggingface.co/api/models/<repo>`, no auth, no model files downloaded)

| | Primary (FP8 MoE) | Dense fallback |
|---|---|---|
| Repo | `Qwen/Qwen3-30B-A3B-Instruct-2507-FP8` | `Qwen/Qwen3-14B` |
| Commit (`sha`) | `5a5a776300a41aaa681dd7ff0106608ef2bc90db` | `40c069824f4251a91eefaf281ebe4c544efd3e18` |
| Last modified | 2025-09-17 | 2025-07-26 |
| License | apache-2.0 | apache-2.0 |
| Type | MoE: 30.5B total / 3.3B active, 128 experts (8 active) | Dense: 14.8B |
| Native context | 262,144 | 32,768 (131,072 via YaRN) |
| Tags confirm | `qwen3_moe`, `fp8` | `qwen3` (no fp8 tag — bf16) |
| Min vLLM (per model card) | `>=0.8.5` | `>=0.8.5` |

**Correction made 2026-11-11:** an earlier version of `configs/serving.yaml`
had `dense_fallback_model: "Qwen/Qwen3-14B-Instruct"` — **this repo does not
exist**. Qwen3's dense 14B line has no separate "-Instruct" variant (unlike
the 30B-A3B MoE line). Fixed to `Qwen/Qwen3-14B`.

## Sources

- https://github.com/vllm-project/vllm/pull/31740 (sm_121 PR, closed unmerged, backend matrix, eugr's FlashInfer-crash comment)
- https://github.com/vllm-project/vllm/issues/29424 (MoE LoRA for quantized models, closed not-planned, FP8/Qwen3-30B-A3B table, garbage-output report)
- https://vllm.ai/blog/2026-06-01-vllm-dgx-spark (vLLM-hosted case-study blog; prefix caching on by default in V1; `--linear-backend`/`--moe-backend` as the stable backend-pinning flags; no sm_121-specific guidance)
- https://catalog.ngc.nvidia.com/orgs/nvidia/containers/vllm (+ `/tags`) — official tag list, dates, DGX Spark OOM note, multi-arch digests
- https://github.com/eugr/spark-vllm-docker (community, MIT, most-referenced on NVIDIA's DGX Spark developer forum)
- https://github.com/Avarok-Cybersecurity/dgx-vllm and https://huggingface.co/Avarok/vllm-dgx-spark (community, license status contradictory between the two pages)
- https://huggingface.co/Qwen/Qwen3-30B-A3B-Instruct-2507-FP8 and https://huggingface.co/Qwen/Qwen3-14B (model cards)
- https://huggingface.co/api/models/Qwen/Qwen3-30B-A3B-Instruct-2507-FP8 and .../Qwen/Qwen3-14B (public HF Hub API — commit SHAs above, fetched directly by this repo's tooling, not quoted from a third party)
- Image digests: `docker manifest inspect <image>` / `docker buildx imagetools inspect --verbose <image>` run directly from this repo's dev machine, 2026-11-11 (metadata only; no image layers pulled)

## What this doc does NOT establish

No claim here has been run against a real GB10 GPU. "Works" above is either
(a) an upstream contributor's unreviewed claim, (b) a third party's forum
report, or (c) absence of evidence against it — never this repo's own
measurement. See `docs/PENDING_HARDWARE_CHECKS.md` for exactly what a real
session must confirm before any of this is cited as settled.
