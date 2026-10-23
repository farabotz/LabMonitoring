$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
# Hanya cluster lokal proyek ini; fast = tutup koneksi DB pengembangan secara tertib.
& "$root\.tools\postgres\pgsql\bin\pg_ctl.exe" -D "$root\.runtime\pgdata" -m fast stop
if ($LASTEXITCODE -ne 0) { throw 'Penghentian cluster lokal gagal/tidak berjalan.' }
