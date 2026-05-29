#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
AIVIS_DIR="${AIVIS_ENGINE_DIR:-$ROOT_DIR/.vendor/AivisSpeech-Engine}"
SESSION="${AIVIS_TMUX_SESSION:-aivis-speech-engine}"
HOST="${AIVIS_ENGINE_BIND_HOST:-127.0.0.1}"
PORT="${AIVIS_ENGINE_PORT:-10101}"

if [[ ! -d "$AIVIS_DIR" ]]; then
  echo "AivisSpeech Engine directory not found: $AIVIS_DIR" >&2
  exit 1
fi

if tmux has-session -t "$SESSION" 2>/dev/null; then
  tmux kill-session -t "$SESSION"
fi

tmux new-session -d -s "$SESSION" -c "$AIVIS_DIR" \
  "env -u VIRTUAL_ENV uv run run.py --host '$HOST' --port '$PORT' --no-use_gpu --output_log_utf8"

echo "Started $SESSION on http://$HOST:$PORT"
