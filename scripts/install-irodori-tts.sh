#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TTS_DIR="${IRODORI_REPO_DIR:-$ROOT_DIR/.vendor/Irodori-TTS}"
TORCH_BACKEND="${IRODORI_TORCH_BACKEND:-cu128}"

echo "=== Irodori-TTS install (torch backend: $TORCH_BACKEND) ==="
echo "    purpose: CLI backend / ref_latent encoding"

mkdir -p "$(dirname "$TTS_DIR")"
if [[ ! -d "$TTS_DIR/.git" ]]; then
  echo "Cloning Irodori-TTS → $TTS_DIR"
  git clone https://github.com/Aratako/Irodori-TTS "$TTS_DIR"
else
  echo "Updating Irodori-TTS"
  git -C "$TTS_DIR" pull --ff-only
fi

echo "Syncing dependencies"
uv sync --directory "$TTS_DIR" --extra "$TORCH_BACKEND"

echo "=== Irodori-TTS install complete ==="
