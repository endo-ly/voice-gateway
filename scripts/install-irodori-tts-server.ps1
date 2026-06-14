$ErrorActionPreference = "Stop"

$RootDir = Resolve-Path "$PSScriptRoot/.."
$ServerDir = if ($env:IRODORI_SERVER_DIR) { $env:IRODORI_SERVER_DIR } else { "$RootDir/.vendor/Irodori-TTS-Server" }
$TorchBackend = if ($env:IRODORI_TORCH_BACKEND) { $env:IRODORI_TORCH_BACKEND } else { "cu128" }

Write-Host "=== Irodori-TTS-Server install (torch backend: $TorchBackend) ==="
Write-Host "    purpose: server backend (managed HTTP engine)"

$parent = Split-Path $ServerDir -Parent
if (-not (Test-Path $parent)) { New-Item -ItemType Directory -Path $parent | Out-Null }

if (-not (Test-Path "$ServerDir/.git")) {
    Write-Host "Cloning Irodori-TTS-Server -> $ServerDir"
    git clone https://github.com/Aratako/Irodori-TTS-Server $ServerDir
} else {
    Write-Host "Updating Irodori-TTS-Server"
    git -C $ServerDir pull --ff-only
}

Write-Host "Syncing dependencies"
uv sync --directory $ServerDir --extra $TorchBackend

Write-Host "=== Irodori-TTS-Server install complete ==="
