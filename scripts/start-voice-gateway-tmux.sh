#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SESSION="${VOICE_GATEWAY_TMUX_SESSION:-voice-gateway}"
HOST="${VOICE_GATEWAY_HOST:-127.0.0.1}"
PORT="${VOICE_GATEWAY_PORT:-8012}"
MODE="${VOICE_GATEWAY_MODE:-all}"
AIVIS_BASE_URL="${AIVIS_BASE_URL:-http://127.0.0.1:10101}"
AIVIS_MANAGE_ENGINE="${AIVIS_MANAGE_ENGINE:-1}"
AIVIS_ENGINE_DIR="${AIVIS_ENGINE_DIR:-$ROOT_DIR/.vendor/AivisSpeech-Engine}"
STT_CALLBACK_URL="${STT_CALLBACK_URL:-http://127.0.0.1:8787/stt/events}"

if tmux has-session -t "$SESSION" 2>/dev/null; then
  tmux kill-session -t "$SESSION"
fi

case "$AIVIS_MANAGE_ENGINE" in
  1|true|TRUE|yes|YES|on|ON)
    pkill -f "$AIVIS_ENGINE_DIR/.venv/bin/python3 run.py --host .* --port 10101" 2>/dev/null || true
    pkill -f "uv run run.py --host .* --port 10101" 2>/dev/null || true
    ;;
esac

tmux new-session -d -s "$SESSION" -c "$ROOT_DIR" \
  "env -u VIRTUAL_ENV VOICE_GATEWAY_MODE='$MODE' AIVIS_BASE_URL='$AIVIS_BASE_URL' AIVIS_MANAGE_ENGINE='$AIVIS_MANAGE_ENGINE' AIVIS_ENGINE_DIR='$AIVIS_ENGINE_DIR' STT_CALLBACK_URL='$STT_CALLBACK_URL' uv run uvicorn app.main:app --host '$HOST' --port '$PORT'"

echo "Started $SESSION on http://$HOST:$PORT"
