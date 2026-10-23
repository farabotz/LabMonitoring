import json
from datetime import timedelta
from pathlib import Path
import cv2
import numpy as np
import pytest
from cryptography.fernet import Fernet
from sqlalchemy import select
from services.api.models import Audit, Challenge, User, now
from conftest import enroll


def test_face_challenge_binding_expiry_and_consumption(system, auth):
    app, c = system
    if not Path("models/face_detection_yunet_2023mar.onnx").exists():
        pytest.skip("Model belum disiapkan")
    app.state.settings.face_enabled = True
    a, _ = enroll(c, auth, "A")
    b, _ = enroll(c, auth, "B")
    challenge = c.post("/face/challenges", headers=a, json={"nim": "TEST001"}).json()
    _, jpg = cv2.imencode(".jpg", np.zeros((480, 640, 3), dtype=np.uint8))
    files = [("frames", ("test.jpg", jpg.tobytes(), "image/jpeg"))] * 3
    data = {"challenge_id": challenge["challenge_id"], "request_key": "face-request-123456"}
    assert c.post("/sessions/face", headers=b, data=data, files=files).status_code == 401
    assert c.post("/sessions/face", headers=a, data=data, files=files).status_code == 401
    with app.state.factory() as s:
        assert s.get(Challenge, challenge["challenge_id"]).consumed
    assert c.post("/sessions/face", headers=a, data=data, files=files).status_code == 401
    expired = c.post("/face/challenges", headers=a, json={"nim": "TEST001"}).json()
    with app.state.factory.begin() as s:
        s.get(Challenge, expired["challenge_id"]).expires_at = now() - timedelta(seconds=1)
    data["challenge_id"] = expired["challenge_id"]
    assert c.post("/sessions/face", headers=a, data=data, files=files).status_code == 401


def test_delete_template_does_not_retain_biometrics_in_audit(system, auth):
    app, c = system
    template = {"embedding": [0.1] * 128, "model": "test-only-template"}
    with app.state.factory.begin() as s:
        u = s.scalar(select(User).where(User.nim == "TEST001"))
        user_id = u.id
        u.face_template = Fernet(app.state.settings.biometric_key.get_secret_value()).encrypt(json.dumps(template).encode())
        assert b"embedding" not in u.face_template
    assert c.delete(f"/admin/users/{user_id}/face", headers=auth).status_code == 200
    with app.state.factory() as s:
        assert s.get(User, user_id).face_template is None
        audits = list(s.scalars(select(Audit).where(Audit.action == "face.delete")))
        assert len(audits) == 1
        assert "embedding" not in audits[0].detail
