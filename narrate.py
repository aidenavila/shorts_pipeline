"""
narrate.py — turn story text into an audio file PLUS word-level timings.

edge-tts streams two kinds of chunks:
  - {"type": "audio", "data": b"..."}                      -> the mp3 bytes
  - {"type": "WordBoundary", "offset", "duration", "text"} -> caption timing

As of 2026 Microsoft's free endpoint is flaky about sending WordBoundary
metadata even when the audio itself comes through fine. So:
  - if we get word timings, great, captions are perfectly synced;
  - if we get audio but NO timings, we estimate timing from the audio length
    (captions are evenly paced — good enough, and never blocks a render);
  - only if NO audio arrives at all do we stop, because then the voice really
    is blocked and you need a different engine (see README).
"""
import asyncio
import os
import re

import edge_tts

# 1 second = 10,000,000 ticks of 100 ns
TICKS_PER_SECOND = 10_000_000


async def _synthesize(text, voice, rate, pitch, out_path):
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    kwargs = {}
    if rate:
        kwargs["rate"] = rate
    if pitch:
        kwargs["pitch"] = pitch

    communicate = edge_tts.Communicate(text, voice, **kwargs)
    words = []
    audio_bytes = 0
    with open(out_path, "wb") as f:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
                audio_bytes += len(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                start = chunk["offset"] / TICKS_PER_SECOND
                dur = chunk["duration"] / TICKS_PER_SECOND
                words.append({"word": chunk["text"],
                              "start": start, "end": start + dur})
    return words, audio_bytes


def _estimate_timings(text, duration):
    """Spread `duration` seconds across words, weighted by word length so longer
    words get proportionally more time. Approximate but keeps captions in step
    with the overall narration length."""
    tokens = re.findall(r"\S+", text)
    if not tokens:
        return []
    weights = [max(len(t), 2) for t in tokens]
    total = sum(weights)
    out, t = [], 0.0
    for tok, wt in zip(tokens, weights):
        span = duration * wt / total
        out.append({"word": tok, "start": t, "end": t + span})
        t += span
    return out


def _audio_duration(path):
    from moviepy import AudioFileClip
    clip = AudioFileClip(path)
    try:
        return clip.duration
    finally:
        clip.close()


def narrate(text, voice, out_path, rate="", pitch=""):
    """
    Returns (out_path, word_timings) where word_timings is a list of
    {"word", "start", "end"} dicts in seconds.
    """
    words, audio_bytes = asyncio.run(
        _synthesize(text, voice, rate, pitch, out_path))

    if audio_bytes < 1024:
        raise RuntimeError(
            "edge-tts returned no audio at all — Microsoft's free voice is "
            "blocking this connection. Time to switch the voice engine; ask "
            "for the offline-TTS setup."
        )

    if not words:
        duration = _audio_duration(out_path)
        words = _estimate_timings(text, duration)
        print(f"     (word-timing metadata unavailable — estimated from "
              f"{duration:.1f}s of audio; captions are evenly paced)")

    return out_path, words