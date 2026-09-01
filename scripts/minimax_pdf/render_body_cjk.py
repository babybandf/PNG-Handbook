#!/usr/bin/env python3
"""Render the body PDF with CJK typography, light technical-doc styling,
and a complete PDF outline built from every h1-h4 heading."""

import argparse
import io
import json
import os
import re
import sys
import importlib.util
from pathlib import Path


def ensure_deps():
    missing = [p for p in ("reportlab", "pypdf")
               if importlib.util.find_spec(p) is None]
    if missing:
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-q"] + missing)


ensure_deps()

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.colors import HexColor, white
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.pdfmetrics import registerFontFamily, stringWidth
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame,
    Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, Flowable, KeepTogether,
    XPreformatted, Image as RLImage,
)


def register_fonts(tokens: dict):
    for name, spec in tokens.get("font_specs", {}).items():
        path, idx = spec[0], int(spec[1])
        if os.path.exists(path):
            pdfmetrics.registerFont(TTFont(name, path, subfontIndex=idx))
    fam = tokens.get("font_family_map") or {}
    if fam:
        registerFontFamily(
            fam["normal"],
            normal=fam["normal"],
            bold=fam["bold"],
            italic=fam["normal"],
            boldItalic=fam["bold"],
        )


class CalloutBox(Flowable):
    def __init__(self, text: str, style, accent: str, bg: str):
        super().__init__()
        self._para = Paragraph(text, style)
        self._accent = HexColor(accent)
        self._bg = HexColor(bg)

    def wrap(self, aw, ah):
        self._w = aw
        _, ph = self._para.wrap(aw - 36, ah)
        self._h = ph + 22
        return aw, self._h

    def draw(self):
        c = self.canv
        c.setFillColor(self._bg)
        c.roundRect(0, 0, self._w, self._h, 5, fill=1, stroke=0)
        c.setFillColor(self._accent)
        c.rect(0, 0, 4, self._h, fill=1, stroke=0)
        self._para.drawOn(c, 18, 11)


class MathPlaceholder(Flowable):
    """Reserves space for a vector formula stamped in later by pdflatex output."""

    def __init__(self, mid: str, w: float, h: float, recorder):
        super().__init__()
        self._mid = mid
        self._w = float(w)
        self._h = float(h)
        self._recorder = recorder
        self.hAlign = "CENTER"

    def wrap(self, aw, ah):
        return self._w, self._h

    def draw(self):
        x, y = self.canv.absolutePosition(0, 0)
        self._recorder(id=self._mid, page=self.canv.getPageNumber(),
                       x=x, y=y, w=self._w, h=self._h)


class OutlineDoc(BaseDocTemplate):
    LEVELS = {"H1": 0, "H2": 1, "H3": 2, "H4": 2}

    def __init__(self, path: str, tokens: dict, **kw):
        self._t = tokens
        self._bk_n = 0
        self._prev_level = 0
        self._headings = 0
        self.math_placeholders: list[dict] = []
        info = {
            "title": tokens.get("title", ""),
            "author": tokens.get("author", ""),
            "subject": tokens.get("subject", ""),
        }
        super().__init__(path, **info, **kw)
        fr = Frame(self.leftMargin, self.bottomMargin,
                   self.width, self.height, id="body")
        self.addPageTemplates([PageTemplate(id="main", frames=fr, onPage=self._decorate)])

    def record_math(self, **kw):
        self.math_placeholders.append(kw)

    def _decorate(self, canv, doc):
        t = self._t
        lm, rm = doc.leftMargin, doc.rightMargin
        pw, ph = doc.pagesize
        top = ph - doc.topMargin

        canv.saveState()
        canv.setStrokeColor(HexColor(t["accent"]))
        canv.setLineWidth(1.1)
        canv.line(lm, top + 12, pw - rm, top + 12)
        canv.setFillColor(HexColor(t["muted"]))
        canv.setFont(t["font_body_rl"], t["size_meta"])
        canv.drawString(lm, top + 16, t["title"])
        canv.drawRightString(pw - rm, top + 16, t.get("date", ""))

        canv.setStrokeColor(HexColor(t["box_border"]))
        canv.setLineWidth(0.5)
        canv.line(lm, doc.bottomMargin - 12, pw - rm, doc.bottomMargin - 12)
        canv.setFillColor(HexColor(t["muted"]))
        canv.setFont(t["font_body_rl"], t["size_meta"])
        if t.get("author"):
            canv.drawString(lm, doc.bottomMargin - 22, t["author"])
        canv.drawRightString(pw - rm, doc.bottomMargin - 22, str(doc.page))
        canv.restoreState()

    def afterFlowable(self, flowable):
        if isinstance(flowable, Paragraph):
            level = self.LEVELS.get(flowable.style.name)
            if level is None:
                return
            text = flowable.getPlainText().strip()
            if not text:
                return
            self._bk_n += 1
            self._headings += 1
            level = min(level, self._prev_level + 1)
            self._prev_level = level
            key = f"bk{self._bk_n}"
            self.canv.bookmarkPage(key)
            self.canv.addOutlineEntry(text, key, level, 0)


def make_styles(t: dict) -> dict:
    hf = t["font_display_rl"]
    bf = t["font_body_rl"]
    bfb = t["font_body_b_rl"]
    dk = t["body_text"]
    d = t["dark"]
    mu = t["muted"]

    def cjk(style: ParagraphStyle) -> ParagraphStyle:
        style.wordWrap = "CJK"
        return style

    return {
        "h1": cjk(ParagraphStyle("H1", fontName=hf, fontSize=t["size_h1"],
                  leading=t["size_h1"] * 1.35, textColor=HexColor(d),
                  spaceBefore=t["section_gap"], spaceAfter=4)),
        "h2": cjk(ParagraphStyle("H2", fontName=hf, fontSize=t["size_h2"],
                  leading=t["size_h2"] * 1.4, textColor=HexColor(d),
                  spaceBefore=18, spaceAfter=5)),
        "h3": cjk(ParagraphStyle("H3", fontName=bfb, fontSize=t["size_h3"],
                  leading=t["size_h3"] * 1.5, textColor=HexColor(d),
                  spaceBefore=12, spaceAfter=3)),
        "h4": cjk(ParagraphStyle("H4", fontName=bfb, fontSize=t["size_body"] + 0.5,
                  leading=(t["size_body"] + 0.5) * 1.5, textColor=HexColor(d),
                  spaceBefore=10, spaceAfter=3)),
        "body": cjk(ParagraphStyle("Body", fontName=bf, fontSize=t["size_body"],
                    leading=t["line_gap"], textColor=HexColor(dk),
                    spaceAfter=t["para_gap"], alignment=TA_JUSTIFY)),
        "bullet": cjk(ParagraphStyle("Bullet", fontName=bf, fontSize=t["size_body"],
                      leading=t["line_gap"] - 1, textColor=HexColor(dk),
                      spaceAfter=4, leftIndent=14)),
        "numbered": cjk(ParagraphStyle("Numbered", fontName=bf, fontSize=t["size_body"],
                        leading=t["line_gap"] - 1, textColor=HexColor(dk),
                        spaceAfter=4, leftIndent=22, firstLineIndent=-22)),
        "callout": cjk(ParagraphStyle("Callout", fontName=bfb,
                       fontSize=t["size_body"] + 0.5, leading=16.5,
                       textColor=HexColor(d))),
        "caption": cjk(ParagraphStyle("Caption", fontName=bf, fontSize=t["size_caption"],
                       leading=13, textColor=HexColor(mu), spaceAfter=6,
                       alignment=TA_CENTER)),
        "table_header": cjk(ParagraphStyle("TblH", fontName=bfb, fontSize=9,
                            leading=12.5, textColor=HexColor(t["table_header_text"]))),
        "table_cell": cjk(ParagraphStyle("TblC", fontName=bf, fontSize=9,
                           leading=12.5, textColor=HexColor(dk))),
        "code": ParagraphStyle("Code", fontName="Courier", fontSize=8.5,
                               leading=12, textColor=HexColor(dk)),
        "code_lang": ParagraphStyle("CodeLang", fontName="Helvetica", fontSize=7,
                                    leading=10, textColor=HexColor(mu)),
        "math_fallback": ParagraphStyle("MathFb", fontName="Courier", fontSize=9,
                                        leading=13, textColor=HexColor(dk)),
        "eq_label": ParagraphStyle("EqLabel", fontName="Helvetica", fontSize=9,
                                   leading=12, textColor=HexColor(mu)),
    }


def _divider(accent: str) -> HRFlowable:
    return HRFlowable(width="100%", thickness=1.0, color=HexColor(accent),
                      spaceBefore=12, spaceAfter=12)


def _image_from_bytes(png_bytes: bytes, usable_w: float, max_frac: float,
                      max_h: float) -> RLImage:
    img = RLImage(io.BytesIO(png_bytes))
    max_w = usable_w * max_frac
    if img.drawWidth > max_w:
        scale = max_w / img.drawWidth
        img.drawWidth = max_w
        img.drawHeight = img.drawHeight * scale
    if img.drawHeight > max_h:
        scale = max_h / img.drawHeight
        img.drawHeight = max_h
        img.drawWidth = img.drawWidth * scale
    return img


def _render_math_png(expr: str, dpi: int = 200):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig = plt.figure(figsize=(8, 1.2))
        fig.patch.set_facecolor("white")
        ax = fig.add_axes([0, 0, 1, 1])
        ax.set_axis_off()
        ax.text(0.5, 0.5, f"${expr}$", fontsize=16, ha="center", va="center",
                transform=ax.transAxes)
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight",
                    facecolor="white", pad_inches=0.1)
        plt.close(fig)
        buf.seek(0)
        return buf.read()
    except Exception:
        return None


def _strip_boxed(expr: str) -> str:
    token = r"\boxed"
    while token in expr:
        i = expr.index(token)
        j = expr.index("{", i)
        depth = 0
        for k in range(j, len(expr)):
            if expr[k] == "{":
                depth += 1
            elif expr[k] == "}":
                depth -= 1
                if depth == 0:
                    break
        expr = expr[:i] + expr[j + 1:k] + expr[k + 1:]
    return expr.strip()


def _math_to_lines(expr: str) -> list[str]:
    expr = _strip_boxed(expr)
    expr = re.sub(r"\\le(?![a-zA-Z])", r"\\leq", expr)
    expr = re.sub(r"\\ge(?![a-zA-Z])", r"\\geq", expr)
    if r"\begin{cases}" not in expr:
        return [expr]
    lines = []
    while r"\begin{cases}" in expr:
        pre = expr[: expr.index(r"\begin{cases}")].strip().rstrip("=").strip()
        rest = expr[expr.index(r"\begin{cases}") + len(r"\begin{cases}"):]
        body = rest[: rest.index(r"\end{cases}")]
        expr = rest[rest.index(r"\end{cases}") + len(r"\end{cases}"):]
        rows = [r.strip().replace("&", r"\quad ").rstrip("\\").strip()
                for r in body.split(r"\\")]
        rows = [r for r in rows if r]
        for n, row in enumerate(rows):
            prefix = f"{pre} = " if (pre and n == 0) else (r"\quad " if not pre else r"\;\;")
            lines.append((prefix + " " + row).strip())
    if expr.strip():
        lines.append(expr.strip())
    return lines


def _add_heading(story, item, ctx, level):
    para = Paragraph(item["text"], ctx["styles"][f"h{level}"])
    if level == 1:
        story.append(KeepTogether([para, _divider(ctx["acc"])]))
    else:
        story.append(para)


def mixed_code_markup(text: str) -> str:
    from md2content import char_font

    lines = text.split("\n")
    out_lines = []
    for ln in lines:
        ln = ln.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        parts, cur, cur_f = [], "", None
        for ch in ln:
            o = ord(ch)
            f = "Courier" if 0x20 <= o <= 0x7E else char_font(ch)
            if f != cur_f and cur:
                parts.append((cur_f, cur))
                cur = ""
            cur_f, cur = f, cur + ch
        if cur:
            parts.append((cur_f, cur))
        seg = ""
        for f, chunk in parts:
            if f == "Courier":
                seg += chunk
            else:
                seg += f'<font name="{f}">{chunk}</font>'
        out_lines.append(seg)
    return "\n".join(out_lines)


def _add_code(story, item, ctx):
    t, acc, mu = ctx["tokens"], ctx["acc"], ctx["mu"]
    uw = ctx["usable_w"]
    text = item.get("text", "")
    lang = item.get("language", "")

    style = ctx["styles"]["code"]
    max_len = max((len(ln.expandtabs(4)) for ln in text.splitlines()), default=0)
    fs = 8.5
    while max_len * stringWidth("0", "Courier", fs) > uw - 32 and fs > 5.8:
        fs -= 0.25
    style = ParagraphStyle("CodeAdj", parent=style, fontSize=fs, leading=fs * 1.4)

    markup = mixed_code_markup(text)
    box_style = [
        ("BACKGROUND",   (0, 0), (-1, -1), HexColor(t["code_bg"])),
        ("LINEBEFORE",   (0, 0), (0, -1), 2.5, HexColor(acc)),
        ("BOX",          (0, 0), (-1, -1), 0.5, HexColor(t["box_border"])),
        ("LEFTPADDING",  (0, 0), (-1, -1), 14),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING",   (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 8),
    ]

    story.append(Spacer(1, 5))
    if lang:
        story.append(Paragraph(lang.upper(), ctx["styles"]["code_lang"]))

    lines = markup.split("\n")
    per_chunk = max(1, int((ctx["frame_h"] - 32) / style.leading))
    chunks = [lines[i:i + per_chunk] for i in range(0, len(lines), per_chunk)] \
        if len(lines) > per_chunk else [lines]
    for chunk in chunks:
        pre = XPreformatted("\n".join(chunk), style)
        tbl = Table([[pre]], colWidths=[uw])
        tbl.setStyle(TableStyle(box_style))
        story.append(tbl)
    story.append(Spacer(1, 5))


def _add_table(story, item, ctx):
    t, styles = ctx["tokens"], ctx["styles"]
    uw, acc = ctx["usable_w"], ctx["acc"]

    headers = [Paragraph(h, styles["table_header"]) for h in item["headers"]]
    rows = [[Paragraph(str(c), styles["table_cell"]) for c in row]
            for row in item.get("rows", [])]
    n_cols = len(item["headers"])

    if "col_widths" in item and len(item["col_widths"]) == n_cols:
        col_w = [uw * f for f in item["col_widths"]]
    else:
        col_w = [uw / n_cols] * n_cols

    tbl = Table([headers] + rows, colWidths=col_w, repeatRows=1)
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), HexColor(t["table_header_bg"])),
        ("TEXTCOLOR",     (0, 0), (-1, 0), HexColor(t["table_header_text"])),
        ("FONTNAME",      (0, 0), (-1, 0), t["font_body_b_rl"]),
        ("TOPPADDING",    (0, 0), (-1, 0), 6),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [HexColor("#FFFFFF"), HexColor(t["table_row_alt"])]),
        ("FONTNAME",      (0, 1), (-1, -1), t["font_body_rl"]),
        ("TOPPADDING",    (0, 1), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
        ("BOX",           (0, 0), (-1, -1), 0.6, HexColor(t["box_border"])),
        ("LINEBELOW",     (0, 0), (-1, 0), 1.0, HexColor(acc)),
        ("TEXTCOLOR",     (0, 1), (-1, -1), HexColor(t["body_text"])),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(Spacer(1, 4))
    story.append(tbl)
    if item.get("caption"):
        story.append(Spacer(1, 4))
        story.append(Paragraph(item["caption"], styles["caption"]))
    story.append(Spacer(1, 10))


def _add_figure(story, item, ctx):
    ctx["figure_n"] += 1
    path = str(item.get("path", item.get("src", "")))
    caption_text = item.get("caption", "")
    caption = f"图 {ctx['figure_n']}：{caption_text}" if caption_text \
        else f"图 {ctx['figure_n']}"

    group: list = []
    if not os.path.exists(path):
        group.append(Paragraph(f"[Image not found: {path}]",
                               ctx["styles"]["caption"]))
    else:
        try:
            img = RLImage(path)
            uw = ctx["usable_w"]
            max_h = ctx["max_fig_h"]
            if img.drawWidth > uw:
                scale = uw / img.drawWidth
                img.drawWidth = uw
                img.drawHeight = img.drawHeight * scale
            if img.drawHeight > max_h:
                scale = max_h / img.drawHeight
                img.drawHeight = max_h
                img.drawWidth = img.drawWidth * scale
            group.append(Spacer(1, 6))
            group.append(img)
        except Exception as e:
            group.append(Paragraph(f"[Image error: {e}]", ctx["styles"]["caption"]))
    group.append(Spacer(1, 4))
    group.append(Paragraph(caption, ctx["styles"]["caption"]))
    story.append(KeepTogether(group))
    story.append(Spacer(1, 10))


def _add_math(story, item, ctx):
    uw = ctx["usable_w"]
    expr = item.get("text", "").strip()
    label = item.get("label", "").strip()

    meta = ctx.get("math_meta") or {}
    mid = item.get("math_id", "")
    if ctx["tokens"].get("math_engine") == "latex" and mid in meta:
        info = meta[mid]
        story.append(Spacer(1, 6))
        story.append(MathPlaceholder(mid, info["w"], info["h"], ctx["math_recorder"]))
        if label:
            story.append(Spacer(1, 2))
            story.append(Paragraph(label, ctx["styles"]["eq_label"]))
        story.append(Spacer(1, 6))
        return

    png_path = item.get("path", "")
    if png_path and os.path.exists(png_path):
        # KaTeX-rendered PNG: 3x device pixels; css px -> pt at 0.75
        info = meta.get(item.get("math_id", ""), {})
        story.append(Spacer(1, 8))
        img = RLImage(png_path)
        if info.get("w"):
            img.drawWidth = info["w"] * 0.75
            img.drawHeight = info["h"] * 0.75
        else:
            img.drawWidth = img.drawWidth / 4.0
            img.drawHeight = img.drawHeight / 4.0
        max_w = uw * 0.92
        max_h = ctx["max_fig_h"] * 0.9
        if img.drawWidth > max_w:
            scale = max_w / img.drawWidth
            img.drawWidth = max_w
            img.drawHeight = img.drawHeight * scale
        if img.drawHeight > max_h:
            scale = max_h / img.drawHeight
            img.drawHeight = max_h
            img.drawWidth = img.drawWidth * scale
        group: list = [img]
        if label:
            group.append(Spacer(1, 2))
            group.append(Paragraph(label, ctx["styles"]["eq_label"]))
        holder = Table([group] if len(group) == 1 else [[group[0]], [group[1]]],
                       colWidths=[uw])
        holder.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER")]))
        story.append(holder)
        story.append(Spacer(1, 8))
        return

    lines = _math_to_lines(expr)
    pngs = [p for p in (_render_math_png(ln) for ln in lines) if p is not None]

    if not pngs:
        story.append(Spacer(1, 6))
        pre = XPreformatted(expr, ctx["styles"]["math_fallback"])
        tbl = Table([[pre]], colWidths=[uw])
        tbl.setStyle(TableStyle([
            ("BACKGROUND",   (0, 0), (-1, -1), HexColor(ctx["tokens"]["code_bg"])),
            ("LEFTPADDING",  (0, 0), (-1, -1), 14),
            ("RIGHTPADDING", (0, 0), (-1, -1), 14),
            ("TOPPADDING",   (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING",(0, 0), (-1, -1), 8),
        ]))
        story.append(tbl)
        story.append(Spacer(1, 6))
        return

    story.append(Spacer(1, 8))
    if label and len(pngs) == 1:
        img = _image_from_bytes(pngs[0], uw, max_frac=0.72, max_h=ctx["max_fig_h"])
        row_tbl = Table([[img, Paragraph(label, ctx["styles"]["eq_label"])]],
                        colWidths=[uw - 44, 44])
        row_tbl.setStyle(TableStyle([
            ("ALIGN", (0, 0), (0, 0), "CENTER"),
            ("ALIGN", (1, 0), (1, 0), "RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        story.append(row_tbl)
    else:
        group = [[_image_from_bytes(png, uw, max_frac=0.72,
                                    max_h=ctx["max_fig_h"] / len(pngs))]
                 for png in pngs]
        holder = Table(group, colWidths=[uw])
        holder.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER")]))
        story.append(holder)
    story.append(Spacer(1, 8))


_RESETS_NUMBERED = frozenset({
    "h1", "h2", "h3", "h4", "body", "bullet", "callout", "table",
    "image", "figure", "code", "math", "divider", "caption",
    "pagebreak", "spacer",
})


def build_story(content: list, tokens: dict, styles: dict, ctx: dict) -> list:
    story: list = []
    for item in content:
        kind = item.get("type", "body")
        if kind in _RESETS_NUMBERED:
            ctx["numbered_n"] = 0

        if kind == "h1":
            _add_heading(story, item, ctx, 1)
        elif kind == "h2":
            _add_heading(story, item, ctx, 2)
        elif kind == "h3":
            _add_heading(story, item, ctx, 3)
        elif kind == "h4":
            _add_heading(story, item, ctx, 4)
        elif kind == "body":
            story.append(Paragraph(item["text"], styles["body"]))
        elif kind == "bullet":
            story.append(Paragraph(f"\u2022\u2002{item['text']}", styles["bullet"]))
        elif kind == "numbered":
            ctx["numbered_n"] += 1
            story.append(Paragraph(f"{ctx['numbered_n']}.\u2002{item['text']}",
                                   styles["numbered"]))
        elif kind == "callout":
            story.append(Spacer(1, 6))
            story.append(CalloutBox(item["text"], styles["callout"],
                                    ctx["acc"], ctx["tokens"]["callout_bg"]))
            story.append(Spacer(1, 8))
        elif kind == "table":
            _add_table(story, item, ctx)
        elif kind == "figure":
            _add_figure(story, item, ctx)
        elif kind == "code":
            _add_code(story, item, ctx)
        elif kind == "math":
            _add_math(story, item, ctx)
        elif kind == "divider":
            story.append(_divider(ctx["acc"]))
        elif kind == "caption":
            story.append(Paragraph(item["text"], styles["caption"]))
        elif kind == "pagebreak":
            story.append(PageBreak())
        elif kind == "spacer":
            story.append(Spacer(1, item.get("pt", 12)))
    return story


def build(tokens: dict, content: list, out_path: str) -> dict:
    register_fonts(tokens)
    styles = make_styles(tokens)

    math_meta: dict = {}
    meta_path = tokens.get("math_meta", "")
    if meta_path and os.path.exists(meta_path):
        with open(meta_path, encoding="utf-8") as f:
            math_meta = json.load(f)

    doc = OutlineDoc(
        out_path, tokens,
        pagesize=A4,
        leftMargin=tokens["margin_left"],
        rightMargin=tokens["margin_right"],
        topMargin=tokens["margin_top"],
        bottomMargin=tokens["margin_bottom"],
    )
    usable_w = A4[0] - tokens["margin_left"] - tokens["margin_right"]
    frame_h = A4[1] - tokens["margin_top"] - tokens["margin_bottom"]
    ctx = {
        "tokens": tokens,
        "styles": styles,
        "usable_w": usable_w,
        "acc": tokens["accent"],
        "acc_lt": tokens["accent_lt"],
        "mu": tokens["muted"],
        "dark": tokens["dark"],
        "figure_n": 0,
        "numbered_n": 0,
        "max_fig_h": frame_h * 0.94,
        "frame_h": frame_h,
        "math_meta": math_meta,
        "math_recorder": doc.record_math,
    }
    doc.build(build_story(content, tokens, styles, ctx))

    placeholders_path = Path(out_path).with_name(
        Path(out_path).stem + ".placeholders.json")
    placeholders_path.write_text(
        json.dumps(doc.math_placeholders, indent=1), encoding="utf-8")

    size = os.path.getsize(out_path)
    return {"status": "ok", "out": out_path, "size_kb": size // 1024,
            "pages": doc.page, "headings": doc._headings,
            "math_placeholders": len(doc.math_placeholders),
            "placeholders_file": str(placeholders_path)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tokens", default="tokens.json")
    parser.add_argument("--content", default="content.json")
    parser.add_argument("--out", default="body.pdf")
    args = parser.parse_args()

    for fpath in (args.tokens, args.content):
        if not os.path.exists(fpath):
            print(json.dumps({"status": "error", "error": f"File not found: {fpath}"}),
                  file=sys.stderr)
            sys.exit(1)

    with open(args.tokens, encoding="utf-8") as f:
        tokens = json.load(f)
    with open(args.content, encoding="utf-8") as f:
        content = json.load(f)

    try:
        result = build(tokens, content, args.out)
        print(json.dumps(result, ensure_ascii=False))
    except Exception as e:
        import traceback
        print(json.dumps({"status": "error", "error": str(e),
                          "trace": traceback.format_exc()}, ensure_ascii=False),
              file=sys.stderr)
        sys.exit(3)


if __name__ == "__main__":
    main()
