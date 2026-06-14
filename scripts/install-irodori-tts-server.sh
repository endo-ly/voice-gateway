#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVER_DIR="${IRODORI_SERVER_DIR:-$ROOT_DIR/.vendor/Irodori-TTS-Server}"
TORCH_BACKEND="${IRODORI_TORCH_BACKEND:-cu128}"

echo "=== Irodori-TTS-Server install (torch backend: $TORCH_BACKEND) ==="
echo "    purpose: server backend (managed HTTP engine)"

mkdir -p "$(dirname "$SERVER_DIR")"
if [[ ! -d "$SERVER_DIR/.git" ]]; then
  echo "Cloning Irodori-TTS-Server → $SERVER_DIR"
  git clone https://github.com/Aratako/Irodori-TTS-Server "$SERVER_DIR"
else
  echo "Updating Irodori-TTS-Server"
  git -C "$SERVER_DIR" pull --ff-only
fi

echo "Syncing dependencies"
uv sync --directory "$SERVER_DIR" --extra "$TORCH_BACKEND"

echo "=== Irodori-TTS-Server install complete ==="
