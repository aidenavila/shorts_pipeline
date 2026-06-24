"""
render.py — prepare the background, layer captions, export the final mp4.

Audio is muxed in with a DIRECT FFmpeg call instead of through moviepy. moviepy
writes the video; FFmpeg attaches the narration. This is version-proof and
sidesteps the silent-audio issues some moviepy/OS combos hit.
"""
import os
import random
import subprocess

import imageio_ffmpeg
from moviepy import (
    VideoFileClip, AudioFileClip, CompositeVideoClip, concatenate_videoclips,
)


def prepare_background(path, duration, target_size):
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Background video not found: {path}\n"
            "Put a licensed loop there (gameplay, stock footage, etc.)."
        )
    tw, th = target_size
    clip = VideoFileClip(path).without_audio()

    if clip.duration < duration:                       # loop if too short
        loops = int(duration // clip.duration) + 1
        clip = concatenate_videoclips([clip] * loops)

    max_start = max(clip.duration - duration, 0)        # trim to a window
    start = random.uniform(0, max_start)
    clip = clip.subclipped(start, start + duration)

    scale = max(tw / clip.w, th / clip.h)               # cover-crop to frame
    clip = clip.resized(scale)
    clip = clip.cropped(width=tw, height=th,
                        x_center=clip.w / 2, y_center=clip.h / 2)
    return clip


def render_short(background_path, narration_path, caption_clips,
                 out_path, target_size, fps):
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)

    audio = AudioFileClip(narration_path)
    duration = audio.duration
    audio.close()  # we only needed the length; FFmpeg muxes the real audio

    background = prepare_background(background_path, duration, target_size)
    final = (CompositeVideoClip([background, *caption_clips], size=target_size)
             .with_duration(duration))

    # 1) moviepy renders VIDEO ONLY (audio=False).
    tmp_video = out_path + ".video_only.mp4"
    final.write_videofile(
        tmp_video, fps=fps, codec="libx264", audio=False,
        preset="medium", threads=os.cpu_count() or 4,
    )

    # 2) FFmpeg attaches the narration (copy video, encode audio to AAC).
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [
        ffmpeg, "-y", "-i", tmp_video, "-i", narration_path,
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        "-map", "0:v:0", "-map", "1:a:0", "-shortest", out_path,
    ]
    result = subprocess.run(cmd, stdout=subprocess.DEVNULL,
                            stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        raise RuntimeError("FFmpeg audio mux failed:\n" + result.stderr[-800:])

    if os.path.exists(tmp_video):
        os.remove(tmp_video)
    return out_path