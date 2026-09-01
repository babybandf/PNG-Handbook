#!/usr/bin/env python3
"""Generate the light cover HTML from config.json."""

import argparse
import html
import json
import sys
from pathlib import Path

PAGE_W, PAGE_H = 794, 1123


def dot_grid(accent: str, opacity: float = 0.10) -> str:
    cols, rows, gap, r = 14, 10, 24, 1.6
    dots = []
    for row in range(rows):
        for col in range(cols):
            cx = col * gap
            cy = row * gap
            dots.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{accent}"/>')
    return (
        f'<svg style="position:absolute;right:56px;bottom:56px;'
        f'width:{(cols - 1) * gap + 2 * r}px;height:{(rows - 1) * gap + 2 * r}px;'
        f'pointer-events:none;opacity:{opacity}" xmlns="http://www.w3.org/2000/svg">'
        + "".join(dots) + "</svg>"
    )


def render_html(cfg: dict) -> str:
    esc = html.escape
    cover_accent = cfg.get("cover_accent", cfg["accent"])
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
.bar {{
  position: absolute; left: 0; top: 0;
  width: 8px; height: {PAGE_H}px; background: {cover_accent};
}}
.content {{
  position: absolute; left: 92px; right: 84px; top: 0; bottom: 0;
  display: flex; flex-direction: column; justify-content: center;
  padding-bottom: 60px;
}}
.eyebrow {{
  font-size: 10px; font-weight: 600; letter-spacing: 0.26em;
  color: {cfg['accent_strong']}; margin-bottom: 44px;
}}
.title {{
  font-family: {cfg['cover_font_title']};
  font-weight: 700; font-size: 52px; line-height: 1.32;
  color: {cfg['cover_ink']}; max-width: 580px;
  word-wrap: break-word;
}}
.rule {{
  width: 56px; height: 3px; background: {cover_accent};
  margin: 34px 0 26px;
}}
.subtitle {{
  font-size: 13px; color: {cfg['muted']}; line-height: 1.8;
  max-width: 500px;
}}
.meta {{
  position: absolute; left: 92px; bottom: 76px;
  font-size: 11px; color: {cfg['muted']}; letter-spacing: 0.05em;
}}
</style>
</head>
<body>
<div class="page">
  <div class="bar"></div>
  {dot_grid(cover_accent)}
  <div class="content">
    <div class="eyebrow">{esc(cfg['doc_type'])} &nbsp;·&nbsp; {esc(cfg['date'])}</div>
    <div class="title">{esc(cfg['title'])}</div>
    <div class="rule"></div>
    <div class="subtitle">{esc(cfg['subtitle'])}</div>
  </div>
  <div class="meta">{esc(cfg['author'])}</div>
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
