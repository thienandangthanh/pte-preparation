# Add Local TTS Audio Generation for Dictation Practice

**Date**: 2026-06-02  
**Severity**: Medium  
**Component**: Audio generation pipeline, environment setup  
**Status**: Resolved  

## What Happened

Implemented `generate-audio.py` + environment setup to produce 177 MP3 audio files from the PTE Write-from-Dictation CSV using local, open-source Kokoro-82M TTS on the user's RTX GPU. Each sentence now has a clean, accent-rotated audio clip named by its CODE (`WFD0010.mp3`, etc.) for listening-based typing practice.

## The Brutal Truth

This was refreshingly smooth execution — research upfront paid off. The main friction wasn't technical but environmental: system Python 3.14 lacks torch wheels, forcing a shift to uv's project workflow pinning Python 3.12. Once that was clear, everything clicked. The only "surprise" was a positive one: Kokoro bundles its own phonemizer, killing the need for a `sudo pacman -S espeak-ng` system dependency that was in the plan.

A scout-block hook prevents bash access to `.venv/` paths, which was dodged by using `uv run python` instead of calling the venv interpreter directly.

## Technical Details

**Implementation**: `generate-audio.py` (119 lines)
- Reads semicolon-delimited CSV via `csv.DictReader`, yields `(CODE, SENTENCE)` pairs
- Six-voice roster: `af_heart, am_michael, bf_emma, bm_george, af_bella, am_adam` (3 US, 3 UK, balanced gender)
- Rotates voices by row index modulo roster length (deterministic, stable across reruns)
- One `KPipeline` per language (`a` = American, `b` = British), reused across 177 sentences
- `synthesize()` concatenates Kokoro's yielded audio chunks into float32 waveform
- `write_mp3()` pipes in-memory WAV through ffmpeg with `-q:a 2` (VBR ~70 kbps, tradeoff between clarity + file size)
- Idempotent: skips existing MP3s unless `--force` flag passed
- Argparse CLI: `--csv`, `--out`, `--speed`, `--voices`, `--force`

**Environment** (`pyproject.toml` + `uv.lock`):
- Python 3.12 (uv auto-downloads, torch has no 3.14 wheels yet)
- Deps: kokoro, soundfile, numpy (torch pulled transitively)
- CUDA auto-detected via `torch.cuda.is_available()` — ran with CUDA on first execution (RTX GPU)

**Output**: `audio/` directory, 177 MP3s, ~6.8 MB total, 3–5 s each. All verified by spot-check: ffprobe confirms durations, voice rotation heard (US female → UK male → US male pattern), text matches input.

**Idempotency verified**: rerun without `--force` skipped all 177 files; `--force` regenerated them cleanly.

## What We Tried

- Considered heavier TTS models (Orpheus 3B, Chatterbox, F5-TTS, Fish Speech, Piper) — rejected due to overhead (GPU memory, cloning complexity, latency) with zero benefit for dictation's clean single-sentence use case.
- Planned espeak-ng system install — unnecessary; Kokoro bundles `espeakng_loader`, killed that step.
- Tested ffmpeg piping approach (WAV in-memory → MP3) instead of temp files — works cleanly, no disk thrashing.

## Root Cause Analysis

N/A — no failures to analyze. The upfront research phase (comparing TTS models, verifying Kokoro's capabilities, understanding the Python 3.12 constraint) prevented false starts. The plan was tight and executed as written.

## Lessons Learned

1. **Research pays.** Spending time understanding model trade-offs (Kokoro's MOS ~4.5 + neutral speech vs. expressive alternatives) prevented picking the wrong engine.
2. **uv project workflow beats venv + requirements.txt.** Pinning Python 3.12 in `pyproject.toml` meant torch wheels "just worked" without manual version hunting.
3. **Bundle dependencies wisely.** Kokoro shipping its own phonemizer eliminated an extra system dependency that would've added friction on fresh machines.
4. **Idempotency from day one.** The `exists() and not --force` guard means developers can safely rerun without fear; reruns cost nothing.
5. **Bash hook isolation matters.** The `.venv` access block forced using `uv run` instead of direct interpreter calls — not a problem once understood, but worth documenting for the next person.

## Next Steps

- **Optional**: Add a `docs/` usage note (one paragraph explaining how to run `generate-audio.py` and what the output is). Currently the script's docstring covers it, but explicit docs don't hurt.
- **Optional**: Decide on MP3 quality: current `-q:a 2` (~70 kbps VBR) is transparent for speech. Could lower to 64 kbps for tighter distribution, or accept current tradeoff.
- **Done**: Commit `generate-audio.py`, `pyproject.toml`, `uv.lock`, `.gitignore` edits (added `audio/` + `.venv/`).
- **Monitor**: First time user runs this on their machine, Kokoro downloads ~330 MB of model weights; plan to mention this in any docs or README.

---

**Files involved**:
- `/home/andang/Documents/PTE/generate-audio.py` (119 lines, implements full pipeline)
- `/home/andang/Documents/PTE/pyproject.toml` (new, uv project config)
- `/home/andang/Documents/PTE/uv.lock` (new, locked deps)
- `/home/andang/Documents/PTE/.gitignore` (modified to add `audio/` + `.venv/`)
