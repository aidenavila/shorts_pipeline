"""
subtitles.py — caption builders.

Two styles:
  - make_caption_clips()           : simple, a few words at a time (centered).
  - make_highlight_caption_clips() : the popular "word-by-word" look — a small
                                     group is shown, and the currently-spoken
                                     word is recoloured (and slightly enlarged)
                                     as the narration reaches it.

The highlight style works because edge-tts gives us each word's start/end. For
every group we lay the words out ourselves (measuring rendered widths, wrapping
to a second line if needed) so we know each word's exact (x, y). Then per word:
  - a base (white) clip spanning the whole group's time, at that position;
  - a highlight (coloured, optionally scaled) clip on top, shown only during
    that word's own time window.
Because we control the coordinates, the highlight lands exactly over its word.
"""
from moviepy import TextClip


def _chunk(word_timings, max_words):
    return [word_timings[i:i + max_words]
            for i in range(0, len(word_timings), max_words)]


def _word_clip(text, font, font_size, color, stroke_color, stroke_width):
    return TextClip(
        font=font, text=text, font_size=font_size, color=color,
        stroke_color=stroke_color, stroke_width=stroke_width, method="label",
    )


# --------------------------------------------------------------------------- #
# Simple style
# --------------------------------------------------------------------------- #
def make_caption_clips(word_timings, video_size, font, *,
                       max_words=3, font_size=90, color="white",
                       stroke_color="black", stroke_width=5,
                       y_fraction=0.60):
    w, h = video_size
    clips = []
    for chunk in _chunk(word_timings, max_words):
        text = " ".join(x["word"] for x in chunk).upper()
        start, end = chunk[0]["start"], chunk[-1]["end"]
        clip = (
            TextClip(font=font, text=text, font_size=font_size, color=color,
                     stroke_color=stroke_color, stroke_width=stroke_width,
                     method="caption", size=(int(w * 0.9), None),
                     text_align="center")
            .with_start(start)
            .with_duration(max(end - start, 0.2))
            .with_position(("center", int(h * y_fraction)))
        )
        clips.append(clip)
    return clips


# --------------------------------------------------------------------------- #
# Highlight (word-by-word) style
# --------------------------------------------------------------------------- #
def _layout_group(group, video_size, font, font_size, base_color,
                  stroke_color, stroke_width, y_fraction):
    """Measure + position each word in the group. Returns a list of dicts with
    keys: word(dict), base(TextClip), width, height, x, y."""
    W, H = video_size
    max_w = int(W * 0.9)
    space = int(font_size * 0.32)

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

    line_h = max(it["height"] for it in items)
    gap = int(line_h * 0.15)
    total_h = len(lines) * line_h + (len(lines) - 1) * gap
    top = int(H * y_fraction) - total_h // 2

    for li, line in enumerate(lines):
        line_w = sum(it["width"] for it in line) + space * (len(line) - 1)
        x = (W - line_w) // 2
        y = top + li * (line_h + gap)
        for it in line:
            it["x"], it["y"] = x, y
            x += it["width"] + space
    return items


def make_highlight_caption_clips(word_timings, video_size, font, *,
                                 max_words=4, font_size=90, base_color="white",
                                 highlight_color="#FFE000", stroke_color="black",
                                 stroke_width=5, active_scale=1.12,
                                 y_fraction=0.60):
    clips = []
    for group in _chunk(word_timings, max_words):
        g_start, g_end = group[0]["start"], group[-1]["end"]
        items = _layout_group(group, video_size, font, font_size, base_color,
                              stroke_color, stroke_width, y_fraction)
        for it in items:
            w = it["word"]
            # Base (white) for the whole group duration.
            clips.append(
                it["base"].with_start(g_start)
                          .with_duration(max(g_end - g_start, 0.1))
                          .with_position((it["x"], it["y"]))
            )
            # Highlight (coloured + popped) only while this word is spoken.
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
