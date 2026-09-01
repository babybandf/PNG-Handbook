#!/usr/bin/env python3
"""Generate a VitePress-home-inspired cover HTML from config.json."""

import argparse
import html
import json
import sys
from pathlib import Path

PAGE_W, PAGE_H = 794, 1123


def render_html(cfg: dict) -> str:
    esc = html.escape
    return f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8">
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
html, body {{
  width: {PAGE_W}px; height: {PAGE_H}px; overflow: hidden;
  background: {cfg['cover_bg']};
}}
.page {{
  position: relative; width: {PAGE_W}px; height: {PAGE_H}px;
  background: {cfg['cover_bg']}; overflow: hidden;
  font-family: {cfg['cover_font_body']};
}}
.home-hero {{
  position: absolute; left: 64px; right: 58px; top: {cfg['cover_hero_top']}px;
}}
.name {{
  font-family: {cfg['cover_font_title']};
  font-weight: 700; font-size: 52px; line-height: 1.25;
  letter-spacing: -0.035em; color: {cfg['cover_accent']};
  word-wrap: break-word;
}}
.text {{
  margin-top: 22px; font-weight: 700; font-size: 42px; line-height: 1.3;
  letter-spacing: -0.025em; color: {cfg['cover_text']};
}}
.tagline {{
  margin-top: 34px; max-width: 620px; font-size: 20px; font-weight: 500;
  line-height: 1.55; color: {cfg['cover_tagline_color']};
}}
.meta {{
  position: absolute; left: 64px; bottom: 66px;
  font-size: 11px; color: {cfg['cover_tagline_color']}; letter-spacing: 0.04em;
}}
</style>
</head>
<body>
<div class="page">
  <div class="home-hero">
    <div class="name">{esc(cfg['title'])}</div>
    <div class="text">{esc(cfg['cover_hero_text'])}</div>
    <div class="tagline">{esc(cfg['cover_tagline'])}</div>
  </div>
  <div class="meta">{esc(cfg['author'])} &nbsp;·&nbsp; {esc(cfg['date'])}</div>
</div>
</body>
</html>
"""


def main():
    parser = argparse.ArgumentParser(description="Light cover HTML generator")
    parser.add_argument("--config", default=str(Path(__file__).parent / "config.json"))
    parser.add_argument("--out", default="cover.html")
    args = parser.parse_args()

    cfg = json.loads(Path(args.config).read_text(encoding="utf-8"))
    Path(args.out).write_text(render_html(cfg), encoding="utf-8")
    print(json.dumps({"status": "ok", "out": args.out}))


if __name__ == "__main__":
    sys.exit(main())
