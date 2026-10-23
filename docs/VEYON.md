# Integrasi Veyon

## Pin dan kontrak

Release stabil terverifikasi: **Veyon 4.11.4**, terbit 15 Oktober 2026.
Installer Windows x64 `veyon-4.11.4.0-win64-setup.exe`:
SHA256 `bb428d1779a4e54055c8439c069e824904377ddc2e76b5e273cabd9d867f43ed`.
Signature Authenticode installer pada host: **Valid**. Metadata GitHub disimpan
di `evidence/veyon-release.json`. Paket diekstrak ke `.tools/veyon`, bukan
dipasang sebagai service sistem.

CLI `about` mengonfirmasi 4.11.4, Qt 6.10.3, OpenSSL 3.5.9. Source diperiksa
pada [tag v4.11.4](https://github.com/veyon/veyon/tree/v4.11.4).
[Dokumentasi WebAPI](https://docs.veyon.io/en/latest/developer/webapi.html)
yang dibaca masih berlabel 4.10.4; fitur ditentukan dari source tag, tidak main.

| Operasi adapter | Kontrak resmi pada tag |
|---|---|
| Koneksi | POST `/api/v1/authentication/<HOST>` dengan `method`, `credentials` |
| AuthKeys | UUID `0c69b301-81b4-42d6-8fae-128cdd113314`, keyname dan PEM private key |
| Header berikutnya | `Connection-Uid` dari `connection-uid` respons |
| Status autentikasi | GET `/api/v1/user` dalam koneksi terautentikasi |
| Screenshot saat diminta | GET `/api/v1/framebuffer?format=jpeg&quality=70&width=960` |
| Kunci layar administratif | PUT `/api/v1/feature/ccb535a2-1d24-4cc1-a709-8b47d2b2ac79`, active+arguments |
| Tutup koneksi | DELETE `/api/v1/authentication/<HOST>` dengan header koneksi |

Adapter selalu mencoba menutup koneksi setelah operasi. Tidak ada endpoint
reboot, poweroff, logoff Windows atau injeksi credential Windows. Password
akun Windows bersama tidak disimpan. Informasi Windows user hanya diberi label
Windows user; NIM admin berasal dari tabel sessions sesuai device_id.

## Persiapan pilot yang harus dilakukan pengelola

1. Pasang installer resmi x64 di **satu admin + dua klien pilot** menggunakan
   hak admin. Master pada admin, Service pada klien; jangan rollout seluruh lab.
2. Backup konfigurasi sebelum perubahan melalui Configurator/CLI export.
   Simpan di direktori admin ber-ACL. Buat key pair berbeda untuk pengelola;
   hanya public key yang dipasang ke klien. Private key tidak boleh di mahasiswa.
3. Periksa access control Veyon agar hanya admin/pengelola yang berhak. Uji
   koneksi menggunakan Master dahulu, termasuk verifikasi host/IP secara fisik.
4. Siapkan WebAPI pada admin (`veyon-cli webapi runserver` adalah modul resmi).
   Default source `HttpServerPort=11080`, HTTP server off pada service,
   `HttpsEnabled=false`. HTTP server **bind Any**, jadi alamat loopback pada
   adapter tidak membatasi listener Veyon. Konfigurasikan HTTPS + sertifikat,
   ACL firewall hanya server sesi, atau isolasi loopback yang benar-benar diuji.
5. Konfigurasi tag 4.11.4 ada pada `WebAPI/HttpsEnabled`,
   `WebAPI/TlsCertificateFile`, `WebAPI/TlsPrivateKeyFile`,
   `WebAPI/HttpServerPort`. Jangan menyetel global pada host tanpa backup.
6. Isi env server `VEYON_URL`, `VEYON_KEY_NAME`, `VEYON_PRIVATE_KEY_PATH`,
   `VEYON_CA` dengan prefix `LABACCESS_`. CA wajib diverifikasi; tidak ada verify=False.
7. Admin mengisi `veyon_host` untuk device_id melalui UI. Uji status, screenshot
   PC berizin, kemudian tutup koneksi. Kunci layar hanya setelah peringatan,
   alasan, konfirmasi, dan jalur buka kunci melalui Master tersedia.

## Yang terbukti dan belum

- Terbukti: versi binary dan signature/checksum, keberadaan modul CLI webapi,
  kontrak adapter terhadap transport test yang jelas, penolakan konfigurasi
  HTTP LAN, endpoint gagal eksplisit ketika kunci/service belum siap.
- Belum terbukti: koneksi terautentikasi live ke Veyon Service, screenshot live,
  kontrol kunci dan bantuan remote pada PC pilot. MockTransport pada tes
  **bukan bukti integrasi live**.
- Host non-elevated tidak memiliki Veyon Service. Percobaan membaca `--help`
  pada binary server ternyata memulai server (source tidak menyediakan parser
  help), menghasilkan kegagalan token/privilege; proses tersebut dihentikan
  berdasarkan path/PID milik pengujian. Tidak ada service/firewall/policy dipasang.
  `veyon-cli --version`/`about` adalah pemeriksaan versi yang tepat.

Untuk bantuan remote yang belum ada di UI, tombol **Buka Veyon Master** membuka
aplikasi resmi. Tidak ada implementasi ulang remote desktop.

Sumber: [download](https://veyon.io/en/download/),
[instalasi resmi](https://docs.veyon.io/en/latest/admin/installation.html),
[WebApiHttpServer.cpp](https://github.com/veyon/veyon/blob/v4.11.4/plugins/webapi/WebApiHttpServer.cpp),
[WebApiController.cpp](https://github.com/veyon/veyon/blob/v4.11.4/plugins/webapi/WebApiController.cpp).
