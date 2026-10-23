# Pemasangan dan pengujian Windows

## Status sebelum pemasangan lab

Host pengembangan: Windows 10 Pro 19045 x64, non-elevated. Target Windows 11
belum diuji. Baca TEST_RESULTS dan STATUS untuk status executable/installer
aktual. Jangan memasang seluruh lab sebelum satu admin + dua klien pilot lulus.

Tidak mengubah login Windows, akun bersama, shell, policy atau firewall secara
otomatis. UI login dan autostart bukan pembatasan OS. Windows 11 edisi kampus
dan kebijakannya harus diperiksa sebelum memilih mekanisme enforcement.

## Dependency sumber pada mesin baru

Gunakan Python 3.11 x64 dari sumber resmi/uv managed, Git, dan jaringan untuk
persiapan. Jangan memakai Python Microsoft Store untuk build Nuitka.

```powershell
# Jika uv belum tersedia, buat bootstrap environment tanpa memasang global:
python -m venv .tools/bootstrap
.tools/bootstrap/Scripts/python.exe -m pip install uv==0.13.5
.tools/bootstrap/Scripts/uv.exe venv --python 3.11.15 .venv
.tools/bootstrap/Scripts/uv.exe sync --locked
.venv/Scripts/python.exe -m scripts.fetch_models
```

`uv.lock` menyimpan versi, marker Python dan hash artifacts; `requirements.lock.txt`
merupakan ekspor runtime untuk pip `--require-hashes`. Bila pindah mesin gunakan
lock, bukan memasang dependency tanpa versi. Runtime awal workspace ini `.venv`
3.13.14; environment build/tes final `.tools/buildenv` 3.11.15. Keduanya terisolasi.
Perintah Python dalam panduan boleh diganti `.tools/buildenv/Scripts/python.exe`
pada workspace yang sudah disiapkan ini.

## PostgreSQL pengembangan lokal tanpa Docker/service sistem

Binary yang dipakai: PostgreSQL 17.6-1 Windows x64, dari
`https://get.enterprisedb.com/postgresql/postgresql-17.6-1-windows-x64-binaries.zip`.
Sumber rujukan: [PostgreSQL Windows](https://www.postgresql.org/download/windows/),
[EDB binaries](https://www.enterprisedb.com/download-postgresql-binaries).
Ekstrak sehingga terdapat `.tools/postgres/pgsql/bin/initdb.exe`, `lib`, `share`.
SHA256 unduhan pengembangan dicatat di `evidence/software-checksums.json`;
hash lokal ini tidak diklaim sebagai pemeriksaan signature penerbit PostgreSQL.

```powershell
./scripts/Start-LocalPostgres.ps1
.venv/Scripts/python.exe -m scripts.bootstrap --init-env
.venv/Scripts/python.exe -m alembic upgrade head
.venv/Scripts/python.exe -m scripts.bootstrap --demo
./scripts/Start-Api.ps1
```

`--init-env` menolak menimpa `.env`; bootstrap menolak jika sudah ada admin.
Jangan mengulang bootstrap untuk mereset data. Untuk admin asli, hilangkan
`--demo`, masukkan password min. 12 karakter secara interaktif. Demo menghasilkan
password acak untuk admin/DEMO001/DEMO002 dan menyimpan DPAPI di `.runtime/demo.dpapi`.
Tampilkan hanya melalui `.venv/Scripts/python.exe -m scripts.show_demo`.

Cluster lokal memakai port **55432**, listen **127.0.0.1**, trust lokal khusus
pengembangan. Ini bukan konfigurasi server LAN produksi. Hentikan hanya cluster
proyek ini dengan `scripts/Stop-LocalPostgres.ps1`, bukan menghentikan PC/service lain.

Lindungi `.env` lokal (helper hanya menarget satu file di workspace, menyimpan
backup DACL dan tidak mengubah isinya):

```powershell
./scripts/Protect-LocalSecret.ps1 -Path .env
# Rollback memakai lokasi backup persis yang dilaporkan:
./scripts/Protect-LocalSecret.ps1 -RestoreBackup .runtime/acl-ID_DARI_OUTPUT.json
```

Pada server/service produksi, tetapkan ACL untuk identitas service yang benar;
helper development ini tidak memberi akses otomatis ke akun service lain.

## Server pilot LAN

1. Sediakan PostgreSQL terpatch pada PC admin/server LAN; buat database/role
   aplikasi khusus, SCRAM password, akses DB hanya akun server. Jangan expose
   database ke seluruh mahasiswa. Port default PostgreSQL 5432 bila dipilih,
   bukan port aktif cluster dev 55432. Uji migrasi pada salinan sebelum upgrade.
2. Buat `.env` dari bootstrap lalu ubah DATABASE_URL untuk target yang jelas.
   Pindahkan key ke direktori admin/service ber-ACL. Jangan menaruh Fernet key
   dalam database atau source. Jalankan Alembic, bootstrap satu admin.
3. Siapkan hostname DNS/reservasi DHCP server. Sertifikat harus cocok hostname/IP.
   Gunakan PKI kampus atau CA pilot terbatas. Helper pilot:

```powershell
.venv/Scripts/python.exe -m scripts.create_pilot_tls --hostname admin-lab --ip 192.168.10.2 --out .runtime/tls-pilot
./scripts/Start-Api.ps1 -BindAddress 0.0.0.0 -Port 8443 -Certificate .runtime/tls-pilot/server.pem -PrivateKey .runtime/tls-pilot/server.key
```

Alamat di contoh harus diganti sesuai LAN. CA pilot 90 hari, server certificate
30 hari; helper tidak menimpa berkas. Batasi ACL private key ke admin/service
sebelum pemakaian. Salin **hanya ca.pem** ke klien, jangan CA/server private key.

4. Buka hanya TCP 8443 dari subnet PC lab pada firewall host server sesuai
   kebijakan pengelola. Tidak ada skrip yang mematikan firewall. Port API yang
   benar-benar diuji lokal 8000/port acak test; 8443 adalah opsi deployment.
5. Jalankan klien/admin dengan `--server https://admin-lab:8443 --ca C:/LabAccess/ca.pem`.
   CA harus dipercaya dan hostname harus cocok. Tidak ada opsi `--insecure`.
6. Pastikan PC admin tetap dapat masuk saat LAN/API mati. Uji backup/restore dan
   prosedur recovery sebelum mengaktifkan pembatasan OS atau kontrol Veyon.

## Aplikasi desktop dan enrollment PC

```powershell
.venv/Scripts/python.exe -m apps.admin_console.main --server http://127.0.0.1:8000
.venv/Scripts/python.exe -m apps.student_client.main --server http://127.0.0.1:8000
```

Login admin → Daftarkan PC → isi nama unik dan host Veyon terverifikasi.
Masukkan token sekali pakai 15 menit pada desktop mahasiswa. UUID dan credential
perangkat disimpan di `%LOCALAPPDATA%/LabAccess/student/device.dpapi`, terikat akun
Windows yang membuatnya. Jangan clone credential ke PC lain. Perubahan DHCP
tidak mengubah UUID; kehilangan DPAPI memerlukan enrollment ulang dan penyelesaian
sesi lama secara eksplisit. Jalur password tetap ada bila kamera/model gagal.

Di UI mahasiswa terlihat pemberitahuan pemantauan Veyon. Kamera hanya dibuka
saat capture lalu ditutup pada selesai/batal/gagal. Frame tidak disimpan lokal.

## Agent foreground dan rencana SCM

Jalur opsional untuk menghindari pemberian secret perangkat ke UI:

```powershell
whoami /user
.venv/Scripts/python.exe -m scripts.enroll_agent --server https://admin-lab:8443 --ca C:/LabAccess/ca.pem --allowed-sid SID_AKUN_UI --config .runtime/agent.dpapi
.venv/Scripts/python.exe -m services.windows_agent.worker --config .runtime/agent.dpapi
# Di sesi pengguna interaktif:
.venv/Scripts/python.exe -m apps.student_client.main --agent-pipe LabAccess-Agent
```

Isi SID aktual dan token secara interaktif. Untuk foreground, gunakan identitas
agent yang membuat DPAPI. Host SCM disediakan di service.py; belum diuji sebagai
LocalSystem. Provision DPAPI harus dilakukan di bawah identitas service yang
tepat dengan ACL ProgramData; jangan menganggap service dapat membuka DPAPI user.
Tidak ada pemasangan SCM otomatis; kamera/UI tidak pernah dijalankan dari Session 0.

## Build dan installer

Pilihan: Nuitka **4.3.1**, standalone, Python 3.11.15 x64, MinGW64 yang diunduh
Nuitka (GCC 15.2.0/mingw-w64 13.0.0). Tidak mengganti compiler/global runtime.
`pyside6-deploy` dievaluasi sebagai wrapper Nuitka; CLI langsung dipilih agar opsi
dan compiler eksplisit. Persiapan environment build:

```powershell
$env:UV_PROJECT_ENVIRONMENT='.tools/buildenv'
.venv/Scripts/uv.exe venv --python 3.11.15 .tools/buildenv
.venv/Scripts/uv.exe sync --locked
$env:NUITKA_CACHE_DIR="$PWD/.tools/nuitka-cache"
./scripts/Build-Windows.ps1 -Target all -Compiler mingw64
```

Script memakai dua compiler jobs untuk membatasi beban host. Output aplikasi:
`build/student/entry_student.dist/LabAccess-student.exe` dan
`build/admin/entry_admin.dist/LabAccess-admin.exe` bersama DLL/data di foldernya.
Jangan menyalin hanya EXE dari standalone directory. Laporan build ada di build/.

Installer terpisah memakai **NSIS 3.13** portable dari
[NSIS resmi](https://nsis.sourceforge.io/Download), ekstrak ke `.tools/nsis/nsis-3.13`.
Tidak perlu memasang NSIS secara sistem.

```powershell
.tools/buildenv/Scripts/python.exe -m scripts.license_inventory
./scripts/Build-Installers.ps1
.tools/buildenv/Scripts/python.exe -m scripts.verify_artifacts
# Hanya pada akun uji lokal yang belum memiliki instalasi ini:
./scripts/Verify-Installers.ps1
```

Output yang diharapkan (cek STATUS untuk yang benar-benar sudah dibuat):
`dist/LabAccess-student-Setup-0.1.0.exe` dan admin. Instalasi per-user ke
`%LOCALAPPDATA%/Programs/LabAccess-student` atau admin, dengan Start Menu shortcut
dan uninstaller terpisah. Tidak memasang Veyon/DB, mengganti policy, atau memasang
autostart diam-diam. Credential DPAPI/data kerja tidak dihapus saat uninstall.
Menjalankan ulang installer mengganti payload aplikasi sambil mempertahankan data.
Tutup aplikasi sebelum upgrade; validasi pada pilot sebelum deployment banyak PC.
Untuk LAN, berikan endpoint dan CA saat memasang agar shortcut Start Menu dapat
langsung dipakai sebagai aplikasi desktop:

```powershell
./dist/LabAccess-student-Setup-0.1.0.exe /SERVER=https://admin-lab:8443 /CA=C:/LabAccess/ca.pem
./dist/LabAccess-admin-Setup-0.1.0.exe /SERVER=https://admin-lab:8443 /CA=C:/LabAccess/ca.pem
```

Gunakan tanda kutip di sekitar argumen bila path mengandung spasi. Konfigurasi
endpoint/CA (tanpa credential) disimpan per pengguna pada
LocalAppData/LabAccess/connection-student.ini atau connection-admin.ini, dipakai
membentuk argumen shortcut. Upgrade tanpa opsi baru mempertahankannya; uninstall
mempertahankan konfigurasi ini dan DPAPI. URL/CA tetap diverifikasi oleh aplikasi.
Menjalankan EXE langsung dari folder tanpa argumen memakai default CLI; gunakan
shortcut terkonfigurasi untuk LAN. HTTP hanya untuk uji loopback.
Verifier menolak target, shortcut atau registry yang telah ada sebelum tes. Bukti
install/upgrade/uninstall ditulis ke evidence/installers-all.json bila kedua target
lulus (`installers-student.json` atau `installers-admin.json` untuk satu target).
Hash toolchain build dicatat di evidence/toolchain.json; laporan Nuitka menyimpan
detail modul/opsi. Kesamaan bit-per-bit antarmesin belum diklaim.

Autostart opsional dapat ditambahkan/dibatalkan melalui `Set-Startup.ps1`.
Contoh setelah installer terpasang:

```powershell
./scripts/Set-Startup.ps1 -Executable "$env:LOCALAPPDATA/Programs/LabAccess-student/app/LabAccess-student.exe" -Server https://admin-lab:8443 -Ca C:/LabAccess/ca.pem
./scripts/Set-Startup.ps1 -Remove
```

Skrip menolak menimpa startup yang sudah ada dan menolak melepas nilai yang telah
berubah di luar skrip. Catatan kepemilikan berada di LocalAppData/LabAccess.
Startup bukan pengunci OS. Lisensi/corresponding source perlu dilengkapi sesuai
[LICENSES.md](LICENSES.md) sebelum distribusi di luar pengujian internal.

## Pemeriksaan pembatasan Windows

```powershell
./scripts/Inspect-Windows.ps1
```

Catat edisi, build, hak akses, akun mahasiswa non-admin, Veyon dan kamera.
Assigned Access mode single-app pada dokumentasi Microsoft memakai UWP/Edge;
jangan menyamakan PySide6 Win32 dengan kiosk UWP. Shell Launcher dibatasi edisi
Enterprise/Education/IoT dan sendirinya tidak mencegah akses aplikasi lain.
[Assigned Access](https://learn.microsoft.com/en-us/windows/configuration/assigned-access/),
[Shell Launcher](https://learn.microsoft.com/en-us/windows/configuration/shell-launcher/).

Uji pada satu PC Win11 berizin dengan backup policy serta akun admin recovery:
Alt+Tab, Win, Task Manager, close/crash UI, boot/reboot, server mati dan rollback.
Sebelum semua lulus, status produk adalah **prototipe autentikasi dan pencatatan
sesi**, bukan PC terkunci. Credential Provider bukan default MVP.
