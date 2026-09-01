#!/usr/bin/env python3
"""One-command PDF builder: markdown chapters -> styled PDF with vector TeX
formulas, rendered mermaid diagrams and a complete outline.

Usage:
    python3 build.py                          # defaults from config.json
    python3 build.py --accent "#33A6B8" --output out.pdf
    python3 build.py --math-engine latex|katex|matplotlib
"""

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

PKG = Path(__file__).resolve().parent
ROOT = PKG.parent.parent
sys.path.insert(0, str(PKG))

from md2content import convert, init_fonts            # noqa: E402
import merge_outline                                   # noqa: E402
import render_body_cjk                                 # noqa: E402
import render_cover                                    # noqa: E402

TEX_TEMPLATE = r"""\documentclass[border=0pt]{standalone}
\usepackage{amsmath,amssymb,xcolor}
\definecolor{ink}{HTML}{%s}
\begin{document}
{\color{ink}$%s$}
\end{document}
"""


def find_pdflatex() -> Path | None:
    candidates = [
        shutil.which("pdflatex"),
        Path.home() / "Library/TinyTeX/bin/universal-darwin/pdflatex",
        Path.home() / ".TinyTeX/bin/universal-darwin/pdflatex",
        Path.home() / ".TinyTeX/bin/x86_64-linux/pdflatex",
    ]
    for c in candidates:
        if c and Path(c).exists():
            return Path(c)
    return None


def check_python_deps() -> None:
    missing = []
    for mod in ("reportlab", "pypdf", "fontTools", "matplotlib"):
        try:
            __import__(mod)
        except ImportError:
            missing.append(mod)
    if missing:
        raise SystemExit(
            f"缺少 Python 依赖：{', '.join(missing)}。"
            f"请先安装（如：python3 -m pip install reportlab pypdf matplotlib fonttools）"
        )


def check_node(playwright: bool = True) -> None:
    if shutil.which("node") is None:
        raise SystemExit("缺少 node。请安装 Node.js 18+。")
    if playwright:
        probe = subprocess.run(
            ["node", "-e",
             "try { require('playwright') } catch (e) { "
             "const root = require('child_process').execSync('npm root -g')"
             ".toString().trim(); require(root + '/playwright') }"],
            capture_output=True,
        )
        if probe.returncode != 0:
            raise SystemExit("缺少 playwright。请运行：npm install -g playwright "
                             "&& npx playwright install chromium")


def compile_formulas(blocks: list[dict], work: Path, pdflatex: Path,
                     ink: str) -> tuple[dict, list[str]]:
    tex_dir = work / "tex"
    tex_dir.mkdir(exist_ok=True)
    meta: dict = {}
    failures: list[str] = []
    by_expr: dict[str, Path] = {}

    for block in blocks:
        mid = block["math_id"]
        expr = " ".join(block["text"].split())
        try:
            if expr not in by_expr:
                tex_path = tex_dir / f"f{len(by_expr)}.tex"
                tex_path.write_text(TEX_TEMPLATE % (ink.lstrip("#").upper(), expr),
                                    encoding="utf-8")
                proc = subprocess.run(
                    [str(pdflatex), "-interaction=nonstopmode",
                     "-output-directory", str(tex_dir), str(tex_path)],
                    capture_output=True, timeout=60,
                )
                pdf_path = tex_path.with_suffix(".pdf")
                if proc.returncode != 0 or not pdf_path.exists():
                    failures.append(mid)
                    continue
                by_expr[expr] = pdf_path
            from pypdf import PdfReader
            box = PdfReader(by_expr[expr]).pages[0].mediabox
            meta[mid] = {"pdf": str(by_expr[expr]),
                         "w": float(box.width), "h": float(box.height)}
        except Exception:
            failures.append(mid)
    return meta, failures


def write_mermaid_page(cfg: dict, out: Path) -> None:
    m = cfg["mermaid"]
    node_modules = ROOT / "node_modules"
    html = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8">
<style>
  body {{ margin: 0; padding: 24px; background: #FFFFFF; }}
  #out svg {{ display: block; }}
</style>
</head>
<body>
<div id="out"></div>
<script src="file://{node_modules}/mermaid/dist/mermaid.min.js"></script>
<script>
  const mermaid = window.__esbuild_esm_mermaid_nm.mermaid.default
    || window.__esbuild_esm_mermaid_nm.mermaid
  mermaid.initialize({{
    startOnLoad: false,
    securityLevel: 'loose',
    theme: 'neutral',
    themeVariables: {{
      primaryColor: '{m['primary_color']}',
      primaryBorderColor: '{m['primary_border_color']}',
      primaryTextColor: '{m['primary_text_color']}',
      lineColor: '{m['line_color']}',
      fontSize: '{m['font_size']}',
      fontFamily: `{m['font_family']}`,
    }},
    flowchart: {{ htmlLabels: true, curve: 'basis', padding: 8, nodeSpacing: 24, rankSpacing: 30 }},
    state: {{ nodeSpacing: 24, rankSpacing: 30, diagramPadding: 8 }},
  }})
  window.renderDiagram = async (code) => {{
    const {{ svg }} = await mermaid.render('m' + Math.random().toString(36).slice(2), code)
    document.getElementById('out').innerHTML = svg
    const el = document.querySelector('#out svg')
    el.style.maxWidth = 'none'
    const vb = el.viewBox.baseVal
    el.setAttribute('width', vb.width)
    el.setAttribute('height', vb.height)
    const rect = el.getBoundingClientRect()
    return {{ w: Math.ceil(rect.width), h: Math.ceil(rect.height) }}
  }}
  window.__ready = true
</script>
</body>
</html>
"""
    out.write_text(html, encoding="utf-8")


def write_katex_page(cfg: dict, out: Path) -> None:
    katex = ROOT / "node_modules" / "katex" / "dist"
    html = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8">
<link rel="stylesheet" href="file://{katex}/katex.min.css">
<style>
  body {{ margin: 0; padding: 10px; background: #FFFFFF; }}
  #out {{ display: inline-block; color: {cfg['dark']}; font-size: 17px; }}
</style>
</head>
<body>
<span id="out"></span>
<script src="file://{katex}/katex.min.js"></script>
<script>
  window.renderMath = async (expr) => {{
    katex.render(expr, document.getElementById('out'), {{
      displayMode: true, throwOnError: false, strict: false,
    }})
    await document.fonts.ready
    const el = document.getElementById('out')
    const r = el.getBoundingClientRect()
    return {{ w: Math.ceil(r.width), h: Math.ceil(r.height) }}
  }}
  window.__ready = true
</script>
</body>
</html>
"""
    out.write_text(html, encoding="utf-8")


def run_node(script: list[str]) -> None:
    proc = subprocess.run(["node", *script], capture_output=True, text=True)
    sys.stdout.write(proc.stdout)
    if proc.returncode != 0:
        sys.stderr.write(proc.stderr)
        raise SystemExit(f"node 步骤失败：{' '.join(script[:1])} {script[1]}")


def make_tokens(cfg: dict, engine: str, math_meta_path: Path) -> dict:
    ts = cfg["type_scale"]
    fonts = cfg["fonts"]
    m = cfg["margins"]
    return {
        "title": cfg["title"],
        "author": cfg["author"],
        "date": cfg["date"],
        "subject": cfg["subject"],
        "accent": cfg["accent"],
        "accent_lt": cfg["accent_lt"],
        "dark": cfg["dark"],
        "body_text": cfg["body_text"],
        "muted": cfg["muted"],
        "box_border": cfg["box_border"],
        "table_header_bg": cfg["table_header_bg"],
        "table_header_text": cfg["table_header_text"],
        "table_row_alt": cfg["table_row_alt"],
        "code_bg": cfg["code_bg"],
        "callout_bg": cfg["callout_bg"],
        "font_display_rl": fonts["heading"][0],
        "font_body_rl": fonts["body"][0],
        "font_body_b_rl": fonts["body_bold"][0],
        "font_specs": cfg["font_files"],
        "font_family_map": cfg["font_family_map"],
        "math_engine": engine,
        "math_meta": str(math_meta_path),
        "size_h1": ts["size_h1"],
        "size_h2": ts["size_h2"],
        "size_h3": ts["size_h3"],
        "size_body": ts["size_body"],
        "size_caption": ts["size_caption"],
        "size_meta": ts["size_meta"],
        "line_gap": ts["line_gap"],
        "section_gap": ts["section_gap"],
        "para_gap": ts["para_gap"],
        "margin_left": m["left"],
        "margin_right": m["right"],
        "margin_top": m["top"],
        "margin_bottom": m["bottom"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the PNG handbook PDF")
    parser.add_argument("--config", default=str(PKG / "config.json"))
    parser.add_argument("--output", help="final PDF path "
                        f"(default: {ROOT / 'PNG图像格式解码算法与工程实现.pdf'})")
    parser.add_argument("--accent", help="override accent color (hex)")
    parser.add_argument("--cover-bg", help="override cover background (hex)")
    parser.add_argument("--math-engine", choices=["auto", "latex", "katex", "matplotlib"],
                        default="auto")
    parser.add_argument("--workdir", help="keep intermediate files in this dir")
    parser.add_argument("--keep-work", action="store_true")
    args = parser.parse_args()

    check_python_deps()
    check_node()

    cfg = json.loads(Path(args.config).read_text(encoding="utf-8"))
    if args.accent:
        cfg["accent"] = args.accent
    if args.cover_bg:
        cfg["cover_bg"] = args.cover_bg

    if args.workdir:
        work = Path(args.workdir).resolve()
        work.mkdir(parents=True, exist_ok=True)
    else:
        work = Path(tempfile.mkdtemp(prefix="minimax-pdf-"))

    init_fonts(cfg["font_files"])
    print(f"[1/7] 解析章节 -> content.json（工作目录 {work}）")
    content, mmd_manifest = convert(cfg["chapters"],
                                    ROOT / cfg["chapter_dir"], work)
    (work / "content.json").write_text(
        json.dumps(content, ensure_ascii=False, indent=1), encoding="utf-8")
    (work / "mermaid_manifest.json").write_text(
        json.dumps(mmd_manifest, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"[2/7] 渲染 {len(mmd_manifest)} 个 mermaid 图")
    write_mermaid_page(cfg, work / "mermaid_page.html")
    if mmd_manifest:
        run_node([str(PKG / "render_mermaid.mjs"),
                  str(work / "mermaid_manifest.json"), str(work),
                  str(work / "mermaid_page.html")])

    print("[3/7] 渲染公式（真矢量 LaTeX）")
    math_blocks = [b for b in content if b["type"] == "math"]
    pdflatex = find_pdflatex()
    engine = args.math_engine
    if engine == "auto":
        engine = "latex" if pdflatex else "katex"
        if engine == "katex" and not (ROOT / "node_modules/katex/dist/katex.min.js").exists():
            engine = "matplotlib"
    print(f"      公式引擎：{engine}（pdflatex={'yes' if pdflatex else 'no'}，"
          f"公式 {len(math_blocks)} 个）")

    math_meta: dict = {}
    meta_file = work / "math_meta.json"
    if engine == "latex" and math_blocks:
        if not pdflatex:
            raise SystemExit("math_engine=latex 但未找到 pdflatex。"
                             "请安装 TinyTeX 或改用 --math-engine katex")
        meta, failed = compile_formulas(math_blocks, work, pdflatex, cfg["body_text"])
        if failed:
            print(f"      pdflatex 失败 {len(failed)} 个，回退 KaTeX：{failed}")
        if not (ROOT / "node_modules/katex/dist/katex.min.js").exists():
            meta_file = work / "math_meta.json"
            meta_file.write_text(json.dumps(meta, indent=1), encoding="utf-8")
        else:
            rest = [b for b in math_blocks if b["math_id"] not in meta]
            if rest:
                write_katex_page(cfg, work / "katex_page.html")
                (work / "math_manifest.json").write_text(
                    json.dumps([{"id": b["math_id"], "expr": b["text"]}
                                for b in rest], ensure_ascii=False),
                    encoding="utf-8")
                run_node([str(PKG / "render_math.mjs"),
                          str(work / "math_manifest.json"), str(work),
                          str(work / "katex_page.html"),
                          str(work / "math_katex_meta.json")])
                katex_meta = json.loads(
                    (work / "math_katex_meta.json").read_text(encoding="utf-8"))
                for b in rest:
                    if b["math_id"] in katex_meta:
                        meta[b["math_id"]] = {
                            "png": str(work / f"{b['math_id']}.png"),
                            "w": katex_meta[b["math_id"]]["w"],
                            "h": katex_meta[b["math_id"]]["h"],
                        }
            meta_file.write_text(json.dumps(meta, indent=1), encoding="utf-8")
    elif engine == "katex" and math_blocks:
        write_katex_page(cfg, work / "katex_page.html")
        (work / "math_manifest.json").write_text(
            json.dumps([{"id": b["math_id"], "expr": b["text"]}
                        for b in math_blocks], ensure_ascii=False),
            encoding="utf-8")
        run_node([str(PKG / "render_math.mjs"),
                  str(work / "math_manifest.json"), str(work),
                  str(work / "katex_page.html"), str(meta_file)])
    else:
        meta_file.write_text("{}", encoding="utf-8")

    print("[4/7] 渲染封面")
    cover_html = work / "cover.html"
    cover_html.write_text(render_cover.render_html(cfg), encoding="utf-8")
    run_node([str(PKG / "render_cover.mjs"), str(cover_html),
              str(work / "cover.pdf")])

    print("[5/7] 渲染正文（ReportLab + 完整书签）")
    tokens = make_tokens(cfg, engine if engine != "auto" else "matplotlib", meta_file)
    (work / "tokens.json").write_text(
        json.dumps(tokens, ensure_ascii=False, indent=2), encoding="utf-8")
    body_pdf = work / "body.pdf"
    body_result = render_body_cjk.build(tokens, content, str(body_pdf))
    print(f"      正文 {body_result['pages']} 页，标题 {body_result['headings']} 个，"
          f"公式占位 {body_result.get('math_placeholders', 0)} 个")

    if engine == "latex" and body_result.get("math_placeholders"):
        print("[6/7] 矢量公式叠加")
        stamped_pdf = work / "body-stamped.pdf"
        proc = subprocess.run(
            [sys.executable, str(PKG / "stamp_math.py"),
             "--body", str(body_pdf),
             "--placeholders", body_result["placeholders_file"],
             "--meta", str(meta_file),
             "--out", str(stamped_pdf)],
            capture_output=True, text=True,
        )
        sys.stdout.write(proc.stdout)
        if proc.returncode != 0:
            sys.stderr.write(proc.stderr)
            raise SystemExit("公式叠加失败")
        body_pdf = stamped_pdf
    else:
        print("[6/7] 跳过公式叠加（无矢量公式）")

    print("[7/7] 合并封面与正文，校验书签")
    final_pdf = work / "final.pdf"
    merge_cfg = {
        "cover": str(work / "cover.pdf"),
        "body": str(body_pdf),
        "out": str(final_pdf),
        "expected_bookmarks": body_result["headings"],
        "margins": cfg["margins"],
        "meta": {
            "title": cfg["title"],
            "subject": cfg["subject"],
            "author": cfg["author"],
        },
    }
    (work / "merge_cfg.json").write_text(json.dumps(merge_cfg, ensure_ascii=False),
                                         encoding="utf-8")
    merge_result = merge_outline.merge(merge_cfg["cover"], merge_cfg["body"],
                                       merge_cfg["out"], merge_cfg["meta"],
                                       merge_cfg["expected_bookmarks"])
    problems = merge_outline.layout_qa(merge_cfg["out"], cfg["margins"])
    merge_result["layout_problems"] = problems
    print(json.dumps(merge_result, ensure_ascii=False, indent=1))

    output = Path(args.output) if args.output else ROOT / cfg["output_name"]
    if not output.is_absolute():
        output = ROOT / output
    output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(final_pdf, output)
    print(f"完成：{output}")

    if not args.keep_work and not args.workdir:
        shutil.rmtree(work, ignore_errors=True)
    return 0 if merge_result["status"] == "ok" and not problems else 1


if __name__ == "__main__":
    sys.exit(main())
