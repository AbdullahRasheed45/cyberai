#!/usr/bin/env python3
"""Representative workload — an INTEGRATION SMOKE (NOT a learning benchmark; the
adapter is ping/pong-trained). It exercises model -> rule -> untrusted scorer and
preserves full artifacts with DISTINCT outcome categories (Astra #7).

A base-vs-adapter comparison on the same tasks is meaningful ONLY with genuinely
task-relevant training data, so it is deliberately omitted here.
"""

import json
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

import yaml

from detection_verifier.acceptance import (
    CandidateError,
    CandidateTimeout,
    EvaluationInputError,
    ResultTooLarge,
    evaluate_untrusted_candidate,
)
from rental.clients import InferenceError, parse_completion
from rental.paths import artifact_dir


def main():
    URL = os.environ["VLLM_URL"]
    MODEL = os.environ.get("SERVED_MODEL", "smoke")
    DOMAIN = os.environ.get("WORKLOAD_DOMAIN", "web")
    if DOMAIN not in ("web", "detection"):
        raise ValueError("WORKLOAD_DOMAIN must be web or detection")
    FX = Path("fixtures") / DOMAIN
    from detection_verifier.checker import PROCESS_CREATION_SCHEMA, WEB_REQUEST_SCHEMA

    SCHEMA = WEB_REQUEST_SCHEMA if DOMAIN == "web" else PROCESS_CREATION_SCHEMA
    if DOMAIN == "web":
        FX = FX / "dev"

    def _j(n):
        return [
            json.loads(line)
            for line in (FX / n).read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    obj = yaml.safe_load(
        (FX.parent / "objective.yaml" if DOMAIN == "web" else FX / "objective.yaml").read_text(
            encoding="utf-8"
        )
    )
    pres, absent, oos = (
        _j("behaviour_present.jsonl"),
        _j("behaviour_absent.jsonl"),
        _j("out_of_scope.jsonl"),
    )

    prompt = (
        f"Output ONLY a Sigma YAML rule between <rule> and </rule> for {SCHEMA.category}.\n"
        f"Objective: {json.dumps(obj['label_space'])}\n"
        f"Allowed fields: {sorted(SCHEMA.all)}\n"
        "This is a development integration smoke, not an acceptance evaluation."
    )

    t0 = time.monotonic()
    req = urllib.request.Request(
        URL,
        data=json.dumps(
            {
                "model": MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 400,
                "temperature": 0,
            }
        ).encode(),
        headers={"Content-Type": "application/json"},
    )
    artifact = {
        "task": "generate_detection_rule",
        "kind": "integration_smoke",
        "domain": DOMAIN,
        "prompt": prompt,
    }
    try:
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                parsed = parse_completion(r.status, r.read().decode())
        except urllib.error.HTTPError as he:
            raise InferenceError(f"http {he.code}: {he.read().decode()[:300]}") from he
        artifact["raw_response"] = parsed["content"]  # full, untruncated
        m = re.search(r"<rule>(.*?)</rule>", parsed["content"], re.S)
        if not m:
            artifact["outcome"] = "UNPARSEABLE_NO_RULE_BLOCK"
        else:
            rule = yaml.safe_load(m.group(1))
            v = evaluate_untrusted_candidate(
                rule, pres, absent, out_of_scope=oos, schema=SCHEMA, timeout_s=10.0
            )
            artifact["outcome"] = f"VERDICT_{v.outcome}"
            artifact["metrics"] = {
                "coverage": v.metrics.coverage,
                "fp": v.metrics.fp,
                "reasons": v.metrics.reasons,
            }
    except InferenceError as e:
        artifact["outcome"] = "SERVED_ERROR"
        artifact["error"] = str(e)
    except yaml.YAMLError as e:
        artifact["outcome"] = "UNPARSEABLE_YAML"
        artifact["error"] = str(e)
    except EvaluationInputError as e:
        artifact["outcome"] = "OPERATOR_INPUT_ERROR"
        artifact["error"] = str(e)
    except CandidateTimeout as e:
        artifact["outcome"] = "CANDIDATE_TIMEOUT"
        artifact["error"] = str(e)
    except (CandidateError, ResultTooLarge) as e:
        artifact["outcome"] = "CANDIDATE_ERROR"
        artifact["error"] = str(e)
    artifact["complete_runtime_s"] = round(time.monotonic() - t0, 2)
    os.makedirs(artifact_dir(), exist_ok=True)
    (Path(artifact_dir()) / "workload_result.json").write_text(
        json.dumps(artifact, indent=2), encoding="utf-8"
    )
    print(json.dumps({k: v for k, v in artifact.items() if k != "raw_response"}, indent=2))


if __name__ == "__main__":
    main()
