import httpx
import pytest
from packages.veyon_adapter.webapi import VeyonAdapter, AUTH_KEYS, SCREEN_LOCK


def test_webapi_contract_and_close(tmp_path):
    key = tmp_path / "private.pem"
    key.write_text("test-only-key")
    calls = []
    def respond(request):
        calls.append((request.method, request.url.path))
        if request.method == "POST":
            import json
            assert json.loads(request.content)["method"] == AUTH_KEYS
            return httpx.Response(200, json={"connection-uid": "test-uid"})
        assert request.headers["Connection-Uid"] == "test-uid"
        if request.url.path.endswith("framebuffer"):
            return httpx.Response(200, content=b"jpeg-contract-test")
        return httpx.Response(200, json={})
    adapter = VeyonAdapter("http://127.0.0.1:11080", "test", key, transport=httpx.MockTransport(respond))
    with adapter.connection("lab-01") as link:
        assert link.status()["connected"]
        assert link.framebuffer() == b"jpeg-contract-test"
        link.screen_lock(True)
    assert calls[0] == ("POST", "/api/v1/authentication/lab-01")
    assert ("PUT", "/api/v1/feature/" + SCREEN_LOCK) in calls
    assert calls[-1] == ("DELETE", "/api/v1/authentication/lab-01")


def test_veyon_requires_tls_for_lan(tmp_path):
    with pytest.raises(ValueError):
        VeyonAdapter("http://192.0.2.1:11080", "key", tmp_path / "secret")
