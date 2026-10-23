param([ValidateSet('student','admin','all')][string]$Target='all')
$ErrorActionPreference='Stop'
$root=(Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location -LiteralPath $root
$nsis=Join-Path $root '.tools/nsis/nsis-3.13/makensis.exe'
if (!(Test-Path -LiteralPath $nsis)) { throw 'Siapkan NSIS 3.13 portable resmi terlebih dahulu.' }
New-Item -ItemType Directory -Force dist | Out-Null
$targets=if ($Target -eq 'all') { @('student','admin') } else { @($Target) }
foreach ($app in $targets) {
    if (!(Test-Path -LiteralPath "build/$app/entry_$app.dist/LabAccess-$app.exe")) { throw "EXE $app belum tersedia; build tidak dilanjutkan." }
    & $nsis "/DAPP=$app" scripts/installer.nsi
    if ($LASTEXITCODE -ne 0) { throw "Installer $app gagal" }
}
Get-ChildItem dist -Filter '*.exe' | Get-FileHash -Algorithm SHA256
