"""Regression checks for cover design tokens."""

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import render_cover


class CoverTokenTests(unittest.TestCase):
    def test_uses_cover_accent_for_cover_graphics(self) -> None:
        config_path = Path(__file__).with_name('config.json')
        cfg = json.loads(config_path.read_text(encoding='utf-8'))
        cfg['cover_accent'] = '#38BDF8'

        html = render_cover.render_html(cfg)

        self.assertIn('background: #38BDF8', html)
        self.assertIn('fill="#38BDF8"', html)


if __name__ == '__main__':
    unittest.main()
