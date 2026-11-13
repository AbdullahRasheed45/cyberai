import pytest

from lab.web_workflow.live import LiveLab


@pytest.mark.parametrize(
    "case,expected",
    [
        ("success", "VERIFIED"),
        ("failed", "NOT_VERIFIED"),
        ("pre_satisfied", "UNVERIFIABLE_PRE_SATISFIED"),
        ("patched_control", "NOT_VERIFIED"),
    ],
)
def test_real_http_boundary_and_independent_audit(case, expected, tmp_path):
    with LiveLab(tmp_path / "lab.sqlite", case) as lab:
        before = lab.snapshot()
        result = lab.request("other" if case != "failed" else "owner")
        assert lab.verify(before, result) == expected
        if expected == "VERIFIED":
            lab.patch()
            assert lab.request("other")["status"] == 403
            assert lab.request("owner")["status"] == 200
            assert lab.health()


def test_reset_removes_previous_success_and_patch(tmp_path):
    with LiveLab(tmp_path / "lab.sqlite", "success") as lab:
        before = lab.snapshot()
        assert lab.verify(before, lab.request("other")) == "VERIFIED"
        lab.patch()
        lab.reset("success")
        assert lab.snapshot()["breaches"] == 0
        assert lab.request("other")["status"] == 200


def test_claim_without_audit_evidence_is_quarantined(tmp_path):
    with LiveLab(tmp_path / "lab.sqlite", "success") as lab:
        before = lab.snapshot()
        fake_response = {"status": 200, "body": {"account": "other"}}
        assert lab.verify(before, fake_response) == "QUARANTINED_VERIFIER_DISAGREEMENT"
