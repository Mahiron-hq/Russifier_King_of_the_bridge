<#
.SYNOPSIS
    Builds the installer from a local copy of King of the Bridge.

.DESCRIPTION
    1. Copies the game into build\original, putting back originals from RussianMod_backup if the mod is installed.
    2. Builds the C# helper and code patcher against that copy.
    3. Applies the mod to a second copy (build\patched) with tools\build_mod.py.
    4. Packs the difference into build\payload.tar and takes the window art from the game.
    5. Builds the installer and copies it to dist\.

.PARAMETER GameDir
    Folder that holds "King of the Bridge.exe". Defaults to the usual Steam location.
#>
param(
    [string]$GameDir = "C:\Program Files (x86)\Steam\steamapps\common\King of the Bridge"
)

$ErrorActionPreference = "Stop"
$Repo = Split-Path -Parent $PSScriptRoot
$Build = Join-Path $Repo "build"
$Original = Join-Path $Build "original"
$Patched = Join-Path $Build "patched"
$Python = Join-Path $Repo ".venv\Scripts\python.exe"
$Data = "King of the Bridge_Data"
$Manifest = Join-Path $Repo "Cargo.toml"

function Invoke-Checked([string]$What, [scriptblock]$Command) {
    Write-Host "== $What"
    & $Command
    if ($LASTEXITCODE -ne 0) { throw "$What failed with exit code $LASTEXITCODE" }
}

function Copy-Tree([string]$From, [string]$To) {
    robocopy $From $To /E /NFL /NDL /NJH /NJS /NP | Out-Null
    # robocopy reports success with codes below 8.
    if ($LASTEXITCODE -ge 8) { throw "copying $From failed (robocopy $LASTEXITCODE)" }
    $global:LASTEXITCODE = 0
}

if (-not (Test-Path (Join-Path $GameDir "King of the Bridge.exe"))) { throw "no King of the Bridge.exe in $GameDir" }
if (-not (Test-Path $Python)) { throw "missing .venv; see tools\requirements.txt" }

foreach ($dir in $Original, $Patched) {
    if (Test-Path $dir) { Remove-Item -Recurse -Force $dir }
}

Write-Host "== Clean copy of the game"
Copy-Tree (Join-Path $GameDir $Data) (Join-Path $Original $Data)
Copy-Item (Join-Path $GameDir "King of the Bridge.exe") $Original
$Backup = Join-Path $GameDir "RussianMod_backup"
if (Test-Path (Join-Path $Backup $Data)) { Copy-Tree (Join-Path $Backup $Data) (Join-Path $Original $Data) }
Get-ChildItem (Join-Path $Original "$Data\StreamingAssets\aa\StandaloneWindows64") -Filter "*russian(ru)*" | Remove-Item
Get-ChildItem $Original -Recurse -Filter "*.kotb-tmp" | Remove-Item
foreach ($extra in "$Data\Managed\KotbRussian.dll", "$Data\StreamingAssets\ru") {
    $path = Join-Path $Original $extra
    if (Test-Path $path) { Remove-Item -Recurse -Force $path }
}
if (Select-String -Path (Join-Path $Original "$Data\StreamingAssets\aa\catalog.json") -Pattern "russian(ru)" -SimpleMatch -Quiet) {
    throw "the game copy still contains the mod; verify the game files in Steam"
}

$Managed = Join-Path $Original "$Data\Managed"
Invoke-Checked "KotbRussian.dll" { dotnet build (Join-Path $Repo "mod\KotbRussian") -c Release -nologo -v q "-p:GameManaged=$Managed" }
Invoke-Checked "KotbPatcher.exe" { dotnet build (Join-Path $Repo "mod\KotbPatcher") -c Release -nologo -v q }

Write-Host "== Patched copy"
Copy-Tree $Original $Patched
$Settings = Join-Path $Build "first_run_settings.json"
Invoke-Checked "Mod files" { & $Python (Join-Path $Repo "tools\build_mod.py") $Patched $Settings }

$Payload = Join-Path $Build "payload.tar"
Invoke-Checked "Payload" {
    cargo run --manifest-path $Manifest --release --locked --quiet -p patchset --bin build-payload -- `
        --original $Original --patched $Patched --settings $Settings --out $Payload
}
$Ui = Join-Path $Build "ui"
Invoke-Checked "Window art" { & $Python (Join-Path $Repo "tools\extract_ui_art.py") $Original $Ui }
Invoke-Checked "Third-party licences" { & $Python (Join-Path $Repo "tools\third_party_licenses.py") (Join-Path $Ui "third_party.txt") }
Invoke-Checked "Installer" { cargo build --manifest-path $Manifest --release --locked -p installer }

$Version = (tar -xOf $Payload manifest.json | ConvertFrom-Json).version
$Dist = Join-Path $Repo "dist"
New-Item -ItemType Directory -Force $Dist | Out-Null
$Exe = Join-Path $Dist ("KotB_Russian_" + ($Version -replace " ", "_") + ".exe")
Copy-Item (Join-Path $Repo "target\release\installer.exe") $Exe -Force
Write-Host "== Done: $Exe"
