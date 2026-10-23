param([string]$Executable='', [string]$Server='', [string]$Ca='', [string]$AgentPipe='', [switch]$Remove)
$ErrorActionPreference = 'Stop'
$key='HKCU:\Software\Microsoft\Windows\CurrentVersion\Run'
$name='LabAccessStudent'
$statePath=Join-Path $env:LOCALAPPDATA 'LabAccess\startup-state.json'
$properties=Get-ItemProperty -LiteralPath $key -ErrorAction SilentlyContinue
$current=if ($properties -and $properties.PSObject.Properties[$name]) { $properties.PSObject.Properties[$name].Value } else { $null }
if ($Remove) {
    if (!(Test-Path -LiteralPath $statePath)) { throw 'Tidak ada catatan startup yang dikelola skrip ini; registry tidak diubah.' }
    $state=Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
    if ($null -ne $current -and $current -ne $state.command) { throw 'Startup berubah sejak pemasangan; pertahankan perubahan pengguna dan tinjau manual.' }
    Remove-ItemProperty -LiteralPath $key -Name $name -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $statePath
    Write-Output 'Startup LabAccess untuk akun ini dihapus; data dan akun Windows dipertahankan.'
} else {
    if (!$Executable) { throw 'Executable wajib ketika memasang startup.' }
    $resolved=(Resolve-Path -LiteralPath $Executable).Path
    if ([IO.Path]::GetExtension($resolved) -ne '.exe') { throw 'Pilih EXE hasil build.' }
    if ($current -or (Test-Path -LiteralPath $statePath)) { throw 'Startup/catatannya sudah ada; tidak menimpa. Lepas konfigurasi yang dikelola terlebih dahulu.' }
    $command='"'+$resolved+'"'
    foreach ($entry in @(@('--server',$Server),@('--ca',$Ca),@('--agent-pipe',$AgentPipe))) {
        if ($entry[1]) {
            if ($entry[1] -match '["\r\n]') { throw 'Argumen startup mengandung karakter tidak valid.' }
            $command += ' '+$entry[0]+' "'+$entry[1]+'"'
        }
    }
    New-Item -ItemType Directory -Force (Split-Path -Parent $statePath) | Out-Null
    @{command=$command;created_utc=[DateTime]::UtcNow.ToString('o')} | ConvertTo-Json | Set-Content -LiteralPath $statePath -Encoding UTF8
    New-Item -Path $key -Force | Out-Null
    New-ItemProperty -LiteralPath $key -Name $name -PropertyType String -Value $command | Out-Null
    Write-Output 'Startup akun ini terpasang. Startup bukan pembatasan akses OS.'
}
