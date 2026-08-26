#!/usr/bin/env python3
"""Build the Chinese PNG handbook as a single PDF with rendered Mermaid diagrams."""

from __future__ import annotations

import argparse
import http.server
import os
import re
import socketserver
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from pathlib import Path

try:
    from pypdf import PdfReader, PdfWriter
    from pypdf.generic import ArrayObject, NameObject
except ImportError:  # pragma: no cover - dependency error is handled in main
    PdfReader = None
    PdfWriter = None
    ArrayObject = None
    NameObject = None


ROOT = Path(__file__).resolve().parent.parent
CN_DIR = ROOT / "cn"
TEMP_SOURCE = ROOT / "pdf-book.md"
DIST_DIR = ROOT / ".vitepress" / "dist"
TEMP_HTML = DIST_DIR / "pdf-book.html"
DEFAULT_OUTPUT = ROOT / "PNG图像格式解码算法与工程实现.pdf"
HEADING_RE = re.compile(r"^(#{1,3})\s+(.+?)\s*$")
FENCE_RE = re.compile(r"^\s*(```|~~~)")


PRINT_STYLE = r"""
<style>
.pdf-cover {
  min-height: 82vh;
  display: flex;
  flex-direction: column;
  justify-content: center;
  text-align: center;
}
.pdf-cover h1 { border: 0; font-size: 34px; line-height: 1.35; }
.pdf-cover p { color: #52606d; font-size: 17px; }
.pdf-page-break { break-before: page; }
.pdf-section-anchor { display: block; position: relative; top: -1rem; }
.pdf-bookmark-probe {
    display: inline-block;
    width: 1px;
    height: 1px;
    overflow: hidden;
    color: transparent;
    font-size: 1px;
}

@media print {
  @page { size: A4; margin: 17mm 15mm 19mm; }
  .VPNav, .VPSidebar, .VPLocalNav, .VPDocAside, .VPDocFooter,
  .VPFooter, .VPSkipLink { display: none !important; }
  .VPContent, .VPDoc, .VPDoc .container, .VPDoc .content,
  .vp-doc { margin: 0 !important; padding: 0 !important; max-width: none !important; }
  html, body { background: white !important; color: #17202a !important; }
  body { font-size: 10.5pt; line-height: 1.55; }
  h1 { break-before: page; font-size: 23pt; }
    .pdf-cover h1 { break-before: auto; }
  h2, h3, h4 { break-after: avoid; }
  table, pre, blockquote, .mermaid { break-inside: avoid; }
  pre { white-space: pre-wrap; overflow-wrap: anywhere; font-size: 8.2pt; }
  table { font-size: 8.8pt; width: 100%; }
  img, svg { max-width: 100% !important; max-height: 225mm !important; }
  .mermaid { text-align: center; }
  a { color: inherit; text-decoration: none; }
}
</style>
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="将 cn 目录中的章节合并为带完整目录和 Mermaid 图的 PDF。"
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"输出 PDF 路径（默认：{DEFAULT_OUTPUT.relative_to(ROOT)}）",
    )
    parser.add_argument(
        "--browser",
        type=Path,
        help="Edge 或 Chrome 可执行文件路径；默认自动查找。",
    )
    parser.add_argument(
        "--keep-source",
        action="store_true",
        help="保留生成的 pdf-book.md，便于调试。",
    )
    parser.add_argument(
        "--skip-build",
        action="store_true",
        help="复用现有 .vitepress/dist/pdf-book.html，仅用于调试打印阶段。",
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="只验证现有输出 PDF 的书签数量和跳转目标。",
    )
    return parser.parse_args()


def chapter_files() -> list[Path]:
    names = ["00", "01", "02", "02-1"]
    names.extend(f"{index:02d}" for index in range(3, 7))
    names.append("06-1")
    names.extend(f"{index:02d}" for index in range(7, 15))
    names.extend(("14-1", "15"))
    files = [CN_DIR / f"{name}.md" for name in names]
    missing = [str(path.relative_to(ROOT)) for path in files if not path.exists()]
    if missing:
        raise RuntimeError(f"章节文件不完整，缺少：{', '.join(missing)}")
    return files


def plain_heading(markdown_text: str) -> str:
    text = re.sub(r"!\[([^]]*)\]\([^)]*\)", r"\1", markdown_text)
    text = re.sub(r"\[([^]]+)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"[`*_~]", "", text)
    return text.strip()


def annotate_chapters(files: list[Path]) -> tuple[str, list[tuple[int, str, str]]]:
    sections: list[str] = []
    toc: list[tuple[int, str, str]] = []
    anchor_number = 0

    for chapter_index, path in enumerate(files):
        lines = path.read_text(encoding="utf-8").splitlines()
        output_lines: list[str] = []
        fence_marker: str | None = None

        if chapter_index:
            output_lines.append('<div class="pdf-page-break"></div>')

        for line_number, line in enumerate(lines):
            fence_match = FENCE_RE.match(line)
            if fence_match:
                marker = fence_match.group(1)
                if fence_marker is None:
                    fence_marker = marker
                elif marker == fence_marker:
                    fence_marker = None
                output_lines.append(line)
                continue

            heading_match = HEADING_RE.match(line) if fence_marker is None else None
            if not heading_match:
                output_lines.append(line)
                continue

            level = len(heading_match.group(1))
            title = heading_match.group(2)
            if chapter_index == 0 and line_number == 0:
                title = "00. 前言"
                line = "# 00. 前言"

            anchor_number += 1
            anchor = f"section-{anchor_number}"
            output_lines.append(
                f'<a id="{anchor}" class="pdf-section-anchor"></a>'
            )
            output_lines.append(line)
            output_lines.append(
                f'<a href="https://png-handbook.invalid/{anchor}" '
                'class="pdf-bookmark-probe" aria-hidden="true">&#8203;</a>'
            )
            toc.append((level, plain_heading(title), anchor))

        sections.append("\n".join(output_lines).strip())

    return "\n\n".join(sections), toc


def create_book_source(
    files: list[Path],
) -> tuple[int, list[tuple[int, str, str]]]:
    body, toc = annotate_chapters(files)
    mermaid_count = len(re.findall(r"(?m)^\s*(?:```|~~~)mermaid\s*$", body))
    source = f"""---
title: PNG 图像格式、解码算法与工程实现
sidebar: false
aside: false
lastUpdated: false
editLink: false
pageClass: pdf-book
---

{PRINT_STYLE}

<div class="pdf-cover">
  <h1>PNG 图像格式、解码算法与工程实现</h1>
  <p>从文件格式、Chunk、zlib、DEFLATE，到 Scanline 重建、Adam7、颜色处理与硬件架构</p>
  <p>版本 0.9 · 2026-08-19</p>
</div>

<div class="pdf-page-break"></div>

{body}
"""
    TEMP_SOURCE.write_text(source, encoding="utf-8", newline="\n")
    return mermaid_count, toc


def find_browser(explicit: Path | None) -> Path:
    if explicit:
        if explicit.is_file():
            return explicit.resolve()
        raise RuntimeError(f"浏览器不存在：{explicit}")

    candidates = [
        Path(os.environ.get("PROGRAMFILES(X86)", ""))
        / "Microsoft/Edge/Application/msedge.exe",
        Path(os.environ.get("PROGRAMFILES", ""))
        / "Microsoft/Edge/Application/msedge.exe",
        Path(os.environ.get("LOCALAPPDATA", ""))
        / "Microsoft/Edge/Application/msedge.exe",
        Path(os.environ.get("PROGRAMFILES", ""))
        / "Google/Chrome/Application/chrome.exe",
        Path(os.environ.get("PROGRAMFILES(X86)", ""))
        / "Google/Chrome/Application/chrome.exe",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise RuntimeError("找不到 Microsoft Edge 或 Google Chrome，请用 --browser 指定路径。")


def build_site() -> None:
    npm = "npm.cmd" if os.name == "nt" else "npm"
    subprocess.run([npm, "run", "docs:build"], cwd=ROOT, check=True)
    if not TEMP_HTML.is_file():
        raise RuntimeError(f"VitePress 未生成 {TEMP_HTML.relative_to(ROOT)}")


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, _format: str, *_args: object) -> None:
        pass


class ReusableTCPServer(socketserver.TCPServer):
    allow_reuse_address = True


def browser_flags(profile: Path) -> list[str]:
    return [
        "--headless=new",
        "--disable-gpu",
        "--no-proxy-server",
        "--disable-background-networking",
        "--disable-component-update",
        "--no-first-run",
        "--disable-extensions",
        "--run-all-compositor-stages-before-draw",
        "--virtual-time-budget=30000",
        f"--user-data-dir={profile}",
    ]


def verify_mermaid(browser: Path, url: str, expected_count: int) -> None:
    with tempfile.TemporaryDirectory(prefix="png-handbook-browser-") as profile:
        try:
            result = subprocess.run(
                [str(browser), *browser_flags(Path(profile)), "--dump-dom", url],
                cwd=ROOT,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=60,
            )
            stdout = result.stdout
        except subprocess.TimeoutExpired as error:
            stdout = error.stdout or b""

    document = stdout.decode("utf-8", errors="replace")
    rendered_count = document.count('data-processed="true"')
    svg_count = len(re.findall(r"<svg(?:\s|>)", document))
    if rendered_count < expected_count or svg_count < expected_count:
        raise RuntimeError(
            "Mermaid 渲染校验失败："
            f"预期 {expected_count} 个，已处理 {rendered_count} 个，SVG {svg_count} 个"
        )
    print(f"Mermaid 渲染校验通过：{expected_count} 个图均已生成 SVG。")


def add_pdf_bookmarks(
    pdf_path: Path, entries: list[tuple[int, str, str]]
) -> None:
    if (
        PdfReader is None
        or PdfWriter is None
        or ArrayObject is None
        or NameObject is None
    ):
        raise RuntimeError(
            "缺少 pypdf。请先运行：python -m pip install -r requirements.txt"
        )

    reader = PdfReader(pdf_path)
    page_for_anchor: dict[str, int] = {}
    prefix = "https://png-handbook.invalid/"

    for page_number, page in enumerate(reader.pages):
        retained_annotations = ArrayObject()
        for annotation_ref in page.get("/Annots", []):
            annotation = annotation_ref.get_object()
            action = annotation.get("/A")
            uri = action.get("/URI") if action else None
            if isinstance(uri, str) and uri.startswith(prefix):
                page_for_anchor[uri.removeprefix(prefix)] = page_number
            else:
                retained_annotations.append(annotation_ref)

        if retained_annotations:
            page[NameObject("/Annots")] = retained_annotations
        elif "/Annots" in page:
            del page["/Annots"]

    missing = [anchor for _level, _title, anchor in entries if anchor not in page_for_anchor]
    if missing:
        raise RuntimeError(
            f"PDF 书签定位失败：{len(missing)} 个标题没有页面目标，"
            f"首个缺失目标为 {missing[0]}"
        )

    writer = PdfWriter()
    writer.clone_document_from_reader(reader)
    writer.add_metadata(
        {
            "/Title": "PNG 图像格式、解码算法与工程实现",
            "/Subject": "PNG 文件格式、解码算法与工程实现",
            "/Language": "zh-CN",
        }
    )

    parents: dict[int, object] = {}
    for level, title, anchor in entries:
        parent = parents.get(level - 1)
        item = writer.add_outline_item(
            title,
            page_for_anchor[anchor],
            parent=parent,
        )
        parents[level] = item
        for deeper_level in list(parents):
            if deeper_level > level:
                del parents[deeper_level]

    temporary = pdf_path.with_suffix(".bookmarked.pdf")
    with temporary.open("wb") as stream:
        writer.write(stream)
    temporary.replace(pdf_path)

    verify_pdf_bookmarks(pdf_path, len(entries))


def verify_pdf_bookmarks(pdf_path: Path, expected_count: int) -> None:
    if PdfReader is None:
        raise RuntimeError(
            "缺少 pypdf。请先运行：python -m pip install -r requirements.txt"
        )

    verified = PdfReader(pdf_path)
    outline_count = 0
    invalid_destinations = 0

    def count_outline(items: list[object]) -> None:
        nonlocal invalid_destinations, outline_count
        for item in items:
            if isinstance(item, list):
                count_outline(item)
            else:
                page_number = verified.get_destination_page_number(item)
                if not 0 <= page_number < len(verified.pages):
                    invalid_destinations += 1
                outline_count += 1

    count_outline(verified.outline)
    if outline_count != expected_count or invalid_destinations:
        raise RuntimeError(
            f"PDF 书签校验失败：预期 {expected_count} 个，实际 {outline_count} 个，"
            f"无效目标 {invalid_destinations} 个"
        )
    print(
        f"PDF 书签校验通过：{outline_count} 个书签均具有有效页面目标，"
        f"PDF 共 {len(verified.pages)} 页。"
    )


def print_pdf(
    browser: Path,
    output: Path,
    expected_mermaid: int,
    bookmarks: list[tuple[int, str, str]],
) -> None:
    handler = lambda *args, **kwargs: QuietHandler(  # noqa: E731
        *args, directory=str(DIST_DIR), **kwargs
    )
    server = ReusableTCPServer(("127.0.0.1", 0), handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        url = f"http://127.0.0.1:{port}/pdf-book.html"
        for _ in range(50):
            try:
                request = urllib.request.Request(url, method="HEAD")
                urllib.request.urlopen(request, timeout=1).close()
                break
            except OSError:
                time.sleep(0.1)
        else:
            raise RuntimeError("本地 PDF 页面服务启动失败")

        verify_mermaid(browser, url, expected_mermaid)

        output = output.resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        if output.exists():
            output.unlink()

        with tempfile.TemporaryDirectory(prefix="png-handbook-print-") as profile:
            command = [
                str(browser),
                *browser_flags(Path(profile)),
                "--print-to-pdf-no-header",
                f"--print-to-pdf={output}",
                url,
            ]
            try:
                subprocess.run(command, cwd=ROOT, check=True, timeout=60)
            except subprocess.TimeoutExpired:
                if not output.is_file() or output.stat().st_size < 10_000:
                    raise
    finally:
        server.shutdown()
        server.server_close()

    if not output.is_file() or output.stat().st_size < 10_000:
        raise RuntimeError("PDF 未生成或文件异常小")
    add_pdf_bookmarks(output, bookmarks)


def main() -> int:
    args = parse_args()
    output = args.output if args.output.is_absolute() else ROOT / args.output

    try:
        files = chapter_files()
        print(f"合并 {len(files)} 个章节并生成完整目录……")
        mermaid_count, bookmarks = create_book_source(files)
        if args.verify_only:
            if not output.is_file():
                raise RuntimeError(f"PDF 不存在：{output}")
            verify_pdf_bookmarks(output, len(bookmarks))
            return 0

        browser = find_browser(args.browser)
        if args.skip_build:
            if not TEMP_HTML.is_file():
                raise RuntimeError("没有可复用的 pdf-book.html，请移除 --skip-build")
        else:
            print("使用 VitePress 渲染 Markdown 和 Mermaid……")
            build_site()
        print(f"使用 {browser.name} 生成 PDF……")
        print_pdf(browser, output, mermaid_count, bookmarks)
        size_mb = output.stat().st_size / (1024 * 1024)
        print(f"完成：{output}（{size_mb:.2f} MiB）")
        return 0
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        print(f"错误：{error}", file=sys.stderr)
        return 1
    finally:
        if not args.keep_source:
            TEMP_SOURCE.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())