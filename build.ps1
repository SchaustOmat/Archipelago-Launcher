# Builds dist\ArchipelagoLauncher.exe (downloads at setup)
# and with -Full also dist\ArchipelagoLauncher-Full.exe (Archipelago + SoH bundled, works offline for those).
param([switch]$Full)
# PyInstaller logs to stderr; Windows PowerShell would treat that as an error under 'Stop'.
$ErrorActionPreference = 'Continue'
Set-Location $PSScriptRoot

if (-not (Test-Path .venv)) { py -3.14 -m venv .venv }
.\.venv\Scripts\python -m pip install -q -r requirements.txt pyinstaller

$common = @('--noconfirm', '--onefile', '--windowed', '--clean', '--collect-submodules', 'websockets', 'main.py')
.\.venv\Scripts\pyinstaller @common --name ArchipelagoLauncher
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller failed' }

if ($Full) {
    # File names must match what aplauncher/install.py asks the payload for.
    $cfg = .\.venv\Scripts\python -c "from aplauncher import config as c; print(c.AP_URL); print(c.AP_VERSION); print(c.SOH_ZIP_URL); print(c.SOH_APWORLD_URL); print(c.SOH_VERSION)"
    $apUrl, $apVer, $sohUrl, $worldUrl, $sohVer = $cfg
    $payload = 'build\payload'
    New-Item -ItemType Directory -Force $payload | Out-Null
    $files = @{
        "Setup.Archipelago.$apVer.exe"          = $apUrl
        "SoH_Archipelago_${sohVer}_Windows.zip" = $sohUrl
        "oot_soh-$sohVer.apworld"               = $worldUrl
    }
    foreach ($name in $files.Keys) {
        $dest = Join-Path $payload $name
        if (-not (Test-Path $dest)) {
            Write-Host "Downloading $name"
            curl.exe -sSL -o $dest $files[$name]
            if ($LASTEXITCODE -ne 0) { throw "download failed: $name" }
        }
    }
    .\.venv\Scripts\pyinstaller @common --name ArchipelagoLauncher-Full --add-data "$payload;payload"
    if ($LASTEXITCODE -ne 0) { throw 'PyInstaller (full) failed' }
}
Get-ChildItem dist\*.exe | Select-Object Name, @{n = 'MB'; e = { [math]::Round($_.Length / 1MB, 1) } }
