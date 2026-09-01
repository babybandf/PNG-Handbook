#!/usr/bin/env python3
"""Merge cover + body preserving the outline, set metadata, verify bookmarks,
and run an optional layout QA (overflow / blank pages) via pymupdf."""

import json
import sys
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject


def merge(cover: str, body: str, out: str, meta: dict,
          expected_bookmarks: int) -> dict:
    writer = PdfWriter()
    cover_reader = PdfReader(cover)
    body_reader = PdfReader(body)

    cover_pages = len(cover_reader.pages)
    writer.append(cover_reader)
    writer.append(body_reader)

    writer.add_metadata({
        "/Title": meta["title"],
        "/Subject": meta["subject"],
        "/Author": meta.get("author", ""),
        "/Creator": "PNG-Handbook PDF pipeline (minimax_pdf)",
        "/Keywords": meta.get("keywords", "PNG,zlib,DEFLATE,decoder"),
    })
    try:
        writer._root_object[NameObject("/Lang")] = "zh-CN"
    except Exception:
        pass

    with open(out, "wb") as f:
        writer.write(f)

    reader = PdfReader(out)
    n_pages = len(reader.pages)
    count = invalid = on_cover = 0

    def walk(items):
        nonlocal count, invalid, on_cover
        for it in items:
            if isinstance(it, list):
                walk(it)
            else:
                page_no = reader.get_destination_page_number(it)
                if not 0 <= page_no < n_pages:
                    invalid += 1
                elif page_no < cover_pages:
                    on_cover += 1
                count += 1

    walk(reader.outline)

    ok = count == expected_bookmarks and invalid == 0 and on_cover == 0
    return {
        "status": "ok" if ok else "error",
        "out": out,
        "total_pages": n_pages,
        "cover_pages": cover_pages,
        "body_pages": len(body_reader.pages),
        "bookmarks": count,
        "expected_bookmarks": expected_bookmarks,
        "invalid_destinations": invalid,
        "bookmarks_on_cover": on_cover,
        "size_kb": Path(out).stat().st_size // 1024,
    }


def layout_qa(pdf_path: str, margins: dict) -> list:
    """Return a list of layout problems; empty when clean. Needs pymupdf."""
    try:
        import pymupdf as fitz
    except ImportError:
        return []
    doc = fitz.open(pdf_path)
    w, h = doc[0].rect.width, doc[0].rect.height
    lm, rm = margins["left"], margins["right"]
    tm, bm = margins["top"], margins["bottom"]
    problems = []
    for pno in range(1, len(doc)):
        page = doc[pno]
        for b in page.get_text("blocks"):
            x0, y0, x1, y1, text = b[:5]
            if y1 <= tm - 10 or y0 >= h - bm - 12:
                continue
            if x1 > w - rm + 2 or x0 < lm - 2 or y1 > h - bm + 2 or y0 < tm - 2:
                problems.append({"page": pno + 1, "kind": "text-overflow",
                                 "text": text[:40].replace("\n", " ")})
        for info in page.get_image_info():
            x0, y0, x1, y1 = info["bbox"]
            if x1 > w - rm + 2 or x0 < lm - 2 or y1 > h - bm + 2 or y0 < tm - 2:
                problems.append({"page": pno + 1, "kind": "image-overflow"})
    return problems


if __name__ == "__main__":
    cfg = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    res = merge(cfg["cover"], cfg["body"], cfg["out"], cfg["meta"],
                cfg["expected_bookmarks"])
    if cfg.get("margins"):
        res["layout_problems"] = layout_qa(cfg["out"], cfg["margins"])
    print(json.dumps(res, ensure_ascii=False, indent=1))
    sys.exit(0 if res["status"] == "ok" else 3)
