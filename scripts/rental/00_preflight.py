def main():
    from pathlib import Path

    #!/usr/bin/env python3
    """Preflight: validate the freeze AND the real environment (Astra #1/#3) — GB10/
    ARM, image digests present, the selected images' ACTUAL deps importable, and the
    LOCAL serving checkpoint verified against the declared serving identity (an
    attestation checkbox is not checkpoint verification). Fails closed; writes to the
    per-run artifact dir."""

    import json
    import os
    import subprocess
    import sys

    import yaml

    from rental.checkpoint import verify_local_checkpoint
    from rental.freeze import validate_freeze, validate_lineage
    from rental.paths import artifact_dir
    from rental.snapshot import MANIFEST_NAME, verify_against_manifest

    def sh(c):
        try:
            return subprocess.check_output(
                c, shell=True, text=True, stderr=subprocess.DEVNULL
            ).strip()
        except Exception:
            return None

    def fail(errs):
        os.makedirs(artifact_dir(), exist_ok=True)
        Path(os.path.join(artifact_dir(), "preflight.json")).write_text(
            json.dumps({"preflight": "FAILED", "errors": errs}, indent=2), encoding="utf-8"
        )
        print(json.dumps({"preflight": "FAILED", "errors": errs}, indent=2))
        sys.exit(1)

    cfg = yaml.safe_load(
        Path(os.environ.get("FREEZE", "scripts/rental/FREEZE.yaml")).read_text(encoding="utf-8")
    )
    errs = validate_freeze(cfg)
    errs += validate_lineage(
        cfg.get("tokenizer_identity", ""),
        cfg.get("trainable_base_repo", ""),
        cfg.get("trainable_base_commit", ""),
    )

    # images present by EXACT digest
    for key in ("vllm_image", "unsloth_image"):
        img = cfg.get(key, "")
        if img and "@sha256:" in img and sh(f"docker image inspect {img}") is None:
            errs.append(f"{key} absent or digest mismatch locally: {img}")

    # accelerator probe inside the pinned images (GPU config, versions, CUDA, bf16).
    # Robust to entrypoint banners: the probe prints a MARKER-delimited JSON line; we
    # extract that line, never json.loads() of all stdout. Each image is parsed and
    # compared to pins SEPARATELY (no dict-merge version clobbering).
    from rental.probe import compare_versions, extract_probe, probe_argv

    probe, probe_logs = {}, {}
    if not errs:
        pins = {
            d.split("==")[0].lower(): d.split("==")[1]
            for d in (cfg.get("dependencies") or [])
            if "==" in d
        }
        specs = {
            "vllm_image": (cfg["vllm_image"], ["vllm", "torch"]),
            "unsloth_image": (
                cfg["unsloth_image"],
                ["torch", "transformers", "unsloth", "trl", "peft", "bitsandbytes"],
            ),
        }
        for key, (img, comps) in specs.items():
            r = subprocess.run(probe_argv(img), capture_output=True, text=True)
            raw = (r.stdout or "") + (r.stderr or "")
            probe_logs[key] = raw  # keep diagnostics/banners
            parsed = extract_probe(raw)
            if parsed is None:
                errs.append(f"{key}: accelerator probe produced no parseable result")
                continue
            probe[key] = parsed
            if not parsed.get("cuda"):
                errs.append(f"{key}: CUDA not available")
            if key == "unsloth_image" and not parsed.get("bf16"):
                errs.append(f"{key}: bf16 not supported on device")
            errs += [
                f"{key}: {e}" for e in compare_versions(parsed.get("versions", {}), pins, comps)
            ]

    # LOCAL serving checkpoint verified against the declared serving identity
    mp = os.environ.get("MODEL_PATH")
    if not mp:
        errs.append("MODEL_PATH not set (cannot verify local serving checkpoint)")
    else:
        errs += verify_local_checkpoint(mp, cfg.get("serving_quantisation", ""))
        # EXACT identity: require + enforce the materialised snapshot manifest
        man_path = os.path.join(mp, MANIFEST_NAME)
        if not os.path.isfile(man_path):
            errs.append(f"{MANIFEST_NAME} not found in {mp} (run materialise_checkpoint.py first)")
        else:
            man = json.loads(Path(man_path).read_text(encoding="utf-8"))
            if man.get("repo") != cfg.get("serving_base_repo"):
                errs.append(
                    f"snapshot repo {man.get('repo')!r} != serving_base_repo "
                    f"{cfg.get('serving_base_repo')!r}"
                )
            if man.get("commit") != cfg.get("serving_base_commit"):
                errs.append(
                    f"snapshot commit {man.get('commit')!r} != serving_base_commit "
                    f"{cfg.get('serving_base_commit')!r}"
                )
            errs += verify_against_manifest(mp, man.get("manifest", {}))
            os.makedirs(artifact_dir(), exist_ok=True)  # preserve manifest in the evidence bundle
            Path(os.path.join(artifact_dir(), MANIFEST_NAME)).write_text(
                json.dumps(man), encoding="utf-8"
            )

    gpu = sh("nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader")
    if not gpu or "GB10" not in (gpu or ""):
        errs.append(f"GB10 not detected (nvidia-smi: {gpu!r})")
    if sh("uname -m") != "aarch64":
        errs.append("not aarch64")

    if errs:
        fail(errs)
    report = {
        "preflight": "PASSED",
        "gpu": gpu,
        "arch": "aarch64",
        "trainable_base": f"{cfg['trainable_base_repo']}@{cfg['trainable_base_commit']}",
        "serving_base": f"{cfg['serving_base_repo']}@{cfg['serving_base_commit']}",
        "serving_quant": cfg["serving_quantisation"],
        "serving_provenance": cfg["serving_quant_provenance"],
        "model_path": mp,
        "accelerator_probe": probe,
        "probe_logs": probe_logs,
    }
    os.makedirs(artifact_dir(), exist_ok=True)
    Path(os.path.join(artifact_dir(), "preflight.json")).write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
