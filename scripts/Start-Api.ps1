param([string]$BindAddress = '127.0.0.1', [int]$Port = 8000, [string]$Certificate = '', [string]$PrivateKey = '')
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location -LiteralPath $root
if ($BindAddress -notin @('127.0.0.1','::1') -and (!$Certificate -or !$PrivateKey)) { throw 'TLS wajib untuk LAN.' }
$options = @('-m','uvicorn','services.api.main:create_app','--factory','--host',$BindAddress,'--port',"$Port",'--no-access-log','--no-proxy-headers')
if ($Certificate) { $options += @('--ssl-certfile',$Certificate,'--ssl-keyfile',$PrivateKey) }
& .venv\Scripts\python.exe @options
