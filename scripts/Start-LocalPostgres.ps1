$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location -LiteralPath $root
$pg = Join-Path $root '.tools\postgres\pgsql\bin'
$data = Join-Path $root '.runtime\pgdata'
if (!(Test-Path -LiteralPath "$pg\initdb.exe")) { throw 'Siapkan binary PostgreSQL terlebih dahulu; baca SETUP_WINDOWS.md.' }
New-Item -ItemType Directory -Force .runtime | Out-Null
if (!(Test-Path -LiteralPath "$data\PG_VERSION")) {
    & "$pg\initdb.exe" -D $data -U labaccess -A trust --encoding=UTF8 --locale=C
    if ($LASTEXITCODE -ne 0) { throw 'initdb gagal' }
    Add-Content -LiteralPath "$data\postgresql.conf" -Value "`nlisten_addresses = '127.0.0.1'`nport = 55432"
    # Cluster pengembangan hanya loopback. Produksi wajib SCRAM + role terpisah.
}
& "$pg\pg_ctl.exe" -D $data status
if ($LASTEXITCODE -ne 0) {
    & "$pg\pg_ctl.exe" -D $data -l "$root\.runtime\postgres.log" start
    if ($LASTEXITCODE -ne 0) { throw 'pg_ctl start gagal' }
}
& "$pg\psql.exe" -h 127.0.0.1 -p 55432 -U labaccess -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='labaccess'" | ForEach-Object { $script:exists = $_ }
if ($script:exists -ne '1') {
    & "$pg\createdb.exe" -h 127.0.0.1 -p 55432 -U labaccess labaccess
    if ($LASTEXITCODE -ne 0) { throw 'createdb gagal' }
}
