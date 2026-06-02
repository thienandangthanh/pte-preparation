#!/usr/bin/env python3
"""Generate PTE Write-from-Dictation practice audio from dictation-list.csv.

Synthesizes one MP3 per sentence with the local Kokoro-82M TTS model, rotating
through clear US/UK male+female voices so practice mimics the exam's accent
variety. Files are named by the sentence CODE (e.g. audio/WFD0010.mp3).

Engine: Kokoro-82M (Apache-2.0). Runs on CPU; uses CUDA automatically if a
GPU-enabled torch build is installed. First run downloads model weights (~330MB).

Usage:
    python generate-audio.py                  # generate all into audio/
    python generate-audio.py --force          # regenerate existing
    python generate-audio.py --speed 0.9      # slightly slower pace
"""
import argparse
import csv
import io
import subprocess
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

ROOT = Path(__file__).parent
DEFAULT_CSV = ROOT / "dictation-list.csv"
DEFAULT_OUT = ROOT / "audio"
SAMPLE_RATE = 24000  # Kokoro native output rate

# Curated roster: balanced US/UK, male/female. Prefix 'a'=American, 'b'=British.
DEFAULT_VOICES = [
    "af_heart",    # US female
    "am_michael",  # US male
    "bf_emma",     # UK female
    "bm_george",   # UK male
    "af_bella",    # US female
    "am_adam",     # US male
]


def load_rows(csv_path: Path):
    """Yield (code, sentence) pairs from the semicolon-delimited CSV."""
    with csv_path.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f, delimiter=";"):
            code = (row.get("CODE") or "").strip().lstrip("#")
            sentence = (row.get("SENTENCE") or "").strip()
            if code and sentence:
                yield code, sentence


def synthesize(pipeline, sentence: str, voice: str, speed: float) -> np.ndarray:
    """Run Kokoro and concatenate yielded chunks into one float32 waveform."""
    chunks = [audio for _, _, audio in pipeline(sentence, voice=voice, speed=speed)]
    if not chunks:
        raise RuntimeError("Kokoro produced no audio")
    return np.concatenate(chunks)


def write_mp3(audio: np.ndarray, dest: Path) -> None:
    """Encode waveform to MP3 via an in-memory WAV piped through ffmpeg."""
    buf = io.BytesIO()
    sf.write(buf, audio, SAMPLE_RATE, format="WAV")
    subprocess.run(
        ["ffmpeg", "-loglevel", "error", "-y", "-i", "pipe:0", "-q:a", "2", str(dest)],
        input=buf.getvalue(),
        check=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate PTE dictation audio (Kokoro TTS).")
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV, help="Source CSV path")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="Output directory")
    parser.add_argument("--speed", type=float, default=1.0, help="Speech rate (1.0 = natural)")
    parser.add_argument("--voices", nargs="+", default=DEFAULT_VOICES, help="Voice roster to rotate")
    parser.add_argument("--force", action="store_true", help="Regenerate existing files")
    args = parser.parse_args()

    rows = list(load_rows(args.csv))
    if not rows:
        print(f"No rows found in {args.csv}", file=sys.stderr)
        return 1
    args.out.mkdir(parents=True, exist_ok=True)

    # Import torch/kokoro late so --help stays fast.
    import torch
    from kokoro import KPipeline

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Device: {device} | voices: {', '.join(args.voices)}")

    # One pipeline per language; reused across all sentences.
    pipelines = {
        "a": KPipeline(lang_code="a", device=device),  # American English
        "b": KPipeline(lang_code="b", device=device),  # British English
    }

    total = len(rows)
    generated = skipped = 0
    for i, (code, sentence) in enumerate(rows):
        dest = args.out / f"{code}.mp3"
        if dest.exists() and not args.force:
            skipped += 1
            continue
        voice = args.voices[i % len(args.voices)]
        pipeline = pipelines[voice[0]]
        audio = synthesize(pipeline, sentence, voice, args.speed)
        write_mp3(audio, dest)
        generated += 1
        print(f"[{i + 1}/{total}] {dest.name}  ({voice})")

    print(f"Done. Generated {generated}, skipped {skipped}, total {total} -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
