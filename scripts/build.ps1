<#
.SYNOPSIS
Builds the plugin and packs a ready-to-extract release archive into release/.

.DESCRIPTION
Downloads the pinned BepInEx build (verifying its SHA-256), compiles src/RussianTranslationMod
against it and the game's assemblies, and lays out the same tree as the published releases:
doorstop_config.ini, winhttp.dll and BepInEx/ with the plugin and the data files.

.PARAMETER GameDir
Installed King of the Bridge folder that the plugin is compiled against.

.PARAMETER Configuration
MSBuild configuration. Release by default.

.PARAMETER MSBuildArgs
Extra arguments passed to MSBuild as they are.

.EXAMPLE
.\scripts\build.ps1 -GameDir 'D:\Games\King of the Bridge'
#>
[CmdletBinding()]
param(
    [string]$GameDir = 'C:\Program Files (x86)\Steam\steamapps\common\King of the Bridge',
    [ValidateSet('Release', 'Debug')]
    [string]$Configuration = 'Release',

    [string[]]$MSBuildArgs = @()
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$BepInExVersion = '5.4.23.4'
$BepInExUrl = "https://github.com/BepInEx/BepInEx/releases/download/v$BepInExVersion/BepInEx_win_x64_$BepInExVersion.zip"
$BepInExSha256 = 'f881201b79da03e513bf97cdf39607ffa7f9e0d31a519b1aeeca8eb60f8309e7'

$repo = Split-Path -Parent $PSScriptRoot
$project = Join-Path $repo 'src\RussianTranslationMod\RussianTranslationMod.csproj'
$releaseDir = Join-Path $repo 'release'

function Find-MSBuild {
    $vswhere = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio\Installer\vswhere.exe'
    if (-not (Test-Path $vswhere)) {
        throw 'vswhere.exe not found. Install Visual Studio 2022 or Build Tools with the .NET desktop build workload.'
    }
    $found = & $vswhere -latest -requires Microsoft.Component.MSBuild -find 'MSBuild\**\Bin\MSBuild.exe' |
        Select-Object -First 1
    if (-not $found) { throw 'MSBuild not found by vswhere.' }
    $found
}

if (-not (Test-Path (Join-Path $GameDir 'King of the Bridge_Data\Managed\Assembly-CSharp.dll'))) {
    throw "Game assemblies not found in '$GameDir'. Pass the game folder with -GameDir."
}

$cacheDir = Join-Path $releaseDir '.cache'
$bepInExZip = Join-Path $cacheDir "BepInEx_win_x64_$BepInExVersion.zip"
New-Item -ItemType Directory -Force $cacheDir | Out-Null
if (-not (Test-Path $bepInExZip)) {
    Write-Host "Downloading BepInEx $BepInExVersion..."
    Invoke-WebRequest $BepInExUrl -OutFile $bepInExZip -UseBasicParsing
}
$actual = (Get-FileHash $bepInExZip -Algorithm SHA256).Hash.ToLowerInvariant()
if ($actual -ne $BepInExSha256) {
    Remove-Item $bepInExZip
    throw "BepInEx archive checksum mismatch (got $actual). The file was removed."
}
$bepInExTmp = Join-Path $cacheDir 'bepinex'
if (Test-Path $bepInExTmp) { Remove-Item $bepInExTmp -Recurse -Force }
Expand-Archive $bepInExZip $bepInExTmp

Write-Host "Building $Configuration..."
& (Find-MSBuild) $project /nologo /verbosity:minimal "/p:Configuration=$Configuration" "/p:GameDir=$GameDir" `
    "/p:BepInExCoreDir=$(Join-Path $bepInExTmp 'BepInEx\core')" @MSBuildArgs
if ($LASTEXITCODE -ne 0) { throw "MSBuild failed with exit code $LASTEXITCODE." }

$pluginDll = Join-Path $repo "src\RussianTranslationMod\bin\$Configuration\RussianTranslationMod.dll"
$version = ([Diagnostics.FileVersionInfo]::GetVersionInfo($pluginDll).FileVersion -split '\.')[0..2] -join '.'


$name = "RussianTranslationMod-v$version"
$stage = Join-Path $releaseDir $name
if (Test-Path $stage) { Remove-Item $stage -Recurse -Force }

New-Item -ItemType Directory -Force (Join-Path $stage 'BepInEx\plugins\image') | Out-Null
Copy-Item (Join-Path $bepInExTmp 'winhttp.dll'), (Join-Path $bepInExTmp 'doorstop_config.ini') $stage
Copy-Item (Join-Path $bepInExTmp 'BepInEx\core') (Join-Path $stage 'BepInEx\core') -Recurse

$plugins = Join-Path $stage 'BepInEx\plugins'
Copy-Item $pluginDll $plugins
Copy-Item (Join-Path $repo 'data\translation.txt'), (Join-Path $repo 'data\image_mapping.txt'),
    (Join-Path $repo 'data\fonts\alagard-unicode-tmp') $plugins
Copy-Item (Join-Path $repo 'data\images\translated\*.png') (Join-Path $plugins 'image')

$archive = Join-Path $releaseDir "$name.zip"
if (Test-Path $archive) { Remove-Item $archive }
Add-Type -AssemblyName System.IO.Compression.FileSystem
[IO.Compression.ZipFile]::CreateFromDirectory($stage, $archive)

Write-Host "Done: $archive"
