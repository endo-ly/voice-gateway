#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REAZON_DIR="${STT_VENDOR_DIR:-${REAZONSPEECH_REPO_DIR:-$ROOT_DIR/.vendor/ReazonSpeech}}"

mkdir -p "$(dirname "$REAZON_DIR")"

if [[ ! -d "$REAZON_DIR/.git" ]]; then
  git clone https://github.com/reazon-research/ReazonSpeech "$REAZON_DIR"
else
  git -C "$REAZON_DIR" pull --ff-only
fi

uv pip install "$REAZON_DIR/pkg/k2-asr"
uv pip install sherpa-onnx
