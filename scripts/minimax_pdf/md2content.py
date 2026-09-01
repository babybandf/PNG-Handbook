#!/usr/bin/env python3
"""Convert markdown chapters into content.json blocks and a mermaid manifest."""

import json
import re
import sys
from pathlib import Path

from fontTools.ttLib import TTFont

FENCE_RE = re.compile(r"^\s*(```|~~~)\s*([A-Za-z0-9_-]*)\s*$")
HEADING_RE = re.compile(r"^(#{1,4})\s+(.+?)\s*$")
MATH_LINE_RE = re.compile(r"^\s*\$\$\s*$")
MATH_INLINE_RE = re.compile(r"^\s*\$\$(.+)\$\$\s*$")
TABLE_SEP_RE = re.compile(r"^\|[-: |]+\|$")
BULLET_RE = re.compile(r"^[-*+]\s+(.*)$")
NUMBERED_RE = re.compile(r"^(\d+)[.、]\s+(.*)$")
CODE_SPAN_RE = re.compile(r"`([^`\n]+)`")
LINK_RE = re.compile(r"!?\[([^\]]*)\]\([^)]*\)")

PROSE_CJK_FONT = "Songti"
INLINE_CODE_CJK_FONT = "HeitiSCLight"
FALLBACK_FONT = "ArialUni"

_SONGTI_CMAP: set[int] | None = None


def init_fonts(font_files: dict) -> None:
    """Load the coverage map from the configured body font (key: 'Songti')."""
    global _SONGTI_CMAP
    path, idx = font_files["Songti"]
    font = TTFont(path, fontNumber=int(idx), lazy=True)
    _SONGTI_CMAP = set(font.getBestCmap().keys())


def _cmap() -> set[int]:
    global _SONGTI_CMAP
    if _SONGTI_CMAP is None:
        init_fonts({
            "Songti": ["/System/Library/Fonts/Supplemental/Songti.ttc", 6],
        })
    return _SONGTI_CMAP


def char_font(ch: str, cjk_name: str = PROSE_CJK_FONT) -> str:
    o = ord(ch)
    if 0x20 <= o <= 0x7E:
        return "Courier"
    if o in _cmap():
        return cjk_name
    return FALLBACK_FONT


def mixed_font_markup(plain_text: str, ascii_font: str, cjk_font: str) -> str:
    out = []
    prev_font = None
    run = ""
    for ch in plain_text:
        f = char_font(ch, cjk_font)
        if f != prev_font and run:
            out.append((prev_font, run))
            run = ""
        prev_font = f
        run += ch
    if run:
        out.append((prev_font, run))
    parts = []
    for f, seg in out:
        seg = seg.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        if f == ascii_font:
            parts.append(seg)
        else:
            parts.append(f'<font name="{f}">{seg}</font>')
    return "".join(parts)


def inline(text: str, protect_bold: bool = False) -> str:
    spans: list[str] = []

    def _stash(m: re.Match) -> str:
        spans.append(m.group(1))
        return f"\x00{len(spans) - 1}\x00"

    text = CODE_SPAN_RE.sub(_stash, text)
    text = LINK_RE.sub(r"\1", text)
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = re.sub(r"&lt;br\s*/?&gt;", "<br/>", text, flags=re.I)
    if not protect_bold:
        text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    else:
        text = text.replace("**", "")

    def _restore(m: re.Match) -> str:
        raw = spans[int(m.group(1))]
        return mixed_font_markup(raw, ascii_font="Courier",
                                 cjk_font=INLINE_CODE_CJK_FONT)

    text = re.sub(r"\x00(\d+)\x00", _restore, text)

    parts = re.split(r"(<[^>]+>)", text)
    fixed = []
    for seg in parts:
        if seg.startswith("<") and seg.endswith(">"):
            fixed.append(seg)
            continue
        buf, cur = [], ""
        cur_missing = False
        for ch in seg:
            missing = char_font(ch) == FALLBACK_FONT
            if missing != cur_missing and cur:
                if cur_missing:
                    buf.append(f'<font name="{FALLBACK_FONT}">{cur}</font>')
                else:
                    buf.append(cur)
                cur = ""
            cur_missing = missing
            cur += ch
        if cur:
            if cur_missing:
                buf.append(f'<font name="{FALLBACK_FONT}">{cur}</font>')
            else:
                buf.append(cur)
        fixed.append("".join(buf))
    return "".join(fixed)


def _display_width(s: str) -> float:
    return sum(2.0 if ord(c) > 0x2E7F else 1.0 for c in s)


def table_col_widths(headers: list[str], rows: list[list[str]]) -> list[float]:
    n = len(headers)
    widths = [_display_width(h) for h in headers]
    for row in rows:
        for i in range(min(n, len(row))):
            widths[i] = max(widths[i], _display_width(row[i]))
    total = sum(widths)
    if total <= 0:
        return [1.0 / n] * n
    clamped = [max(w, 0.08 * total) for w in widths]
    s = sum(clamped)
    return [c / s for c in clamped]


def math_expr(raw: str) -> dict | None:
    expr = " ".join(line.strip() for line in raw.splitlines() if line.strip())
    expr = re.sub(r"\\operatorname\s*", r"\\mathrm", expr)
    expr = re.sub(r"\\text\s*", r"\\mathrm", expr)
    if re.search(r"[\u4e00-\u9fff]", expr):
        return None
    return {"type": "math", "text": expr}


def convert(chapters: list[str], chapter_dir: Path,
            build_dir: Path) -> tuple[list[dict], list[dict]]:
    """Walk chapters once; figure ids in blocks and manifest stay aligned."""
    content: list[dict] = []
    manifest: list[dict] = []
    fig_index = 0
    math_index = 0

    for idx, name in enumerate(chapters):
        path = chapter_dir / f"{name}.md"
        lines = path.read_text(encoding="utf-8").splitlines()
        if idx:
            content.append({"type": "pagebreak"})
        para: list[str] = []

        def flush() -> None:
            if para:
                t = " ".join(x.strip() for x in para).strip()
                if t:
                    content.append({"type": "body", "text": inline(t)})
                para.clear()

        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()

            if not stripped:
                flush()
                i += 1
                continue

            fm = FENCE_RE.match(line)
            if fm:
                flush()
                fence, lang = fm.group(1), fm.group(2).lower()
                body: list[str] = []
                i += 1
                while i < len(lines) and not lines[i].strip().startswith(fence):
                    body.append(lines[i])
                    i += 1
                i += 1
                code = "\n".join(body)
                if lang == "mermaid":
                    fid = f"mmd_{name}_{fig_index}"
                    fig_index += 1
                    manifest.append({"id": fid, "code": code.strip()})
                    content.append({
                        "type": "figure",
                        "path": str(build_dir / f"{fid}.png"),
                        "caption": "",
                        "figure_id": fid,
                    })
                else:
                    content.append({
                        "type": "code",
                        "text": code,
                        "language": "" if lang in ("", "text") else lang,
                    })
                continue

            hm = HEADING_RE.match(stripped)
            if hm:
                flush()
                level = len(hm.group(1))
                content.append({
                    "type": f"h{level}",
                    "text": inline(hm.group(2), protect_bold=True),
                })
                i += 1
                continue

            if MATH_LINE_RE.match(stripped) or MATH_INLINE_RE.match(stripped):
                flush()
                single = MATH_INLINE_RE.match(stripped)
                raw = single.group(1) if single else None
                if single:
                    i += 1
                else:
                    buf: list[str] = []
                    i += 1
                    while i < len(lines) and not MATH_LINE_RE.match(lines[i].strip()):
                        buf.append(lines[i])
                        i += 1
                    i += 1
                    raw = "\n".join(buf)
                block = math_expr(raw)
                if block is None:
                    content.append({"type": "body", "text": inline(" ".join(raw.split()))})
                else:
                    mid = f"math_{math_index}"
                    math_index += 1
                    block["math_id"] = mid
                    block["path"] = str(build_dir / f"{mid}.png")
                    content.append(block)
                continue

            if stripped.startswith(">"):
                flush()
                quote: list[str] = []
                while i < len(lines) and lines[i].strip().startswith(">"):
                    quote.append(re.sub(r"^>\s?", "", lines[i].strip()))
                    i += 1
                qtext = "<br/>".join(x.strip() for x in quote if x.strip())
                content.append({"type": "callout", "text": inline(qtext)})
                continue

            if stripped.startswith("|"):
                flush()
                tlines: list[str] = []
                while i < len(lines) and lines[i].strip().startswith("|"):
                    tlines.append(lines[i].strip())
                    i += 1
                data = [ln for ln in tlines if not TABLE_SEP_RE.match(ln)]
                parsed = [[c.strip() for c in ln.strip("|").split("|")]
                          for ln in data]
                if not parsed:
                    continue
                headers = [inline(c, protect_bold=True) for c in parsed[0]]
                rows = [[inline(c) for c in row] for row in parsed[1:]]
                ncol = len(headers)
                rows = [(r + [""] * ncol)[:ncol] for r in rows]
                content.append({
                    "type": "table",
                    "headers": headers,
                    "rows": rows,
                    "col_widths": table_col_widths(parsed[0], parsed[1:]),
                })
                continue

            bm = BULLET_RE.match(stripped)
            if bm:
                flush()
                item = bm.group(1)
                while (i + 1 < len(lines) and lines[i + 1].strip()
                       and re.match(r"^\s{2,}\S", lines[i + 1])):
                    i += 1
                    item += " " + lines[i].strip()
                content.append({"type": "bullet", "text": inline(item)})
                i += 1
                continue

            nm = NUMBERED_RE.match(stripped)
            if nm:
                flush()
                item = nm.group(2)
                while (i + 1 < len(lines) and lines[i + 1].strip()
                       and re.match(r"^\s{2,}\S", lines[i + 1])):
                    i += 1
                    item += " " + lines[i].strip()
                content.append({"type": "numbered", "text": inline(item)})
                i += 1
                continue

            if re.match(r"^-{3,}$|^\*{3,}$|^_{3,}$", stripped):
                flush()
                i += 1
                continue

            para.append(line)
            i += 1

        flush()

    return content, manifest


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Markdown chapters -> content.json")
    parser.add_argument("--config", default=str(Path(__file__).parent / "config.json"))
    parser.add_argument("--out", default="content.json")
    parser.add_argument("--fig-dir", default=".")
    args = parser.parse_args()

    cfg = json.loads(Path(args.config).read_text(encoding="utf-8"))
    init_fonts(cfg["font_files"])
    content, manifest = convert(cfg["chapters"], Path(cfg["chapter_dir"]),
                                Path(args.fig_dir).resolve())
    Path(args.out).write_text(
        json.dumps(content, ensure_ascii=False, indent=1), encoding="utf-8")

    counts: dict[str, int] = {}
    for b in content:
        counts[b["type"]] = counts.get(b["type"], 0) + 1
    print(json.dumps({"blocks": len(content), "figures": len(manifest), **counts},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
