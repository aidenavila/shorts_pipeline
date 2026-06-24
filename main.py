"""
main.py — the orchestration layer. Run:  python main.py

Pipeline:  story text -> TTS narration (+timings) -> captions -> compose -> mp4

The sample story is hard-coded so you can run end-to-end immediately.
fetch_reddit_story() shows where to plug in PRAW for real automation.
"""
import config
from narrate import narrate
from subtitles import make_caption_clips, make_highlight_caption_clips
from render import render_short


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
    # Common Reddit shorthand -> spoken form (extend as you like)
    for k, v in {
        "AITA": "Am I the asshole",
        "WIBTA": "Would I be the asshole",
        "NTA": "Not the asshole",
        "YTA": "You're the asshole",
        "TIFU": "Today I messed up",
    }.items():
        text = re.sub(rf"\b{k}\b", v, text)
    return text


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
    print(f"     {len(words)} words timed, audio -> {narration_path}")

    print("     Building captions...")
    if config.CAPTION_STYLE == "highlight":
        captions = make_highlight_caption_clips(
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
    else:
        captions = make_caption_clips(
            words, config.VIDEO_SIZE, config.FONT,
            max_words=config.MAX_WORDS_PER_CAPTION,
            font_size=config.CAPTION_FONT_SIZE,
            color=config.CAPTION_COLOR,
            stroke_color=config.CAPTION_STROKE_COLOR,
            stroke_width=config.CAPTION_STROKE_WIDTH,
            y_fraction=config.CAPTION_Y_FRACTION,
        )
    print(f"     {len(captions)} caption clips ({config.CAPTION_STYLE} style)")

    print("3/3  Rendering (ffmpeg)...")
    out = render_short(
        config.BACKGROUND_VIDEO, narration_path, captions,
        config.OUTPUT_FILE, config.VIDEO_SIZE, config.FPS,
    )
    print(f"Done -> {out}")


if __name__ == "__main__":
    main()
