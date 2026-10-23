# Hasil pengujian aktual

Tanggal mulai: 22 Oktober 2026, host Windows 10 Pro 10.0.19045 x64,
non-elevated. Target Windows 11 belum diuji. Semua akun pengujian sintetis.
Tidak ada peserta manusia, data akurasi wajah atau hasil pilot fisik yang dikarang.

## Pengujian yang lulus

| Kelompok | Hasil | Bukti |
|---|---|---|
| Suite final Python 3.11.15 + PostgreSQL 17.6 | **36 passed**, 113.86 detik, sesudah perbaikan IPC dan privasi logout; satu warning kompatibilitas TestClient/httpx | `evidence/tests-release-final.xml` |
| Suite sebelum perbaikan IPC/logout | 36 passed, 114.10 detik, termasuk instrumen evaluasi dan batas waktu rate limit | `evidence/tests-final-36.xml` |
| Suite setelah filter alasan dan durasi server | 34 passed, 100.28 detik | `evidence/tests-release-complete.xml` |
| Suite PostgreSQL sebelum penyempurnaan riwayat | 34 passed, 98.90 detik | `evidence/tests-final-34.xml` |
| Suite awal SQLite (terisolasi) | 24 passed, 117.59 detik | `evidence/tests-sqlite.xml` |
| Suite lengkap SQLite | **34 passed**, 160.04 detik | `evidence/tests-final-sqlite.xml` |
| Pemeriksaan setelah audit konfigurasi/Veyon ditambahkan | **3 passed**, 35.94 detik, termasuk kedua mode desktop live | `evidence/tests-config-audit.xml` |
| Filter alasan lintas database | 1 passed pada SQLite; huruf besar/kecil dan karakter wildcard literal diperiksa | `evidence/tests-filter-sqlite.xml` |
| Suite awal PostgreSQL | 24 passed, 65.53 detik | `evidence/tests-postgres.xml` |
| Desktop Qt langsung dan via named pipe | Login pengelola, enrollment/direct atau credential agent, login mahasiswa → TCP API → DB → admin, putus API, restart, reconnect dan logout | Termasuk suite final; `evidence/desktop-student.png`, `desktop-admin.png` |
| HTTPS live | CA pilot cocok diterima; CA tidak dipercaya ditolak; HTTP remote ditolak | Termasuk suite final dan `tests-body-tls.xml` |
| Agent Windows | Named pipe lokal, ACL/SID impersonasi, metadata tanpa secret, admin endpoint ditolak, UI via bridge berjalan | Termasuk suite final, `tests-agent.xml` |
| Inferensi ML runtime nyata | Checksum model, YuNet menolak frame kosong, frame malformed ditolak; SFace mengeluarkan embedding 128 dimensi pada tensor sintetis | Termasuk suite final; bukan uji identitas/akurasi manusia |
| Kamera host | Read 640×480, release=true, 0 frame tersimpan | `evidence/camera-check.json` |
| Migrasi | Alembic revision 0001 diterapkan pada DB development PostgreSQL | `alembic_version`; tidak menggunakan SQLite fallback di produksi |
| Backup/restore | pg_dump → DB baru labaccess_restore_20261022, 3 akun dipulihkan | Backup di `.runtime` tidak masuk Git; DB asal tetap utuh |
| REA | Setup ready/exit 0, doctor exit 0, workflow aligned, konfigurasi lain identik | `rea-plan.json`, `rea-setup.json`, `rea-doctor.json` |
| Secret lokal | DACL `.env` hanya akun saat ini/SYSTEM/Administrators, isi tidak berubah; rollback DACL pada fixture lulus | `evidence/secret-acl.json` |
| Kedua EXE final | PE x64; mahasiswa 35.188.224 byte, admin 32.100.352 byte; smoke exit 0 | `evidence/artifacts.json`, `docs/ARTIFACTS.md` |
| Kedua installer final | Install → smoke → upgrade → smoke → uninstall lulus; hash cocok dengan build; konfigurasi koneksi/CA dan berkas eksternal utuh | `evidence/installers-all.json` |
| Guard evaluasi offline | 3 tes lulus; metadata consent, reuse frame, split dan lock threshold; dataset kosong CLI exit 1 tanpa hasil | `tests-evaluation-guards.xml`, `evaluation-empty-guard.json` |

Suite final mencakup password benar/salah/tidak terdaftar/nonaktif, role admin/operator/
mahasiswa, reset password, token palsu/kedaluwarsa/perangkat lain, token enrollment
sekali pakai, satu NIM/PC satu sesi, dua login simultan dan retry simultan identik,
logout idempotent, pindah PC setelah akhir administratif, stale/reconnect/restart,
CSV formula injection, filter riwayat, limit autentikasi, batas body streamed,
penolakan boolean face_verified, binding/expiry/consumption challenge, template
terenkripsi dan penghapusan tanpa menyimpan ulang biometrik pada audit.

Percobaan ulang filter SQLite sempat salah karena environment database diisi
string kosong. Environment tersebut dilepas (bukan menunjuk DB produksi), lalu
tes lulus. Tidak ada perubahan/reset database akibat kesalahan invocation itu.

Warning tersisa berasal dari Starlette TestClient yang menyarankan httpx2.
Transport produksi menggunakan httpx 0.28.1 terpin dan telah diuji; warning ini
tidak dijadikan alasan mengganti dependency tanpa uji kompatibilitas.

## 35 klien simulasi

Data/schema sintetis terisolasi di database test PostgreSQL, HTTP nyata,
satu host. Tidak menjalankan 35 GUI, 35 webcam atau 35 Veyon Server.

| Metrik | Hasil |
|---|---:|
| Login berhasil / sesi terlihat admin | 35 / 35 |
| Login p50 | 3542 ms |
| Login p95 | 4252 ms |
| Heartbeat p95 selama burst | 1886 ms |
| GET inventaris admin | 72 ms |
| Waktu burst dan logout | 5.76 s |
| Peak RSS process tree server | 970.33 MiB |

Bukti `evidence/load-35.json`, skrip `scripts/load_test.py`. Login serentak
Argon2id menggunakan RAM besar secara sengaja. Angka ini bukan beban normal
heartbeat saja dan bukan ukuran RAM/CPU klien desktop. CPU/RAM desktop, latensi
refresh visual p50/p95, beban Veyon dan 35 PC fisik masih perlu pilot.

## Kegagalan yang ditemukan dan penanganannya

1. Temp default SQLite pada pengujian awal gagal `database or disk is full`.
   Tidak menghapus data pengguna; pemindahan TEMP/basetemp khusus ke `.runtime`
   menghasilkan suite lulus. Gunakan lokasi test yang jelas pada perintah ulang.
2. Uji 35 klien awal mengalami timeout QueuePool karena autentikasi menahan satu
   koneksi lalu rate limit meminta koneksi lain dari pool sama. Pool rate limit
   dipisahkan; ulang uji 35/35 berhasil. Bukan sekadar menambah tombol/UI.
3. Named pipe awal menggunakan namespace fungsi impersonasi yang salah, lalu
   impersonasi dilakukan sebelum membaca pesan. Diperbaiki ke win32security
   setelah ReadFile; tes IPC dan desktop agent lulus.
4. Build awal Python Microsoft Store 3.13 + Zig gagal menemukan self executable
   Zig. Laporan `evidence/build-attempts/python313-zig-failed.xml`. Build final
   memakai Python 3.11 terisolasi + MinGW64; status akhir ada pada STATUS.
5. Veyon server tidak memiliki parser `--help`; percobaan memulai server dan
   melaporkan token/privilege tidak tersedia pada host user. Proses pengujian
   dihentikan, tidak memasang service/firewall. CLI about/version digunakan
   untuk verifikasi berikutnya. Kontrol live tidak diklaim berhasil.
6. Rollback DACL melalui Set-Acl meminta SeSecurityPrivilege pada host ini.
   Helper diperbaiki memakai API Windows khusus DACL tanpa mengubah privilege,
   owner atau SACL. ACE/SID/mask/proteksi inheritance pada fixture pulih identik;
   flag auto-inherited dinormalisasi Windows.
7. Uji rate limit pernah melewati pergantian menit sehingga percobaan ke-11
   masuk jendela baru (35/36 tes lulus). Kebijakan server fixed-window sesuai
   desain; tes diperbaiki memakai clock server terkontrol dan memeriksa reset
   jendela juga. Laporan kegagalan dipertahankan di
   `evidence/tests-rate-boundary-failed.xml`, bukan dihapus.
8. Tes desktop melalui agent menemukan respons named pipe hilang ketika server
   memanggil DisconnectNamedPipe sebelum klien membaca. Server kini memanggil
   FlushFileBuffers dan klien menunggu ketersediaan instance pipe. Uji pembaca
   lambat nyata serta kedua alur desktop lulus **3/3 dalam 43,64 detik**
   (`evidence/tests-ipc-logout-final.xml`). Percobaan gagal dipertahankan.
   Logout admin juga menghapus tabel dan mengabaikan callback dari token lama.
   Timeout I/O service SCM terhadap klien lokal yang sengaja tidak membaca masih
   merupakan batasan yang harus diselesaikan sebelum pemasangan service produksi.

## Belum lulus / belum dijalankan

- REA discovery MCP pada sesi Codex baru dan operasi baca-saja identitas server.
- Veyon Service + Master pilot, koneksi terautentikasi, screenshot/control live.
- Enrollment/verifikasi wajah manusia, kalibrasi threshold, FMR/FNMR,
  no/multi-face dengan peserta nyata, foto cetak/replay/deepfake dan PAD.
- SCM LocalSystem/provisioning credential/ACL produksi dan recovery service.
- Uji runtime startup HKCU: host menolak pembuatan proses perintah verifikasi
  dengan `Access is denied (os error 5)` sebelum perintah berjalan. Sintaks
  skrip valid; registrasi/rollback startup belum dinyatakan lulus. Tidak
  mengganti izin lingkungan untuk memaksakan pengujian ini.
- Windows 11 non-admin, enforcement OS dan jalur recovery setelah policy/crash.
- Pilot satu admin + dua klien, kemudian 5–10 dan 30–35 PC fisik.
- Build EXE/install/upgrade/uninstall: lihat STATUS dan artifacts.json; jangan
  menyamakan hasil Windows 10 yang sudah lulus dengan hasil pilot Windows 11.
