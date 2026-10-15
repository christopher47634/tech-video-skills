#!/usr/bin/env python3
"""Step 6：配音 + BGM + SFX 一次性混音（单次 amix, normalize=0）-> 立体声 WAV。

依赖 amix 的 normalize 选项（较新的 FFmpeg 才有，见 README 的版本说明）。
SFX 时间表从 JSON 读取：[[0.0, "whoosh"], [4.5, "typing_key"], ...]（名称对应 sfx/<名称>.wav）。
输出声道：默认立体声（-ac 2）。edge-tts 的配音是单声道，会被复制到左右声道；
如需更小体积可加 --mono。

用法: python mix.py build/voiceover.mp3 --schedule sfx_schedule.json --bgm bgm.wav -o build/mixed-audio.wav
"""
import argparse
import json
import subprocess
from collections import Counter

from common import ffmpeg


def probe_duration(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=nw=1:nk=1", path],
                       capture_output=True, text=True, check=True, timeout=60)
    return float(r.stdout.strip())


def require_normalize():
    r = subprocess.run(["ffmpeg", "-hide_banner", "-h", "filter=amix"],
                       capture_output=True, text=True, check=True)
    if "normalize" not in r.stdout:
        raise SystemExit("当前 ffmpeg 的 amix 没有 normalize 选项，请升级 ffmpeg（见 README）。")


ap = argparse.ArgumentParser()
ap.add_argument("voiceover")
ap.add_argument("--schedule", required=True, help="SFX 时间表 JSON")
ap.add_argument("--sfx-dir", default="sfx")
ap.add_argument("--bgm")
ap.add_argument("--bgm-vol", type=float, default=0.08)
ap.add_argument("--sfx-vol", type=float, default=0.5)
ap.add_argument("--mono", action="store_true")
ap.add_argument("-o", "--output", default="build/mixed-audio.wav")
a = ap.parse_args()

require_normalize()
dur = probe_duration(a.voiceover)
with open(a.schedule, encoding="utf-8") as f:
    schedule = json.load(f)
names = sorted({n for _, n in schedule})
counts = Counter(n for _, n in schedule)

inputs = ["-i", a.voiceover]
for n in names:
    inputs += ["-i", f"{a.sfx_dir}/{n}.wav"]
bgm_idx = None
if a.bgm:
    inputs += ["-i", a.bgm]
    bgm_idx = 1 + len(names)

parts, mix_labels = ["[0:a]aresample=44100[vo]"], ["[vo]"]
sfx_pads = {}
for k, n in enumerate(names, start=1):
    c = counts[n]
    if c == 1:
        sfx_pads[n] = [f"[{k}:a]"]
    else:
        outs = [f"[sp{k}_{j}]" for j in range(c)]
        parts.append(f"[{k}:a]asplit={c}" + "".join(outs))
        sfx_pads[n] = outs
used = Counter()
for i, (t, n) in enumerate(schedule):
    pad = sfx_pads[n][used[n]]
    used[n] += 1
    ms = int(round(t * 1000))
    parts.append(f"{pad}aresample=44100,adelay={ms}:all=1,volume={a.sfx_vol}[x{i}]")
    mix_labels.append(f"[x{i}]")
if bgm_idx is not None:
    parts.append(f"[{bgm_idx}:a]atrim=0:{dur:.3f},asetpts=PTS-STARTPTS,"
                 f"volume={a.bgm_vol},aresample=44100[bgm]")
    mix_labels.append("[bgm]")
parts.append("".join(mix_labels) + f"amix=inputs={len(mix_labels)}:duration=first:normalize=0,"
             "alimiter=limit=0.9:attack=5:release=50[out]")

ffmpeg(*inputs, "-filter_complex", ";".join(parts), "-map", "[out]",
       "-ar", "44100", "-ac", "1" if a.mono else "2", "-t", f"{dur:.3f}", a.output)
print("OK:", a.output)
