from scripts.evaluate_scores import evaluate


def test_metrics_use_observed_denominators():
    base = {"participant_code": "test-synthetic", "quality_pass": "1", "challenge_pass": "1", "latency_ms": "100", "session_opened": "0"}
    rows = [base | {"comparison": "genuine", "cosine_score": "0.7"},
            base | {"comparison": "genuine", "cosine_score": "0.2"},
            base | {"comparison": "impostor", "cosine_score": "0.8"},
            base | {"comparison": "impostor", "cosine_score": "0.1"},
            base | {"comparison": "genuine", "cosine_score": "", "quality_pass": "0"}]
    result = evaluate(rows, .5)
    assert result["FMR"] == result["FNMR"] == .5
    assert result["quality_failures"] == 1
    assert evaluate([], .5)["FMR"] is None
    assert evaluate([base | {"session_opened": ""}], .5)["login_success_rate"] is None
    assert evaluate([base | {"comparison": "impostor", "challenge_pass": "0", "cosine_score": ".8"}], .5)["FMR"] == 1
