import json
import pytest
from scripts.score_dataset import load_dataset


def test_dataset_rejects_consent_and_reused_capture(tmp_path):
    # Berkas sintetis hanya menguji pembatasan dataset; bukan wajah/inferensi palsu.
    names = ["e1", "e2", "e3", "c1", "c2", "c3", "t1", "t2", "t3"]
    for name in names:
        (tmp_path / name).write_bytes(name.encode())
    person = {"consent_confirmed": False, "identity_checked": True,
              "enrollment_session": "E01", "frames": names[:3]}
    attempt = {"participant_code": "P01", "claimed_code": "P01", "capture_session": "C01",
               "split": "calibration", "direction": "left", "frames": names[3:6]}
    data = {"participants": {"P01": person}, "attempts": [attempt]}
    manifest = tmp_path / "dataset.json"
    def run():
        manifest.write_text(json.dumps(data))
        return load_dataset(manifest, "calibration", .5)
    with pytest.raises(ValueError, match="Persetujuan"):
        run()
    person["consent_confirmed"] = True
    assert len(run()[2]) == 1
    attempt["frames"] = names[:3]
    with pytest.raises(ValueError, match="Frame enrollment"):
        run()
    attempt["frames"] = names[3:6]
    data["attempts"].append(attempt | {"split": "test", "capture_session": "T01"})
    with pytest.raises(ValueError, match="tumpang tindih"):
        run()


def test_final_dataset_requires_threshold_lock(tmp_path):
    for i in range(6):
        (tmp_path / str(i)).write_bytes(str(i).encode())
    data = {"participants": {"P01": {"consent_confirmed": True, "identity_checked": True,
             "enrollment_session": "E01", "frames": ["0", "1", "2"]}},
            "attempts": [{"participant_code": "P01", "claimed_code": "P01", "capture_session": "T01",
                          "split": "test", "direction": "right", "frames": ["3", "4", "5"]}]}
    manifest = tmp_path / "dataset.json"
    manifest.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="sudah dikunci"):
        load_dataset(manifest, "test", .5)
    lock = tmp_path / "lock.json"
    lock.write_text(json.dumps({"status": "locked", "threshold": .6, "locked_at": "2026-10-22", "approved_by": "operator"}))
    with pytest.raises(ValueError, match="berbeda"):
        load_dataset(manifest, "test", .5, lock)
