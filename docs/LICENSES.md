# Lisensi, atribusi dan distribusi

Dokumen ini mencatat pemeriksaan teknis distribusi, bukan keputusan hukum
milik kampus. Sinkronisasi source ke repository privat mengikuti instruksi
pemilik; binary dan dependency build tidak ikut diunggah. Lisensi
source LabAccess sendiri harus ditetapkan pemilik TA sebelum distribusi publik;
tidak menetapkan lisensi pemilik secara sepihak.

## Komponen utama

| Komponen terpin | Lisensi/sumber pemeriksaan | Implikasi paket |
|---|---|---|
| Veyon 4.11.4 | COPYING GPLv2; header banyak file menyebut v2 atau versi lebih baru | Pertahankan copyright, GPL dan corresponding source bila mendistribusikan binary/derivatif sesuai lisensi tepatnya. Installer LabAccess tidak membundel binary Veyon. |
| PySide6/Qt 6.10.3 | LGPLv3/GPLv3 atau komersial, dan ketentuan modul Qt masing-masing | Paket memakai QtCore/Gui/Widgets dan plugin yang diperlukan secara dinamis. Sertakan lisensi, notice, informasi instalasi/penggantian library dan corresponding source/penawaran yang sah sesuai lisensi. |
| YuNet ONNX 2023mar | MIT pada direktori model opencv_zoo commit terpin | Sertakan notice/copyright dan MIT. Lisensi bobot diperiksa terpisah. |
| SFace ONNX 2021dec | Apache-2.0 pada direktori model opencv_zoo commit terpin | Pertahankan teks lisensi/notice relevan, dokumentasikan perubahan bila ada. Bobot tidak dimodifikasi. |
| OpenCV Python 4.14.0.94 | Apache-2.0 dengan komponen third party pada wheel | Periksa bundled codecs/media/third party notices. |
| NumPy 2.4.6 pada Python 3.11 | BSD-3-Clause + bundled numerical library notices | Simpan notice komponen wheel. Lock juga memiliki versi sesuai Python lain. |
| FastAPI, SQLAlchemy, Alembic, httpx, PyJWT | Umumnya MIT; metadata/teks tiap versi disalin | Pertahankan notice. |
| Argon2-cffi, pydantic, uvicorn, psycopg, cryptography | Beragam MIT/BSD/LGPL/Apache; lihat inventory dan teks wheel | Jangan menganggap seluruh dependency berlisensi sama. psycopg/libpq/crypto memiliki komponen tersendiri. |
| PostgreSQL 17.6 | PostgreSQL License | Binary disiapkan terpisah, bukan dependency yang dibundel ke klien. |
| Nuitka 4.3.1 | Apache-2.0, detail runtime/komponen lihat paket | Alat build; tidak mengubah hak lisensi dependency yang dibundel. |
| CPython 3.11.15 | PSF dan notice komponen interpreter | LICENSE.txt dari runtime build disertakan. |
| NSIS 3.13 | zlib/libpng + lisensi komponen | Installer memakai kompresor zlib; COPYING paket NSIS disertakan. |
| REA 6.7.0 | Tool pengembangan; lihat paket resmi | Tidak masuk installer/runtime mahasiswa. |

`docs/DEPENDENCIES.json` adalah daftar **aktual** metadata versi environment build,
termasuk tool tes/build. `third_party/licenses/` menyalin teks license/copying/notice
dari wheel yang tersedia, serta Veyon/model. Metadata bukan pengganti pemeriksaan
lisensi setiap modul/binary akhir. Jalankan ulang inventory setelah mengubah lock.

Wheel PySide6/Shiboken pada environment ini menyatakan opsi LGPL/GPL pada metadata,
tetapi berkas lisensi yang terdaftar di wheel hanya LicenseRef-Qt-Commercial.txt.
Teks LGPLv3, GPLv3 dan GPLv2 dilengkapi dari source resmi Qt tag v6.10.3 pada
`third_party/licenses/Qt`; hal ini dicatat di evidence/license-metadata-note.json.

Payload standalone aktual juga memuat QtNetwork, QtSvg dan QtPdf melalui plugin
gambar/TLS, serta OpenSSL dan runtime Microsoft Visual C++. Header source
[QtPdf 6.10.3](https://github.com/qt/qtwebengine/blob/v6.10.3/src/pdf/qpdfdocument.cpp)
dan [QtSvg 6.10.3](https://github.com/qt/qtsvg/blob/v6.10.3/src/svg/qsvgrenderer.cpp)
menyediakan opsi LGPLv3/GPL. QtPdf membawa PDFium dan notice third party terkait;
penyelesaian corresponding source/notice binary akhir tetap syarat distribusi luar.
Pemberitahuan GCC Runtime Library Exception 3.1 disertakan di folder GCC;
ini tidak mengubah lisensi dependency lainnya.

## Hubungan dengan Veyon

Implementasi memakai proses terpisah dan protokol WebAPI resmi, tidak menyalin
core remote desktop atau mengubah binary Veyon. Tidak menyatakan semua bentuk
companion otomatis bebas kewajiban GPL. Bila integrasi kelak menjadi plugin,
linking library, fork atau satu karya turunan yang didistribusikan, nilai ulang
scope lisensi dan sediakan corresponding source sesuai kewajiban.
Distribusi kumpulan paket terpisah tetap harus mempertahankan notice masing-masing.

## Sebelum mendistribusikan keluar pengujian internal

Sertakan source LabAccess yang cocok versi build, lock, skrip compiler/installer,
notice dependency, dan corresponding source Qt/PySide6/komponen LGPL yang tepat
atau penawaran sah yang benar-benar dapat dipenuhi. Salinan teks lisensi dan URL
sumber **saja** tidak otomatis memenuhi seluruh kewajiban corresponding source.
Jangan membatasi reverse engineering untuk debugging perubahan library LGPL;
pastikan DLL dapat diganti dan aplikasi hasil relink dapat dijalankan. Jangan
menambahkan modul Qt khusus GPL secara tidak sengaja pada build.

Rujukan primer:
[Veyon COPYING](https://github.com/veyon/veyon/blob/v4.11.4/COPYING),
[kewajiban Qt](https://www.qt.io/development/open-source-lgpl-obligations),
[YuNet license](https://github.com/opencv/opencv_zoo/blob/48b10fa505aeb51fbd127fc60a5c660040e823b7/models/face_detection_yunet/LICENSE),
[SFace license](https://github.com/opencv/opencv_zoo/blob/48b10fa505aeb51fbd127fc60a5c660040e823b7/models/face_recognition_sface/LICENSE).
