"""
parts.py — split a long narration into ~1-minute parts for a multi-part series.

Given the word timings, we cut the story into chunks no longer than
MAX_PART_SECONDS, preferring to break at the end of a sentence so a part never
stops mid-thought. For each part we slice the matching audio out of the single
narration file (no re-narrating) and re-zero the caption times.
"""
import subprocess

import imageio_ffmpeg
from moviepy import TextClip

_SENTENCE_ENDINGS = (".", "!", "?", "\u2026", '."', '!"', '?"')


def split_words_into_parts(words, max_seconds):
    """Return a list of word-lists, each spanning <= ~max_seconds. Always breaks
    at the LAST sentence boundary that still fits; only hard-cuts when a single
    sentence is itself longer than max_seconds."""
    if not words:
        return []
    parts = []
    i, n = 0, len(words)
    while i < n:
        start = words[i]["start"]
        last_sentence_end = None
        j = i
        while j < n and (words[j]["end"] - start) <= max_seconds:
            if words[j]["word"].rstrip().endswith(_SENTENCE_ENDINGS):
                last_sentence_end = j
            j += 1
        if j >= n:                       # everything left fits in one part
            parts.append(words[i:n])
            break
        if last_sentence_end is not None:  # clean break at a sentence end
            end_idx = last_sentence_end
        else:                              # one long sentence -> hard cut
            end_idx = j - 1
        parts.append(words[i:end_idx + 1])
        i = end_idx + 1
    return parts


def rezero(words, offset):
    """Shift word times so the part starts at t=0."""
    return [{"word": w["word"],
             "start": max(w["start"] - offset, 0.0),
             "end": max(w["end"] - offset, 0.0)} for w in words]


def slice_audio(narration_path, start, end, out_path):
    """Cut [start, end] seconds out of the narration into its own file."""
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [ffmpeg, "-y", "-i", narration_path,
           "-ss", f"{start:.3f}", "-to", f"{end:.3f}", out_path]
    r = subprocess.run(cmd, stdout=subprocess.DEVNULL,
                       stderr=subprocess.PIPE, text=True)
    if r.returncode != 0:
        raise RuntimeError("ffmpeg audio slice failed:\n" + r.stderr[-500:])
    return out_path


def make_part_badge(text, video_size, font, duration, font_size=52):
    """A small 'PART n/N' label pinned near the top of the frame."""
    W, H = video_size
    clip = TextClip(font=font, text=text, font_size=font_size, color="white",
                    stroke_color="black", stroke_width=4, method="label",
                    margin=(10, 10))
    return (clip.with_start(0).with_duration(duration)
                .with_position(("center", int(H * 0.07))))