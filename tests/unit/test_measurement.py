import httpx
import pytest

from scripts.measure_throughput import _one_completion


def test_counts_actual_tokens_when_generation_stops_early():
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda r: httpx.Response(200, json={"usage": {"completion_tokens": 3}})
        )
    ) as client:
        result = _one_completion(client, "http://test/completions", "model", "prompt", 128)
    assert result["completion_tokens"] == 3
    assert result["wall_s"] > 0


def test_missing_usage_fails_instead_of_inventing_tokens():
    with (
        httpx.Client(
            transport=httpx.MockTransport(lambda r: httpx.Response(200, json={"choices": []}))
        ) as client,
        pytest.raises(ValueError, match="completion_tokens"),
    ):
        _one_completion(client, "http://test/completions", "model", "prompt", 128)
