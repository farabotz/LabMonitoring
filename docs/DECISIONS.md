# Keputusan implementasi

Tanggal pemeriksaan: 22 Oktober 2026. Semua default dapat ditinjau setelah pilot.

| Keputusan | Dasar dan konsekuensi |
|---|---|
| Companion desktop + server sesi, tanpa fork Veyon | Fungsi identitas/audit terpisah; Veyon menangani remote desktop. Source tag 4.11.4 cukup menjelaskan kontrak. REA tidak digunakan untuk dekompilasi tanpa tujuan. |
| Windows 10 Pro host pengembangan, Windows 11 target | Host nyata 19045, non-elevated. Belum ada klaim enforcement/instalasi lab. |
| PostgreSQL 17.6 portable lokal, port 55432 | Tidak memasang service sistem. Cluster pengembangan khusus loopback; autentikasi trust hanya untuk development. Server pilot produksi memakai SCRAM, role terbatas, backup dan TLS. Upgrade patch PostgreSQL sebelum produksi setelah uji kompatibilitas. |
| Python 3.11 untuk build; venv awal 3.13 untuk pengembangan saat pemeriksaan | Python dari Microsoft Store ditemukan pada venv awal. Build menggunakan environment terisolasi 3.11 yang kompatibel MinGW Nuitka; tidak mengubah runtime global. Versi dependency dan hash ada di uv.lock. |
| Nuitka standalone + installer terpisah | `pyside6-deploy` merupakan wrapper Nuitka; CLI Nuitka langsung memberikan compiler/options eksplisit dan laporan build. Direktori DLL Qt tetap dinamis untuk penggantian library dan lisensi. |
| Enrollment device UUID acak + token sekali pakai | ID bertahan dalam DPAPI sampai unenrollment/install ulang; IP DHCP bukan identitas. Kehilangan credential memerlukan pendaftaran ulang oleh admin dan penanganan sesi lama. |
| Direct UI heartbeat sebagai jalur MVP yang diuji | Credential DPAPI milik akun Windows bersama; serangan dengan hak akun tersebut tetap dalam threat model. Agent dengan named pipe disediakan terpisah, belum dipasang sebagai LocalSystem. |
| Password Argon2id, JWT HS256 60 menit | Token sesi terikat device_id, diverifikasi bersama credential perangkat dan status sesi di DB. Heartbeat perangkat mengeluarkan token baru untuk sesi yang masih terbuka. Reset password mencabut token admin melalui auth_version. |
| Dua partial unique indexes pada sesi ended_at IS NULL | Satu NIM dan satu device hanya memiliki satu sesi terbuka, termasuk saat stale. Transaksi/constraint mengatasi race antar request/server. |
| Idempotency key global unik | Password dan wajah memiliki fingerprint HMAC berisi perangkat, user, metode dan proof. Retry identik mengembalikan sesi sama; request lain dengan key sama ditolak. |
| Heartbeat 10 s, stale 30 s, grace 30 menit | Hilangnya heartbeat tidak menutup sesi otomatis. Grace memicu prosedur bantuan manual; sesi tetap dicadangkan sampai rekoneksi/admin menyelesaikannya. Tidak mematikan aplikasi Windows. |
| Waktu UTC server | `last_seen` menyimpan bukti terakhir. `ended_at` saat deteksi restart/admin adalah waktu transisi, bukan waktu persis terakhir pemakaian. |
| Face default off, threshold awal 0.50 | Ini parameter kerja yang BELUM dikalibrasi, bukan akurasi/threshold final. Server memeriksa tiga frame dan gerakan geometris acak berumur 30 s. Bukan PAD terlatih. |
| Retensi usulan | Template hanya selama mengikuti penelitian; penghapusan eksplisit melalui UI/API. Sesi selesai 90 hari lewat maintenance. Audit disimpan sampai kebijakan kampus menetapkan retensinya; belum otomatis dipangkas. Backup memiliki retensi terpisah. |
| TLS untuk LAN, HTTP hanya loopback | Tidak ada verify=False dan tidak membuka firewall menyeluruh. WebAPI Veyon default bind Any pada source; wajib TLS+ACL/firewall saat disiapkan di pilot. |
| Peran operator/admin | Operator mengelola mahasiswa, riwayat, akhir sesi, status/screenshot Veyon. Hanya admin membuat operator/admin, enroll device, mengubah mapping, mengunci layar, melihat audit. |
| Akun sintetis dengan password acak | Tidak ada password demo tetap. Berkas demo DPAPI lokal diabaikan Git. |

Belum ada SSO/OIDC kampus, Credential Provider, algoritma pengenal wajah baru,
penilaian sebab kerusakan, atau klaim keamanan OS.
