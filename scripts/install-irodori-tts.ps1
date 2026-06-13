$ErrorActionPreference = "Stop"

$RootDir = Resolve-Path "$PSScriptRoot/.."
$TtsDir = if ($env:IRODORI_REPO_DIR) { $env:IRODORI_REPO_DIR } else { "$RootDir/.vendor/Irodori-TTS" }
$TorchBackend = if ($env:IRODORI_TORCH_BACKEND) { $env:IRODORI_TORCH_BACKEND } else { "cu128" }

Write-Host "=== Irodori-TTS install (torch backend: $TorchBackend) ==="
Write-Host "    purpose: CLI backend / ref_latent encoding"

$parent = Split-Path $TtsDir -Parent
if (-not (Test-Path $parent)) { New-Item -ItemType Directory -Path $parent | Out-Null }

if (-not (Test-Path "$TtsDir/.git")) {
    Write-Host "Cloning Irodori-TTS -> $TtsDir"
    git clone https://github.com/Aratako/Irodori-TTS $TtsDir
} else {
    Write-Host "Updating Irodori-TTS"
    git -C $TtsDir pull --ff-only
}

Write-Host "Syncing dependencies"
uv sync --directory $TtsDir --extra $TorchBackend

Write-Host "=== Irodori-TTS install complete ==="
