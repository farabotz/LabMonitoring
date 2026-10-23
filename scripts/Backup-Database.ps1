param([Parameter(Mandatory=$true)][string]$Destination, [string]$DbHost='127.0.0.1', [int]$Port=55432, [string]$DbUser='labaccess', [string]$Database='labaccess')
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
if (Test-Path -LiteralPath $Destination) { throw 'Target sudah ada; backup tidak menimpa berkas.' }
# pg_dump meminta password interaktif/PGPASSFILE. Tidak menaruh password pada argumen/log.
& "$root\.tools\postgres\pgsql\bin\pg_dump.exe" -h $DbHost -p $Port -U $DbUser -d $Database -Fc -f $Destination
if ($LASTEXITCODE -ne 0) { throw 'Backup gagal.' }
Get-FileHash -LiteralPath $Destination -Algorithm SHA256
Write-Output 'Simpan backup pada media terenkripsi. Cadangkan kunci Fernet terpisah dari dump.'
