#!/usr/bin/env python3
"""Smoke step 2/2: RELOAD + verify in a FRESH process, ONE resident base.
Round-8: single PEFT loading path (PeftModel.from_pretrained) -> documented
disable_adapter context; verifies identities against train_meta; compares adapter
tensors via canonical keys; adds a real generate() check (#1/#2/#5/#7)."""

from __future__ import annotations


def classify_reload(adapted, reference, base, atol, rtol):
    """Judge reloaded-adapter logits against the training-time reference.

    The saved-vs-reloaded adapter TENSOR comparison is the strict persistence
    check. Logits here come from different kernel paths (Unsloth's patched LoRA
    at train time vs standard PEFT after reload) in bf16, where rounding alone
    can exceed 1e-3. So: exact closeness passes as "exact"; otherwise the reload
    must still pick the trained model's top token AND sit closer to the trained
    reference than the un-adapted base does ("kernel_tolerant", labelled). Anything
    else means the adapter did not come back and fails.
    """
    import torch

    ref_diff = float((adapted - reference).abs().max())
    base_vs_ref = float((base - reference).abs().max())
    if torch.allclose(adapted, reference, atol=atol, rtol=rtol):
        return "exact", ref_diff, base_vs_ref
    if int(adapted.argmax()) == int(reference.argmax()) and ref_diff < base_vs_ref:
        return "kernel_tolerant", ref_diff, base_vs_ref
    return "failed", ref_diff, base_vs_ref


def main():

    import contextlib
    import json
    import os
    import sys
    from pathlib import Path

    import torch

    OUT = os.environ.get("SMOKE_OUT", "out_smoke")

    def save(result):
        # Persist the verdict for the evidence bundle (stdout alone is lost on export).
        with contextlib.suppress(OSError):
            Path(OUT, "reload_result.json").write_text(
                json.dumps(result, indent=2), encoding="utf-8"
            )

    def fail(m):
        result = {"smoke_reload": "FAILED", "reason": m}
        save(result)
        print(json.dumps(result))
        sys.exit(1)

    if not torch.cuda.is_available():
        fail("CPU-only torch")

    ADAPTER = os.path.join(OUT, "adapter")
    ADAPTER_NAME = os.environ.get("SMOKE_ADAPTER_NAME", "smoke")
    ATOL = float(os.environ.get("SMOKE_ATOL", "1e-3"))
    RTOL = float(os.environ.get("SMOKE_RTOL", "1e-3"))
    meta = json.loads(Path(os.path.join(OUT, "train_meta.json")).read_text(encoding="utf-8"))
    MODEL, COMMIT = meta["model"], meta["resolved_commit"]  # reload the SAME commit (#5)
    if os.environ.get("RUN_ID") and meta.get("run_id") != os.environ.get("RUN_ID"):
        fail(
            f"train_meta run_id {meta.get('run_id')!r} "
            f"!= current RUN_ID {os.environ.get('RUN_ID')!r}"
        )
    ref = torch.load(os.path.join(OUT, "reference_probe.pt"))
    probe = ref["probe_ids"].to("cuda")

    import importlib.util

    from peft import PeftModel
    from unsloth import FastModel

    # Reload the base EXACTLY as trained (same precision + kwargs) so logits compare.
    spec = importlib.util.spec_from_file_location(
        "smoke_train", Path(__file__).with_name("smoke_train.py")
    )
    smoke_train = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(smoke_train)
    precision = meta.get("precision", "bf16")  # pre-precision train_meta files were bf16
    sequence_length = meta["training_config"]["max_seq_length"]
    base, tok = FastModel.from_pretrained(
        **smoke_train.base_load_kwargs(
            FastModel.from_pretrained, MODEL, COMMIT, sequence_length, precision, torch
        )
    )
    # identity checks vs training (#5)
    if getattr(tok, "name_or_path", MODEL) != meta["tokenizer_name_or_path"]:
        fail(
            f"tokenizer identity mismatch: {getattr(tok, 'name_or_path', MODEL)} "
            f"!= {meta['tokenizer_name_or_path']}"
        )
    acfg = json.loads(
        Path(os.path.join(ADAPTER, "adapter_config.json")).read_text(encoding="utf-8")
    )
    if acfg.get("base_model_name_or_path") != meta["adapter_base_model"]:
        fail("adapter base_model_name_or_path differs from training metadata")

    # ONE base, single PEFT path with a documented disable_adapter context (#1/#2)
    model = PeftModel.from_pretrained(base, ADAPTER, adapter_name=ADAPTER_NAME)
    if ADAPTER_NAME not in set(model.peft_config):
        fail(f"adapter {ADAPTER_NAME!r} not loaded")
    model.eval()
    with torch.no_grad():
        adapted = model(probe).logits[0, -1].float().cpu()
        with model.disable_adapter():
            base_logits = model(probe).logits[0, -1].float().cpu()

    # saved vs reloaded adapter tensors, canonicalised across names (#1/#7)
    from detection_verifier.adapter_utils import compare_state_dicts

    reloaded = {
        n: p.detach().float().cpu()
        for n, p in model.named_parameters()
        if "lora_" in n and ADAPTER_NAME in n
    }
    ok, detail = compare_state_dicts(ref["adapter_state"], reloaded, atol=ATOL, rtol=RTOL)
    if not ok:
        fail(f"adapter tensor comparison failed: {detail}")

    base_diff = float((adapted - base_logits).abs().max())
    if base_diff == 0.0:
        fail("adapter does not affect inference (base and adapted logits identical)")
    logit_match, ref_diff, base_vs_ref = classify_reload(
        adapted, ref["ref_logits"], base_logits, ATOL, RTOL
    )
    if logit_match == "failed":
        fail(
            f"reloaded logits do not reproduce the trained model: max_diff={ref_diff:.3e}, "
            f"base-vs-reference={base_vs_ref:.3e}, top token "
            f"{int(adapted.argmax())} vs {int(ref['ref_logits'].argmax())}"
        )

    # real local generation (#7)
    with torch.no_grad():
        gen = model.generate(probe, max_new_tokens=8, do_sample=False)
    if gen.shape[1] <= probe.shape[1]:
        fail("generation produced no new tokens")
    text = tok.decode(gen[0], skip_special_tokens=True)

    result = {
        "smoke_reload": "PASSED",
        "run_id": meta.get("run_id"),
        "active_adapter": ADAPTER_NAME,
        "adapter_tensor_check": detail,
        "logit_match": logit_match,
        "reloaded_vs_reference_logits_max_diff": round(ref_diff, 6),
        "base_vs_reference_logits_max_diff": round(base_vs_ref, 6),
        "base_vs_adapted_logits_max_diff": round(base_diff, 6),
        "generated_tokens": int(gen.shape[1] - probe.shape[1]),
        "generation_sample": text[-60:],
        "atol": ATOL,
        "rtol": RTOL,
        "note": "proves adapter LOADS, AFFECTS inference, and GENERATES; "
        "NOT evidence of useful learning (that is the eval harness). "
        "logit_match=kernel_tolerant means bf16 kernel-path differences exceeded "
        "atol/rtol while top token and closeness-to-trained still held.",
    }
    save(result)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
