def main():
    from pathlib import Path

    #!/usr/bin/env python3
    """Rental-setup: materialise the declared serving snapshot + manifest (Astra #1).
    Run once with real repo+commit before the trial; needs the hub."""

    import json
    import os
    import sys

    import yaml

    from rental.snapshot import materialise

    cfg = yaml.safe_load(
        Path(os.environ.get("FREEZE", "scripts/rental/FREEZE.yaml")).read_text(encoding="utf-8")
    )
    repo, commit = cfg["serving_base_repo"], cfg["serving_base_commit"]
    dest = os.environ.get("MODEL_PATH") or sys.exit("set MODEL_PATH (snapshot destination)")
    man = materialise(repo, commit, dest)
    print(
        json.dumps({"materialised": repo + "@" + commit, "files": len(man), "dest": dest}, indent=2)
    )


if __name__ == "__main__":
    main()
