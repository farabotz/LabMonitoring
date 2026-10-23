param([ValidateSet('student','admin','all')][string]$Target='all', [int]$SmokeTimeoutSeconds=180)
$ErrorActionPreference='Stop'
$root=(Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location -LiteralPath $root
$results=@()
$targets=if ($Target -eq 'all') { @('student','admin') } else { @($Target) }
$sentinel=Join-Path $root ('.runtime/install-preserve-'+[Guid]::NewGuid().ToString('N')+'.txt')
New-Item -ItemType Directory -Force (Split-Path -Parent $sentinel) | Out-Null
[IO.File]::WriteAllText($sentinel,'Data sintetis di luar payload; harus tetap utuh.')
$sentinelHash=(Get-FileHash -LiteralPath $sentinel -Algorithm SHA256).Hash
function Wait-OwnProcess([string]$Executable,[string[]]$Arguments) {
    $p=Start-Process -FilePath $Executable -ArgumentList $Arguments -PassThru -WindowStyle Hidden
    if (!$p.WaitForExit($SmokeTimeoutSeconds*1000)) { throw "Proses belum selesai: $Executable (PID $($p.Id)); tidak dihentikan otomatis." }
    $p.Refresh()
    if ($p.ExitCode -ne 0) { throw "Exit code $($p.ExitCode): $Executable" }
}
# Jangan menimpa instalasi/shortcut/registry pengguna yang sudah ada.
foreach ($app in $targets) {
    $name="LabAccess-$app"
    $installDir=Join-Path $env:LOCALAPPDATA "Programs\$name"
    $shortcut=Join-Path ([Environment]::GetFolderPath('Programs')) "$name.lnk"
    $reg="HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\$name"
    $connectionIni=Join-Path $env:LOCALAPPDATA "LabAccess\connection-$app.ini"
    if ((Test-Path -LiteralPath $installDir) -or (Test-Path -LiteralPath $shortcut) -or (Test-Path -LiteralPath $reg)) {
        throw "Target sudah ada; tes dibatalkan tanpa menimpanya: $installDir"
    }
    if (Test-Path -LiteralPath $connectionIni) { throw "Konfigurasi koneksi pengguna sudah ada; tes tidak menimpanya: $connectionIni" }
    if (!(Test-Path -LiteralPath "dist/$name-Setup-0.1.0.exe")) { throw "Installer $name belum dibangun." }
}
$tlsDir=Join-Path $root ('.runtime/Installer CA-'+[Guid]::NewGuid().ToString('N'))
& (Join-Path $root '.tools/buildenv/Scripts/python.exe') -m scripts.create_pilot_tls --hostname installer.test.invalid --out $tlsDir
if ($LASTEXITCODE -ne 0) { throw 'CA fixture tidak dapat dibuat.' }
$caFile=Join-Path $tlsDir 'ca.pem'
foreach ($app in $targets) {
    $name="LabAccess-$app"
    $installDir=[IO.Path]::GetFullPath((Join-Path $env:LOCALAPPDATA "Programs\$name"))
    $shortcut=Join-Path ([Environment]::GetFolderPath('Programs')) "$name.lnk"
    $reg="HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\$name"
    $connectionIni=Join-Path $env:LOCALAPPDATA "LabAccess\connection-$app.ini"
    $installer=(Resolve-Path -LiteralPath "dist/$name-Setup-0.1.0.exe").Path
    $expectedExeHash=(Get-FileHash -LiteralPath "build/$app/entry_$app.dist/$name.exe" -Algorithm SHA256).Hash
    $row=[ordered]@{app=$app;target=$installDir;tested_at_utc=[DateTime]::UtcNow.ToString('o');installer_sha256=(Get-FileHash -LiteralPath $installer -Algorithm SHA256).Hash;install=$false;upgrade=$false;smoke=$false;uninstall=$false;external_data_preserved=$false}
    Wait-OwnProcess $installer @('/S','/SERVER=http://127.0.0.1:8000',('/CA="'+$caFile+'"'))
    if (!(Test-Path -LiteralPath "$installDir\labaccess-$app.marker") -or !(Test-Path -LiteralPath $shortcut) -or !(Test-Path -LiteralPath $reg)) { throw 'Instalasi tidak lengkap.' }
    $row.install=$true
    $row['installed_exe_sha256']=(Get-FileHash -LiteralPath "$installDir\app\$name.exe" -Algorithm SHA256).Hash
    if ($row.installed_exe_sha256 -ne $expectedExeHash) { throw 'Installer memuat EXE berbeda dari build saat ini.' }
    $shell=New-Object -ComObject WScript.Shell
    if ($shell.CreateShortcut($shortcut).Arguments -notmatch '--server "http://127.0.0.1:8000"') { throw 'Konfigurasi shortcut tidak tersimpan.' }
    if (!$shell.CreateShortcut($shortcut).Arguments.Contains('--ca "'+$caFile+'"')) { throw 'Path CA dengan spasi tidak tersimpan.' }
    $connectionHash=(Get-FileHash -LiteralPath $connectionIni).Hash
    $smokeArgs=@('--smoke-test','--ca',('"'+$caFile+'"'))
    if ($app -eq 'student') { $smokeArgs += @('--config',('"'+(Join-Path $root '.runtime/installer-unused.dpapi')+'"')) }
    Wait-OwnProcess "$installDir\app\$name.exe" $smokeArgs
    $row.smoke=$true
    Wait-OwnProcess $installer @('/S')
    if ((Get-FileHash -LiteralPath "$installDir\app\$name.exe" -Algorithm SHA256).Hash -ne $row.installed_exe_sha256) { throw 'Hash EXE berubah saat upgrade identik.' }
    if ((Get-FileHash -LiteralPath $connectionIni).Hash -ne $connectionHash) { throw 'Upgrade mengubah konfigurasi koneksi.' }
    Wait-OwnProcess "$installDir\app\$name.exe" $smokeArgs
    $row.upgrade=$true
    # Uninstaller sendiri memverifikasi target absolut + marker sebelum menghapus.
    # Tidak ada Remove-Item rekursif dalam skrip verifikasi ini.
    Wait-OwnProcess "$installDir\Uninstall.exe" @('/S')
    $deadline=[DateTime]::UtcNow.AddSeconds(30)
    while ((Test-Path -LiteralPath $installDir) -and [DateTime]::UtcNow -lt $deadline) { Start-Sleep -Milliseconds 250 }
    if ((Test-Path -LiteralPath $installDir) -or (Test-Path -LiteralPath $shortcut) -or (Test-Path -LiteralPath $reg)) { throw "Uninstall belum bersih: $installDir" }
    $row.uninstall=$true
    if ((Get-FileHash -LiteralPath $connectionIni).Hash -ne $connectionHash) { throw 'Uninstall mengubah konfigurasi koneksi.' }
    $row['connection_preserved']=$true
    $row.external_data_preserved=((Get-FileHash -LiteralPath $sentinel -Algorithm SHA256).Hash -eq $sentinelHash)
    if (!$row.external_data_preserved) { throw 'Data sentinel berubah.' }
    $results += [pscustomobject]$row
    $results | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath "evidence/installers-$Target.json" -Encoding UTF8
    # Hanya konfigurasi fixture yang tidak ada sebelum tes dan tetap cocok hash-nya.
    Remove-Item -LiteralPath $connectionIni
}
$results | Format-Table
