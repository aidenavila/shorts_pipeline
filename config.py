"""
Central settings. Tweak these without touching the pipeline logic.
"""
import os
import shutil

# ---- Output frame ----------------------------------------------------------
# 1080x1920 = vertical 9:16 for Shorts. Use (1920, 1080) for normal long-form.
VIDEO_SIZE = (1080, 1920)
FPS = 30

# ---- Narration (edge-tts) --------------------------------------------------
# Free, no API key, decent quality. List all voices with:  edge-tts --list-voices
# Good English narrators: en-US-GuyNeural, en-US-ChristopherNeural,
# en-US-AriaNeural, en-GB-RyanNeural
VOICE = "en-US-GuyNeural"
# Speaking rate / pitch, e.g. "+10%" to speed up. Empty string = default.
RATE = "+8%"
PITCH = "+0Hz"

# ---- Captions --------------------------------------------------------------
CAPTION_STYLE = "highlight"    # "highlight" (word-by-word) or "simple"
MAX_WORDS_PER_CAPTION = 4      # words shown on screen at once
CAPTION_FONT_SIZE = 90
CAPTION_COLOR = "white"
CAPTION_STROKE_COLOR = "black"
CAPTION_STROKE_WIDTH = 5
HIGHLIGHT_COLOR = "#FFE000"    # colour of the currently-spoken word
ACTIVE_SCALE = 1.12           # how much the active word pops (1.0 = no pop)
# Vertical position as a fraction of frame height (0 = top, 1 = bottom).
CAPTION_Y_FRACTION = 0.60

# ---- Files -----------------------------------------------------------------
# A background loop you own/licensed (gameplay, satisfying clips, etc.).
# Must exist before you run. Any aspect ratio — it gets cover-cropped to 9:16.
BACKGROUND_VIDEO = "assets/background.mp4"
NARRATION_FILE = "build/narration.mp3"
OUTPUT_FILE = "build/short.mp4"

# ---- Reddit source (optional; needs PRAW + credentials) --------------------
USE_REDDIT = False              # False -> always use the built-in sample story
SUBREDDIT = "amitheasshole"    # also try: horror, entitledparents, tifu
REDDIT_SORT = "top"            # "top", "hot", or "new"
REDDIT_TIME_FILTER = "week"    # for "top": hour/day/week/month/year/all
STORY_MIN_CHARS = 200
STORY_MAX_CHARS = 1100         # ~60s Short; raise for long-form videos
SKIP_NSFW = True
SEEN_FILE = "build/seen.json"  # remembers used posts so reruns pick new ones


def find_font():
    """Return a path to a bold TTF. moviepy v2 needs a real font file."""
    candidates = [
        "assets/font.ttf",  # drop your own font here to override
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/Library/Fonts/Arial Bold.ttf",                 # macOS
        "C:/Windows/Fonts/arialbd.ttf",                  # Windows
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    found = shutil.which("fc-match")  # last resort on Linux
    raise FileNotFoundError(
        "No font found. Put a .ttf at assets/font.ttf or install DejaVu fonts."
    )


FONT = None  # resolved lazily in main.py via find_font()
