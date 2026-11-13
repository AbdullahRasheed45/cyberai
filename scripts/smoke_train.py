#!/usr/bin/env python3
"""Smoke step 1/2: TRAIN -> PERSIST (own process). Train/persist/reload/LOCAL-
GENERATE smoke (NO network serving — separate check). Round-8 fixes:
  #2/#5 revision is RESOLVED to an immutable commit BEFORE loading; a moving
        branch is rejected; the resolved commit + identities are persisted so
        reload can verify them.
  #6    verification snapshots live on CPU; the training peak is read before any
        snapshot so it is not contaminated; completed steps = trainer.state.
        global_step; a real training batch + labels are inspected.
  #1/#7 adapter tensors are saved raw-named; the reload step canonicalises names
        and adds a real generate() check.
"""

from __future__ import annotations


def probe_input_ids(tokenizer, messages):
    """Chat-template a probe to an input_ids tensor. transformers v5 returns a
    BatchEncoding (dict) from apply_chat_template(..., return_tensors="pt") where
    v4 returned the tensor; accept both rather than passing a dict to model()."""
    encoded = tokenizer.apply_chat_template(
        messages, add_generation_prompt=True, return_tensors="pt"
    )
    if hasattr(encoded, "keys") and "input_ids" in encoded:
        encoded = encoded["input_ids"]
    return encoded


def verify_router_frozen(named_parameters):
    """Check routing modules without confusing expert gate_proj projections."""
    routers = []
    for name, parameter in named_parameters:
        components = name.lower().split(".")
        if any(part == "gate" or "router" in part or part.endswith("_gate") for part in components):
            routers.append(name)
            if parameter.requires_grad:
                raise ValueError(f"router parameter is trainable: {name}")
    return routers


def main():

    import inspect
    import json
    import os
    import re
    import sys
    import time
    from pathlib import Path

    import torch

    from rental import training_config
    from rental.plan import FreezeInvalid, TrainingBenchmarkConfig

    def fail(m):
        print(json.dumps({"smoke_train": "FAILED", "reason": m}))
        sys.exit(1)

    try:
        BENCH = TrainingBenchmarkConfig.from_env(os.environ)
    except FreezeInvalid as exc:
        fail(str(exc))
    hp_path = os.environ.get("TRAINING_CONFIG", training_config.DEFAULT_PATH)
    try:
        HP = training_config.load(hp_path)
    except training_config.TrainingConfigError as exc:
        fail(str(exc))
    import hashlib

    hp_sha256 = hashlib.sha256(Path(hp_path).read_bytes()).hexdigest()
    if not torch.cuda.is_available():
        fail("CPU-only torch wheel — fix the container")
    if not torch.cuda.is_bf16_supported():
        fail("bf16 unsupported on this device")

    MODEL = os.environ.get("SMOKE_MODEL", "unsloth/Qwen3-30B-A3B")
    REVISION = os.environ.get("SMOKE_REVISION")
    if not REVISION:
        fail("set SMOKE_REVISION (branch or commit) to pin the model")
    if not re.fullmatch(r"[0-9a-f]{40}", REVISION):
        fail("SMOKE_REVISION must be an immutable 40-hex commit")
    OUT = os.environ.get("SMOKE_OUT", "out_smoke")
    ADAPTER = os.path.join(OUT, "adapter")
    RUN_ID = os.environ.get("RUN_ID", "")
    if os.path.isdir(OUT) and os.listdir(OUT):
        fail(
            f"output dir {OUT} already exists and is non-empty "
            "(refusing to reuse; use a fresh RUN_ID)"
        )
    os.makedirs(OUT, exist_ok=True)

    # --- resolve to an immutable commit BEFORE loading (#5) ---
    from huggingface_hub import HfApi

    try:
        COMMIT = HfApi().model_info(MODEL, revision=REVISION).sha
    except Exception as e:
        fail(f"cannot resolve {MODEL}@{REVISION} to a commit: {e}")
    if not re.fullmatch(r"[0-9a-f]{40}", COMMIT or ""):
        fail(f"resolved revision {COMMIT!r} is not an immutable 40-hex commit")

    import peft
    import transformers
    import trl
    import unsloth
    from unsloth import FastModel

    load_started = time.monotonic()
    model, tok = FastModel.from_pretrained(
        model_name=MODEL,
        revision=COMMIT,
        max_seq_length=BENCH.max_seq_length,
        dtype=torch.bfloat16,
        load_in_4bit=False,
        load_in_8bit=False,
        full_finetuning=False,
    )
    torch.cuda.synchronize()
    load_runtime_s = time.monotonic() - load_started

    # assert bf16 (#2): inspect all param dtypes; fp32 only for norm/router/gate/bias
    dtypes = {}
    for n, p in model.named_parameters():
        dtypes[str(p.dtype)] = dtypes.get(str(p.dtype), 0) + 1
        if p.dtype == torch.float16:
            fail(f"unexpected fp16 param {n}")
    if "torch.bfloat16" not in dtypes:
        fail(f"no bf16 params; dtypes={dtypes}")
    bad = [
        n
        for n, p in model.named_parameters()
        if p.dtype != torch.bfloat16
        and not any(k in n.lower() for k in ("norm", "router", "gate", "bias"))
    ]
    if bad:
        fail(f"non-bf16 params outside documented exceptions: {bad[:3]}")

    model = FastModel.get_peft_model(
        model,
        r=HP.lora_rank,
        lora_alpha=HP.lora_alpha,
        lora_dropout=HP.lora_dropout,
        target_modules=list(HP.target_modules),
        use_gradient_checkpointing=HP.gradient_checkpointing,
        random_state=HP.seed,
    )  # router frozen by default (verified below)
    try:
        router_parameters = verify_router_frozen(model.named_parameters())
    except ValueError as exc:
        fail(str(exc))

    def snapshot_cpu(m):  # on CPU so it does not inflate the training peak (#6)
        return {
            n: p.detach().float().cpu().clone()
            for n, p in m.named_parameters()
            if p.requires_grad and "lora" in n
        }

    pre = snapshot_cpu(model)
    if not pre:
        fail("no trainable LoRA tensors")

    tok.padding_side = "left"
    from datasets import Dataset

    MODE = os.environ.get("TRAIN_MODE", "pingpong")
    PILOT = os.environ.get("PILOT_DATA", "")
    if MODE == "pilot":
        if not PILOT or not os.path.isfile(PILOT):
            fail(
                f"TRAIN_MODE=pilot but pilot file {PILOT!r} is missing "
                "(refusing to silently run ping/pong)"
            )
        pilot_bytes = Path(PILOT).read_bytes()
        rows = [
            json.loads(line) for line in pilot_bytes.decode("utf-8").splitlines() if line.strip()
        ]
        if not rows:
            fail(f"pilot file {PILOT!r} is empty/malformed")
        texts = [tok.apply_chat_template(r["messages"], tokenize=False) for r in rows]
        ds = Dataset.from_list([{"text": t} for t in texts])
        tok_lens = sorted(len(tok(t).input_ids) for t in texts)
        meta_dataset = {
            "mode": "pilot",
            "file": os.path.basename(PILOT),
            "sha256": hashlib.sha256(pilot_bytes).hexdigest(),
            "examples": len(rows),
            "token_len_min_median_max": [tok_lens[0], tok_lens[len(tok_lens) // 2], tok_lens[-1]],
        }
    elif MODE == "pingpong":

        def text_of(u, a):
            return tok.apply_chat_template(
                [{"role": "user", "content": u}, {"role": "assistant", "content": a}],
                tokenize=False,
            )

        ds = Dataset.from_list([{"text": text_of(f"ping {i}", f"pong {i}")} for i in range(10)])
        meta_dataset = {
            "mode": "pingpong",
            "examples": 10,
            "note": "plumbing only, NOT a learning signal",
        }
    else:
        fail(f"unknown TRAIN_MODE {MODE!r}")

    from trl import SFTConfig, SFTTrainer

    cfg_ok = set(inspect.signature(SFTConfig.__init__).parameters)
    cfg = dict(
        max_steps=BENCH.max_steps,
        per_device_train_batch_size=BENCH.batch_size,
        gradient_accumulation_steps=BENCH.grad_accum,
        learning_rate=HP.learning_rate,
        lr_scheduler_type=HP.lr_scheduler_type,
        warmup_steps=HP.warmup_steps,
        max_grad_norm=HP.max_grad_norm,
        weight_decay=HP.weight_decay,
        seed=HP.seed,
        packing=HP.packing,
        logging_steps=1,
        bf16=True,
        dataset_text_field="text",
        output_dir=OUT,
        save_strategy="no",  # the adapter is saved explicitly below; no stray checkpoints
        report_to="none",
    )
    seq_key = "max_length" if "max_length" in cfg_ok else "max_seq_length"
    if seq_key not in cfg_ok:
        fail(f"trl {trl.__version__}: no supported explicit sequence-length parameter")
    cfg[seq_key] = BENCH.max_seq_length
    bad = [k for k in cfg if k not in cfg_ok]
    if bad:
        fail(f"trl {trl.__version__} SFTConfig rejects {bad}")
    tr = set(inspect.signature(SFTTrainer.__init__).parameters)
    tok_kw = (
        {"processing_class": tok}
        if "processing_class" in tr
        else (
            {"tokenizer": tok}
            if "tokenizer" in tr
            else fail("SFTTrainer: no tokenizer/processing_class")
        )
    )
    from transformers import TrainerCallback

    class StepMeasurements(TrainerCallback):
        """Optimizer-step timing includes every accumulated microbatch and GPU work."""

        def __init__(self):
            self.step_seconds = []
            self.step_tokens = []
            self.processed_tokens = 0
            self.supervised_tokens = 0
            self.microbatches = 0
            self.sequence_length_histogram = {}

        def on_step_begin(self, args, state, control, **kwargs):
            torch.cuda.synchronize()
            self.step_started = time.monotonic()
            self.tokens_before_step = self.processed_tokens

        def on_log(self, args, state, control, logs=None, **kwargs):
            with Path(OUT, "training_logs.jsonl").open("a", encoding="utf-8") as stream:
                stream.write(
                    json.dumps({"step": int(state.global_step), "metrics": logs or {}}) + "\n"
                )

        def on_step_end(self, args, state, control, **kwargs):
            torch.cuda.synchronize()
            self.step_seconds.append(time.monotonic() - self.step_started)
            self.step_tokens.append(self.processed_tokens - self.tokens_before_step)
            # Preserve completed-step evidence even if a later step/save fails.
            with Path(OUT, "step_measurements.jsonl").open("a", encoding="utf-8") as stream:
                stream.write(
                    json.dumps(
                        {
                            "completed_step": len(self.step_seconds),
                            "seconds": self.step_seconds[-1],
                            "nonpadding_tokens": self.step_tokens[-1],
                            "processed_nonpadding_tokens": self.processed_tokens,
                            "processed_supervised_tokens": self.supervised_tokens,
                            "cuda_allocated_bytes": torch.cuda.memory_allocated(),
                            "cuda_reserved_bytes": torch.cuda.memory_reserved(),
                        }
                    )
                    + "\n"
                )

    measurements = StepMeasurements()

    class MeasuredSFTTrainer(SFTTrainer):
        def training_step(self, model, inputs, *args, **kwargs):
            # Count the actual batches consumed, including repeats/accumulation;
            # corpus size and requested sequence length are not processed tokens.
            mask = inputs.get("attention_mask")
            if mask is None:
                fail("training batch missing attention_mask; actual non-padding tokens unavailable")
            measurements.processed_tokens += int(mask.sum().item())
            labels = inputs.get("labels")
            if labels is None:
                fail("training batch missing supervised labels")
            measurements.supervised_tokens += int((labels != -100).sum().item())
            measurements.microbatches += 1
            for length in mask.sum(dim=-1).detach().cpu().tolist():
                key = str(int(length))
                measurements.sequence_length_histogram[key] = (
                    measurements.sequence_length_histogram.get(key, 0) + 1
                )
            return super().training_step(model, inputs, *args, **kwargs)

    trainer = MeasuredSFTTrainer(
        model=model, train_dataset=ds, args=SFTConfig(**cfg), callbacks=[measurements], **tok_kw
    )

    # inspect a real batch + labels (#6)
    batch = next(iter(trainer.get_train_dataloader()))
    labels = batch.get("labels")
    batch_info = {
        "input_ids_shape": list(batch["input_ids"].shape),
        "has_labels": labels is not None,
        "non_masked_label_tokens": int((labels != -100).sum()) if labels is not None else None,
    }

    torch.cuda.reset_peak_memory_stats()
    res = trainer.train()
    train_peak = round(torch.cuda.max_memory_allocated() / 1e9, 1)  # read BEFORE snapshots (#6)
    train_peak_reserved = round(torch.cuda.max_memory_reserved() / 1e9, 1)
    steps = int(trainer.state.global_step)  # not reconstructed (#6)
    train_secs = float(res.metrics.get("train_runtime", 0.0)) or None
    try:
        verify_router_frozen(model.named_parameters())
    except ValueError as exc:
        fail(str(exc))
    if len(measurements.step_seconds) != steps or measurements.processed_tokens <= 0:
        fail("actual training-step/token instrumentation did not cover the completed run")
    steady_seconds = measurements.step_seconds[BENCH.measure_warmup_steps :]
    steady_tokens = measurements.step_tokens[BENCH.measure_warmup_steps :]
    if not steady_seconds or any(value <= 0 for value in steady_seconds):
        fail("no valid completed steps after measurement warm-up")

    post = snapshot_cpu(model)
    deltas = {n: float((post[n] - pre[n]).abs().max()) for n in post}
    changed = [n for n, d in deltas.items() if d > 0]
    if not changed:
        fail("no adapter tensor changed during training")
    if any(not torch.isfinite(post[n]).all() for n in post):
        fail("non-finite adapter tensor")

    probe = probe_input_ids(tok, [{"role": "user", "content": "ping 3"}]).to("cuda")
    model.eval()
    with torch.no_grad():
        ref_logits = model(probe).logits[0, -1].float().cpu()

    model.save_pretrained(ADAPTER)
    tok.save_pretrained(ADAPTER)
    adapter_cfg = json.loads(
        Path(os.path.join(ADAPTER, "adapter_config.json")).read_text(encoding="utf-8")
    )
    torch.save(
        {"probe_ids": probe.cpu(), "ref_logits": ref_logits, "adapter_state": post},
        os.path.join(OUT, "reference_probe.pt"),
    )

    meta = {
        "smoke_train": "PASSED",
        "run_id": RUN_ID,
        "model": MODEL,
        "requested_revision": REVISION,
        "resolved_commit": COMMIT,
        "tokenizer_name_or_path": getattr(tok, "name_or_path", MODEL),
        "adapter_base_model": adapter_cfg.get("base_model_name_or_path"),
        "device": torch.cuda.get_device_name(0),
        "versions": {
            "torch": torch.__version__,
            "cuda": torch.version.cuda,
            "transformers": transformers.__version__,
            "trl": trl.__version__,
            "peft": peft.__version__,
            "unsloth": unsloth.__version__,
        },
        "param_dtype_histogram": dtypes,
        "trainer_tokenizer_kw": list(tok_kw)[0],
        "dataset": meta_dataset,
        "batch_inspected": batch_info,
        "changed_adapter_tensors": len(changed),
        "frozen_router_parameter_names": router_parameters,
        "max_adapter_delta": round(max(deltas.values()), 6),
        "final_train_loss": round(float(res.training_loss), 4),
        "completed_steps": steps,
        "train_runtime_s": train_secs,
        "training_config": BENCH.__dict__,
        "hyperparameters": HP.as_dict(),
        "hyperparameters_file_sha256": hp_sha256,
        "load_runtime_s": load_runtime_s,
        "processed_nonpadding_tokens": measurements.processed_tokens,
        "processed_supervised_tokens": measurements.supervised_tokens,
        "completed_microbatches": measurements.microbatches,
        "processed_sequence_length_histogram": measurements.sequence_length_histogram,
        "optimizer_step_seconds": measurements.step_seconds,
        "optimizer_step_nonpadding_tokens": measurements.step_tokens,
        "steady_state_seconds_per_step": sum(steady_seconds) / len(steady_seconds),
        "steady_state_processed_tokens": sum(steady_tokens),
        "steady_state_tok_s": sum(steady_tokens) / sum(steady_seconds),
        "seconds_per_step": round(train_secs / steps, 3) if train_secs and steps else None,
        "train_peak_mem_GB": train_peak,
        "train_peak_reserved_mem_GB": train_peak_reserved,
        "notes": "verification snapshots are on CPU (excluded from train peak); smoke "
        "loss-masking != production policy; results measure THIS config and dataset only.",
    }
    Path(os.path.join(OUT, "train_meta.json")).write_text(
        json.dumps(meta, indent=2), encoding="utf-8"
    )
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
