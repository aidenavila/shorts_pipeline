"""
main.py — orchestration. Run:  py main.py

Pipeline:  Reddit story -> TTS narration (+timings) -> captions -> compose -> mp4

If a story is longer than MAX_PART_SECONDS it's split into a numbered
multi-part series (part1, part2, ...), each ~1 minute, broken at sentence ends.
"""
import os

import config
from narrate import narrate, _audio_duration
from subtitles import make_caption_clips, make_highlight_caption_clips
from render import render_short
from parts import split_words_into_parts, rezero, slice_audio, make_part_badge


SAMPLE_STORY = (
    "AITA for refusing to switch seats on a plane? "
    "I booked a window seat months in advance because I get motion sick. "
    "A mom asked me to move so she could sit with her kid, "
    "but the seat she offered was a middle seat at the back. "
    "I said no, and now half the row thinks I'm the villain. "
    "So... am I the asshole?"
)


def get_story():
    """Pull a real Reddit post if enabled and possible; else use the sample."""
    if not config.USE_REDDIT:
        return clean_text(SAMPLE_STORY)
    try:
        from reddit import fetch_story
        story = fetch_story(
            config.SUBREDDIT,
            sort=config.REDDIT_SORT,
            time_filter=config.REDDIT_TIME_FILTER,
            min_chars=config.STORY_MIN_CHARS,
            max_chars=config.STORY_MAX_CHARS,
            skip_nsfw=config.SKIP_NSFW,
            seen_path=config.SEEN_FILE,
        )
        if story:
            print(f"     Fetched from r/{story['subreddit']}: {story['title'][:70]}")
            return clean_text(story["text"])
        print("     No new qualifying post found; using sample story.")
    except Exception as e:
        print(f"     Reddit fetch unavailable ({e}); using sample story.")
    return clean_text(SAMPLE_STORY)


def clean_text(text):
    """Light cleanup so the narrator doesn't read markdown/links aloud."""
    import re
    text = re.sub(r"\[(.*?)\]\(.*?\)", r"\1", text)  # markdown links -> label
    text = re.sub(r"http\S+", "", text)            # strip any bare URLs
    text = re.sub(r"[*_>#~`\[\]()]", "", text)      # markdown / leftover symbols
    text = re.sub(r"\s+", " ", text).strip()
    for k, v in {
        "AITA": "Am I the asshole", "WIBTA": "Would I be the asshole",
        "NTA": "Not the asshole", "YTA": "You're the asshole",
        "TIFU": "Today I messed up",
    }.items():
        text = re.sub(rf"\b{k}\b", v, text)
    return text


def build_captions(words):
    """Build caption clips for one (re-zeroed) word list, per config style."""
    if config.CAPTION_STYLE == "highlight":
        return make_highlight_caption_clips(
            words, config.VIDEO_SIZE, config.FONT,
            max_words=config.MAX_WORDS_PER_CAPTION,
            font_size=config.CAPTION_FONT_SIZE,
            base_color=config.CAPTION_COLOR,
            highlight_color=config.HIGHLIGHT_COLOR,
            stroke_color=config.CAPTION_STROKE_COLOR,
            stroke_width=config.CAPTION_STROKE_WIDTH,
            active_scale=config.ACTIVE_SCALE,
            y_fraction=config.CAPTION_Y_FRACTION,
        )
    return make_caption_clips(
        words, config.VIDEO_SIZE, config.FONT,
        max_words=config.MAX_WORDS_PER_CAPTION,
        font_size=config.CAPTION_FONT_SIZE,
        color=config.CAPTION_COLOR,
        stroke_color=config.CAPTION_STROKE_COLOR,
        stroke_width=config.CAPTION_STROKE_WIDTH,
        y_fraction=config.CAPTION_Y_FRACTION,
    )


def main():
    config.FONT = config.find_font()
    print(f"Using font: {config.FONT}")

    print("1/3  Getting story...")
    story = get_story()
    print(f"     Story ({len(story)} chars): {story[:80]}...")

    print("2/3  Generating narration...")
    narration_path, words = narrate(
        story, config.VOICE, config.NARRATION_FILE,
        rate=config.RATE, pitch=config.PITCH,
    )
    duration = words[-1]["end"] if words else 0.0
    print(f"     {len(words)} words, ~{duration:.0f}s of narration")

    print("3/3  Rendering (ffmpeg)...")
    base, ext = os.path.splitext(config.OUTPUT_FILE)

    # Single video if short enough (or multi-part disabled).
    if not config.MULTIPART or duration <= config.MAX_PART_SECONDS:
        captions = build_captions(words)
        out = render_short(config.BACKGROUND_VIDEO, narration_path, captions,
                           config.OUTPUT_FILE, config.VIDEO_SIZE, config.FPS)
        print(f"Done -> {out}")
        return

    # Otherwise split into a numbered series.
    parts = split_words_into_parts(words, config.MAX_PART_SECONDS)
    total = len(parts)
    full_dur = _audio_duration(narration_path)
    print(f"     Long story -> {total} parts of up to {config.MAX_PART_SECONDS}s")

    outputs = []
    for idx, part in enumerate(parts, 1):
        p_start = part[0]["start"]
        p_end = min(part[-1]["end"] + 0.4, full_dur)   # small tail so it doesn't clip
        part_audio = f"{base}_part{idx}_audio.mp3"
        slice_audio(narration_path, p_start, p_end, part_audio)

        captions = build_captions(rezero(part, p_start))
        captions.append(make_part_badge(f"PART {idx}/{total}", config.VIDEO_SIZE,
                                        config.FONT, p_end - p_start))

        out = f"{base}_part{idx}{ext}"
        render_short(config.BACKGROUND_VIDEO, part_audio, captions,
                     out, config.VIDEO_SIZE, config.FPS)
        os.remove(part_audio)
        outputs.append(out)
        print(f"     part {idx}/{total} -> {out}")

    print("Done -> " + ", ".join(outputs))


if __name__ == "__main__":
    main()