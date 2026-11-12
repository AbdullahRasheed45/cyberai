import json
import shutil
from pathlib import Path

import pytest
import yaml

from detection_verifier.checker import WEB_REQUEST_SCHEMA, EvaluationInputError, check_rule

WEB = Path(__file__).resolve().parents[1] / "fixtures" / "web"


def test_missing_payload_observation_is_not_a_clean_negative():
    rule = yaml.safe_load((WEB / "rules/good.yml").read_text(encoding="utf-8"))
    positive = json.loads(
        (WEB / "train/behaviour_present.jsonl").read_text(encoding="utf-8").splitlines()[0]
    )
    with pytest.raises(EvaluationInputError, match="QueryString|Body"):
        check_rule(
            rule, [positive], [{"Method": "POST", "UriPath": "/search"}], schema=WEB_REQUEST_SCHEMA
        )


def test_training_export_does_not_read_challenge_data(tmp_path):
    from rental.web_pilot import build_web_pilot_examples

    target = tmp_path / "web"
    shutil.copytree(WEB, target)
    for name in ("heldout", "challenge"):
        shutil.rmtree(target / name, ignore_errors=True)
    assert build_web_pilot_examples(str(target))
