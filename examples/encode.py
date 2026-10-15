#!/usr/bin/env python3
"""Step 4：帧序列 + 配音 -> output.mp4。
用法: python encode.py build/frames build/voiceover.mp3 build/output.mp4 [--fps 30]"""
import argparse

from common import ffmpeg

ap = argparse.ArgumentParser()
ap.add_argument("frames_dir")
ap.add_argument("audio")
ap.add_argument("output")
ap.add_argument("--fps", type=int, default=30)
a = ap.parse_args()
ffmpeg("-framerate", a.fps, "-i", f"{a.frames_dir}/frame_%05d.png", "-i", a.audio,
       "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
       "-c:a", "aac", "-b:a", "192k", "-shortest", a.output)
print("OK:", a.output)
