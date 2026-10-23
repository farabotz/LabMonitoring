# Artefak prototipe 0.1.0

Build final 23 Oktober 2026, Windows 10 Pro 19045 x64 non-elevated, Python
3.11.15, Nuitka 4.3.1, PySide6 6.10.3, GCC 15.2.0/MinGW-w64 13.0.0, NSIS 3.13.
Tidak ada pengujian Windows 11 atau sertifikat penerbit pada binary ini.
Tautan `dist` dan `build` di bawah menunjuk artefak workspace lokal, bukan berkas
yang disimpan di repository GitHub. Gunakan skrip build pada mesin Windows bila
memulai dari clone source.

## Installer terpisah yang benar-benar dibuat

| Aplikasi | Berkas | Ukuran byte |
|---|---|---:|
| Mahasiswa | [LabAccess-student-Setup-0.1.0.exe](../dist/LabAccess-student-Setup-0.1.0.exe) | 89.798.093 |
| Admin | [LabAccess-admin-Setup-0.1.0.exe](../dist/LabAccess-admin-Setup-0.1.0.exe) | 88.468.677 |

Kedua installer lulus install → smoke → upgrade → smoke → uninstall per-user.
Verifier mencocokkan SHA256 EXE terpasang dengan EXE hasil build, memeriksa CA
dengan path berisi spasi, serta mempertahankan konfigurasi koneksi dan berkas
sentinel di luar payload. Laporan lengkap: [installers-all.json](../evidence/installers-all.json).
Fixture pemasangan sudah dilepas; tidak meninggalkan aplikasi terpasang otomatis.

Stub installer NSIS adalah PE x86 (`0x14c`), sedangkan **kedua aplikasi payload
adalah PE x64 (`0x8664`)**. Ini bukan perubahan ekstensi file Python.

## Executable standalone

| Aplikasi | Jalur | Byte EXE | Smoke exit | Peak RSS startup |
|---|---|---:|---:|---:|
| Mahasiswa | build/student/entry_student.dist/LabAccess-student.exe | 35.188.224 | 0 | 103,81 MiB |
| Admin | build/admin/entry_admin.dist/LabAccess-admin.exe | 32.100.352 | 0 | 96,20 MiB |

DLL/data dalam folder `.dist` wajib disertakan jika tidak memakai installer.
Pengukuran RSS mencakup startup/jendela login smoke selama sekitar 2 detik;
total proses 5,79/3,96 detik termasuk startup. Ini bukan beban sesi aktif, kamera,
steady-state, atau hasil perangkat Windows 11. Peak CPU ternormalisasi terhadap
4 logical core adalah 29,10%/28,68%. Bukti PE/hash/smoke: [artifacts.json](../evidence/artifacts.json).

## Source, hash dan reproduksi

[LabAccess-source-0.1.0.zip](../dist/LabAccess-source-0.1.0.zip) berisi source,
migrasi, lockfile, build/installer scripts, notice lisensi, dokumentasi dan bukti
uji sintetis. Tidak berisi `.env`, credential DPAPI, DB, key, dataset peserta,
atau bobot ONNX; bobot disiapkan lewat `scripts.fetch_models` dengan checksum.
[SHA256SUMS.txt](../dist/SHA256SUMS.txt) mencatat hash kedua installer, kedua EXE
dan source archive. Tidak mengklaim reproducibility bit-per-bit antarmesin.
Arsip dan manifest dibuat ulang dengan
`.tools/buildenv/Scripts/python.exe -m scripts.bundle_source` setelah source
masuk daftar Git; jangan memasukkan key/data privat ke daftar tersebut.

Langkah build yang dipakai tercantum di [SETUP_WINDOWS.md](SETUP_WINDOWS.md).
Laporan Nuitka berada di `build/student-report.xml` dan `build/admin-report.xml`;
log lokal final `.runtime/build-release-final.log`. Toolchain/hash lock dicatat
di [toolchain.json](../evidence/toolchain.json).

Server/API dan PostgreSQL disiapkan terpisah; installer desktop tidak memasang
service, Veyon, startup, firewall atau policy Windows. Gunakan TLS/CA saat LAN.
Selesaikan corresponding source/notice yang diwajibkan [lisensi](LICENSES.md)
sebelum distribusi luar pengujian internal. SmartScreen/antivirus dan instalasi
Win11, enforcement OS, Veyon live serta pilot fisik belum dinyatakan lulus.
