import os
import uuid
import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from services.api.config import Settings
from services.api.main import create_app
from services.api.models import Base, User
from services.api.security import hasher


@pytest.fixture
def system(tmp_path):
    url = os.getenv("LABACCESS_TEST_DATABASE_URL", "sqlite:///" + (tmp_path / "test.db").as_posix())
    control = None
    schema = "test_" + uuid.uuid4().hex
    if url.startswith("postgresql"):
        from sqlalchemy.engine import make_url
        parsed = make_url(url)
        if not parsed.database.startswith("labaccess_test_"):
            pytest.fail("Pengujian PostgreSQL hanya diizinkan pada database bernama labaccess_test_*")
        control = create_engine(url)
        with control.begin() as conn:
            conn.execute(text('CREATE SCHEMA "' + schema + '"'))
        url = str(parsed.update_query_dict({"options": "-csearch_path=" + schema}).render_as_string(hide_password=False))
    cfg = Settings(_env_file=None, database_url=url, signing_key="test-signing-secret-key-" + "a" * 40,
                   biometric_key=Fernet.generate_key().decode())
    app = create_app(cfg)
    Base.metadata.create_all(app.state.engine)
    with app.state.factory.begin() as s:
        for nim, role, active in [("admin", "admin", True), ("operator", "operator", True),
                                  ("TEST001", "student", True), ("TEST002", "student", True), ("OFF", "student", False)]:
            s.add(User(nim=nim, name="=UNTRUSTED" if nim == "TEST002" else nim, role=role, active=active,
                       password_hash=hasher.hash("Test-password-123")))
    with TestClient(app) as client:
        yield app, client
    app.state.engine.dispose()
    if control:
        with control.begin() as conn:
            conn.execute(text('DROP SCHEMA "' + schema + '" CASCADE'))
        control.dispose()


@pytest.fixture
def auth(system):
    app, client = system
    r = client.post("/auth/admin", json={"nim": "admin", "password": "Test-password-123"})
    assert r.status_code == 200, r.text
    return {"Authorization": "Bearer " + r.json()["token"]}


def enroll(client, auth, name):
    r = client.post("/admin/enrollments", headers=auth, json={"name": name, "veyon_host": "127.0.0.1"})
    assert r.status_code == 200, r.text
    device_id = str(uuid.uuid4())
    value = r.json()["token"]
    r = client.post("/devices/enroll", json={"token": value, "device_id": device_id})
    assert r.status_code == 201, r.text
    return {"X-Device-Id": device_id, "X-Device-Secret": r.json()["device_secret"]}, value


def login(client, device, nim="TEST001", key=None, password="Test-password-123"):
    return client.post("/sessions/password", headers=device, json={"nim": nim, "password": password,
                       "request_key": key or str(uuid.uuid4())})
