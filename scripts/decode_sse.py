"""Decode SSE speech stream response into a single WAV file.

Usage:
  # From raw SSE file
  python scripts/decode_sse.py -i sse_raw.txt -o output.wav

  # Directly from Gateway (model/voice auto-detected)
  python scripts/decode_sse.py --text "こんにちは。テストです。" -o output.wav

  # With explicit model/voice
  python scripts/decode_sse.py --model irodori-base --voice lyre \
    --text "こんにちは。" -o output.wav

Requirements:
  pip install httpx
"""

import argparse
import base64
import json
import struct
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from typing import Optional

try:
    import httpx
    _HAS_HTTPX = True
except ImportError:
    _HAS_HTTPX = False


def parse_sse(raw_text: str) -> list[dict]:
    events = []
    current_event = None
    current_data = None

    for line in raw_text.splitlines():
        if line.startswith("event: "):
            current_event = line[len("event: "):]
        elif line.startswith("data: "):
            current_data = line[len("data: "):]
        elif line == "" and current_event is not None:
            events.append({"event": current_event, "data": current_data})
            current_event = None
            current_data = None

    if current_event is not None:
        events.append({"event": current_event, "data": current_data})

    return events


def extract_audio_chunks(events: list[dict]) -> list[bytes]:
    chunks = []
    for ev in events:
        if ev["event"] != "audio_chunk":
            continue
        data = json.loads(ev["data"])
        audio = base64.b64decode(data["audio_base64"])
        text_preview = data.get("text", "")[:40]
        print(f"  chunk {data['index']}: {len(audio)} bytes, text={text_preview}")
        chunks.append(audio)

    for ev in events:
        if ev["event"] == "error":
            err = json.loads(ev["data"])
            print(f"  ERROR: {err}", file=sys.stderr)
        elif ev["event"] == "done":
            done = json.loads(ev["data"])
            print(f"  done: {done['chunks']} chunks total")

    return chunks


def combine_wav(chunks: list[bytes]) -> bytes:
    if not chunks:
        raise ValueError("No audio chunks to combine")

    first = chunks[0]
    channels = struct.unpack_from("<H", first, 22)[0]
    sample_rate = struct.unpack_from("<I", first, 24)[0]
    bits_per_sample = struct.unpack_from("<H", first, 34)[0]
    print(f"Format: {sample_rate}Hz, {channels}ch, {bits_per_sample}bit")

    all_pcm = b"".join(c[44:] for c in chunks)

    byte_rate = sample_rate * channels * bits_per_sample // 8
    block_align = channels * bits_per_sample // 8

    wav = bytearray()
    wav += b"RIFF"
    wav += struct.pack("<I", 36 + len(all_pcm))
    wav += b"WAVE"
    wav += b"fmt "
    wav += struct.pack("<I", 16)
    wav += struct.pack("<H", 1)
    wav += struct.pack("<H", channels)
    wav += struct.pack("<I", sample_rate)
    wav += struct.pack("<I", byte_rate)
    wav += struct.pack("<H", block_align)
    wav += struct.pack("<H", bits_per_sample)
    wav += b"data"
    wav += struct.pack("<I", len(all_pcm))
    wav += all_pcm

    return bytes(wav)


def decode_file(input_path: str, output_path: str) -> None:
    raw = Path(input_path).read_text(encoding="utf-8")
    events = parse_sse(raw)
    chunks = extract_audio_chunks(events)
    wav = combine_wav(chunks)
    Path(output_path).write_bytes(wav)
    print(f"WAV written: {output_path} ({len(wav)} bytes)")


def _auto_detect_model_voice(base_url: str) -> tuple[str, str]:
    """Fetch first available TTS model and voice from the Gateway."""
    with httpx.Client(timeout=10.0) as client:
        voices_resp = client.get(f"{base_url}/v1/voices")
        voices_resp.raise_for_status()
        voices = voices_resp.json().get("data", [])
        if not voices:
            raise RuntimeError("No voices available on the Gateway")

        voice = voices[0]
        voice_id = voice["id"]
        preferred_model = voice.get("preferred_model")

        models_resp = client.get(f"{base_url}/v1/models")
        models_resp.raise_for_status()
        models = [m for m in models_resp.json().get("data", []) if m.get("direction", "tts") == "tts"]
        if not models:
            raise RuntimeError("No TTS models available on the Gateway")

        if preferred_model and any(m["id"] == preferred_model for m in models):
            model_id = preferred_model
        else:
            model_id = models[0]["id"]

    return model_id, voice_id


def _base_url_from_endpoint(url: str) -> str:
    """Extract base URL from a full endpoint URL."""
    from urllib.parse import urlsplit
    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.netloc}"


def fetch_and_decode(
    url: str, model: str | None, voice: str | None, text: str,
    output_path: str, extra: Optional[dict] = None,
) -> None:
    if not _HAS_HTTPX:
        print("httpx is required for --url mode. Install with: pip install httpx", file=sys.stderr)
        sys.exit(1)

    if not model or not voice:
        base_url = _base_url_from_endpoint(url)
        auto_model, auto_voice = _auto_detect_model_voice(base_url)
        model = model or auto_model
        voice = voice or auto_voice
        print(f"Auto-detected: model={model}, voice={voice}")

    payload = {
        "model": model,
        "voice": voice,
        "input": text,
        "stream_format": "sse",
    }
    if extra:
        payload.update(extra)

    print(f"Requesting {url} ...")
    chunks = []
    with httpx.Client(timeout=600.0) as client:
        with client.stream("POST", url, json=payload) as resp:
            resp.raise_for_status()
            buffer = ""
            for line in resp.iter_text():
                buffer += line
                if buffer.endswith("\n\n"):
                    events = parse_sse(buffer)
                    for ev in events:
                        if ev["event"] == "audio_chunk":
                            data = json.loads(ev["data"])
                            audio = base64.b64decode(data["audio_base64"])
                            print(f"  chunk {data['index']}: {len(audio)} bytes, text={data.get('text', '')[:40]}")
                            chunks.append(audio)
                        elif ev["event"] == "done":
                            done = json.loads(ev["data"])
                            print(f"  done: {done['chunks']} chunks total")
                        elif ev["event"] == "error":
                            err = json.loads(ev["data"])
                            print(f"  ERROR: {err}", file=sys.stderr)
                    buffer = ""

    wav = combine_wav(chunks)
    Path(output_path).write_bytes(wav)
    print(f"WAV written: {output_path} ({len(wav)} bytes)")


def main():
    parser = argparse.ArgumentParser(description="Decode SSE speech stream into a single WAV file")
    parser.add_argument("-i", "--input", help="Raw SSE response file path")
    parser.add_argument("-o", "--output", default="output.wav", help="Output WAV path (default: output.wav)")

    fetch_group = parser.add_argument_group("direct fetch mode")
    fetch_group.add_argument("--url", nargs="?", const="http://127.0.0.1:8012/v1/audio/speech", help="Gateway endpoint URL (default: http://127.0.0.1:8012/v1/audio/speech)")
    fetch_group.add_argument("--model", default=None, help="Model ID (auto-detected if omitted)")
    fetch_group.add_argument("--voice", default=None, help="Voice ID (auto-detected if omitted)")
    fetch_group.add_argument("--text", help="Input text")
    fetch_group.add_argument("--segment-mode", choices=["conversation", "narration"], help="Segment mode")

    args = parser.parse_args()

    if args.url or args.text:
        if not args.text:
            parser.error("--text is required with --url mode")
        url = args.url or "http://127.0.0.1:8012/v1/audio/speech"
        extra = {}
        if args.segment_mode:
            extra["segment"] = {"enabled": True, "mode": args.segment_mode}
        fetch_and_decode(url, args.model, args.voice, args.text, args.output, extra)
    elif args.input:
        decode_file(args.input, args.output)
    else:
        parser.error("Either --input or --url is required")


if __name__ == "__main__":
    main()
