def main():
    from pathlib import Path

    #!/usr/bin/env python3
    """Rental-setup: materialise the declared serving snapshot + manifest (Astra #1).
    Run once with real repo+commit before the trial; needs the hub."""

    import json
    import os
    import sys
    import time

    import yaml

    from rental.snapshot import materialise

    cfg = yaml.safe_load(
        Path(os.environ.get("FREEZE", "scripts/rental/FREEZE.yaml")).read_text(encoding="utf-8")
    )
    repo, commit = cfg["serving_base_repo"], cfg["serving_base_commit"]
    dest = os.environ.get("MODEL_PATH") or sys.exit("set MODEL_PATH (snapshot destination)")
    started = time.monotonic()
    result = {"repo": repo, "commit": commit, "dest": dest, "passed": False}
    output = Path(os.environ.get("ARTIFACT_DIR", "artifacts/model_download"))
    output.mkdir(parents=True, exist_ok=True)
    try:
        man = materialise(repo, commit, dest)
        result.update(
            passed=True,
            files=len(man),
            snapshot_bytes=sum((Path(dest) / name).stat().st_size for name in man),
        )
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        result["download_and_hash_elapsed_s"] = time.monotonic() - started
        result["note"] = (
            "includes cache checks, download and hashing; not measured network throughput"
        )
        (output / "download_result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(
        json.dumps({"materialised": repo + "@" + commit, "files": len(man), "dest": dest}, indent=2)
    )


if __name__ == "__main__":
    main()
