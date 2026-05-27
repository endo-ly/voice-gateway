#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${STT_ADAPTER_URL:-http://127.0.0.1:8790}"
SAMPLE_WAV="${1:-sample/sample.wav}"

curl -fsS "$BASE_URL/health" | jq .
curl -fsS "$BASE_URL/v1/capabilities" | jq .

if [[ -f "$SAMPLE_WAV" ]]; then
  curl -fsS -X POST "$BASE_URL/v1/audio/transcriptions" \
    -F "file=@$SAMPLE_WAV" \
    -F "source=stackchan" | jq .

  curl -fsS -X POST "$BASE_URL/v1/transcribe" \
    -F "file=@$SAMPLE_WAV" \
    -F "source=stackchan" | jq .

  curl -fsS "$BASE_URL/v1/transcriptions/latest" | jq .
else
  echo "Sample WAV not found: $SAMPLE_WAV" >&2
  echo "Place a short mono 16kHz WAV there, or pass a path as the first argument." >&2
fi
