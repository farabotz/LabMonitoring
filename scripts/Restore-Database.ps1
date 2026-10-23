param([Parameter(Mandatory=$true)][string]$Backup, [Parameter(Mandatory=$true)][string]$NewDatabase, [string]$DbHost='127.0.0.1', [int]$Port=55432, [string]$DbUser='labaccess')
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
if ($NewDatabase -notmatch '^labaccess_restore_[a-zA-Z0-9_]+$') { throw 'Target harus database baru labaccess_restore_*. Tidak boleh restore ke database produksi yang ada.' }
if (!(Test-Path -LiteralPath $Backup)) { throw 'Backup tidak ditemukan.' }
& "$root\.tools\postgres\pgsql\bin\createdb.exe" -h $DbHost -p $Port -U $DbUser $NewDatabase
if ($LASTEXITCODE -ne 0) { throw 'createdb gagal/target sudah ada; tidak menghapus target.' }
& "$root\.tools\postgres\pgsql\bin\pg_restore.exe" -h $DbHost -p $Port -U $DbUser -d $NewDatabase --exit-on-error --no-owner $Backup
if ($LASTEXITCODE -ne 0) { throw 'Restore gagal; database baru dipertahankan untuk diagnosis.' }
Write-Output "Restore selesai ke $NewDatabase. Uji sebelum mengalihkan DATABASE_URL."
