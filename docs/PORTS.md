# Port dan listener

| Komponen | Alamat/port | Status pemeriksaan |
|---|---|---|
| PostgreSQL development | 127.0.0.1 TCP 55432 | Cluster lokal nyata berjalan; tidak bind LAN |
| API development | 127.0.0.1 TCP 8000 | Konfigurasi Start-Api.ps1; jalankan saat demo |
| API selama tes live/TLS/load | 127.0.0.1 TCP port acak OS | Dijalankan dan dihentikan proses test miliknya sendiri |
| API pilot LAN | TCP 8443, HTTPS | Contoh deployment; belum membuka firewall/LAN pada host ini |
| Veyon WebAPI | TCP 11080 default source 4.11.4 | Belum listener live yang dikonfigurasi; perlu TLS/akses terbatas |
| Veyon Server | TCP 11100 default Veyon | Belum Service pilot; jangan membuka ke subnet tanpa konfigurasi access control |
| IPC agent | Named pipe lokal Windows | Tidak memakai port TCP, remote clients ditolak |

Tidak membuka firewall secara menyeluruh, tidak menambah listener LAN diam-diam.
Jika port diubah pengelola, perbarui env/shortcut/mapping dan dokumen pilot.
