# Rancangan evaluasi TA

Tujuan: merancang dan mengevaluasi verifikasi wajah serta pencatatan sesi pada
PC Windows bersama. Tidak mengklaim model/algoritma wajah baru. Jumlah peserta
dan percobaan belum ditentukan dan belum ada hasil akurasi manusia.

## Protokol data

- Rekrut peserta berizin dengan persetujuan, periksa identitas oleh operator,
  gunakan kode pseudonim pada lembar eksperimen, simpan pemetaan secara terpisah.
- Enrollment, kalibrasi dan test harus berasal dari sesi pengambilan berbeda.
  Tidak menilai frame yang digunakan membuat template. Catat waktu/sesi/kamera.
- Variasikan cahaya, jarak, kacamata, posisi dan kondisi webcam secara terencana.
  Catat kegagalan kualitas dan tantangan, bukan membuangnya diam-diam.
- Tentukan FMR/FNMR yang dituju dan aturan pemilihan threshold sebelum test.
  Isi `experiments/threshold-lock-template.json`; kunci threshold, model dan
  versi kode sebelum uji akhir. Jangan tuning menggunakan data test.
- Ambil percobaan genuine dan impostor dengan NIM yang diklaim; catat no face,
  multi-face, belum enroll, webcam gagal, server putus, foto cetak dan replay layar.
  Serangan tidak dilakukan terhadap orang/PC tanpa persetujuan.

## Metrik

FMR matcher = false match / perbandingan impostor yang memiliki skor valid.
FNMR matcher = false non-match / genuine yang memiliki skor valid. Skrip
menghitungnya pada sampel yang lolos kualitas tanpa membuang kegagalan tantangan;
serangan presentasi diberi kategori `attack` tersendiri. Definisi berbasis
perbandingan genuine/impostor mengacu [NIST FRTE 1:1](https://pages.nist.gov/frvt/html/frvt11.html).
Laporkan
denominator dan interval ketidakpastian, jumlah peserta/percobaan, kualitas/PAD
gagal, keberhasilan sesi total, serta latensi autentikasi p50/p95 terpisah.
APCER/BPCER hanya jika kategori serangan, protokol PAD dan denominator sah;
skrip dasar tidak mengeluarkan angka tersebut secara otomatis.
Keberhasilan login hanya dihitung dari baris yang benar-benar memiliki hasil
`session_opened=0/1`. Baris inferensi offline tidak diberi hasil sesi fiktif.
Satu baris adalah satu percobaan tiga frame; skor keputusan adalah minimum
cosine ketiga frame terhadap template rata-rata enrollment, sesuai kebijakan API.

## Membuat skor dari sampel berizin

`scripts.score_dataset` membaca tiga frame per enrollment/percobaan dari
direktori dataset lokal. Tidak mengambil gambar publik atau membuka kamera.
Persetujuan penyimpanan dataset penelitian harus mencakup tujuan/retensinya,
berbeda dari frame login sementara. Simpan data di `.runtime` atau
`experiments/data` yang di-ignore Git, gunakan ACL, lalu hapus sesuai persetujuan.

Salin dataset-template.json dan isi struktur berikut dengan kode pseudonim nyata
setelah peserta setuju; nama/path di contoh ini hanya format:

```json
{
  "participants": {
    "P01": {"consent_confirmed": true, "identity_checked": true,
      "enrollment_session": "ENROLL-A", "frames": ["P01/e1.jpg", "P01/e2.jpg", "P01/e3.jpg"]}
  },
  "attempts": [
    {"participant_code": "P01", "claimed_code": "P01", "capture_session": "CAL-B",
      "split": "calibration", "direction": "left", "frames": ["P01/c1.jpg", "P01/c2.jpg", "P01/c3.jpg"],
      "lighting": "normal", "camera_id": "PC01", "attack_type": "none"}
  ]
}
```

Metadata persetujuan adalah catatan tanggung jawab operator, bukan bukti identitas
otomatis. CLI menolak metadata yang belum lengkap, frame enrollment yang dipakai
ulang, tumpang tindih frame/sesi calibration–test, output yang sudah ada, dan
pengujian akhir tanpa lock threshold/model. Untuk impostor, claimed_code menunjuk
peserta lain yang juga berizin. Untuk cetak/replay, isi attack_type sesuai protokol.

```powershell
.venv/Scripts/python.exe -m scripts.score_dataset .runtime/dataset/manifest.json --split calibration --threshold 0.50 --out .runtime/calibration.csv
# Setelah kalibrasi, isi salinan threshold-lock-template.json:
# status=locked, threshold final, calibration_sessions, locked_at, approved_by, model_commit.
.venv/Scripts/python.exe -m scripts.score_dataset .runtime/dataset/manifest.json --split test --threshold 0.50 --threshold-lock .runtime/threshold-lock.json --out .runtime/test.csv
.venv/Scripts/python.exe -m scripts.evaluate_scores .runtime/test.csv --threshold 0.50 --split test --out .runtime/evaluation.json
```

Script menggunakan YuNet/SFace dan kebijakan verify yang sama. `inference_ms`
merupakan inferensi offline dua pass untuk menghindari duplikasi logika tantangan;
ini **bukan** latensi login UI/API. Isi latency_ms/session_opened dari percobaan
login nyata pada lembar attempts-template.csv. Tidak menulis frame atau embedding
ke CSV. Belum ada pengujian dataset manusia sehingga hasil akurasinya belum ada.

```powershell
.venv/Scripts/python.exe -m scripts.evaluate_scores experiments/data-test.csv --threshold 0.50 --split test --out evidence/evaluation-real.json
.venv/Scripts/python.exe -m scripts.load_test --database-url 'postgresql+psycopg://labaccess@127.0.0.1:55432/labaccess_test_20261022' --clients 35 --out evidence/load-35.json
```

Perintah threshold hanya contoh parameter; jangan menganggap 0.50 final.
CSV kosong template sengaja tidak menghasilkan hasil fiktif. `load_test`
menggunakan data sintetis/schema terpisah, bukan peserta/35 PC fisik.

## Tahapan pilot

| Tahap | Syarat dan skenario | Instrumen |
|---|---|---|
| 1 admin + 2 klien | Akun non-admin, TLS/CA, enrollment unik, login/logout/pindah PC, Veyon status + screenshot, recovery admin | pilot-template.csv, audit API, screenshot hanya berizin |
| 5–10 klien | DHCP berubah, API restart, cabut LAN, stale/reconnect, crash client, reset password, koordinasi admin | Last_seen vs waktu transisi, latensi refresh admin |
| 30–35 PC fisik | Login bersama, heartbeat 10 s, beban Veyon, CPU/RAM desktop/API, install/upgrade/uninstall | perf counters/psutil, log eksperimen, p50/p95 |
| Pembatasan OS | Uji Alt+Tab, Win, Task Manager, close/crash UI, secondary desktop, reboot dan recovery admin | Harus Win11 edisi/akun pilot yang tepat; bukan host admin ini |
| Wajah | Genuine/impostor, cahaya, no/multi-face, serangan cetak/layar | attempts-template.csv, threshold lock |

Ukur CPU/RAM desktop pada perangkat pilot menggunakan Performance Monitor atau
psutil sampling 1 detik; pisahkan idle/login/password/wajah/sesi aktif.
Jangan menyamakan RSS server simulasi dengan RAM klien desktop. Bandingkan
timestamp DB/server dengan waktu tampilan admin untuk latensi end-to-end.
