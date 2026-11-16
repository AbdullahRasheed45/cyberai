#!/usr/bin/env python3
"""Run Qwen only through the bounded, owned-web reference workflow.

This is a rental-time integration measurement, not acceptance evaluation and
not proof of a learning gain. The model proposes JSON; deterministic tools and
verifiers decide the result.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

from lab.web_workflow.reference import run_reference_case
from lab.web_workflow.store import TrajectoryStore
from rental.clients import InferenceError, parse_completion
from rental.offensive_web import action_prompt, parse_action_plan
from rental.paths import artifact_dir


def main() -> None:
    started = time.monotonic()
    artifact = {
        "task": "owned_web_offensive_workflow",
        "kind": "rental_integration_smoke",
        "scope": "symbolic_owned_lab_only",
        "acceptance_data_read": False,
        "model_usage": {"prompt_tokens": None, "completion_tokens": None},
        "action_count": 0,
        "failure_category": None,
    }
    request = urllib.request.Request(
        os.environ["VLLM_URL"],
        data=json.dumps(
            {
                "model": os.environ.get("SERVED_MODEL", "smoke"),
                "messages": [{"role": "user", "content": action_prompt()}],
                "max_tokens": 400,
                "temperature": 0,
            }
        ).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        try:
            with urllib.request.urlopen(request, timeout=300) as response:
                parsed = parse_completion(response.status, response.read().decode())
        except urllib.error.HTTPError as exc:
            raise InferenceError(f"http {exc.code}: {exc.read().decode()[:300]}") from exc
        artifact["model_usage"] = {
            "prompt_tokens": parsed["prompt_tokens"],
            "completion_tokens": parsed["completion_tokens"],
        }
        plan = parse_action_plan(parsed["content"])
        artifact["action_count"] = len(plan)
        record = run_reference_case("success", plan=plan)
        artifact.update(
            offensive_verdict=record.offensive_verdict,
            defensive_verdict=record.defensive_verdict,
            task_success=record.training_eligible,
            failure_category=None if record.training_eligible else "WORKFLOW_NOT_VERIFIED",
        )
        output = Path(artifact_dir())
        TrajectoryStore(output / "web_offensive_trajectories.jsonl").append(record)
    except InferenceError as exc:
        artifact.update(task_success=False, failure_category="SERVED_ERROR", error=str(exc))
    except ValueError as exc:
        artifact.update(task_success=False, failure_category="MODEL_PLAN_REJECTED", error=str(exc))
    finally:
        artifact["runtime_s"] = round(time.monotonic() - started, 4)
        output = Path(artifact_dir())
        output.mkdir(parents=True, exist_ok=True)
        (output / "web_offensive_workflow_result.json").write_text(
            json.dumps(artifact, indent=2), encoding="utf-8"
        )
    print(json.dumps(artifact, indent=2))


if __name__ == "__main__":
    main()
