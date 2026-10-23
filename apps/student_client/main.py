import argparse
import time
import uuid
from pathlib import Path
import psutil
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QWidget, QVBoxLayout, QFormLayout, QLineEdit, QLabel, QMessageBox, QDialog
from packages.desktop.common import Api, Jobs, button, load_secret, save_secret, state_path, title, run_window
from packages.desktop.camera import CaptureDialog


class StudentWindow(QWidget):
    def __init__(self, url=None, config=None, ca=None, agent_pipe=None):
        super().__init__()
        self.setWindowTitle("LabAccess • Mahasiswa")
        self.resize(580, 620)
        self.jobs, self.session, self.busy, self.heartbeat_busy = Jobs(), None, False, False
        self.config = Path(config) if config else state_path()
        self.local = load_secret(self.config)
        self.api = Api(url or self.local.get("url", "http://127.0.0.1:8000"), ca or self.local.get("ca") or True)
        if ca:
            self.local["ca"] = ca
        self.api.device = self.local.get("device", {})
        if agent_pipe:
            from services.windows_agent.client import AgentApi
            self.api = AgentApi(agent_pipe)
        self.boot_id = str(round(psutil.boot_time()))
        self.last_ok, self.base_elapsed, self.session_received = time.monotonic(), 0, time.monotonic()
        self.grace_minutes = 30
        self.request_key, self.login_identity = None, None
        layout = QVBoxLayout(self)
        self.heading = title("LabAccess")
        layout.addWidget(self.heading)
        self.pc = QLabel("PC: " + self.api.device.get("name", "belum terdaftar"))
        layout.addWidget(self.pc)
        form = QFormLayout()
        self.enrollment = QLineEdit()
        self.enrollment.setEchoMode(QLineEdit.Password)
        form.addRow("Token enrollment PC", self.enrollment)
        layout.addLayout(form)
        self.enroll_button = button("Daftarkan PC (sekali)", self.enroll)
        layout.addWidget(self.enroll_button)
        login = QFormLayout()
        self.nim, self.password = QLineEdit(), QLineEdit()
        self.nim.setPlaceholderText("Nomor induk mahasiswa")
        self.password.setEchoMode(QLineEdit.Password)
        login.addRow("NIM", self.nim)
        login.addRow("Password LabAccess", self.password)
        layout.addLayout(login)
        self.password_button = button("Masuk dengan password", self.login_password)
        self.face_button = button("Verifikasi wajah • eksperimental", self.login_face)
        layout.addWidget(self.password_button)
        layout.addWidget(self.face_button)
        self.details = QLabel("Belum ada sesi. Login Windows menggunakan akun bersama; sesi LabAccess terpisah.")
        self.details.setWordWrap(True)
        layout.addWidget(self.details)
        self.logout_button = button("Selesai / logout sesi", self.logout)
        layout.addWidget(self.logout_button)
        self.connection = QLabel("Memeriksa koneksi…")
        layout.addWidget(self.connection)
        self.message = QLabel("")
        self.message.setWordWrap(True)
        layout.addWidget(self.message)
        notice = QLabel("PC lab ini dapat dipantau pengelola melalui Veyon. Kamera hanya aktif saat verifikasi.\nPrototipe autentikasi dan pencatatan sesi; pembatasan OS belum diverifikasi.")
        notice.setWordWrap(True)
        layout.addWidget(notice)
        layout.addStretch()
        self.timer = QTimer(self)
        self.timer.setInterval(10000)
        self.timer.timeout.connect(self.heartbeat)
        self.timer.start()
        self.clock = QTimer(self)
        self.clock.timeout.connect(self.render)
        self.clock.start(1000)
        self.render()
        QTimer.singleShot(100, self.health)
        QTimer.singleShot(200, self.heartbeat)

    def error(self, message):
        self.message.setText(message)

    def perform(self, fn, done):
        if self.busy:
            return
        self.busy = True
        self.render()
        def finish():
            self.busy = False
            self.render()
        self.jobs.run(fn, done, self.error, finish)

    def health(self):
        def done(data):
            self.heading.setText(data["name"])
            self.timer.setInterval(data["heartbeat_seconds"] * 1000)
            self.grace_minutes = data["grace_minutes"]
        self.jobs.run(lambda: self.api.request("GET", "/health"), done, self.error)

    def enroll(self):
        value = self.enrollment.text()
        device_id = self.local.setdefault("device_id", str(uuid.uuid4()))
        def done(data):
            self.api.device = data
            self.local.update({"url": self.api.url, "device": data})
            save_secret(self.config, self.local)
            self.enrollment.clear()
            self.pc.setText("PC: " + data["name"])
            self.message.setText("PC berhasil didaftarkan.")
            self.heartbeat()
        self.perform(lambda: self.api.request("POST", "/devices/enroll", json={"token": value, "device_id": device_id}), done)

    def login_password(self):
        nim, password = self.nim.text().strip(), self.password.text()
        identity = (nim, password)
        if self.login_identity != identity:
            self.request_key = str(uuid.uuid4())
            self.login_identity = identity
        body = {"nim": nim, "password": password, "request_key": self.request_key}
        self.perform(lambda: self.api.request("POST", "/sessions/password", json=body), self.logged_in)

    def logged_in(self, data):
        self.session = data
        self.api.token = data["token"]
        self.password.clear()
        self.login_identity = None
        self.message.setText("Sesi tercatat. Selamat menggunakan laboratorium.")
        self.last_ok = time.monotonic()
        self.base_elapsed = 0
        self.session_received = time.monotonic()

    def login_face(self):
        nim = self.nim.text().strip()
        def capture(challenge):
            dialog = CaptureDialog(self, challenge["direction"])
            if dialog.exec() != QDialog.Accepted:
                self.message.setText("Verifikasi dibatalkan. Gunakan password bila diperlukan.")
                return
            raw = list(dialog.frames)
            dialog.frames.clear()
            key = str(uuid.uuid4())
            def work():
                try:
                    return self.api.request("POST", "/sessions/face", data={"challenge_id": challenge["challenge_id"], "request_key": key},
                                            files=[("frames", ("frame.jpg", frame, "image/jpeg")) for frame in raw])
                finally:
                    raw.clear()
            # Schedule after the challenge job's finished signal clears busy.
            QTimer.singleShot(0, lambda: self.perform(work, self.logged_in))
        self.perform(lambda: self.api.request("POST", "/face/challenges", json={"nim": nim}), capture)

    def heartbeat(self):
        if not self.api.device or self.heartbeat_busy or self.busy:
            return
        self.heartbeat_busy = True
        def done(data):
            was = self.session
            self.last_ok = time.monotonic()
            self.session = data["session"]
            self.connection.setText("Terhubung • waktu server " + data["server_time"])
            if self.session:
                from datetime import datetime
                self.api.token = self.session["token"]
                self.base_elapsed = max(0, (datetime.fromisoformat(data["server_time"]) - datetime.fromisoformat(self.session["started_at"])).total_seconds())
                self.session_received = time.monotonic()
            elif was:
                self.api.token = ""
                self.message.setText("Sesi telah diakhiri admin atau restart terdeteksi. Pekerjaan Windows tidak ditutup.")
            if data["restart_detected"]:
                self.message.setText("Restart PC terdeteksi. Sesi sebelumnya ditandai terinterupsi; silakan login ulang.")
            self.render()
        def error(msg):
            self.connection.setText("Koneksi bermasalah • sesi aktif tetap dicatat; hubungi admin bila berlanjut.")
            self.error(msg)
        self.jobs.run(lambda: self.api.request("POST", "/devices/heartbeat", json={"boot_id": self.boot_id}), done, error,
                      lambda: setattr(self, "heartbeat_busy", False))

    def logout(self):
        def done(data):
            self.session, self.api.token, self.request_key = None, "", None
            self.message.setText("Sesi selesai dan tercatat.")
        self.perform(lambda: self.api.request("POST", "/sessions/logout"), done)

    def render(self):
        registered = bool(self.api.device)
        self.enrollment.setVisible(not registered)
        self.enroll_button.setVisible(not registered)
        for b in (self.password_button, self.face_button):
            b.setEnabled(registered and not self.session and not self.busy)
        self.logout_button.setEnabled(bool(self.session) and not self.busy)
        if self.session:
            minutes = int((self.base_elapsed + time.monotonic() - self.session_received) / 60)
            self.details.setText(f"{self.session['name']} • {self.session['nim']}\nMulai: {self.session['started_at']}\nDurasi sekitar {minutes} menit • {self.session['method']}")
            if time.monotonic() - self.last_ok > self.grace_minutes * 60:
                self.connection.setText("Gangguan melewati grace period. Hubungi admin; pekerjaan Anda tetap berjalan.")
        else:
            self.details.setText("Belum ada sesi aktif. Gunakan NIM dan password LabAccess atau wajah terdaftar.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--server")
    parser.add_argument("--config")
    parser.add_argument("--ca")
    parser.add_argument("--agent-pipe", help="Named pipe lokal agent yang telah dienroll; tidak memakai secret UI")
    parser.add_argument("--smoke-test", action="store_true")
    args = parser.parse_args()
    run_window(lambda: StudentWindow(args.server, args.config, args.ca, args.agent_pipe), args.smoke_test)


if __name__ == "__main__":
    main()
