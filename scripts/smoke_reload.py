#!/usr/bin/env python3
"""Smoke step 2/2: RELOAD + verify in a FRESH process, ONE resident base.
Round-8: single PEFT loading path (PeftModel.from_pretrained) -> documented
disable_adapter context; verifies identities against train_meta; compares adapter
tensors via canonical keys; adds a real generate() check (#1/#2/#5/#7)."""

from __future__ import annotations


def main():

    import json
    import os
    import sys
    from pathlib import Path

    import torch

    def fail(m):
        print(json.dumps({"smoke_reload": "FAILED", "reason": m}))
        sys.exit(1)

    if not torch.cuda.is_available():
        fail("CPU-only torch")

    OUT = os.environ.get("SMOKE_OUT", "out_smoke")
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

    from peft import PeftModel
    from unsloth import FastModel

    sequence_length = meta["training_config"]["max_seq_length"]
    base, tok = FastModel.from_pretrained(
        model_name=MODEL,
        revision=COMMIT,
        max_seq_length=sequence_length,
        dtype=torch.bfloat16,
        load_in_4bit=False,
        full_finetuning=False,
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

    ref_diff = float((adapted - ref["ref_logits"]).abs().max())
    base_diff = float((adapted - base_logits).abs().max())
    if not torch.allclose(adapted, ref["ref_logits"], atol=ATOL, rtol=RTOL):
        fail(f"reloaded logits != training reference (max_diff={ref_diff:.2e})")
    if base_diff <= ATOL:
        fail(f"adapter does not affect inference (base==adapted, max_diff={base_diff:.2e})")

    # real local generation (#7)
    with torch.no_grad():
        gen = model.generate(probe, max_new_tokens=8, do_sample=False)
    if gen.shape[1] <= probe.shape[1]:
        fail("generation produced no new tokens")
    text = tok.decode(gen[0], skip_special_tokens=True)

    print(
        json.dumps(
            {
                "smoke_reload": "PASSED",
                "active_adapter": ADAPTER_NAME,
                "adapter_tensor_check": detail,
                "reloaded_vs_reference_logits_max_diff": round(ref_diff, 6),
                "base_vs_adapted_logits_max_diff": round(base_diff, 6),
                "generated_tokens": int(gen.shape[1] - probe.shape[1]),
                "generation_sample": text[-60:],
                "atol": ATOL,
                "rtol": RTOL,
                "note": "proves adapter LOADS, AFFECTS inference, and GENERATES; "
                "NOT evidence of useful learning (that is the eval harness).",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
