"""Alur Qt sungguhan lewat TCP Uvicorn dan database test terisolasi, tanpa mock API."""
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import uuid
import threading
import pytest
import httpx
from PySide6.QtCore import Qt
from sqlalchemy import select
from apps.admin_console.main import AdminWindow
from apps.student_client.main import StudentWindow
from services.api.models import LabSession
from packages.desktop.common import Api, STYLE
from PySide6.QtWidgets import QApplication


@pytest.mark.parametrize("agent_mode", [False, True])
def test_desktop_password_live(qtbot, system, tmp_path, agent_mode):
    QApplication.instance().setStyleSheet(STYLE)
    app, _ = system
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    url = f"http://127.0.0.1:{port}"
    cfg = app.state.settings
    env = dict(os.environ, LABACCESS_DATABASE_URL=cfg.database_url,
               LABACCESS_SIGNING_KEY=cfg.signing_key.get_secret_value(),
               LABACCESS_BIOMETRIC_KEY=cfg.biometric_key.get_secret_value())
    log = open(tmp_path / "api.log", "w")
    process = subprocess.Popen([sys.executable, "-m", "uvicorn", "services.api.main:create_app", "--factory",
                                "--port", str(port), "--host", "127.0.0.1", "--no-access-log"],
                               env=env, stdout=log, stderr=log,
                               creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0)
    def ready():
        try:
            return httpx.get(url + "/health", timeout=0.2).status_code == 200
        except httpx.HTTPError:
            return False
    admin = student = bridge = bridge_thread = None
    try:
        qtbot.waitUntil(ready, timeout=20000)
        admin = AdminWindow(url)
        qtbot.addWidget(admin)
        admin.show()
        admin.username.setText("admin")
        admin.password.setText("Test-password-123")
        qtbot.mouseClick(admin.login_button, Qt.LeftButton)
        qtbot.waitUntil(lambda: bool(admin.api.token), timeout=15000)
        enrollment = admin.api.request("POST", "/admin/enrollments", json={"name": "UI-PILOT-01"})
        pipe_name = None
        if agent_mode:
            from services.windows_agent.bridge import PipeServer, current_sid
            agent_api = Api(url)
            agent_api.device = agent_api.request("POST", "/devices/enroll", json={"token": enrollment["token"], "device_id": str(uuid.uuid4())})
            pipe_name = "LabAccess-UI-test-" + uuid.uuid4().hex
            bridge = PipeServer(pipe_name, current_sid(), agent_api)
            bridge_thread = threading.Thread(target=bridge.serve, daemon=True)
            bridge_thread.start()
            qtbot.wait(100)
        student = StudentWindow(url, tmp_path / "device.dpapi", agent_pipe=pipe_name)
        qtbot.addWidget(student)
        student.show()
        if not agent_mode:
            student.enrollment.setText(enrollment["token"])
            qtbot.mouseClick(student.enroll_button, Qt.LeftButton)
        qtbot.waitUntil(lambda: bool(student.api.device) and not student.busy, timeout=15000)
        qtbot.waitUntil(lambda: not student.heartbeat_busy, timeout=15000)
        student.nim.setText("TEST001")
        student.password.setText("Test-password-123")
        qtbot.mouseClick(student.password_button, Qt.LeftButton)
        qtbot.waitUntil(lambda: student.session is not None and not student.busy, timeout=15000)
        admin.refresh()
        qtbot.waitUntil(lambda: any(d["session"] for d in admin.devices), timeout=15000)
        assert admin.devices[0]["session"]["nim"] == "TEST001"
        with app.state.factory() as s:
            assert len(list(s.scalars(select(LabSession).where(LabSession.ended_at.is_(None))))) == 1
        Path("evidence").mkdir(exist_ok=True)
        student.grab().save("evidence/desktop-student.png")
        admin.grab().save("evidence/desktop-admin.png")
        # Real network outage: terminate only this test's owned subprocess.
        process.terminate()
        process.wait(timeout=10)
        student.heartbeat()
        qtbot.waitUntil(lambda: not student.heartbeat_busy, timeout=15000)
        assert student.session is not None, "Sesi aktif tidak boleh hilang saat jaringan gagal"
        assert "bermasalah" in student.connection.text()
        # Restart API, preserve DB session, then logout via UI.
        process = subprocess.Popen([sys.executable, "-m", "uvicorn", "services.api.main:create_app", "--factory", "--port", str(port),
                                    "--host", "127.0.0.1", "--no-access-log"], env=env, stdout=log, stderr=log,
                                   creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0)
        qtbot.waitUntil(ready, timeout=20000)
        student.heartbeat()
        qtbot.waitUntil(lambda: not student.heartbeat_busy, timeout=15000)
        qtbot.mouseClick(student.logout_button, Qt.LeftButton)
        qtbot.waitUntil(lambda: student.session is None and not student.busy, timeout=15000)
        admin.load_history()
        qtbot.waitUntil(lambda: bool(admin.history_data), timeout=15000)
        assert admin.history_data[0]["end_reason"] == "student_logout"
        admin.refresh()  # Respons yang sedang berjalan tidak boleh mengisi tabel setelah logout.
        admin.logout_admin()
        qtbot.waitUntil(lambda: not admin.jobs.pending, timeout=15000)
        assert not admin.api.token and not admin.devices and not admin.history_data
        assert all(t.rowCount() == 0 for t in (admin.device_table, admin.user_table, admin.history_table, admin.audit_table))
    finally:
        for window in (student, admin):
            if window:
                window.timer.stop()
                if hasattr(window, "clock"):
                    window.clock.stop()
                qtbot.waitUntil(lambda: not window.jobs.pending, timeout=30000)
                window.close()
        if bridge:
            bridge.stop()
            bridge_thread.join(timeout=6)
        process.terminate()
        process.wait(timeout=10)
        log.close()
