# Checkpoint LabAccess

22–23 Oktober 2026 — implementasi awal berlangsung pada Windows 10 Pro 19045 x64.
Workspace awal kosong, tidak ada AGENTS.md yang ditemukan di workspace/induk.
Git diinisialisasi lokal. Pemilik mengizinkan sinkronisasi source ke repository
privat `https://github.com/farabotz/LabMonitoring` pada 23 Oktober 2026.
Commit menggunakan identitas Git pemilik, tanpa co-author atau atribusi bot.
Riwayat awal remote dipertahankan. Secret, dependency, DB dan artefak build lokal
tidak dimasukkan ke Git; publikasi binary/release tidak dilakukan oleh sinkronisasi ini.

## Target sesi

1. Pasang REA khusus profil Codex aktif, simpan bukti JSON dan batas discovery.
2. Alur password desktop → FastAPI → PostgreSQL → admin, dengan pengujian transaksi.
3. Adapter Veyon versi stabil terpin, verifikasi wajah nyata, build Windows dan dokumentasi pilot.

## Batas yang sudah diketahui

- Host bukan Windows 11; OS enforcement belum terbukti. UI login bukan pengunci OS.
- Pemeriksaan awal tidak menemukan Veyon/PostgreSQL terpasang. Kini PostgreSQL
  portable proyek berjalan di loopback; Veyon hanya diekstrak untuk pemeriksaan.
  Tidak ada kebijakan Windows yang diubah.
- Node global 22.16.0 dipertahankan; runtime REA 22.19.0 terisolasi, checksum resmi diperiksa.

## Checkpoint implementasi yang sudah dibuktikan

- Backend password, admin/operator, enrollment PC sekali pakai, constraint sesi,
  idempotency, heartbeat/stale/restart, logout, riwayat CSV dan audit berjalan.
- Desktop mahasiswa/admin → TCP Uvicorn → PostgreSQL diuji, termasuk API mati/restart.
  Mode direct serta named pipe agent foreground sudah lulus. SCM LocalSystem belum.
- Tes final Python 3.11/PostgreSQL: **36 lulus dalam 113,86 detik**, sesudah
  perbaikan IPC dan privasi logout admin. Laporan evidence/tests-release-final.xml.
  Termasuk limit body streaming, filter alasan, durasi server dan guard dataset.
  Suite lengkap SQLite juga 34 lulus; filter tambahan 1 lulus, tanpa skips.
- Uji 35 klien simulasi sesudah perbaikan pool: 35/35 berhasil; login p95 4252 ms,
  inventaris admin 72 ms. Bukan 35 PC fisik. evidence/load-35.json.
- YuNet/SFace terpin, checksum dan lisensi diverifikasi; inferensi deteksi/embedding
  nyata, tantangan acak, enrollment terenkripsi dan delete API tersedia.
  Belum ada enrollment peserta manusia, kalibrasi/akurasi atau uji replay.
- Kamera host dibuka/read 640x480/ditutup; tidak menyimpan frame.
- HTTPS nyata lolos dengan CA pilot dan menolak CA tidak dipercaya.
- Backup/restore ke labaccess_restore_20261022 berhasil, 3 akun dipulihkan,
  database asal tidak ditimpa. Retensi default dry-run.
- DACL `.env` development dibatasi ke identitas saat ini/SYSTEM/Administrators,
  isi tetap sama. Backup `.runtime/acl-37afaf13be2e43ab89d6833830151f55.json`.
  Rollback diuji pada fixture terpisah; helper tidak mengubah policy/privilege OS.
- REA 6.7.0 setup ready, doctor exit 0, workflow v42 aligned. Konfigurasi selain
  REA identik. MCP sesi aktif belum ditemukan: restart Codex diperlukan nanti.
- Veyon binary 4.11.4 + signature/checksum dan kontrak source tag diperiksa.
  Service/monitoring/control live belum diuji; host non-elevated tanpa service.

## Build dan kemasan

- **Kedua EXE final x64 berhasil**, 23 Oktober 01:09 WIB, semua proses build/QA
  telah selesai exit 0. Mahasiswa 35.188.224 byte; admin 32.100.352 byte.
  Lokasi `build/student/entry_student.dist/LabAccess-student.exe` dan
  `build/admin/entry_admin.dist/LabAccess-admin.exe`. DLL folder wajib disertakan.
- **Kedua installer final lulus** install/smoke/upgrade/smoke/uninstall per-user.
  Mahasiswa `dist/LabAccess-student-Setup-0.1.0.exe` (89.798.093 byte);
  admin `dist/LabAccess-admin-Setup-0.1.0.exe` (88.468.677 byte).
  SHA256 EXE terpasang cocok dengan build; konfigurasi/CA/data eksternal utuh.
  Bukti utama `evidence/installers-all.json`, `evidence/artifacts.json`, docs/ARTIFACTS.md.
  Fixture instalasi sudah dilepas; tidak meninggalkan pemasangan otomatis.
- Smoke EXE exit 0; peak RSS startup mahasiswa 103,81 MiB, admin 96,20 MiB.
  Ini pengukuran jendela login singkat, bukan sesi aktif atau kamera/Windows 11.
- Source final memuat flush respons named pipe, retry ketersediaan pipe, serta
  pembersihan data/callback logout admin. Suite final 36/36 sudah lulus sesudahnya.
- Uji runtime startup ditolak host saat membuat proses perintah (`Access is
  denied`, os error 5), belum lulus; tidak ada izin lingkungan yang dinonaktifkan.

Build final memakai Python 3.11.15 + Nuitka 4.3.1 + MinGW64, dua compiler jobs.
Log awal `.runtime/build-final.log`, rebuild `.runtime/build-release-final.log`. Build awal Python
Store 3.13 + Zig gagal (bukti XML di evidence/build-attempts); tidak disebut EXE.
Tidak ada compiler/verifier yang masih berjalan. Source dan checksum akhir
tersedia di `dist/LabAccess-source-0.1.0.zip` dan `dist/SHA256SUMS.txt`.

## Melanjutkan bila sesi terputus

1. Baca dokumen ini dan docs/REA_SETUP.md. Setelah restart Codex, baca workflow
   reverse-engineer-anything dan cek discovery MCP/identitas baca-saja sesuai skill.
2. Pilot berizin satu admin + dua PC Windows 11: periksa edisi/akun non-admin,
   siapkan TLS/CA API dan Veyon 4.11.4 Service/Master/WebAPI; cocokkan mapping fisik.
3. Uji status/screenshot/kontrol Veyon nyata dan recovery admin. Pembatasan OS
   memerlukan backup policy, jalur rollback dan bukti uji pada edisi pilot.
4. Provision agent SCM di bawah identitas service yang benar, selesaikan timeout
   I/O pipe dan uji ACL/recovery; jangan menganggap DPAPI user dapat dibaca SYSTEM.
5. Enrollment peserta dengan persetujuan, kalibrasi/lock threshold dan dataset
   terpisah; uji foto/replay. Lanjutkan 5–10 lalu 30–35 PC fisik dengan instrumen.
6. Startup masih perlu uji pada host pilot berizin. Lengkapi lisensi/source
   dependency sebelum distribusi luar. Jangan mereset DB; push/publish hanya
   sesuai instruksi pemilik dan target yang diberikan.

## Jalankan workspace saat ini

```powershell
./scripts/Start-LocalPostgres.ps1
./scripts/Start-Api.ps1
# Terminal terpisah:
& ./build/admin/entry_admin.dist/LabAccess-admin.exe
& ./build/student/entry_student.dist/LabAccess-student.exe
.venv/Scripts/python.exe -m scripts.show_demo
```

Credential sintetis acak disimpan DPAPI di .runtime/demo.dpapi; tidak ada password
bawaan tetap. Jangan mengulang bootstrap pada database yang sudah berisi admin.
