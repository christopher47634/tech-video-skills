"""common.py 的单元测试（不依赖 ffmpeg / 浏览器 / 网络）。运行：python -m unittest discover -s examples"""
import os
import tempfile
import unittest

from common import parse_vtt, ts_to_sec


def _write(text):
    fd, path = tempfile.mkstemp(suffix=".vtt")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(text)
    return path


class TestVtt(unittest.TestCase):
    def test_ts(self):
        self.assertAlmostEqual(ts_to_sec("00:00:03.587"), 3.587)
        self.assertAlmostEqual(ts_to_sec("01:02.500"), 62.5)
        self.assertAlmostEqual(ts_to_sec("00:00:01,250"), 1.25)  # SRT 逗号格式

    def test_parse_ok(self):
        p = _write("WEBVTT\n\n00:00:00.100 --> 00:00:03.537\n第一句\n\n"
                   "00:00:03.537 --> 00:00:08.075\n第二句\n")
        try:
            self.assertEqual(parse_vtt(p), [[0.1, 3.537, "第一句"], [3.537, 8.075, "第二句"]])
        finally:
            os.remove(p)

    def test_overlap_rejected(self):
        p = _write("WEBVTT\n\n00:00:00.100 --> 00:00:03.587\na\n\n00:00:03.537 --> 00:00:08.075\nb\n")
        try:
            with self.assertRaises(ValueError):
                parse_vtt(p)
        finally:
            os.remove(p)


if __name__ == "__main__":
    unittest.main()
