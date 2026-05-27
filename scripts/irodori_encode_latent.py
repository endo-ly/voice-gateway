"""Bridge script: encode a WAV file into a DACVAE latent tensor (.pt).

Runs inside Irodori-TTS's environment (cwd = IRODORI_REPO_DIR).
Called by voice-gateway's LatentEncoder via subprocess.
"""

import argparse
import sys
import wave
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))

import torch


def _load_pcm_wav(path: str) -> tuple[torch.Tensor, int]:
    with wave.open(path, "rb") as wav_file:
        channels = wav_file.getnchannels()
        sample_width = wav_file.getsampwidth()
        sample_rate = wav_file.getframerate()
        frames = wav_file.readframes(wav_file.getnframes())

    if sample_width == 1:
        data = torch.frombuffer(frames, dtype=torch.uint8).to(torch.float32)
        data = (data - 128.0) / 128.0
    elif sample_width == 2:
        data = torch.frombuffer(frames, dtype=torch.int16).to(torch.float32)
        data = data / 32768.0
    elif sample_width == 3:
        raw = torch.frombuffer(frames, dtype=torch.uint8).reshape(-1, 3).to(torch.int32)
        data = raw[:, 0] | (raw[:, 1] << 8) | (raw[:, 2] << 16)
        data = torch.where(data >= 0x800000, data - 0x1000000, data).to(torch.float32)
        data = data / 8388608.0
    elif sample_width == 4:
        data = torch.frombuffer(frames, dtype=torch.int32).to(torch.float32)
        data = data / 2147483648.0
    else:
        raise ValueError(f"Unsupported WAV sample width: {sample_width} bytes")

    data = data.reshape(-1, channels).transpose(0, 1).contiguous()
    return data, sample_rate


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-wav", required=True)
    parser.add_argument("--output-pt", required=True)
    parser.add_argument("--checkpoint")
    parser.add_argument("--codec-repo", default="Aratako/Semantic-DACVAE-Japanese-32dim")
    parser.add_argument("--model-device", default="cpu")
    parser.add_argument("--codec-device", default="cpu")
    parser.add_argument("--model-precision", default="fp32")
    parser.add_argument("--codec-precision", default="fp32")
    args = parser.parse_args()

    from irodori_tts.codec import DACVAECodec

    dtype = torch.bfloat16 if args.codec_precision == "bf16" else torch.float32

    codec = DACVAECodec.load(
        repo_id=args.codec_repo,
        device=args.codec_device,
        dtype=dtype,
        deterministic_encode=True,
    )

    wav, sr = _load_pcm_wav(args.input_wav)
    if wav.shape[0] != 1:
        wav = wav.mean(dim=0, keepdim=True)
    wav = wav.unsqueeze(0).to(device=args.codec_device, dtype=dtype)

    latent = codec.encode_waveform(wav, sample_rate=int(sr))[0].cpu()
    torch.save(latent, args.output_pt)
    print(f"Saved latent {latent.shape} -> {args.output_pt}")


if __name__ == "__main__":
    main()
