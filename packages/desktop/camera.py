"""Kamera hanya dibuka ketika dialog capture terlihat; frame hanya di RAM."""
import cv2
from PySide6.QtCore import QTimer
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton


class CaptureDialog(QDialog):
    def __init__(self, parent=None, direction=None):
        super().__init__(parent)
        self.setWindowTitle("Kamera aktif • verifikasi wajah eksperimental")
        self.direction, self.frames, self.last_frame = direction, [], None
        self.cap = None
        self.layout = QVBoxLayout(self)
        self.instruction = QLabel()
        self.layout.addWidget(self.instruction)
        self.preview = QLabel("Membuka kamera…")
        self.preview.setMinimumSize(640, 360)
        self.layout.addWidget(self.preview)
        self.capture = QPushButton("Ambil sampel")
        self.capture.clicked.connect(self.take)
        self.layout.addWidget(self.capture)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.set_instruction()
        QTimer.singleShot(0, self.open_camera)

    def open_camera(self):
        self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        if not self.cap.isOpened():
            self.instruction.setText("Webcam tidak tersedia. Tutup dialog dan gunakan password.")
            self.capture.setEnabled(False)
            self.cap.release()
            return
        self.timer.start(80)

    def set_instruction(self):
        step = len(self.frames)
        words = ["Hadap lurus ke kamera", "Putar kepala ke " + ("kiri Anda" if self.direction == "left" else "kanan Anda"), "Kembali hadap lurus"]
        self.instruction.setText(f"Sampel {step + 1}/3: " + (words[step] if self.direction else "Hadap kamera; ubah sedikit posisi/cahaya antar sampel"))

    def tick(self):
        ok, frame = self.cap.read()
        if not ok:
            self.instruction.setText("Pembacaan kamera gagal. Gunakan password atau ulangi.")
            self.capture.setEnabled(False)
            self.stop()
            return
        self.last_frame = frame
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, channels = rgb.shape
        self.preview.setPixmap(QPixmap.fromImage(QImage(rgb.data, w, h, channels * w, QImage.Format_RGB888).copy()))

    def take(self):
        if self.last_frame is None:
            return
        ok, encoded = cv2.imencode(".jpg", self.last_frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
        if not ok:
            return
        self.frames.append(encoded.tobytes())
        if len(self.frames) == 3:
            self.stop()
            self.accept()
        else:
            self.set_instruction()

    def stop(self):
        self.timer.stop()
        if self.cap:
            self.cap.release()
        self.last_frame = None

    def done(self, result):
        self.stop()
        super().done(result)
