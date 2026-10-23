# Lembar penerimaan pilot

Isi tanggal, operator, versi aplikasi/model/Veyon, ID PC, edisi/build Windows,
akun non-admin dan checksum installer. Jangan menulis password/token/embedding.
Belum ada baris yang boleh dianggap lulus sebelum bukti mesin terkait tersedia.

| Uji | Hasil yang diharapkan | Hasil aktual / bukti |
|---|---|---|
| Install mahasiswa/admin pada Win11 | Shortcut/EXE hidup, data kerja/akun Windows utuh | Belum diuji |
| Upgrade dan uninstall | Credential/data kerja tidak terhapus, hanya payload sendiri dilepas | Belum diuji Win11 |
| Enroll PC dua perangkat | UUID/secret berbeda, token tak dapat dipakai ulang | Belum pilot fisik |
| Login/password/nonaktif/reset | Pesan jelas, akun nonaktif ditolak, reset bekerja | Belum pilot fisik |
| Dua login bersamaan/retry | Satu NIM/PC satu sesi, retry tidak menambah sesi | Belum pilot fisik |
| Cabut LAN/stop API | Login baru ditolak; pekerjaan aktif tetap berjalan; stale terlihat | Belum pilot fisik |
| Reconnect/crash/restart | Sesi sama pada reboot yang sama, restart tercatat interrupted | Belum pilot fisik |
| Hak mahasiswa/operator/admin | Mahasiswa tidak mendapat admin/history/template/kunci Veyon | Belum pilot fisik |
| Veyon live | Status + satu screenshot dan bantuan berizin, CA tervalidasi | Belum diuji |
| Kunci administratif | Ada peringatan/alasan/konfirmasi; admin dapat membuka kembali | Belum diuji |
| Webcam dan wajah | Kamera hanya diperlukan, benar/salah/no/multiface/fallback jelas | Belum enrollment manusia |
| Foto cetak dan replay layar | Catat serangan diterima/ditolak serta kondisi; jangan klaim kebal | Belum diuji |
| Keluar dari UI | Alt+Tab/Win/TaskMgr/close/crash di akun non-admin diuji | Enforcement belum ada |
| Recovery admin | Akun admin tetap dapat masuk saat UI/LAN/policy gagal | Belum diuji enforcement |
| Backup/restore | Restore ke DB baru dan verifikasi data/key sebelum switch | Development sudah diuji; pilot belum |
| CPU/RAM dan update admin | Sampel resource sesuai skenario dan jumlah PC | Belum PC fisik |

Helper pengukuran desktop:

```powershell
./scripts/Measure-Desktop.ps1 -ProcessId PID_DESKTOP -Seconds 60 -OutputCsv experiments/resource-PC01.csv
```

Pengukuran CPU dinormalisasi ke seluruh logical processors, RSS dalam MiB.
Pisahkan skenario idle/login/session; jangan menganggap RSS API simulasi sebagai
angka desktop. Simpan bukti sesuai consent dan hapus sampel sensitif sesuai retensi.
