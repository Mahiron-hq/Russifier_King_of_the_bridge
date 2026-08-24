[CmdletBinding()]
param(
    [Parameter()]
    [string]$GamePath = $env:KOTB_GAME_PATH,

    [ValidateSet('Debug', 'Release')]
    [string]$Configuration = 'Release',

    [switch]$Package,

    [string]$BepInExArchive
)

$ErrorActionPreference = 'Stop'
$projectRoot = $PSScriptRoot

function Copy-ReleaseDocumentation {
    param([Parameter(Mandatory)][string]$Destination)

    foreach ($fileName in @('README.md', 'CHANGELOG.md', 'LICENSE', 'NOTICE', 'THIRD_PARTY_NOTICES.md')) {
        Copy-Item -LiteralPath (Join-Path $projectRoot $fileName) -Destination $Destination -Force
    }
    Copy-Item -LiteralPath (Join-Path $projectRoot 'LICENSES') -Destination $Destination -Recurse -Force
}

if ([string]::IsNullOrWhiteSpace($GamePath)) {
    throw 'Pass -GamePath or set KOTB_GAME_PATH.'
}

$resolvedGamePath = (Resolve-Path -LiteralPath $GamePath).Path
$project = Join-Path $projectRoot 'RussianTranslationMod.csproj'

dotnet build $project -c $Configuration -p:GamePath="$resolvedGamePath"
if ($LASTEXITCODE -ne 0) {
    throw "dotnet build failed with exit code $LASTEXITCODE"
}

if ($Package) {
    $distRoot = Join-Path $projectRoot 'dist'
    $packageRoot = Join-Path $distRoot 'staging\plugin'
    if (Test-Path -LiteralPath $packageRoot) {
        Remove-Item -LiteralPath $packageRoot -Recurse -Force
    }
    $pluginRoot = Join-Path $packageRoot 'BepInEx\plugins\KingOfTheBridge.Russian'
    New-Item -ItemType Directory -Path $pluginRoot -Force | Out-Null
    Copy-ReleaseDocumentation -Destination $packageRoot
    Copy-Item -LiteralPath (Join-Path $projectRoot "bin\$Configuration\KingOfTheBridge.Russian.dll") -Destination $pluginRoot -Force
    Copy-Item -LiteralPath (Join-Path $projectRoot 'translation.txt') -Destination $pluginRoot -Force
    Copy-Item -LiteralPath (Join-Path $projectRoot 'image_mapping.txt') -Destination $pluginRoot -Force
    Copy-Item -LiteralPath (Join-Path $projectRoot 'alagard-unicode-tmp') -Destination $pluginRoot -Force
    Copy-Item -LiteralPath (Join-Path $projectRoot 'assets\images') -Destination $pluginRoot -Recurse -Force

    $archive = Join-Path $distRoot 'KingOfTheBridge_Russian_Plugin.zip'
    if (Test-Path -LiteralPath $archive) {
        Remove-Item -LiteralPath $archive -Force
    }
    Compress-Archive -Path (Join-Path $packageRoot '*') -DestinationPath $archive -CompressionLevel Optimal
    Write-Host "Package: $archive"

    if (-not [string]::IsNullOrWhiteSpace($BepInExArchive)) {
        $resolvedBepInExArchive = (Resolve-Path -LiteralPath $BepInExArchive).Path
        $fullRoot = Join-Path $distRoot 'staging\full'
        if (Test-Path -LiteralPath $fullRoot) {
            Remove-Item -LiteralPath $fullRoot -Recurse -Force
        }
        Expand-Archive -LiteralPath $resolvedBepInExArchive -DestinationPath $fullRoot
        Copy-ReleaseDocumentation -Destination $fullRoot
        $fullPluginRoot = Join-Path $fullRoot 'BepInEx\plugins\KingOfTheBridge.Russian'
        New-Item -ItemType Directory -Path $fullPluginRoot -Force | Out-Null
        Copy-Item -Path (Join-Path $pluginRoot '*') -Destination $fullPluginRoot -Recurse -Force

        $fullArchive = Join-Path $distRoot 'KingOfTheBridge_Russian_Full.zip'
        if (Test-Path -LiteralPath $fullArchive) {
            Remove-Item -LiteralPath $fullArchive -Force
        }
        Compress-Archive -Path (Join-Path $fullRoot '*') -DestinationPath $fullArchive -CompressionLevel Optimal
        Write-Host "Full package: $fullArchive"
        Remove-Item -LiteralPath $fullRoot -Recurse -Force
    }

    Remove-Item -LiteralPath $packageRoot -Recurse -Force
    $stagingRoot = Join-Path $distRoot 'staging'
    if (Test-Path -LiteralPath $stagingRoot) {
        Remove-Item -LiteralPath $stagingRoot -Recurse -Force
    }
}
