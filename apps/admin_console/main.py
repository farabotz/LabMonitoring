import argparse
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit, QLabel,
    QTabWidget, QTableWidget, QTableWidgetItem, QMessageBox, QInputDialog, QFileDialog, QDialog,
    QAbstractItemView, QHeaderView, QComboBox)
from packages.desktop.common import Api, Jobs, button, title, run_window
from packages.desktop.camera import CaptureDialog


def table(columns):
    t = QTableWidget(0, len(columns))
    t.setHorizontalHeaderLabels(columns)
    t.setSelectionBehavior(QAbstractItemView.SelectRows)
    t.setSelectionMode(QAbstractItemView.SingleSelection)
    t.setEditTriggers(QAbstractItemView.NoEditTriggers)
    t.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
    return t


def fill(t, rows):
    selected = t.currentRow()
    t.setRowCount(len(rows))
    for row, values in enumerate(rows):
        for col, value in enumerate(values):
            t.setItem(row, col, QTableWidgetItem(str(value if value is not None else "—")))
    if 0 <= selected < len(rows):
        t.selectRow(selected)


class AdminWindow(QWidget):
    def __init__(self, url="http://127.0.0.1:8000", ca=True):
        super().__init__()
        self.setWindowTitle("LabAccess • Pengelola laboratorium")
        self.resize(1200, 800)
        self.api, self.jobs = Api(url, ca), Jobs()
        self.devices, self.users, self.history_data = [], [], []
        self.polling, self.role = False, None
        self.login_marker = None
        root = QVBoxLayout(self)
        self.heading = title("LabAccess / Pengelola")
        root.addWidget(self.heading)
        self.login_box = QWidget()
        login = QHBoxLayout(self.login_box)
        self.username, self.password = QLineEdit(), QLineEdit()
        self.username.setPlaceholderText("Akun admin/operator")
        self.password.setPlaceholderText("Password LabAccess")
        self.password.setEchoMode(QLineEdit.Password)
        login.addWidget(self.username)
        login.addWidget(self.password)
        self.login_button = button("Masuk pengelola", self.login)
        login.addWidget(self.login_button)
        root.addWidget(self.login_box)
        self.identity = QLabel("Pemantauan hanya untuk PC lab terkelola. Identitas mahasiswa berasal dari sesi LabAccess.")
        root.addWidget(self.identity)
        self.tabs = QTabWidget()
        self.tabs.setEnabled(False)
        root.addWidget(self.tabs)
        inventory = QWidget()
        v = QVBoxLayout(inventory)
        self.device_table = table(["PC", "Koneksi", "Status", "NIM / Nama", "Mulai (UTC)", "Durasi"])
        v.addWidget(self.device_table)
        tools = QHBoxLayout()
        for label, fn in [("Refresh", self.refresh), ("Daftarkan PC", self.issue_enrollment),
                          ("Mapping / masalah PC", self.configure_device), ("Akhiri sesi…", self.end_session),
                          ("Status Veyon", self.veyon_status), ("Lihat layar", self.framebuffer),
                          ("Kunci…", lambda: self.veyon_lock(True)), ("Buka kunci…", lambda: self.veyon_lock(False)),
                          ("Buka Veyon Master", self.open_master)]:
            tools.addWidget(button(label, fn))
        v.addLayout(tools)
        self.tabs.addTab(inventory, "Komputer & sesi")
        accounts = QWidget()
        av = QVBoxLayout(accounts)
        self.user_table = table(["NIM / akun", "Nama", "Peran", "Aktif", "Wajah"])
        av.addWidget(self.user_table)
        actions = QHBoxLayout()
        for label, fn in [("Muat akun", self.load_users), ("Tambah akun", self.add_user), ("Reset password", self.reset_password),
                          ("Aktif/nonaktif", self.toggle_user), ("Enrollment wajah", self.enroll_face), ("Hapus template…", self.delete_face)]:
            actions.addWidget(button(label, fn))
        av.addLayout(actions)
        self.tabs.addTab(accounts, "Mahasiswa & akun")
        hist = QWidget()
        hv = QVBoxLayout(hist)
        filters = QHBoxLayout()
        self.filter_nim, self.filter_device, self.filter_start, self.filter_end = [QLineEdit() for _ in range(4)]
        for entry, placeholder in [(self.filter_nim, "NIM"), (self.filter_device, "device_id"),
                                   (self.filter_start, "Awal UTC: 2026-10-01T00:00:00Z"), (self.filter_end, "Akhir UTC: 2026-10-31T23:59:59Z")]:
            entry.setPlaceholderText(placeholder)
            filters.addWidget(entry)
        self.filter_method = QComboBox()
        self.filter_method.addItems(["Semua metode", "password", "face"])
        filters.addWidget(self.filter_method)
        filters.addWidget(button("Cari", self.load_history))
        filters.addWidget(button("Ekspor CSV", self.export_csv))
        hv.addLayout(filters)
        self.filter_reason = QLineEdit()
        self.filter_reason.setPlaceholderText("Alasan berakhir mengandung teks (misalnya student_logout atau pindah komputer)")
        hv.addWidget(self.filter_reason)
        self.history_table = table(["NIM", "Nama", "PC ID", "Metode", "Mulai UTC", "Last seen UTC", "Selesai UTC", "Alasan"])
        hv.addWidget(self.history_table)
        hv.addWidget(QLabel("Riwayat membantu penelusuran. Login seseorang tidak membuktikan ia menyebabkan kerusakan. Maksimal 10.000 baris per rentang."))
        self.tabs.addTab(hist, "Riwayat")
        audit_page = QWidget()
        au = QVBoxLayout(audit_page)
        au.addWidget(button("Muat audit (admin)", self.load_audit))
        self.audit_table = table(["Waktu UTC", "Pelaku", "Tindakan", "Target", "Detail"])
        au.addWidget(self.audit_table)
        self.tabs.addTab(audit_page, "Audit")
        self.message = QLabel("")
        self.message.setWordWrap(True)
        root.addWidget(self.message)
        root.addWidget(button("Keluar akun pengelola", self.logout_admin))
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(10000)

    def error(self, message):
        if "Token tidak sah" in message or "Hak operator/admin diperlukan" in message:
            self.logout_admin()
        self.message.setText(message)

    def logout_admin(self):
        self.api.token, self.role = "", None
        self.login_marker, self.polling = None, False
        self.devices, self.users, self.history_data = [], [], []
        for widget in (self.device_table, self.user_table, self.history_table, self.audit_table):
            widget.setRowCount(0)
        self.password.clear()
        self.login_button.setEnabled(True)
        self.tabs.setEnabled(False)
        self.login_box.show()
        self.identity.setText("Silakan login pengelola.")

    def task(self, fn, done=None):
        credential = self.api.token
        result = done or (lambda _: self.message.setText("Berhasil."))
        current = lambda: bool(credential) and self.api.token == credential
        self.jobs.run(fn, lambda data: result(data) if current() else None,
                      lambda message: self.error(message) if current() else None)

    def login(self):
        marker = self.login_marker = object()
        body = {"nim": self.username.text().strip(), "password": self.password.text()}
        self.login_button.setEnabled(False)
        def done(data):
            if self.login_marker is not marker:
                return
            self.api.token, self.role = data["token"], data["role"]
            self.password.clear()
            self.tabs.setEnabled(True)
            self.identity.setText(f"{data['name']} • {self.role} • Veyon untuk layar/bantuan, LabAccess untuk identitas dan audit")
            self.login_box.hide()
            self.message.setText("Terhubung.")
            self.refresh()
            self.load_users()
            def health(data):
                self.heading.setText(data["name"] + " / Pengelola")
                self.timer.setInterval(data["heartbeat_seconds"] * 1000)
            self.task(lambda: self.api.request("GET", "/health"), health)
        self.jobs.run(lambda: self.api.request("POST", "/auth/admin", json=body), done,
                      lambda message: self.error(message) if self.login_marker is marker else None,
                      lambda: self.login_button.setEnabled(True) if self.login_marker is marker else None)

    def refresh(self):
        if not self.api.token or self.polling:
            return
        self.polling = True
        credential = self.api.token
        current = lambda: bool(credential) and self.api.token == credential
        def done(data):
            if not current():
                return
            self.devices = data
            rows = []
            for d in data:
                s = d["session"]
                status = "bermasalah: " + d["problem"] if d["problem"] else ("dipakai" if s else "tersedia")
                duration = "—"
                if s:
                    minutes = s["duration_seconds"] // 60
                    duration = str(max(0, minutes)) + " menit"
                rows.append([d["name"], "online" if d["online"] else "offline/stale", status,
                             f"{s['nim']} / {s['name']}" if s else "—", s["started_at"] if s else "—", duration])
            fill(self.device_table, rows)
            self.message.setText(f"{len(data)} PC • pembaruan {datetime.now().strftime('%H:%M:%S')}")
        self.jobs.run(lambda: self.api.request("GET", "/admin/devices"), done,
                      lambda message: self.error(message) if current() else None,
                      lambda: setattr(self, "polling", False) if current() else None)

    def selected(self, collection, t):
        i = t.currentRow()
        if i < 0 or i >= len(collection):
            self.error("Pilih satu baris terlebih dahulu.")
            return None
        return collection[i]

    def issue_enrollment(self):
        name, ok = QInputDialog.getText(self, "Enrollment PC", "Nama PC unik (misalnya LAB-01):")
        if not ok or not name:
            return
        host, ok = QInputDialog.getText(self, "Mapping Veyon", "Hostname/IP PC untuk Veyon (boleh kosong):")
        if not ok:
            return
        def done(data):
            QInputDialog.getText(self, "Token sekali pakai • berlaku 15 menit", "Masukkan token ini pada desktop mahasiswa:", QLineEdit.Normal, data["token"])
        self.task(lambda: self.api.request("POST", "/admin/enrollments", json={"name": name, "veyon_host": host}), done)

    def configure_device(self):
        d = self.selected(self.devices, self.device_table)
        if not d:
            return
        host, ok = QInputDialog.getText(self, "Mapping Veyon", "Hostname/IP yang diverifikasi milik PC ini:", text=d["veyon_host"])
        if not ok:
            return
        problem, ok = QInputDialog.getText(self, "Masalah PC", "Catatan masalah (kosong = normal):", text=d["problem"])
        if ok:
            self.task(lambda: self.api.request("PUT", f"/admin/devices/{d['id']}", json={"active": d["active"], "veyon_host": host, "problem": problem}), lambda _: self.refresh())

    def end_session(self):
        d = self.selected(self.devices, self.device_table)
        if not d or not d["session"]:
            return
        reason, ok = QInputDialog.getText(self, "Akhiri sesi", "Beri peringatan kepada mahasiswa dahulu. Alasan (min. 5 karakter):")
        if ok and QMessageBox.question(self, "Konfirmasi", "Akhiri pencatatan sesi pada " + d["name"] + "? Pekerjaan Windows tetap berjalan.") == QMessageBox.Yes:
            self.task(lambda: self.api.request("POST", f"/admin/sessions/{d['session']['id']}/end", json={"reason": reason}), lambda _: self.refresh())

    def load_users(self):
        def done(data):
            self.users = data
            fill(self.user_table, [[u["nim"], u["name"], u["role"], u["active"], "terdaftar" if u["face_enrolled"] else "belum"] for u in data])
        self.task(lambda: self.api.request("GET", "/admin/users"), done)

    def add_user(self):
        values = []
        for label in ["NIM / akun", "Nama", "Password baru (min. 12 karakter)"]:
            value, ok = QInputDialog.getText(self, "Tambah akun", label, QLineEdit.Password if "Password" in label else QLineEdit.Normal)
            if not ok:
                return
            values.append(value)
        role, ok = QInputDialog.getItem(self, "Peran", "Peran akun:", ["student", "operator", "admin"] if self.role == "admin" else ["student"], editable=False)
        if ok:
            body = dict(zip(["nim", "name", "password"], values)) | {"role": role}
            self.task(lambda: self.api.request("POST", "/admin/users", json=body), lambda _: self.load_users())

    def reset_password(self):
        u = self.selected(self.users, self.user_table)
        if not u:
            return
        password, ok = QInputDialog.getText(self, "Reset password " + u["nim"], "Password baru min. 12 karakter:", QLineEdit.Password)
        if ok:
            self.task(lambda: self.api.request("PUT", f"/admin/users/{u['id']}/password", json={"password": password}))

    def toggle_user(self):
        u = self.selected(self.users, self.user_table)
        if u and QMessageBox.question(self, "Status akun", "Ubah status aktif akun " + u["nim"] + "?") == QMessageBox.Yes:
            self.task(lambda: self.api.request("PUT", f"/admin/users/{u['id']}/state", json={"active": not u["active"]}), lambda _: self.load_users())

    def enroll_face(self):
        u = self.selected(self.users, self.user_table)
        if not u:
            return
        if QMessageBox.question(self, "Persetujuan enrollment", f"Identitas {u['nim']} / {u['name']} telah diperiksa langsung dan peserta telah menyetujui penyimpanan template selama penelitian?") != QMessageBox.Yes:
            return
        capture = CaptureDialog(self)
        if capture.exec() == QDialog.Accepted:
            raw = list(capture.frames)
            capture.frames.clear()
            def work():
                try:
                    return self.api.request("POST", f"/admin/users/{u['id']}/face", data={"consent": "true"},
                                            files=[("frames", ("frame.jpg", f, "image/jpeg")) for f in raw])
                finally:
                    raw.clear()
            self.task(work, lambda _: self.load_users())

    def delete_face(self):
        u = self.selected(self.users, self.user_table)
        if u and QMessageBox.question(self, "Hapus biometrik", "Hapus template " + u["nim"] + " dari database aktif? Backup mengikuti jadwal retensi terpisah.") == QMessageBox.Yes:
            self.task(lambda: self.api.request("DELETE", f"/admin/users/{u['id']}/face"), lambda _: self.load_users())

    def history_params(self):
        return {k: v for k, v in {"nim": self.filter_nim.text().strip(), "device_id": self.filter_device.text().strip(),
                "start": self.filter_start.text().strip(), "end": self.filter_end.text().strip(),
                "method": self.filter_method.currentText() if self.filter_method.currentIndex() else "",
                "end_reason": self.filter_reason.text().strip()}.items() if v}

    def load_history(self):
        params = self.history_params()
        def done(data):
            self.history_data = data
            fill(self.history_table, [[s[k] for k in ["nim", "name", "device_id", "method", "started_at", "last_seen", "ended_at", "end_reason"]] for s in data])
        self.task(lambda: self.api.request("GET", "/admin/history", params=params), done)

    def export_csv(self):
        path, _ = QFileDialog.getSaveFileName(self, "Simpan riwayat", "labaccess-history.csv", "CSV (*.csv)")
        if path:
            params = self.history_params()
            self.task(lambda: self.api.request("GET", "/admin/history.csv", params=params, raw=True), lambda b: Path(path).write_bytes(b))

    def load_audit(self):
        self.task(lambda: self.api.request("GET", "/admin/audit"), lambda data: fill(self.audit_table, [[r[k] for k in ["at", "actor", "action", "target", "detail"]] for r in data]))

    def veyon_status(self):
        d = self.selected(self.devices, self.device_table)
        if d:
            self.task(lambda: self.api.request("GET", f"/admin/devices/{d['id']}/veyon/status"), lambda data: self.message.setText(str(data)))

    def framebuffer(self):
        d = self.selected(self.devices, self.device_table)
        if not d:
            return
        def done(raw):
            dialog = QDialog(self)
            dialog.setWindowTitle("Veyon • " + d["name"] + " • tangkapan saat diminta")
            v = QVBoxLayout(dialog)
            image = QLabel()
            pixmap = QPixmap()
            pixmap.loadFromData(raw)
            image.setPixmap(pixmap)
            v.addWidget(image)
            dialog.exec()
        self.task(lambda: self.api.request("GET", f"/admin/devices/{d['id']}/veyon/framebuffer", raw=True), done)

    def veyon_lock(self, active):
        d = self.selected(self.devices, self.device_table)
        if not d:
            return
        reason, ok = QInputDialog.getText(self, "Kontrol administratif", "Alasan (min. 5 karakter); peringatkan mahasiswa terlebih dahulu:")
        if ok and QMessageBox.question(self, "Konfirmasi Veyon", ("Kunci" if active else "Buka kunci") + " layar " + d["name"] + "? Ini dapat mengganggu pekerjaan.") == QMessageBox.Yes:
            self.task(lambda: self.api.request("PUT", f"/admin/devices/{d['id']}/veyon/lock", params={"active": str(active).lower()}, json={"reason": reason}))

    def open_master(self):
        path = Path(os.getenv("PROGRAMFILES", "C:/Program Files")) / "Veyon" / "veyon-master.exe"
        if not path.exists():
            chosen, _ = QFileDialog.getOpenFileName(self, "Pilih Veyon Master resmi", str(path.parent), "Veyon Master (veyon-master.exe)")
            if not chosen:
                return
            path = Path(chosen)
        try:
            subprocess.Popen([str(path)], cwd=path.parent)
        except OSError:
            self.error("Veyon Master tidak dapat dibuka. Periksa instalasi resmi.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--server", default="http://127.0.0.1:8000")
    parser.add_argument("--ca", default=None)
    parser.add_argument("--smoke-test", action="store_true")
    args = parser.parse_args()
    run_window(lambda: AdminWindow(args.server, args.ca or True), args.smoke_test)


if __name__ == "__main__":
    main()
