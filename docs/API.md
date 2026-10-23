# Kontrak API

Kontrak mesin lengkap: [openapi.json](openapi.json), dihasilkan dari aplikasi
yang sama. Saat server berjalan tersedia `/docs` dan `/openapi.json` untuk
pengembangan. Tidak perlu browser untuk penggunaan mahasiswa/admin.

API LAN wajib HTTPS. Header credential perangkat: `X-Device-Id` dan
`X-Device-Secret`. Token JWT pada `Authorization: Bearer <token>`. Token admin
dan sesi mahasiswa memiliki `kind` berbeda dan tidak saling menggantikan.
Semua waktu ISO 8601 UTC `Z`. Status endpoint bukan instruksi menutup aplikasi Windows.

| Endpoint | Hak | Perilaku |
|---|---|---|
| GET /health | umum | Kesehatan DB, waktu server, interval heartbeat, status eksperimen/enforcement |
| POST /auth/admin | NIM/password pengelola | JWT admin/operator 60 menit; rate limit |
| GET/POST /admin/users | pengelola | Daftar akun tanpa hash/template; operator hanya membuat mahasiswa |
| PUT /admin/users/{id}/password | pengelola sesuai target | Password min. 12, Argon2id, auth_version naik |
| PUT /admin/users/{id}/state | pengelola sesuai target | Aktif/nonaktif; tidak menonaktifkan diri sendiri |
| POST /admin/enrollments | admin | Token acak 15 menit; hash disimpan; sekali pakai |
| POST /devices/enroll | token enrollment | Mendaftarkan UUID + nama/mapping yang ditentukan admin; secret per PC |
| POST /devices/heartbeat | perangkat | boot_id, last_seen, deteksi restart; sesi milik PC ini saja + token segar |
| POST /sessions/password | perangkat + NIM/password | request_key wajib min. 16 karakter, constraint sesi dan idempotency |
| POST /sessions/logout | perangkat + JWT sesi sendiri | Logout idempotent, completed/student_logout |
| GET /admin/devices | pengelola | Inventaris + status heartbeat + sesi mahasiswa |
| PUT /admin/devices/{id} | admin | Mapping Veyon/status aktif/catatan masalah; audit |
| POST /admin/sessions/{id}/end | pengelola | Alasan min. 5 karakter, interrupted; beri peringatan dulu |
| GET /admin/history | pengelola | Filter nim, device_id, method, start, end, end_reason (mengandung teks literal); maksimum 10.000 baris |
| GET /admin/history.csv | pengelola | Filter sama, BOM UTF-8, formula spreadsheet dinetralkan |
| GET /admin/audit | admin | Maksimal 1.000 audit terbaru; tidak ada endpoint hapus |
| POST /face/challenges | perangkat | NIM, nonce random, gerakan kiri/kanan, TTL 30 detik |
| POST /sessions/face | perangkat | Multipart challenge_id, request_key, tepat 3 frames; keputusan server |
| POST /admin/users/{id}/face | pengelola | Multipart consent=true dan 3 frames; operator memeriksa identitas |
| DELETE /admin/users/{id}/face | pengelola | Penghapusan blob aktif/consent timestamp dan audit tanpa biometrik |
| GET /admin/devices/{id}/veyon/status | pengelola | Koneksi WebAPI terautentikasi; Windows user diberi label terpisah |
| GET /admin/devices/{id}/veyon/framebuffer | pengelola | JPEG saat diminta; tidak disimpan kontinu |
| PUT /admin/devices/{id}/veyon/lock?active=true | admin | Alasan wajib, UI konfirmasi; lock administratif bukan login NIM |

Contoh body login (nilai di bawah placeholder, bukan akun bawaan):

```json
{"nim":"NIM_PESERTA","password":"PASSWORD_LABACCESS","request_key":"UUID_ACAK_PER_LOGIN"}
```

Retry dengan key dan payload sama mengembalikan sesi sama. Key sama dengan
payload lain/permintaan yang sudah selesai ditolak 409. Pada wajah, respons yang
hilang dapat dipulihkan dengan retry key/challenge yang sama atau heartbeat;
challenge yang gagal tidak boleh digunakan kembali.

Status umum: 401 credential/token/challenge salah; 403 peran atau perangkat
tidak cocok; 409 konflik sesi/enrollment; 422 input salah; 426 TLS diperlukan;
429 rate limit; 503 metode wajah/kunci integrasi belum siap; 502 kegagalan Veyon.
Tidak ada endpoint menerima `face_verified=true` untuk membuka sesi.
