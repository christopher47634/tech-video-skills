#!/usr/bin/env python3
"""Step 1：用 edge-tts 生成配音 + VTT。稿子通过 --file 传入（不经 shell，不怕引号或以 - 开头）。

用法: python tts.py script.txt --out-dir build [--voice zh-CN-XiaoxiaoNeural] [--rate +15%]
"""
import argparse
import os
import sys

from common import run, parse_vtt

ap = argparse.ArgumentParser()
ap.add_argument("script", help="稿子文本文件（UTF-8）")
ap.add_argument("--out-dir", default="build")
ap.add_argument("--voice", default="zh-CN-XiaoxiaoNeural")
ap.add_argument("--rate", default=None, help='如 "+15%%"；默认不加。改了必须同时重生成 mp3 和 vtt')
args = ap.parse_args()

os.makedirs(args.out_dir, exist_ok=True)
mp3 = os.path.join(args.out_dir, "voiceover.mp3")
vtt = os.path.join(args.out_dir, "voiceover.vtt")
# 用当前解释器的 edge_tts 模块，避免 edge-tts 入口脚本不在 PATH（如 pip --user 安装）
cmd = [sys.executable, "-m", "edge_tts", "--voice", args.voice, "--file", args.script,
       "--write-media", mp3, "--write-subtitles", vtt]
if args.rate:
    cmd.append(f"--rate={args.rate}")  # 用 = 形式，避免 "-10%" 被当成选项
run(cmd, timeout=600)
subs = parse_vtt(vtt)  # 顺便校验
print(f"OK: {mp3}, {vtt} ({len(subs)} 条字幕, 总长约 {subs[-1][1]:.2f}s)")
