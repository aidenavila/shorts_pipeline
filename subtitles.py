"""
subtitles.py — caption builders (simple + word-by-word highlight).

Captions are vertically centered on a target line and clamped inside a safe area
so they never run off the top or bottom of the frame. Each word is rendered with
a small margin so its outline/descenders aren't clipped.
"""
from moviepy import TextClip

SAFE_TOP = 0.10      # keep captions within the middle 80% of the height
SAFE_BOTTOM = 0.90
LINE_SPACING = 1.25  # line height as a multiple of font size


def _chunk(word_timings, max_words):
    return [word_timings[i:i + max_words]
            for i in range(0, len(word_timings), max_words)]


def _word_clip(text, font, font_size, color, stroke_color, stroke_width):
    # margin gives the stroke room so it isn't clipped at the glyph box edges
    m = max(stroke_width * 2, 6)
    return TextClip(
        font=font, text=text, font_size=font_size, color=color,
        stroke_color=stroke_color, stroke_width=stroke_width, method="label",
        margin=(m, m),
    )


# --------------------------------------------------------------------------- #
# Simple style
# --------------------------------------------------------------------------- #
def make_caption_clips(word_timings, video_size, font, *,
                       max_words=3, font_size=90, color="white",
                       stroke_color="black", stroke_width=5,
                       y_fraction=0.50):
    w, h = video_size
    clips = []
    for chunk in _chunk(word_timings, max_words):
        text = " ".join(x["word"] for x in chunk).upper()
        start, end = chunk[0]["start"], chunk[-1]["end"]
        clip = TextClip(
            font=font, text=text, font_size=font_size, color=color,
            stroke_color=stroke_color, stroke_width=stroke_width,
            method="caption", size=(int(w * 0.86), None), text_align="center",
            margin=(max(stroke_width * 2, 6), max(stroke_width * 2, 6)),
        )
        # vertically centre on the target line, clamped to the safe area
        y = int(h * y_fraction) - clip.h // 2
        y = max(int(h * SAFE_TOP), min(y, int(h * SAFE_BOTTOM) - clip.h))
        clip = (clip.with_start(start)
                    .with_duration(max(end - start, 0.2))
                    .with_position(("center", y)))
        clips.append(clip)
    return clips


# --------------------------------------------------------------------------- #
# Highlight (word-by-word) style
# --------------------------------------------------------------------------- #
def _layout_group(group, video_size, font, font_size, base_color,
                  stroke_color, stroke_width, y_fraction):
    W, H = video_size
    max_w = int(W * 0.86)
    space = int(font_size * 0.30)
    line_height = int(font_size * LINE_SPACING)

    items = []
    for w in group:
        base = _word_clip(w["word"].upper(), font, font_size,
                          base_color, stroke_color, stroke_width)
        items.append({"word": w, "base": base, "width": base.w, "height": base.h})

    # Greedy wrap into lines no wider than max_w.
    lines, cur = [[]], 0
    for it in items:
        add = it["width"] if not lines[-1] else it["width"] + space
        if lines[-1] and cur + add > max_w:
            lines.append([it])
            cur = it["width"]
        else:
            lines[-1].append(it)
            cur += add

    total_h = len(lines) * line_height
    top = int(H * y_fraction) - total_h // 2
    # clamp so the whole block stays inside the safe area
    top = max(int(H * SAFE_TOP), min(top, int(H * SAFE_BOTTOM) - total_h))

    for li, line in enumerate(lines):
        line_w = sum(it["width"] for it in line) + space * (len(line) - 1)
        x = (W - line_w) // 2
        line_top = top + li * line_height
        for it in line:
            it["x"] = x
            # centre each word vertically within its line slot
            it["y"] = line_top + (line_height - it["height"]) // 2
            x += it["width"] + space
    return items


def make_highlight_caption_clips(word_timings, video_size, font, *,
                                 max_words=3, font_size=90, base_color="white",
                                 highlight_color="#FFE000", stroke_color="black",
                                 stroke_width=5, active_scale=1.12,
                                 y_fraction=0.50):
    clips = []
    for group in _chunk(word_timings, max_words):
        g_start, g_end = group[0]["start"], group[-1]["end"]
        items = _layout_group(group, video_size, font, font_size, base_color,
                              stroke_color, stroke_width, y_fraction)
        for it in items:
            w = it["word"]
            clips.append(
                it["base"].with_start(g_start)
                          .with_duration(max(g_end - g_start, 0.1))
                          .with_position((it["x"], it["y"]))
            )
            hi = _word_clip(w["word"].upper(), font, font_size,
                            highlight_color, stroke_color, stroke_width)
            hx, hy = it["x"], it["y"]
            if active_scale and active_scale != 1.0:
                hi = hi.resized(active_scale)
                hx = int(it["x"] - it["width"] * (active_scale - 1) / 2)
                hy = int(it["y"] - it["height"] * (active_scale - 1) / 2)
            w_start = w["start"]
            w_end = max(w["end"], w_start + 0.12)
            clips.append(
                hi.with_start(w_start)
                  .with_duration(w_end - w_start)
                  .with_position((hx, hy))
            )
    return clips