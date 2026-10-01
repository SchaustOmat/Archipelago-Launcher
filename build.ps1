# Builds dist\ArchipelagoLauncher.exe (downloads at setup)
# and with -Full also dist\ArchipelagoLauncher-Full.exe (Archipelago + SoH bundled, works offline for those).
param([switch]$Full)
# PyInstaller logs to stderr; Windows PowerShell would treat that as an error under 'Stop'.
$ErrorActionPreference = 'Continue'
Set-Location $PSScriptRoot

if (-not (Test-Path .venv)) { py -3.14 -m venv .venv }
.\.venv\Scripts\python -m pip install -q -r requirements.txt pyinstaller

# bridge\ is zipped into an apworld at install time, so it ships as plain files.
$common = @('--noconfirm', '--onefile', '--windowed', '--clean', '--collect-submodules', 'websockets',
            '--add-data', 'bridge;bridge', '--add-data', 'patches;patches', 'main.py')
.\.venv\Scripts\pyinstaller @common --name ArchipelagoLauncher
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller failed' }

if ($Full) {
    # File names must match what aplauncher/install.py asks the payload for.
    $cfg = .\.venv\Scripts\python -c "from aplauncher import config as c; print(c.AP_URL); print(c.AP_VERSION); print(c.SOH_ZIP_URL); print(c.SOH_APWORLD_URL); print(c.SOH_VERSION); print(c.UT_URL); print(c.UT_VERSION)"
    $apUrl, $apVer, $sohUrl, $worldUrl, $sohVer, $utUrl, $utVer = $cfg
    $payload = 'build\payload'
    New-Item -ItemType Directory -Force $payload | Out-Null
    $files = @{
        "Setup.Archipelago.$apVer.exe"          = $apUrl
        "SoH_Archipelago_${sohVer}_Windows.zip" = $sohUrl
        "oot_soh-$sohVer.apworld"               = $worldUrl
        "tracker-$utVer.apworld"                = $utUrl
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
# Ready-to-send folders and zips: release\ArchipelagoLauncher[-Full]_<version>.zip
$ver = .\.venv\Scripts\python -c "from aplauncher import config; print(config.APP_VERSION)"
New-Item -ItemType Directory -Force release | Out-Null
foreach ($exe in Get-ChildItem dist\*.exe) {
    $name = $exe.BaseName
    $dir = "release\$name"
    Remove-Item -Recurse -Force $dir -ErrorAction SilentlyContinue
    New-Item -ItemType Directory -Force $dir | Out-Null
    Copy-Item $exe.FullName "$dir\ArchipelagoLauncher.exe"
    Copy-Item ANLEITUNG.txt $dir
    $zip = "release\${name}_$ver.zip"
    Remove-Item $zip -ErrorAction SilentlyContinue
    Compress-Archive -Path $dir -DestinationPath $zip
}
# Setup.exe (Inno Setup 6; per-user install, no admin)
$iscc = @("$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe", "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe") |
    Where-Object { Test-Path $_ } | Select-Object -First 1
if ($iscc) {
    foreach ($exe in Get-ChildItem dist\*.exe) {
        & $iscc /Q "/DAppVersion=$ver" "/DSourceExe=$($exe.FullName)" "/DOutName=$($exe.BaseName)-Setup" installer.iss
        if ($LASTEXITCODE -ne 0) { throw "Inno Setup failed for $($exe.Name)" }
    }
} else {
    Write-Host 'Inno Setup 6 not found, skipping Setup.exe (winget install JRSoftware.InnoSetup)'
}
Get-ChildItem release\*.zip, release\*.exe | Select-Object Name, @{n = 'MB'; e = { [math]::Round($_.Length / 1MB, 1) } }
