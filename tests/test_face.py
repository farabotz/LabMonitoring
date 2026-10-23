from pathlib import Path
import cv2
import numpy as np
import pytest
from packages.face_verification.engine import FaceEngine


def test_real_yunet_sface_load_and_blank_rejection():
    if not Path("models/face_detection_yunet_2023mar.onnx").exists():
        pytest.skip("Model belum disiapkan melalui scripts.fetch_models")
    face = FaceEngine(Path("models"))
    _, data = cv2.imencode(".jpg", np.zeros((480, 640, 3), dtype=np.uint8))
    with pytest.raises(ValueError, match="tidak ditemukan"):
        face.enroll([data.tobytes()] * 3)


def test_face_rejects_malformed_frame():
    if not Path("models/face_detection_yunet_2023mar.onnx").exists():
        pytest.skip("Model belum disiapkan")
    with pytest.raises(ValueError, match="tidak valid"):
        FaceEngine(Path("models")).enroll([b"invalid"] * 3)


def test_real_sface_embedding_tensor():
    if not Path("models/face_recognition_sface_2021dec.onnx").exists():
        pytest.skip("Model belum disiapkan")
    fe = FaceEngine(Path("models"))
    # Tensor sintetis untuk menguji runtime embedding, bukan hasil akurasi identitas manusia.
    tensor = np.random.default_rng(42).integers(0, 256, (112, 112, 3), dtype=np.uint8)
    feature = fe.recognizer.feature(tensor)
    assert feature.shape == (1, 128) and np.isfinite(feature).all()
