def main():
    from pathlib import Path

    #!/usr/bin/env python3
    """Export (Astra #2): hashed EVIDENCE bundle (incl. orchestration.json) +
    inference artifacts, from the PER-RUN dir so stale data can't leak into a trial.
    Hashes recomputed from archived bytes; status persisted; nonzero exit on failure."""

    import json
    import os
    import sys

    from rental.paths import artifact_dir
    from rental.report import (
        arcname,
        build_manifest,
        copy_verified_bundle,
        verify_archive,
        write_archive,
    )

    adir = artifact_dir()
    os.makedirs(adir, exist_ok=True)
    out_dir = os.environ.get("SMOKE_OUT", "out_smoke")
    evidence = [
        os.path.join(adir, "preflight.json"),
        os.path.join(adir, "inference_measurements.json"),
        os.path.join(adir, "workload_result.json"),
        os.path.join(
            adir, "orchestration.json"
        ),  # phase log, real commands, resolved config, releases
        os.path.join(out_dir, "train_meta.json"),
        os.environ.get("FREEZE", "scripts/rental/FREEZE.yaml"),
    ]
    # Optional evidence: included when the phase that produces it ran. Serving
    # console logs are the only record of vLLM startup/kernel errors after `rm -f`.
    optional = [
        os.path.join(adir, "web_offensive_trajectories.jsonl"),
        os.path.join(adir, "phase.json"),
        os.path.join(adir, "SNAPSHOT_MANIFEST.json"),
        os.path.join(adir, "cyberai_serve_base.console.log"),
        os.path.join(adir, "cyberai_serve_lora.console.log"),
        os.path.join(out_dir, "step_measurements.jsonl"),
        os.path.join(out_dir, "training_logs.jsonl"),
        os.path.join(out_dir, "reload_result.json"),
    ]
    evidence += [path for path in optional if os.path.isfile(path)]
    inference_artifacts = [
        os.path.join(out_dir, "adapter", "adapter_config.json"),
        os.path.join(out_dir, "adapter", "adapter_model.safetensors"),
    ]
    man = build_manifest(evidence, inference_artifacts)
    present = {**man["evidence"]["present"], **man["inference_artifacts"]["present"]}
    tar = os.path.join(adir, f"bundle_{os.path.basename(adir)}.tar.gz")
    write_archive(tar, list(present), {"MANIFEST.json": json.dumps(man, indent=2).encode()})
    ok, mism = verify_archive(tar, {arcname(p): h for p, h in present.items()})
    out = {
        "export": tar,
        "verified_against_archived_hashes": ok,
        "verify_mismatches": mism,
        "evidence_complete": man["evidence_complete"],
        "missing_evidence": man["evidence"]["missing"],
        "missing_inference_artifacts": man["inference_artifacts"]["missing"],
        "label": "evidence bundle + inference artifacts (adapter = inference/fresh-optimiser "
        "restart, NOT faithful training resume)",
    }
    destination = os.environ.get("EVIDENCE_EXPORT_DIR")
    if destination:
        try:
            out["durable_copy"] = copy_verified_bundle(tar, destination)
        except (OSError, ValueError) as exc:
            out["durable_copy"] = {"error": str(exc)}
            ok = False
    Path(os.path.join(adir, "export_result.json")).write_text(
        json.dumps(out, indent=2), encoding="utf-8"
    )
    print(json.dumps(out, indent=2))
    complete = ok and man["evidence_complete"] and not man["inference_artifacts"]["missing"]
    sys.exit(0 if complete else 2)


if __name__ == "__main__":
    main()
