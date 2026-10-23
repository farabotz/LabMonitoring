# Operasi, gangguan, retensi dan pemulihan

## Sesi dan gangguan

Satu NIM dan satu device hanya memiliki satu sesi dengan ended_at kosong.
Heartbeat default 10 detik, stale setelah 30 detik. Stale adalah status koneksi,
bukan logout. `last_seen` mencatat bukti terakhir server menerima heartbeat.
Tidak ada estimasi waktu logout yang disamarkan sebagai waktu pasti.

Ketika server/LAN tidak tersedia: pembukaan sesi baru ditolak; desktop menampilkan
pesan bantuan. Sesi yang sudah aktif tetap ada, tidak menutup pekerjaan Windows.
Grace default 30 menit adalah batas eskalasi ke pengelola; setelah itu pengelola
memeriksa PC secara langsung dan mengakhiri/memulihkan dengan alasan. Prototipe
tidak otomatis mengunci saat grace habis. Tidak ada bypass offline tersembunyi.

Restart API tidak menggandakan sesi. UI restart pada boot Windows yang sama dapat
memulihkan melalui credential perangkat + heartbeat. Perubahan boot_id dari
psutil.boot_time menandai sesi lama interrupted dengan alasan device_restart_detected.
Waktu ended_at adalah waktu deteksi transisi; last_seen tetap menjadi batas bukti
penggunaan sebelum restart. Perangkat yang tidak pernah kembali memerlukan
penyelesaian manual admin. Perubahan jam OS klien dapat memengaruhi boot_id dan
harus diperiksa pada pilot; waktu sesi tetap server UTC.

Untuk pindah PC: logout normal dahulu. Jika crash/lupa logout, pengelola memberi
peringatan dan memeriksa PC lama → Akhiri sesi dengan alasan → login PC baru.
Tidak menutup paksa aplikasi mahasiswa. Pengakhiran administratif tidak membuktikan
mahasiswa melakukan kesalahan.

## Backup dan restore

```powershell
./scripts/Backup-Database.ps1 -Destination 'D:/backup-pilot/labaccess-YYYYMMDD.dump'
./scripts/Restore-Database.ps1 -Backup 'D:/backup-pilot/labaccess-YYYYMMDD.dump' -NewDatabase labaccess_restore_YYYYMMDD
```

Skrip tidak menimpa backup/DB lama. Restore hanya ke nama baru berawalan
labaccess_restore_. Uji jumlah record, sesi dan dekripsi template dengan key
yang benar sebelum mengganti DATABASE_URL. Restart API dan cek koneksi desktop.
Database produksi port/user/host dapat diisi melalui parameter skrip.

Gunakan media terenkripsi, ACL pengelola, jadwal backup dan uji restore berkala.
Cadangkan Fernet/signing key **terpisah** dari dump. Kehilangan key biometrik
berarti template tidak bisa dipulihkan; lakukan enrollment ulang. Key/dump lama
yang masih tersedia membuat template terhapus tetap dapat dipulihkan: jadwalkan
pemusnahan backup/kunci sesuai kebijakan. Tidak ada key/backup di Git.

## Retensi dan penghapusan

Usulan pilot: template selama mengikuti penelitian, log sesi selesai 90 hari.
Sesuaikan dengan kebijakan kampus/consent. Template dihapus nyata via UI/API
DELETE. Audit penghapusan menyimpan NIM/tindakan saja, tanpa embedding/frame.

```powershell
.venv/Scripts/python.exe -m scripts.maintenance
# Tinjau jumlah/target, lalu jalankan sesuai kebijakan yang disetujui:
.venv/Scripts/python.exe -m scripts.maintenance --apply
```

Maintenance hanya menghapus sesi yang telah berakhir dan melewati retensi,
challenge/enrollment/bucket yang kedaluwarsa. Sesi stale yang masih terbuka
tidak dihapus. Audit belum dipangkas otomatis; tetapkan retensi audit terpisah.

## Pemulihan admin

1. Pertahankan akun administrator Windows terpisah dari akun mahasiswa non-admin.
   Jangan menyimpan password Windows pada LabAccess.
2. Jika UI crash/tidak tersedia, masuk melalui akun admin Windows dan jalankan
   desktop admin dari executable/sumber; API/DB dapat dijalankan ulang tanpa reset.
3. Jika password admin LabAccess hilang, pengelola server berwenang menjalankan:

```powershell
.venv/Scripts/python.exe -m scripts.recover_admin --account admin --reason 'Pemulihan oleh pengelola server'
```

Password diminta interaktif, target harus admin yang ada, semua token admin lama
dicabut lewat auth_version. Akses lokal ke key/database harus dijaga karena skrip
pemulihan memang memberi kuasa pengelola server.

Startup per-user dapat dibatalkan dengan `scripts/Set-Startup.ps1 -Remove`.
Skrip ini tidak memasang shell/policy. Veyon lock dibuka melalui Master menggunakan
akun/key admin. Sebelum mencoba enforcement pada pilot, buat snapshot/backup policy,
uji jalur akun admin saat crash, jaringan putus dan reboot. Belum ada policy enforcement
LabAccess yang diaktifkan oleh sesi pengembangan ini.

## Agent Windows opsional

`services/windows_agent/worker.py` adalah proses tanpa kamera/UI. `service.py`
adalah host SCM, **belum dipasang/diuji sebagai LocalSystem**. Bridge named pipe
memiliki ACL, pembatasan lokal, impersonasi SID dan allowlist. UI dapat memakai
`--agent-pipe LabAccess-Agent`, sementara heartbeat/secret dipegang agent.

Untuk uji foreground tanpa SCM: enroll dengan `scripts.enroll_agent` di bawah
identitas Windows agent yang benar, lalu jalankan worker dengan config DPAPI
tersebut. Konfigurasi contoh dan perintah ada di SETUP_WINDOWS. Jangan membuat
config DPAPI milik user biasa lalu menganggap LocalSystem dapat membacanya.
SCM produksi masih memerlukan provisioning service account/ACL, timeout I/O
pipe dan uji recovery pada pilot; jangan mendaftarkan service secara massal.
