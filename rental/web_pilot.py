from __future__ import annotations

import json
from pathlib import Path

import yaml

from detection_verifier.checker import WEB_REQUEST_SCHEMA, check_rule
from detection_verifier.evaluation import load_split


def _gate_target_generalizes(fixtures_dir: str, good_rule_doc: dict) -> None:
    # Target selection is development only. Public challenge is never acceptance.
    for split_name in ("train", "dev"):
        verdict = check_rule(
            good_rule_doc,
            **{
                "behaviour_present": load_split(fixtures_dir, split_name)["behaviour_present"],
                "behaviour_absent": load_split(fixtures_dir, split_name)["behaviour_absent"],
                "schema": WEB_REQUEST_SCHEMA,
            },
        )
        if verdict.outcome != "VERIFIED":
            raise ValueError(f"target does not verify on {split_name}")


def build_web_pilot_examples(fixtures_dir: str) -> list[dict]:
    obj = yaml.safe_load((Path(fixtures_dir) / "objective.yaml").read_text(encoding="utf-8"))
    good_rule_text = (Path(fixtures_dir) / "rules" / "good.yml").read_text(encoding="utf-8")
    good_rule_doc = yaml.safe_load(good_rule_text)
    _gate_target_generalizes(fixtures_dir, good_rule_doc)

    # Draw shown examples from TRAIN only; target validation uses train/dev.
    train = load_split(fixtures_dir, "train")
    present, absent = train["behaviour_present"], train["behaviour_absent"]
    contract = obj["telemetry_contract"]
    examples = []
    for i in range(min(len(present), len(absent))):
        shown = {
            "positive_example": {k: present[i].get(k) for k in contract["behavioral"]},
            "benign_example": {k: absent[i].get(k) for k in contract["behavioral"]},
        }
        prompt = (
            "Write a Sigma rule (YAML in <rule></rule>) for category "
            f"{contract['category']} detecting this objective:\n"
            f"{json.dumps(obj['label_space'])}\n"
            f"restricted scope: {obj['restricted_scope']}\n"
            f"behavioural fields: {contract['behavioral']}\n"
            f"examples: {json.dumps(shown)}"
        )
        examples.append(
            {
                "messages": [
                    {"role": "user", "content": prompt},
                    {"role": "assistant", "content": f"<rule>\n{good_rule_text}</rule>"},
                ]
            }
        )
    return examples


if __name__ == "__main__":  # pragma: no cover
    import sys

    fx = sys.argv[1] if len(sys.argv) > 1 else "fixtures/web"
    ex = build_web_pilot_examples(fx)
    print(f"built {len(ex)} web pilot examples; train/dev only; no acceptance evaluation")
    print(json.dumps(ex[0], indent=1)[:600])
