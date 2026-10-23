import concurrent.futures
import uuid
from datetime import timedelta
import jwt
import pytest
from sqlalchemy import select
from services.api.models import Device, LabSession, User, now
from services.api.security import token
from conftest import enroll, login


def test_password_end_to_end(system, auth):
    app, c = system
    d, _ = enroll(c, auth, "LAB-01")
    assert c.post("/devices/heartbeat", headers=d, json={"boot_id": "boot-1"}).status_code == 200
    r = login(c, d)
    assert r.status_code == 200, r.text
    session = r.json()
    assert session["method"] == "password"
    rows = c.get("/admin/devices", headers=auth).json()
    assert rows[0]["session"]["nim"] == "TEST001"
    assert rows[0]["online"]
    assert c.post("/sessions/logout", headers=d | {"Authorization": "Bearer " + session["token"]}).status_code == 200
    assert c.post("/sessions/logout", headers=d | {"Authorization": "Bearer " + session["token"]}).status_code == 200
    history = c.get("/admin/history", headers=auth).json()
    assert history[0]["end_reason"] == "student_logout"
    assert c.get("/admin/devices", headers=auth).json()[0]["session"] is None


@pytest.mark.parametrize("nim,password", [("TEST001", "wrong"), ("missing", "Test-password-123"), ("OFF", "Test-password-123"), ("admin", "Test-password-123")])
def test_reject_credentials(system, auth, nim, password):
    _, c = system
    d, _ = enroll(c, auth, "PC")
    assert login(c, d, nim, password=password).status_code == 401


def test_device_secret_and_enrollment_once(system, auth):
    _, c = system
    d, value = enroll(c, auth, "PC")
    assert login(c, d | {"X-Device-Secret": "forged"}).status_code == 401
    assert c.post("/devices/enroll", json={"token": value, "device_id": str(uuid.uuid4())}).status_code == 401


def test_single_nim_and_single_pc(system, auth):
    _, c = system
    a, _ = enroll(c, auth, "A")
    b, _ = enroll(c, auth, "B")
    assert login(c, a).status_code == 200
    assert login(c, b).status_code == 409
    assert login(c, a, "TEST002").status_code == 409


def test_idempotency_and_payload_mismatch(system, auth):
    _, c = system
    d, _ = enroll(c, auth, "PC")
    key = str(uuid.uuid4())
    a, b = login(c, d, key=key), login(c, d, key=key)
    assert a.status_code == b.status_code == 200
    assert a.json()["id"] == b.json()["id"]
    assert login(c, d, "TEST002", key=key).status_code == 409


def test_concurrent_identical_retry(system, auth):
    _, c = system
    d, _ = enroll(c, auth, "A")
    key = str(uuid.uuid4())
    with concurrent.futures.ThreadPoolExecutor(2) as pool:
        futures = [pool.submit(login, c, d, "TEST001", key) for _ in range(2)]
        results = [f.result() for f in futures]
    assert [r.status_code for r in results] == [200, 200]
    assert results[0].json()["id"] == results[1].json()["id"]


@pytest.mark.parametrize("same_pc", [True, False])
def test_concurrent_logins(system, auth, same_pc):
    app, c = system
    a, _ = enroll(c, auth, "A")
    b = a if same_pc else enroll(c, auth, "B")[0]
    with concurrent.futures.ThreadPoolExecutor(2) as pool:
        futures = [pool.submit(login, c, a, "TEST001"), pool.submit(login, c, b, "TEST002" if same_pc else "TEST001")]
        responses = [f.result() for f in futures]
    assert sorted(r.status_code for r in responses) == [200, 409], [r.text for r in responses]
    with app.state.factory() as s:
        assert len(list(s.scalars(select(LabSession).where(LabSession.ended_at.is_(None))))) == 1


def test_expired_and_device_bound_token(system, auth):
    app, c = system
    a, _ = enroll(c, auth, "A")
    b, _ = enroll(c, auth, "B")
    row = login(c, a).json()
    assert c.post("/sessions/logout", headers=b | {"Authorization": "Bearer " + row["token"]}).status_code == 403
    expired = jwt.encode({"sub": row["id"], "kind": "session", "device": a["X-Device-Id"],
                          "iss": "labaccess", "aud": "labaccess", "iat": now() - timedelta(hours=2), "exp": now() - timedelta(hours=1)},
                         app.state.settings.signing_key.get_secret_value(), algorithm="HS256")
    assert c.post("/sessions/logout", headers=a | {"Authorization": "Bearer " + expired}).status_code == 401
    heartbeat = c.post("/devices/heartbeat", headers=a, json={"boot_id": "same"})
    assert heartbeat.json()["session"]["id"] == row["id"]
    assert heartbeat.json()["session"]["token"]


def test_stale_reconnect_and_restart(system, auth):
    app, c = system
    d, _ = enroll(c, auth, "A")
    c.post("/devices/heartbeat", headers=d, json={"boot_id": "boot1"})
    row = login(c, d).json()
    with app.state.factory.begin() as s:
        s.get(Device, d["X-Device-Id"]).last_seen = now() - timedelta(minutes=5)
        s.get(LabSession, row["id"]).last_seen = now() - timedelta(minutes=5)
    status = c.get("/admin/devices", headers=auth).json()[0]
    assert not status["online"] and status["session"]["connection"] == "stale"
    assert c.post("/devices/heartbeat", headers=d, json={"boot_id": "boot1"}).json()["session"]["id"] == row["id"]
    assert c.post("/devices/heartbeat", headers=d, json={"boot_id": "boot2"}).json()["session"] is None
    assert c.get("/admin/history", headers=auth).json()[0]["end_reason"] == "device_restart_detected"


def test_student_no_admin_access(system, auth):
    _, c = system
    d, _ = enroll(c, auth, "PC")
    row = login(c, d).json()
    headers = {"Authorization": "Bearer " + row["token"]}
    for path in ["/admin/devices", "/admin/users", "/admin/history", "/admin/audit", "/admin/history.csv"]:
        assert c.get(path, headers=headers).status_code == 403
    assert c.get("/admin/devices", headers=d).status_code == 401


def test_operator_boundaries_and_reset(system, auth):
    _, c = system
    op = {"Authorization": "Bearer " + c.post("/auth/admin", json={"nim": "operator", "password": "Test-password-123"}).json()["token"]}
    assert c.post("/admin/enrollments", headers=op, json={"name": "forbidden"}).status_code == 403
    users = c.get("/admin/users", headers=op).json()
    admin_id = next(x["id"] for x in users if x["nim"] == "admin")
    student_id = next(x["id"] for x in users if x["nim"] == "TEST001")
    assert c.put(f"/admin/users/{admin_id}/password", headers=op, json={"password": "new-password-123"}).status_code == 403
    assert c.put(f"/admin/users/{student_id}/password", headers=op, json={"password": "new-password-123"}).status_code == 200
    d, _ = enroll(c, auth, "PC")
    assert login(c, d).status_code == 401
    assert login(c, d, password="new-password-123").status_code == 200


def test_admin_end_and_move(system, auth):
    _, c = system
    a, _ = enroll(c, auth, "A")
    b, _ = enroll(c, auth, "B")
    row = login(c, a).json()
    assert c.post(f"/admin/sessions/{row['id']}/end", headers=auth, json={"reason": "pindah komputer setelah peringatan"}).status_code == 200
    assert login(c, b).status_code == 200


def test_rate_limit(system, auth, monkeypatch):
    import services.api.main as api_module
    clock = [api_module.now()]
    # Batas fixed-window diuji dengan waktu server terkontrol, tanpa mengubah
    # jam Windows. Tes tidak boleh gagal acak ketika melewati pergantian menit.
    monkeypatch.setattr(api_module, "now", lambda: clock[0])
    _, c = system
    d, _ = enroll(c, auth, "A")
    codes = [login(c, d, password="bad").status_code for _ in range(11)]
    assert codes[-1] == 429
    clock[0] += timedelta(minutes=1)
    assert login(c, d, password="bad").status_code == 401


def test_csv_injection_and_filter(system, auth):
    _, c = system
    d, _ = enroll(c, auth, "A")
    result = login(c, d, nim="TEST002").json()
    r = c.get("/admin/history.csv", headers=auth, params={"nim": "TEST002"})
    assert "'=UNTRUSTED" in r.text
    assert not c.get("/admin/history", headers=auth, params={"nim": "TEST001"}).json()
    ended = dict(d, Authorization="Bearer " + result["token"])
    assert c.post("/sessions/logout", headers=ended).status_code == 200
    assert len(c.get("/admin/history", headers=auth, params={"end_reason": "LOGOUT"}).json()) == 1
    assert not c.get("/admin/history", headers=auth, params={"end_reason": "%"}).json()
    assert "TEST002" not in c.get("/admin/history.csv", headers=auth, params={"end_reason": "admin:"}).text


def test_face_disabled_and_no_boolean_bypass(system, auth):
    _, c = system
    d, _ = enroll(c, auth, "A")
    assert c.post("/face/challenges", headers=d, json={"nim": "TEST001"}).status_code == 503
    assert c.post("/sessions/face", headers=d, json={"face_verified": True}).status_code == 422


def test_unconfigured_veyon_is_explicit(system, auth):
    _, c = system
    d, _ = enroll(c, auth, "A")
    assert c.get(f"/admin/devices/{d['X-Device-Id']}/veyon/status", headers=auth).status_code == 503
    audit = c.get("/admin/audit", headers=auth).json()
    assert any(r["action"] == "veyon.failed" for r in audit)
    assert any(r["action"] == "config.loaded" for r in audit)


def test_remote_plaintext_rejected(system):
    app, _ = system
    from fastapi.testclient import TestClient
    with TestClient(app, client=("192.0.2.10", 12345)) as remote:
        assert remote.get("/health").status_code == 426


def test_chunked_request_size_is_bounded(system):
    _, c = system
    def chunks():
        yield b'{"nim":"x","password":"'
        for _ in range(7):
            yield b'x' * 1_000_000
        yield b'"}'
    response = c.post("/auth/admin", content=chunks(), headers={"Content-Type": "application/json"})
    assert response.status_code == 413
