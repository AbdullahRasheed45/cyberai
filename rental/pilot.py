"""A task-relevant pilot dataset (Astra #5): detection-rule generation, not
ping/pong. Each example pairs (objective + telemetry examples) -> a KNOWN-GOOD
Sigma rule whose target VERIFIES against the fixtures, so the training signal is
real cyber work. Tiny and for plumbing+representative-length, not a learning claim.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import yaml


def build_pilot_examples(fixtures_dir: str) -> list[dict]:
    obj = yaml.safe_load(
        Path(os.path.join(fixtures_dir, "objective.yaml")).read_text(encoding="utf-8")
    )
    good_rule = Path(os.path.join(fixtures_dir, "rules", "good.yml")).read_text(encoding="utf-8")
    present = [
        json.loads(line)
        for line in (Path(fixtures_dir) / "behaviour_present.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    absent = [
        json.loads(line)
        for line in (Path(fixtures_dir) / "behaviour_absent.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    examples = []
    # vary which telemetry examples are shown; target is the same known-good rule
    for i in range(min(len(present), len(absent))):
        shown = {
            "positive_example": present[i].get("CommandLine"),
            "benign_example": absent[i].get("CommandLine"),
        }
        prompt = (
            "Write a Sigma rule (YAML in <rule></rule>) for category process_creation "
            f"detecting this objective:\n{json.dumps(obj['label_space'])}\n"
            f"flag forms {obj['supported_flag_forms']}\nexamples: {json.dumps(shown)}"
        )
        examples.append(
            {
                "messages": [
                    {"role": "user", "content": prompt},
                    {"role": "assistant", "content": f"<rule>\n{good_rule}</rule>"},
                ]
            }
        )
    return examples
