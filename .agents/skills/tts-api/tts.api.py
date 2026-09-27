#!/usr/bin/env python3
"""TTS SSE streaming client — 長文音声生成用

使用方法:
  uv run --with requests python tts_sse.py --text "読み上げテキスト" --voice lyre --output output.wav
  uv run --with requests python tts_sse.py --text-file input.txt --voice lyre --output output.wav

機能:
  - SSE streaming で文単位の音声チャンクを逐次受信
  - 各チャンクは個別WAVヘッダー付きで届くため、PCMを抽出して結合
  - 単一WAVファイルとして出力

注意:
  - アルファベット・英語固有名詞は事前にカタカナに変換すること（TTSが英語読みに非対応）
  - 入力テキストの改行は \n として渡すこと（制御文字のエスケープ必須）
"""
import argparse
import base64
import json
import os
import struct
import sys

import requests

TTS_URL = os.getenv("TTS_URL", "http://127.0.0.1:8012")


def parse_wav_pcm(wav_bytes: bytes) -> tuple[bytes, int, int, int]:
    """WAVバイト列からPCMデータとフォーマット情報を抽出"""
    sample_rate = 48000
    bits_per_sample = 16
    channels = 1
    pcm_data = b""

    idx = 12  # skip RIFF header
    while idx < len(wav_bytes):
        chunk_id = wav_bytes[idx:idx + 4]
        chunk_size = struct.unpack("<I", wav_bytes[idx + 4:idx + 8])[0]
        if chunk_id == b"data":
            pcm_data = wav_bytes[idx + 8:idx + 8 + chunk_size]
            break
        elif chunk_id == b"fmt ":
            fmt = wav_bytes[idx + 8:idx + 8 + chunk_size]
            if len(fmt) >= 16:
                channels = struct.unpack("<H", fmt[2:4])[0]
                sample_rate = struct.unpack("<I", fmt[4:8])[0]
                bits_per_sample = struct.unpack("<H", fmt[14:16])[0]
        idx += 8 + chunk_size
        if chunk_size % 2 == 1:
            idx += 1  # padding byte

    return pcm_data, sample_rate, bits_per_sample, channels


def build_wav(pcm: bytes, sample_rate: int, bits_per_sample: int, channels: int) -> bytes:
    """PCMデータから単一WAVファイルを構築"""
    byte_rate = sample_rate * channels * bits_per_sample // 8
    block_align = channels * bits_per_sample // 8
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF", 36 + len(pcm), b"WAVE",
        b"fmt ", 16,
        1, channels, sample_rate, byte_rate, block_align, bits_per_sample,
        b"data", len(pcm),
    )
    return header + pcm


def generate_sse(text: str, voice: str = "lyre", model: str = "irodori-base") -> bytes:
    """SSE streaming で音声生成し、結合済みWAVを返す"""
    payload = {"model": model, "voice": voice, "input": text, "stream_format": "sse"}

    print(f"Text: {len(text)} chars | Voice: {voice}", file=sys.stderr)
    print("Requesting TTS (SSE)...", file=sys.stderr)

    resp = requests.post(f"{TTS_URL}/v1/audio/speech", json=payload, stream=True, timeout=300)
    if resp.status_code != 200:
        print(f"ERROR: {resp.status_code} {resp.text[:500]}", file=sys.stderr)
        sys.exit(1)

    pcm_chunks = []
    sample_rate, bits_per_sample, channels = 48000, 16, 1
    count = 0

    for raw_line in resp.iter_lines():
        if not raw_line:
            continue
        line = raw_line.decode("utf-8")
        if not line.startswith("data: "):
            continue
        try:
            data = json.loads(line[6:])
        except json.JSONDecodeError:
            continue

        audio_b64 = data.get("audio_base64")
        if not audio_b64:
            continue

        wav_bytes = base64.b64decode(audio_b64)
        pcm, sr, bps, ch = parse_wav_pcm(wav_bytes)
        pcm_chunks.append(pcm)
        sample_rate, bits_per_sample, channels = sr, bps, ch
        count += 1
        print(f"  Chunk {count}: {len(pcm)} bytes PCM", file=sys.stderr)

    if not pcm_chunks:
        print("ERROR: No audio chunks received", file=sys.stderr)
        sys.exit(1)

    all_pcm = b"".join(pcm_chunks)

    wav = build_wav(all_pcm, sample_rate, bits_per_sample, channels)
    duration = len(all_pcm) / (sample_rate * channels * bits_per_sample // 8)

    print(f"Done: {count} chunks, {duration:.1f}s, {len(wav) / 1048576:.1f} MB", file=sys.stderr)
    return wav


def main():
    parser = argparse.ArgumentParser(description="TTS SSE streaming client")
    parser.add_argument("--text", help="読み上げテキスト")
    parser.add_argument("--text-file", help="テキストファイルパス")
    parser.add_argument("--voice", default="lyre", help="音声ID（デフォルト: lyre）")
    parser.add_argument("--model", default="irodori-base", help="モデルID")
    parser.add_argument("--output", required=True, help="出力WAVパス")
    args = parser.parse_args()

    if args.text_file:
        with open(args.text_file, "r") as f:
            text = f.read()
    elif args.text:
        text = args.text
    else:
        print("ERROR: --text or --text-file required", file=sys.stderr)
        sys.exit(1)

    wav = generate_sse(text, args.voice, args.model)
    with open(args.output, "wb") as f:
        f.write(wav)
    print(f"Saved: {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
