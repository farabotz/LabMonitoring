"""YuNet + SFace sungguhan. Tidak ada fallback dummy atau PAD terlatih."""
import hashlib
import json
import threading
import os
from pathlib import Path
os.environ.setdefault("OPENCV_IO_MAX_IMAGE_PIXELS", "8294400")
import cv2
import numpy as np


class FaceEngine:
    def __init__(self, model_dir: Path):
        manifest = json.loads((model_dir / "manifest.json").read_text())
        for item in manifest["models"]:
            p = model_dir / item["file"]
            if not p.exists() or hashlib.sha256(p.read_bytes()).hexdigest() != item["sha256"]:
                raise ValueError("Checksum model salah atau model tidak tersedia.")
        self.detector = cv2.FaceDetectorYN.create(str(model_dir / manifest["models"][0]["file"]), "", (320, 320), 0.9)
        self.recognizer = cv2.FaceRecognizerSF.create(str(model_dir / manifest["models"][1]["file"]), "")
        self.lock = threading.Lock()

    def sample(self, raw):
        try:
            img = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)
        except cv2.error:
            raise ValueError("Frame kamera tidak valid atau terlalu besar.")
        if img is None or not (160 <= img.shape[0] <= 2160 and 160 <= img.shape[1] <= 3840):
            raise ValueError("Frame kamera tidak valid atau resolusi di luar batas.")
        h, w = img.shape[:2]
        self.detector.setInputSize((w, h))
        _, faces = self.detector.detect(img)
        if faces is None or len(faces) == 0:
            raise ValueError("Wajah tidak ditemukan.")
        if len(faces) != 1:
            raise ValueError("Harus tepat satu wajah pada kamera.")
        face = faces[0]
        x, y, fw, fh = face[:4]
        if min(fw, fh) < 90 or fw * fh / (w * h) < 0.035:
            raise ValueError("Wajah terlalu kecil; mendekatlah ke kamera.")
        if x < 0 or y < 0 or x + fw > w or y + fh > h:
            raise ValueError("Seluruh wajah harus terlihat.")
        crop = img[int(y):int(y + fh), int(x):int(x + fw)]
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        if gray.mean() < 45 or gray.mean() > 215 or cv2.Laplacian(gray, cv2.CV_64F).var() < 35:
            raise ValueError("Kualitas buruk: periksa cahaya dan ketajaman kamera.")
        aligned = self.recognizer.alignCrop(img, face)
        feature = self.recognizer.feature(aligned).reshape(-1).astype(float)
        feature /= np.linalg.norm(feature) + 1e-12
        # Five YuNet landmarks are geometric cues only, not a trained PAD model.
        eyes_mid = (face[4:6] + face[6:8]) / 2
        eye_distance = np.linalg.norm(face[4:6] - face[6:8])
        yaw_proxy = float((face[8] - eyes_mid[0]) / max(eye_distance, 1))
        return feature, yaw_proxy

    def enroll(self, raw_frames):
        with self.lock:
            samples = [self.sample(raw)[0] for raw in raw_frames]
        if min(float(np.dot(samples[0], f)) for f in samples[1:]) < 0.45:
            raise ValueError("Sampel enrollment tidak konsisten; ulangi dengan peserta yang sama.")
        template = np.mean(samples, axis=0)
        template /= np.linalg.norm(template) + 1e-12
        return {"model": "SFace-2021dec", "embedding": template.tolist(), "version": 1}

    def verify(self, raw_frames, template, direction, threshold):
        with self.lock:
            samples = [self.sample(raw) for raw in raw_frames]
        if template.get("model") != "SFace-2021dec":
            raise ValueError("Versi template tidak sesuai model.")
        target = np.asarray(template["embedding"], dtype=float)
        if target.shape != samples[0][0].shape or not np.isfinite(target).all():
            raise ValueError("Template tidak valid; lakukan enrollment ulang.")
        y0, y1, y2 = [s[1] for s in samples]
        # Camera preview is unmirrored: turning participant's left moves nose to image right.
        sign = 1 if direction == "left" else -1
        if abs(y0) > 0.25 or abs(y2 - y0) > 0.12 or sign * (y1 - y0) < 0.16:
            raise ValueError("Tantangan gerakan gagal. Tengah, putar kepala, lalu kembali tengah.")
        if min(float(np.dot(f, target)) for f, _ in samples) < threshold:
            raise ValueError("Wajah tidak cocok dengan NIM yang diklaim.")
        return {"verified": True, "pad": "geometric_challenge_limited"}
