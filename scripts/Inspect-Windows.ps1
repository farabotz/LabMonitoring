$ErrorActionPreference = 'Continue'
$os = Get-CimInstance Win32_OperatingSystem
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = [Security.Principal.WindowsPrincipal]::new($identity)
$report = [ordered]@{
    Caption=$os.Caption; Version=$os.Version; Architecture=$os.OSArchitecture
    Elevated=$principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    Windows11=([version]$os.Version -ge [version]'10.0.22000')
    VeyonService=([bool](Get-Service VeyonService -ErrorAction SilentlyContinue))
    CameraDevices=@(Get-PnpDevice -Class Camera -PresentOnly -ErrorAction SilentlyContinue | Select-Object FriendlyName,Status)
    Enforcement='BELUM DIVERIFIKASI; tidak ada policy diubah'
}
$report | ConvertTo-Json -Depth 5
