# LabAccess

Prototipe desktop pengelolaan sesi PC lab bersama, Python/PySide6 + FastAPI + PostgreSQL.
NIM berasal dari sesi aplikasi; akun Windows bersama tetap terpisah. Veyon menangani
pemantauan/bantuan jarak jauh. Nama aplikasi dapat diubah lewat `LABACCESS_APP_NAME`.

**Status dan hasil aktual:** [STATUS.md](STATUS.md), [hasil uji](docs/TEST_RESULTS.md).
UI login bukan pengunci Windows. Wajah bersifat eksperimental dan default nonaktif.
Riwayat penggunaan tidak membuktikan penyebab kerusakan.

Installer sudah dibangun dan diuji pada host Windows 10 x64, tersedia lokal di
`dist/LabAccess-student-Setup-0.1.0.exe` dan `dist/LabAccess-admin-Setup-0.1.0.exe`.
Folder `dist`/`build` merupakan output lokal dan tidak disimpan di Git. Untuk
mesin baru ikuti [panduan build](docs/SETUP_WINDOWS.md).
Lihat [artefak dan cakupan verifikasi](docs/ARTIFACTS.md). Windows 11 masih memerlukan pilot.

## Jalankan paling cepat pada workspace yang telah disiapkan

PowerShell dari root proyek:

```powershell
./scripts/Start-LocalPostgres.ps1
./scripts/Start-Api.ps1
# Terminal kedua:
& ./build/admin/entry_admin.dist/LabAccess-admin.exe
# Terminal ketiga:
& ./build/student/entry_student.dist/LabAccess-student.exe
# Tampilkan password sintetis acak hanya pada dialog lokal:
.venv/Scripts/python.exe -m scripts.show_demo
```

Alternatif dari source: `.venv/Scripts/python.exe -m apps.admin_console.main`
dan `.venv/Scripts/python.exe -m apps.student_client.main`.

Login admin, gunakan **Daftarkan PC**, lalu masukkan token 15 menit pada aplikasi
mahasiswa. Login sebagai `DEMO001`/`DEMO002` dengan password dari dialog. Identitas
perangkat disimpan DPAPI; jangan menyalin berkas perangkat ke PC lain.

Untuk mesin baru, dependency, model, PostgreSQL, TLS LAN, build dan pemasangan,
ikuti [SETUP_WINDOWS.md](docs/SETUP_WINDOWS.md). Tidak perlu Docker Desktop.

## Pengujian

```powershell
$env:TEMP="$PWD/.runtime/tmp"; $env:TMP=$env:TEMP
.venv/Scripts/python.exe -m pytest -q --basetemp=.runtime/tests
# PostgreSQL test wajib database baru dengan awalan labaccess_test_:
$env:LABACCESS_TEST_DATABASE_URL='postgresql+psycopg://labaccess@127.0.0.1:55432/labaccess_test_20261022'
.venv/Scripts/python.exe -m pytest -q --basetemp=.runtime/tests-pg
```

Suite memisahkan schema PostgreSQL per tes; tidak mereset database aplikasi.
`--basetemp` adalah folder khusus hasil tes yang boleh dibersihkan pytest.

## Peta dokumen

- [Arsitektur dan data](docs/ARCHITECTURE.md), [keputusan](docs/DECISIONS.md), [threat model](docs/THREAT_MODEL.md)
- [API](docs/API.md), [wajah dan threshold](docs/FACE_ENROLLMENT.md), [gangguan dan pemulihan](docs/OPERATIONS.md)
- [Veyon](docs/VEYON.md), [REA](docs/REA_SETUP.md), [evaluasi TA](docs/EVALUATION.md)
- [Lisensi dan atribusi](docs/LICENSES.md), [batasan](docs/LIMITATIONS.md)

REA hanya alat pengembangan. Aplikasi mahasiswa tidak memerlukan Node/REA/internet
setelah dependency/model disiapkan. Source ini tidak mengandung credential kampus,
data wajah mahasiswa atau password bawaan tetap.
