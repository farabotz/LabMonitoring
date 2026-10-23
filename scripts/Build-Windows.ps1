param([ValidateSet('student','admin','all')][string]$Target = 'all', [ValidateSet('zig','msvc','mingw64')][string]$Compiler = 'mingw64', [string]$Python = '.tools/buildenv/Scripts/python.exe')
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location -LiteralPath $root
if (![Environment]::Is64BitOperatingSystem) { throw 'Build ini untuk Windows x64.' }
New-Item -ItemType Directory -Force .runtime/tmp,build | Out-Null
$env:TEMP = "$root\.runtime\tmp"
$env:TMP = $env:TEMP
$env:PROCESSOR_ARCHITECTURE = 'AMD64'
$env:PYTHONPATH = $root
$targets = if ($Target -eq 'all') { @('student','admin') } else { @($Target) }
foreach ($app in $targets) {
    $compilerOption = if ($Compiler -eq 'msvc') { '--msvc=latest' } else { "--$Compiler" }
    $options = @('-m','nuitka',"scripts/entry_$app.py",'--mode=standalone','--enable-plugin=pyside6',
        '--include-qt-plugins=platforms,styles,imageformats','--windows-console-mode=disable',
        '--assume-yes-for-downloads','--jobs=2', $compilerOption,
        "--output-dir=build/$app", "--output-filename=LabAccess-$app.exe",
        "--report=build/$app-report.xml",'--company-name=LabAccess Research Prototype',
        '--product-name=LabAccess','--file-version=0.1.0.0','--product-version=0.1.0.0',
        '--nofollow-import-to=pytest,services.api,sqlalchemy,scipy,matplotlib')
    & $Python @options
    if ($LASTEXITCODE -ne 0) { throw "Build $app gagal: $LASTEXITCODE" }
}
