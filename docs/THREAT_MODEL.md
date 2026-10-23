# Threat model dan batas prototipe

## Aset dan lawan

Aset: password/hash, template biometrik, frame sementara, secret perangkat,
token admin/sesi, pemetaan perangkat, kunci Veyon, riwayat dan integritas audit.
Lawan: mahasiswa pada akun Windows bersama yang mencoba melewati UI, rekan di
LAN, pencurian database/backup, operator melampaui haknya, replay/foto/deepfake,
serta salah konfigurasi admin. Admin OS/server memiliki kuasa besar dan tetap
merupakan pihak tepercaya; prototipe tidak tahan kompromi administrator OS.

| Ancaman | Kontrol yang diimplementasikan | Batas/bukti lanjutan |
|---|---|---|
| Menebak password/NIM | Argon2id salt acak, rate limit counter DB, pesan generik | Rate limit per NIM dapat disalahgunakan untuk menolak layanan; distribusi serangan perlu evaluasi |
| Mahasiswa memanggil API admin | JWT bertipe terpisah, role dan active/auth_version dibaca DB | Tes otorisasi tersedia; uji penetrasi eksternal belum dilakukan |
| Device palsu/DHCP | Secret per PC, hash DB, enrollment sekali pakai, UUID stabil | Credential direct mode dapat diakses proses dengan identitas Windows bersama yang sama; DPAPI tidak melawan pemilik akun itu |
| Login ganda/retry | Transaksi, lock row perangkat, partial unique index, fingerprint HMAC | Diuji SQLite dan PostgreSQL; load 35 PC fisik belum |
| Pencurian token sesi | TTL 60 menit, binding device + secret, ended_at diperiksa | Rotasi signing key membatalkan semua token; prosedur koordinasi diperlukan |
| Replay wajah | Challenge acak 30 s, device binding, consumed atomik, kualitas + gerakan | Tidak ada trusted camera/attestation. Klien terkompromi dapat mengirim frame palsu. Gerakan RGB bukan PAD terlatih |
| Kebocoran biometrik | Fernet authenticated encryption, key terpisah dari DB, tidak ada endpoint download, frame RAM sementara | Python/OpenCV tidak menjamin secure erase seluruh salinan RAM. Dump + key bersama membuka data. Backup lama perlu dihapus sesuai retensi |
| MITM LAN | TLS wajib untuk remote, CA diverifikasi, HTTP hanya loopback | Sertifikat/ACL jaringan pilot belum dipasang. Klien lokal OS berbahaya dapat mengakses server dev loopback |
| Salah host Veyon | Mapping device_id ke host hanya admin, audit kontrol, kunci hanya server | Verifikasi fisik hostname/IP sebelum kontrol. DHCP host Veyon sebaiknya DNS/reservasi |
| Mengunci/memutus pekerjaan | Konfirmasi UI dan alasan kontrol/akhir sesi; tidak ada poweroff/reboot API | Pembatasan OS belum tersedia. Jalur recovery admin harus diuji sebelum enforcement |
| Melampaui scope agent | Named pipe ACL, local-only, SID impersonasi dan allowlist | Satu koneksi pipe dapat menahan worker; timeout I/O dan denial-of-service hardening perlu uji sebelum SCM produksi |
| Menyalahkan pengguna dari log | UI/dokumen menyatakan log bukan bukti sebab kerusakan | Investigasi perlu bukti tambahan dan prosedur kampus |

## Penyimpanan dan operasi

`.env`, `.runtime`, `.tools`, model besar, kunci, database dan credential tidak
masuk Git. `.env` pengembangan berisi key; produksi pindahkan ke direktori
ProgramData dengan ACL akun service+admin, dan lindungi media backup. Tidak ada
keylogger, rekaman layar kontinu, rekaman webcam sepanjang sesi, pengiriman
data NIM/wajah ke REA, maupun model cloud.

Capture klien berada di RAM. Parser multipart Starlette 1.9.0 menggunakan spool
1 MiB: upload lebih besar dapat memakai TEMP server sebelum `UploadFile` ditutup.
Kode menutup file setelah dibaca; cleanup request juga menutup upload. TEMP
produksi harus ber-ACL identitas server dan berada pada volume yang terlindungi.
Penghapusan file sementara bukan jaminan secure erase media/RAM. Dataset evaluasi
offline disimpan hanya dengan persetujuan/retensi penelitian yang terpisah.

Retensi 90 hari dan periode template merupakan usulan penelitian, belum
persetujuan kebijakan kampus. Consent, tujuan, hak menarik diri dan prosedur
penghapusan harus diberikan sebelum enrollment manusia.
