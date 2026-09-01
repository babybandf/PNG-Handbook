#!/usr/bin/env python3
"""Stamp vector pdflatex formula PDFs onto the body PDF at placeholder positions."""

import argparse
import json
import sys
from pathlib import Path

from pypdf import PdfReader, PdfWriter, Transformation


def stamp(body: str, placeholders_file: str, meta_file: str, out: str) -> dict:
    placeholders = json.loads(Path(placeholders_file).read_text(encoding="utf-8"))
    meta = json.loads(Path(meta_file).read_text(encoding="utf-8"))

    reader = PdfReader(body)
    writer = PdfWriter()
    writer.append(reader)

    formula_cache: dict[str, object] = {}
    stamped, missing = 0, []
    for ph in placeholders:
        mid = ph["id"]
        info = meta.get(mid)
        if info is None or not Path(info["pdf"]).exists():
            missing.append(mid)
            continue
        if mid not in formula_cache:
            formula_cache[mid] = PdfReader(info["pdf"]).pages[0]
        page = writer.pages[ph["page"] - 1]
        page.merge_transformed_page(
            formula_cache[mid],
            Transformation().translate(ph["x"], ph["y"]),
        )
        stamped += 1

    with open(out, "wb") as f:
        writer.write(f)

    result = {
        "status": "ok" if stamped == len(placeholders) and not missing else "error",
        "out": out,
        "stamped": stamped,
        "placeholders": len(placeholders),
        "missing": missing,
    }
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--body", required=True)
    parser.add_argument("--placeholders", required=True)
    parser.add_argument("--meta", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    result = stamp(args.body, args.placeholders, args.meta, args.out)
    print(json.dumps(result, ensure_ascii=False))
    sys.exit(0 if result["status"] == "ok" else 3)


if __name__ == "__main__":
    main()
