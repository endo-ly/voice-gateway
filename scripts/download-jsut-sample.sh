#!/usr/bin/env bash
set -euo pipefail

SAMPLE_DIR="${1:-sample}"
REPO_ID="FluidInference/JSUT-basic5000"

mkdir -p "$SAMPLE_DIR"

uv run python - "$SAMPLE_DIR" "$REPO_ID" <<'PY'
from pathlib import Path
import sys

from huggingface_hub import hf_hub_download

sample_dir = Path(sys.argv[1])
repo_id = sys.argv[2]
files = [
    "basic5000/BASIC5000_4501.wav",
    "basic5000/transcript_utf8.txt",
    "LICENCE.txt",
]

for filename in files:
    cached = Path(hf_hub_download(repo_id=repo_id, repo_type="dataset", filename=filename))
    target = sample_dir / Path(filename).name
    target.write_bytes(cached.read_bytes())
    print(target)
PY

ffmpeg -y -i "$SAMPLE_DIR/BASIC5000_4501.wav" \
  -ac 1 -ar 16000 "$SAMPLE_DIR/jsut-basic5000-4501-16k.wav"

rg '^BASIC5000_4501:' "$SAMPLE_DIR/transcript_utf8.txt"
