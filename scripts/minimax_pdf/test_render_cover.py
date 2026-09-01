"""Regression checks for cover design tokens."""

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import render_cover


class CoverTokenTests(unittest.TestCase):
    def test_renders_light_home_cover_without_legacy_decoration(self) -> None:
        config_path = Path(__file__).with_name('config.json')
        cfg = json.loads(config_path.read_text(encoding='utf-8'))

        html = render_cover.render_html(cfg)

        self.assertIn('class="home-hero"', html)
        self.assertIn('top: 290px', html)
        self.assertIn('color: #3451B2', html)
        self.assertIn('从格式规范到软硬件解码器', html)
        self.assertIn('系统理解 Chunk、zlib、DEFLATE、Scanline、Adam7 与工程实现', html)
        self.assertNotIn('class="bar"', html)
        self.assertNotIn('<svg', html)


if __name__ == '__main__':
    unittest.main()
