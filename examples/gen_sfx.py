#!/usr/bin/env python3
"""Step 5：用 ffmpeg lavfi 合成 SFX，并用 volumedetect 校验音量（max 低于 -15 dB 视为失败）。
用法: python gen_sfx.py [--out-dir sfx]
"""
import argparse
import os

from common import ffmpeg
from volume import max_volume

# 名称 -> (lavfi 源, 滤镜)
SFX = {
    "whoosh": ("anoisesrc=d=0.5:c=white:a=0.6", "bandpass=f=2000:width_type=o:w=2,aecho=0.8:0.88:60:0.4,volume=3.0"),
    "typing_key": ("anoisesrc=d=0.04:c=pink:a=0.8", "highpass=f=3000,lowpass=f=8000,volume=4.0"),
    "pop": ("sine=f=1000:d=0.12", "volume=3.0"),
    "tick": ("sine=f=5000:d=0.03", "volume=3.0"),
    "blip": ("sine=f=1500:d=0.15", "volume=3.0"),
    "chime": ("sine=f=523:d=1.2", "volume=2.0"),
}

ap = argparse.ArgumentParser()
ap.add_argument("--out-dir", default="sfx")
a = ap.parse_args()
os.makedirs(a.out_dir, exist_ok=True)
bad = []
for name, (src, af) in SFX.items():
    path = os.path.join(a.out_dir, f"{name}.wav")
    ffmpeg("-f", "lavfi", "-i", src, "-af", af, "-ar", "44100", path)
    mv = max_volume(path)
    print(f"{name}: max_volume {mv} dB")
    if mv < -15:
        bad.append(name)
if bad:
    raise SystemExit(f"音量过低（<-15 dB）：{bad}，请提高 a= 或 volume=")
