"""Tiny CPU PEFT save/load/disable/generate integration test (Astra #4).

Exercises the REAL adapter plumbing on a randomly-initialised tiny model — no
download, no GPU. Skips cleanly where torch/peft/transformers are absent (e.g.
this sandbox), and runs on any machine with them before the rental.
"""

from __future__ import annotations

import tempfile

import pytest

from detection_verifier.adapter_utils import compare_state_dicts

torch = pytest.importorskip("torch")
peft = pytest.importorskip("peft")
transformers = pytest.importorskip("transformers")


def _tiny_model():
    from transformers import LlamaConfig, LlamaForCausalLM

    cfg = LlamaConfig(
        vocab_size=64,
        hidden_size=32,
        intermediate_size=64,
        num_hidden_layers=2,
        num_attention_heads=4,
        num_key_value_heads=4,
        max_position_embeddings=64,
    )
    return LlamaForCausalLM(cfg)


def test_peft_save_load_disable_generate_roundtrip():
    import copy

    from peft import LoraConfig, PeftModel, get_peft_model

    torch.manual_seed(0)
    base = _tiny_model().eval()
    base_state = copy.deepcopy(base.state_dict())  # preserve the ORIGINAL base (#6)
    lcfg = LoraConfig(r=4, lora_alpha=8, target_modules=["q_proj", "v_proj"], lora_dropout=0.0)
    model = get_peft_model(base, lcfg)
    # make the adapter non-trivial (lora_B inits to zero -> no effect otherwise)
    with torch.no_grad():
        for n, p in model.named_parameters():
            if "lora_B" in n:
                p.normal_()
    saved = {
        n: p.detach().float().clone()
        for n, p in model.named_parameters()
        if p.requires_grad and "lora" in n
    }

    probe = torch.tensor([[1, 2, 3, 4]])
    model.eval()
    with torch.no_grad():
        adapted = model(probe).logits[0, -1]

    with tempfile.TemporaryDirectory() as d:
        model.save_pretrained(d)
        fresh = _tiny_model().eval()
        fresh.load_state_dict(base_state)  # SAME base weights as training (#6)
        reloaded_model = PeftModel.from_pretrained(fresh, d, adapter_name="smoke")
        reloaded_model.eval()
        with torch.no_grad():
            re_adapted = reloaded_model(probe).logits[0, -1]
            with reloaded_model.disable_adapter():
                re_base = reloaded_model(probe).logits[0, -1]
        gen = reloaded_model.generate(probe, max_new_tokens=4, do_sample=False)

    reloaded = {
        n: p.detach().float()
        for n, p in reloaded_model.named_parameters()
        if "lora_" in n and "smoke" in n
    }
    ok, detail = compare_state_dicts(saved, reloaded, atol=1e-4, rtol=1e-4)
    assert ok, detail  # save==reload across adapter names
    assert torch.allclose(adapted, re_adapted, atol=1e-4)  # reload reproduces training-time output
    assert not torch.allclose(re_adapted, re_base, atol=1e-4)  # adapter actually affects inference
    assert gen.shape[1] > probe.shape[1]  # generation produced tokens
