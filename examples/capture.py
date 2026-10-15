#!/usr/bin/env python3
"""Step 3：Playwright 逐帧截图。场景时间从 scenes.json 读取，不在代码里硬编码。

HTML 必须暴露 window.seekTo(t)（t 的纯函数，见 scenes.example.html）。
脚本会把 scenes.json 的 scenes 注入 window.SCENES，把 VTT 字幕注入 window.SUBS。
任何一帧失败都会以非零状态退出并列出失败帧，不会留下序号断档的帧序列。

浏览器选择优先级：--chromium 参数 > 环境变量 CHROMIUM_PATH > Playwright 自带 Chromium。

用法: python capture.py scenes.html --scenes scenes.json --vtt build/voiceover.vtt --out build/frames
"""
import argparse
import json
import os
import pathlib
import shutil
import sys

from playwright.sync_api import sync_playwright

from common import parse_vtt

ap = argparse.ArgumentParser()
ap.add_argument("html")
ap.add_argument("--scenes", required=True, help="scenes.json")
ap.add_argument("--vtt", help="voiceover.vtt（可选）")
ap.add_argument("--out", default="build/frames")
ap.add_argument("--chromium", default=os.environ.get("CHROMIUM_PATH"))
args = ap.parse_args()

cfg = json.loads(pathlib.Path(args.scenes).read_text(encoding="utf-8"))
W, H, FPS = cfg["width"], cfg["height"], cfg["fps"]
duration = cfg["scenes"][-1]["end"]
total = int(round(duration * FPS))
subs = parse_vtt(args.vtt) if args.vtt else []

out = pathlib.Path(args.out)
if out.exists():
    shutil.rmtree(out)
out.mkdir(parents=True)

failed = []
with sync_playwright() as p:
    launch_kw = {"headless": True, "args": ["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"]}
    if args.chromium:
        launch_kw["executable_path"] = args.chromium
    browser = p.chromium.launch(**launch_kw)
    page = browser.new_page(viewport={"width": W, "height": H})
    page.goto(pathlib.Path(args.html).resolve().as_uri(), wait_until="networkidle")
    page.evaluate("([s, u]) => { window.SCENES = s; window.SUBS = u; }", [cfg["scenes"], subs])
    page.evaluate("document.fonts.ready")
    for i in range(total):
        try:
            page.evaluate("t => window.seekTo(t)", i / FPS)
            page.screenshot(path=str(out / f"frame_{i:05d}.png"))
        except Exception as e:  # 记录并继续，最后统一报告
            failed.append((i, str(e).splitlines()[0]))
    browser.close()

if failed:
    print(f"FAILED: {len(failed)}/{total} 帧失败，帧序列不完整，已中止：", file=sys.stderr)
    for i, msg in failed[:50]:
        print(f"  frame {i} (t={i / FPS:.3f}s): {msg}", file=sys.stderr)
    sys.exit(1)
print(f"OK: {total} 帧 -> {out}")
