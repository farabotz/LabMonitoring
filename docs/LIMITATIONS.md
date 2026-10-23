# Batas yang diketahui

1. Host Windows 10 Pro non-elevated; instalasi, kamera dan enforcement Windows 11
   harus diuji lagi. Tidak ada claim PC terkunci atau perubahan login Windows.
2. Veyon 4.11.4 diperiksa binary/source/kontrak. Koneksi terautentikasi live,
   screenshot/control berizin dan Service+Master pilot belum dibuktikan.
3. Wajah default nonaktif. Inferensi model berjalan, tetapi belum ada peserta,
   enrollment manusia sah, verifikasi identitas, kalibrasi/akurasi atau uji
   serangan foto/replay. Tantangan geometris bukan PAD terlatih.
4. Direct desktop menyimpan credential per perangkat di DPAPI akun bersama.
   Proses lain dengan akun Windows yang sama dapat membaca DPAPI. Mode agent
   membatasi secret ke proses/identitas agent, namun endpoint IPC yang diizinkan
   tetap dapat dipanggil oleh proses dengan SID UI yang sama. Tidak ada kamera
   tepercaya/attestation.
5. Named pipe/foreground agent dan alur UI dijalankan dalam tes. SCM LocalSystem,
   ACL production, timeout terhadap koneksi pipe macet, dan recovery service belum diuji.
6. Tidak ada offline bypass, SSO/OIDC resmi, Credential Provider atau kebijakan
   Windows dinamis. Sesi stale tetap terbuka sampai reconnect/admin menyelesaikan.
7. API single-node, query histori maksimum 10.000 dan audit 1.000 terbaru; belum
   pagination/scheduler terkelola. Maintenance retensi harus dijadwalkan pengelola.
8. Argon2id sengaja memakai RAM; login 35 simulasi bersamaan mendekati 1 GB RSS
   process tree server pada host ini. Ukur kapasitas PC admin bersama Veyon.
9. Cluster PostgreSQL development memakai trust loopback dan versi 17.6 yang
   dipilih untuk binary portable; bukan konfigurasi produksi. Gunakan patch
   terdukung terbaru yang sudah diuji dan SCRAM/role terbatas sebelum LAN produksi.
10. Penghapusan template DB aktif tidak memusnahkan backup lama atau seluruh
    salinan memori Python. Retensi/backup/key lifecycle perlu kebijakan kampus.
11. Executable/installer belum ditandatangani sertifikat penerbit milik kampus.
    SmartScreen, antivirus, upgrade/uninstall dan resource fisik Win11 perlu pilot.
12. Ketentuan source/library LGPL/GPL dan lisensi source TA harus diselesaikan
    sebelum distribusi luar. Sinkronisasi source ke repo privat hanya sesuai
    instruksi pemilik; tidak ada publikasi binary atau pengiriman pesan pihak lain.

Lihat STATUS dan TEST_RESULTS untuk status build terakhir dan bukti actual,
termasuk kegagalan yang telah dikoreksi. Tidak ada hasil penelitian yang dikarang.
