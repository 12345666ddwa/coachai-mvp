#!/usr/bin/env python3
"""Transcribe meeting recording with faster-whisper (auto language)."""
import sys
import time
from faster_whisper import WhisperModel

SRC = "/mnt/c/Users/18613/Downloads/2026年09月04日 18点13分.mp3"
OUT = "/home/gaogao/workspace/ai-coach/meeting_transcript.txt"

t0 = time.time()
print("loading model...", flush=True)
model = WhisperModel("small", device="cpu", compute_type="int8")
print(f"model loaded in {time.time()-t0:.0f}s, transcribing...", flush=True)

segments, info = model.transcribe(
    SRC,
    language=None,          # auto-detect
    vad_filter=True,        # skip silence
    beam_size=5,
    initial_prompt=None,
)

lines = []
for seg in segments:
    ts = f"[{int(seg.start // 60):02d}:{int(seg.start % 60):02d}-{int(seg.end // 60):02d}:{int(seg.end % 60):02d}]"
    line = f"{ts} {seg.text.strip()}"
    lines.append(line)
    print(line, flush=True)

with open(OUT, "w", encoding="utf-8") as f:
    f.write(f"# Meeting transcript\n# Source: {SRC}\n# Duration: {info.duration:.0f}s | Language: {info.language} (p={info.language_probability:.2f})\n\n")
    f.write("\n".join(lines))

print(f"\nDONE in {time.time()-t0:.0f}s | {len(lines)} segments | language={info.language} | saved to {OUT}", flush=True)
