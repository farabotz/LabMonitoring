# Enrollment, verifikasi dan threshold

## Status ilmiah

Menggunakan model yang tersedia: YuNet deteksi dan SFace embedding. Tidak
mengklaim algoritma pengenalan baru. Verifikasi **1:1**: NIM menentukan satu
template. Wajah dan password merupakan alternatif, bukan otomatis dua faktor.

Model dari opencv_zoo commit `48b10fa505aeb51fbd127fc60a5c660040e823b7`:

| Model | Lisensi bobot diperiksa | SHA256 |
|---|---|---|
| YuNet 2023mar | MIT | `8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4` |
| SFace 2021dec | Apache-2.0 | `0ba9fbfa01b5270c96627c4ef784da859931e02f04419c829e83484087c34e79` |

Manifest dengan URL terpin ada di `models/manifest.json`. Downloader membandingkan
OID SHA256 pointer Git LFS terhadap konten aktual. Server memeriksa ulang checksum
saat memuat model. Library OpenCV memiliki lisensi terpisah. Tidak mengunduh saat login.

## Enrollment peserta

1. Operator memeriksa identitas asli dan kecocokan NIM secara langsung.
2. Jelaskan tujuan penelitian, retensi, hak menarik diri, risiko replay, dan
   alternatif password. Simpan formulir consent sesuai prosedur kampus.
3. Pada desktop admin pilih mahasiswa → Enrollment wajah → konfirmasi identitas
   dan consent. Tidak boleh menggunakan foto publik/teman sebagai enrollment sah.
4. Ambil tiga sampel kamera di perangkat operator; ubah sedikit posisi/cahaya.
   Ini minimum MVP. Gunakan beberapa sesi pengambilan untuk penelitian lapangan.
5. Server menolak tidak ada wajah/multiwajah, wajah kecil/terpotong, buram,
   terlalu gelap/terang, serta embedding antar sampel yang tidak konsisten.
6. Hanya template rata-rata ternormalisasi yang disimpan terenkripsi Fernet.
   Frame tidak disimpan. Kamera ditutup saat selesai/batal/gagal.
7. Hapus melalui tombol Hapus template/API DELETE ketika peserta menarik diri
   atau selesai penelitian; uji DB aktif tidak lagi memiliki blob. Audit hanya
   mencatat penghapusan/NIM, tidak menyimpan ulang biometrik. Backup mengikuti
   jadwal retensi dan pemusnahan kunci; penghapusan DB tidak menghapus backup lama.

## Login dan mitigasi replay

Aktifkan secara sengaja `LABACCESS_FACE_ENABLED=true`, siapkan model dan restart
API. Server menerbitkan nonce acak/UUID untuk device+NIM, masa berlaku 30 detik,
tantangan kiri/kanan. UI mengambil tengah → putar → tengah. Server memeriksa
gerakan dari posisi hidung relatif mata serta skor cosine terhadap satu template.
Nonce dikonsumsi atomik, termasuk ketika gagal. Keputusan bukan boolean klien.

Tantangan geometris RGB adalah **mitigasi terbatas**, bukan model PAD terlatih dan
bukan bukti tahan foto/replay/deepfake. Tidak ada attestation kamera. Klien jahat
dapat menyusun frame. Uji cetak dan layar pada webcam pilot wajib sebelum penggunaan
nyata; tetap sediakan password. Batas gerakan dan kualitas juga perlu dikalibrasi
untuk kamera aktual serta kebutuhan aksesibilitas.

## Kalibrasi

`LABACCESS_FACE_THRESHOLD=0.50` adalah parameter awal belum tervalidasi. Pisahkan
peserta/sesi enrollment, kalibrasi dan pengujian; jangan menguji ulang frame
enrollment. Tentukan target FMR/FNMR, pilih threshold pada data kalibrasi, lalu
kunci sebelum evaluasi akhir. Gunakan skrip `scripts.evaluate_scores` dan
instrumen di `experiments/`. Laporkan kegagalan kualitas/tantangan terpisah
dari penolakan identitas. Jangan memakai skor benchmark internet sebagai hasil lab.

## Bukti host

Kamera terdeteksi HP HD Webcam; dibuka, membaca 640×480, ditutup, 0 frame disimpan.
Model dimuat, deteksi frame kosong menolak wajah, SFace menghasilkan tensor
embedding 128 dimensi dari input sintetis. Belum ada enrollment peserta manusia,
login wajah benar/salah atau akurasi penelitian. Tidak ada peserta/akurasi fiktif.
