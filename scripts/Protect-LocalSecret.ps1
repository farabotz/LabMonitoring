param([string]$Path='.env', [string]$RestoreBackup='')
$ErrorActionPreference='Stop'
$root=(Resolve-Path (Join-Path $PSScriptRoot '..')).Path
if ($RestoreBackup) {
    $backup=Get-Content -LiteralPath $RestoreBackup -Raw | ConvertFrom-Json
    $Path=$backup.path
}
$resolved=(Resolve-Path -LiteralPath $Path).Path
$allowedRoot=$root.TrimEnd('\')+'\'
if (!$resolved.StartsWith($allowedRoot,[StringComparison]::OrdinalIgnoreCase)) { throw 'Helper ini hanya mengubah ACL file di workspace ini.' }
$item=Get-Item -LiteralPath $resolved
if ($item.PSIsContainer -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) { throw 'Target harus satu file biasa, bukan directory/link.' }
if ($RestoreBackup) {
    & (Join-Path $root '.venv/Scripts/python.exe') (Join-Path $root 'scripts/restore_dacl.py') (Resolve-Path -LiteralPath $RestoreBackup).Path
    if ($LASTEXITCODE -ne 0) { throw 'Pemulihan DACL gagal; tidak ada privilege OS yang diubah.' }
    Write-Output 'DACL file target dipulihkan; isi file tidak diubah.'
} else {
    New-Item -ItemType Directory -Force (Join-Path $root '.runtime') | Out-Null
    $old=Get-Acl -LiteralPath $resolved
    $backupPath=Join-Path $root ('.runtime/acl-'+[Guid]::NewGuid().ToString('N')+'.json')
    @{path=$resolved;sddl=$old.GetSecurityDescriptorSddlForm([Security.AccessControl.AccessControlSections]::Access)} | ConvertTo-Json | Set-Content -LiteralPath $backupPath -Encoding UTF8
    $acl=New-Object Security.AccessControl.FileSecurity
    $acl.SetAccessRuleProtection($true,$false)
    $sid=[Security.Principal.WindowsIdentity]::GetCurrent().User.Value
    foreach ($id in @($sid,'S-1-5-18','S-1-5-32-544')) {
        $identity=New-Object Security.Principal.SecurityIdentifier($id)
        $rule=New-Object Security.AccessControl.FileSystemAccessRule($identity,'FullControl','Allow')
        $acl.AddAccessRule($rule)
    }
    Set-Acl -LiteralPath $resolved -AclObject $acl
    Write-Output "DACL dibatasi ke identitas saat ini, SYSTEM dan Administrators. Backup: $backupPath"
}
