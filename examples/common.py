"""公共工具：ffmpeg 调用（无 shell、失败即抛错）与 VTT 解析。"""
import re
import subprocess
import sys


def run(cmd, **kwargs):
    """执行外部命令。cmd 必须是 list（不经过 shell），失败抛 CalledProcessError。"""
    print("+", " ".join(str(c) for c in cmd), file=sys.stderr)
    return subprocess.run([str(c) for c in cmd], check=True, **kwargs)


def ffmpeg(*args):
    return run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *args], timeout=600)


_TS = re.compile(r"(?:(\d+):)?(\d{2}):(\d{2})[.,](\d{3})")


def ts_to_sec(ts):
    m = _TS.fullmatch(ts.strip())
    if not m:
        raise ValueError(f"bad timestamp: {ts!r}")
    h, mi, s, ms = m.groups()
    mi_i, s_i = int(mi), int(s)
    if mi_i >= 60 or s_i >= 60:
        raise ValueError(f"invalid minute/second in timestamp: {ts!r}")
    return int(h or 0) * 3600 + mi_i * 60 + s_i + int(ms) / 1000


def parse_vtt(path):
    """返回 [[start, end, text], ...]。跳过 NOTE/STYLE 块，拒绝倒挂与相邻字幕重叠。"""
    subs = []
    with open(path, encoding="utf-8-sig") as f:
        blocks = re.split(r"\n\s*\n", f.read().replace("\r\n", "\n"))
    for block in blocks:
        lines = [ln for ln in block.strip().split("\n") if ln.strip()]
        if not lines:
            continue
        head = lines[0].strip()
        if head.startswith(("WEBVTT", "NOTE", "STYLE", "REGION")):
            continue
        for i, line in enumerate(lines):
            if "-->" in line:
                parts = line.split("-->")
                if len(parts) != 2:
                    raise ValueError(f"bad cue line: {line!r}")
                a, b = (x.strip().split()[0] for x in parts)
                start, end = ts_to_sec(a), ts_to_sec(b)
                if end <= start:
                    raise ValueError(f"字幕结束时间必须大于开始时间：{[start, end]}")
                subs.append([start, end, " ".join(lines[i + 1:])])
                break
    for prev, cur in zip(subs, subs[1:]):
        if cur[0] < prev[1] - 1e-6:
            raise ValueError(f"字幕重叠：{prev[:2]} 与 {cur[:2]}")
    return subs
