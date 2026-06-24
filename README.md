# Reddit/Quora → YouTube Shorts pipeline (minimal, working)

A small, modular pipeline that turns a block of story text into a narrated,
captioned 9:16 vertical video:

```
story text → TTS narration (+word timings) → synced captions → compose → short.mp4
```

It runs end-to-end out of the box using **free** tools (edge-tts for voice,
moviepy + ffmpeg for video). Swap pieces out as you grow.

## How the two video tools relate
- **ffmpeg** — the low-level engine that actually encodes/crops/muxes video.
- **moviepy** — a Python wrapper that loads clips as objects, composites them,
  and calls ffmpeg to export. This project uses moviepy for composition; the
  final `write_videofile` step is ffmpeg doing the real work.

## Files
| File | Job |
|------|-----|
| `config.py` | All settings (voice, size, caption style, Reddit source, paths). |
| `narrate.py` | Text → mp3 **and** word-level timings (edge-tts). |
| `subtitles.py` | Word timings → captions: simple **or** word-by-word highlight. |
| `reddit.py` | Pull real story posts from a subreddit via PRAW. |
| `render.py` | Background prep (loop + cover-crop) → compose → export. |
| `main.py` | Ties it together; real fetch with sample-story fallback. |

## Setup
```bash
pip install -r requirements.txt        # moviepy>=2.1, edge-tts>=7.0
# ffmpeg must be on your PATH:  https://ffmpeg.org/download.html
#   macOS:  brew install ffmpeg
#   Ubuntu: sudo apt install ffmpeg
```

Then provide one asset:
```
mkdir -p assets
# put a licensed background loop here (gameplay, stock footage, etc.):
assets/background.mp4
```
Any aspect ratio works — it gets cover-cropped to 9:16 automatically. A font is
auto-detected; drop your own at `assets/font.ttf` to override (a bold font
reads best on Shorts).

## Run
```bash
python main.py        # writes build/short.mp4
```
This uses the built-in sample AITA story so you can confirm everything works
before wiring up real fetching.

## Caption styles
Set `CAPTION_STYLE` in `config.py`:
- `"highlight"` (default) — the word-by-word look: a small group of words is
  shown and the currently-spoken word turns yellow and pops slightly, moving in
  time with the narration. Tune with `HIGHLIGHT_COLOR`, `ACTIVE_SCALE`,
  `MAX_WORDS_PER_CAPTION`.
- `"simple"` — a few centered words at a time, no per-word highlight.

Both get their timing straight from edge-tts's word boundaries, so captions
stay in sync without any separate transcription step.

## Real Reddit stories (PRAW)
Already wired in. To turn it on:
1. `pip install praw` (it's in requirements.txt).
2. Create a **script** app at https://www.reddit.com/prefs/apps.
3. Export credentials (read-only access — no username/password needed):
   ```bash
   export REDDIT_CLIENT_ID="your_id"
   export REDDIT_CLIENT_SECRET="your_secret"
   export REDDIT_USER_AGENT="shorts-pipeline/0.1 by u/yourname"
   ```
4. Pick the source in `config.py`: `SUBREDDIT`, `REDDIT_SORT`,
   `REDDIT_TIME_FILTER`, and the `STORY_MIN_CHARS`/`STORY_MAX_CHARS` length
   budget (~1100 chars keeps a Short under ~60s; raise it for long-form).

`reddit.py` skips stickied/non-text/NSFW posts, enforces the length budget, and
records used post ids in `build/seen.json` so reruns automatically pick a new
story. If credentials are missing or no post qualifies, the pipeline logs why
and falls back to the built-in sample — it never hard-crashes. Set
`USE_REDDIT = False` to always use the sample.

`clean_text()` in `main.py` strips markdown/URLs and expands shorthand like
AITA/NTA into spoken form so the narrator reads naturally. Quora still has no
official API — scrape it (fragile) or paste stories manually.

## Tuning knobs (all in `config.py`)
- `VOICE` — run `edge-tts --list-voices` to browse. Try `en-US-ChristopherNeural`.
- `RATE` / `PITCH` — e.g. `"+8%"` to speed up delivery.
- `VIDEO_SIZE` — `(1080,1920)` Shorts, or `(1920,1080)` for long-form.
- `MAX_WORDS_PER_CAPTION`, font size/color/stroke, `CAPTION_Y_FRACTION`.

## Where to go next
1. **Better voice** — edge-tts is free and fine; ElevenLabs / Azure / OpenAI TTS
   sound noticeably better and are the single biggest quality lever. Their
   timestamp output (or WhisperX forced alignment) can replace edge-tts timings.
2. **Speed at scale** — moviepy is readable but slow and memory-hungry, and the
   highlight style adds ~2 clips per word. Once you render many videos a day,
   rewrite `render.py`'s compose/export as direct ffmpeg `subprocess` calls
   (filter_complex for overlay + drawtext/subtitles).
3. **Long-form videos** — raise `STORY_MAX_CHARS`, set `VIDEO_SIZE=(1920,1080)`,
   and optionally stitch several stories per video.
4. **Upload** — automate with the YouTube Data API.

## Two things worth knowing before you scale
- **YouTube policy:** mass-produced, low-effort, or "reused" TTS-over-gameplay
  content risks monetization/repetition strikes. Channels that last add some
  editorial value (selection, commentary, editing) rather than pure automation.
- **Licensing:** make sure your background footage **and** TTS voices are
  cleared for commercial use, and respect each subreddit's content rules.
