# Pemasangan REA khusus Codex

Pemeriksaan 22 Oktober 2026, sumber:
[repository resmi](https://github.com/morluto/rea),
[installation](https://github.com/morluto/rea/blob/main/docs/installation.md),
[client configuration](https://github.com/morluto/rea/blob/main/docs/client-configuration.md),
[skill Codex](https://developers.openai.com/codex/skills/).
Salinan dokumentasi yang dibaca ada di `evidence/rea-installation.md` dan `rea-client.md`.

## Versi dan integritas

- Paket resmi registry npm `rea-agents@6.7.0`; repository metadata cocok `morluto/rea`.
- Tarball: `https://registry.npmjs.org/rea-agents/-/rea-agents-6.7.0.tgz`.
- SHA1: `11f23ba377303a5c28b3162180cf2bf3f3643708`.
- SRI: `sha512-yhIx2ioJYYT1C/tONfYeitC6LhnKmCh+ZwRUOgYuhSc733lGhkkt73zhug9WmLgxoMdKuqIYGCoBfD4fXkOhFw==`.
- Metadata integritas/signature/provenance: `evidence/rea-package.json`. Signature registry
  dicatat sebagai metadata, bukan klaim audit keamanan/pemeriksaan provenance kriptografis terpisah.
- Engine paket `^22.19.0 || ^24.11.0 || >=26.0.0`.
- Node global 22.16.0/npm 11.21.1 dipertahankan. Node 22.19.0 x64 dari nodejs.org
  diperiksa terhadap SHASUMS256 resmi, ditempatkan pada
  `C:\Users\Fitra\.codex\tools\rea-node-22.19.0\node.exe`.

`CODEX_HOME` kosong/tidak disetel, maka profil aktif yang diperiksa installer
adalah `C:\Users\Fitra\.codex\config.toml`. Tidak ada REA sebelumnya.

## Rencana dan penerapan aktual

REA dipasang pada prefix terisolasi
`C:\Users\Fitra\.codex\tools\rea-6.7.0`, tanpa mengganti Node/npm global.
CLI langsung dipilih agar registrasi menggunakan Node yang memenuhi engine,
tidak kembali ke `npx` dengan Node global 22.16.0.

```powershell
$node='C:\Users\Fitra\.codex\tools\rea-node-22.19.0\node.exe'
$rea='C:\Users\Fitra\.codex\tools\rea-6.7.0\node_modules\rea-agents\scripts\rea.mjs'
& $node $rea setup --client codex --dry-run --json
& $node $rea setup --client codex --yes --json
& $node $rea doctor --client codex --skill --json
```

Hasil nyata:

| Pemeriksaan | Hasil |
|---|---|
| Dry-run | exit 0, status `planned`, hanya `configure_client:codex` dan `install_skill` |
| Setup | exit 0, status `ready`, `configured_codex`, `installed_skill` |
| Doctor | exit 0, `healthy=true`, `environment_healthy=false` |
| Registrasi Codex | `aligned`, command absolut Node + CLI 6.7.0 + `mcp` |
| Workflow disk | `C:\Users\Fitra\.agents\skills\reverse-engineer-anything`, versi 42, 207 tools, `aligned` |
| Konfigurasi lain | Dibandingkan TOML sebelum/sesudah tanpa tabel rea: identik |
| MCP sesi Codex ini | Belum ditemukan pada katalog tools sesi; doctor `live_server.state=unknown` |

`environment_healthy=false` karena engine analisis opsional tidak dikonfigurasi,
bukan kegagalan registrasi. Tidak memasang Hopper/engine berbayar. Tidak memakai
`--all-detected` atau `--skill=false`. Tidak mendekompilasi Veyon.

Backup installer: `C:\Users\Fitra\.codex\config.toml.rea.backup`.
Snapshot tambahan sebelum setup: `config.toml.labaccess-before-rea.backup` pada
direktori profil yang sama. Tidak dimasukkan ke Git karena dapat berisi konfigurasi sensitif.
Bukti JSON: `evidence/rea-plan.json`, `rea-setup.json`, `rea-doctor.json`.

## Satu tindakan untuk discovery sesi baru

**Restart Codex satu kali**, kemudian buka kembali workspace dan minta:

> Baca STATUS.md, lalu baca skill reverse-engineer-anything yang dipasang. Cek
> discovery MCP REA pada sesi baru dan lakukan pemeriksaan identitas baca-saja
> `binary_session` sesuai skill. Lanjutkan checkpoint LabAccess tanpa reset data.

Jangan menganggap MCP aktif hanya dari tabel konfigurasi/hasil doctor. Belum ada
operasi REA dari katalog MCP aktif sesi ini yang dapat dibuktikan. REA bukan
dependency runtime aplikasi dan tidak boleh menerima frame/NIM peserta.
