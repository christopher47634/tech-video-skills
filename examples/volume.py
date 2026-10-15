#!/usr/bin/env python3
"""用 volumedetect 读取 max_volume。注意输出目标必须是 `-f null -`，缺 `-` 会报错。
用法: python volume.py file1 [file2 ...]
"""
import re
import subprocess
import sys


def max_volume(path):
    r = subprocess.run(
        ["ffmpeg", "-hide_banner", "-i", path, "-af", "volumedetect", "-f", "null", "-"],
        capture_output=True, text=True, check=True, timeout=300)
    m = re.search(r"max_volume:\s*(-?[\d.]+) dB", r.stderr)
    if not m:
        raise RuntimeError(f"volumedetect 没有输出 max_volume: {path}")
    return float(m.group(1))


if __name__ == "__main__":
    for f in sys.argv[1:]:
        print(f"{f}: {max_volume(f)} dB")
