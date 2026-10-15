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
    return int(h or 0) * 3600 + int(mi) * 60 + int(s) + int(ms) / 1000


def parse_vtt(path):
    """返回 [[start, end, text], ...]。遇到相邻字幕重叠时报错而不是静默接受。"""
    subs = []
    with open(path, encoding="utf-8") as f:
        blocks = re.split(r"\n\s*\n", f.read().replace("\r\n", "\n"))
    for block in blocks:
        lines = [ln for ln in block.strip().split("\n") if ln.strip()]
        for i, line in enumerate(lines):
            if "-->" in line:
                a, b = (x.strip().split()[0] for x in line.split("-->"))
                subs.append([ts_to_sec(a), ts_to_sec(b), " ".join(lines[i + 1:])])
                break
    for prev, cur in zip(subs, subs[1:]):
        if cur[0] < prev[1] - 1e-6:
            raise ValueError(f"字幕重叠：{prev[:2]} 与 {cur[:2]}")
    return subs
