#!/usr/bin/env python3
"""Remove selected ADT quiz pages from the book's reading order.

The source HTML files are intentionally kept on disk as a recoverable backup.
"""

from __future__ import annotations

import json
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    if len(sys.argv) < 2:
        raise SystemExit("Usage: remove_generated_quiz_pages.py POSITION [POSITION ...]")
    target_positions = tuple(sorted({int(value) for value in sys.argv[1:]}))

    pages_path = ROOT / "content" / "pages.json"
    pages = json.loads(pages_path.read_text(encoding="utf-8"))

    if any(position < 1 or position > len(pages) for position in target_positions):
        raise RuntimeError(f"Positions must be between 1 and {len(pages)}")
    removed = [pages[position - 1] for position in target_positions]
    unexpected = [entry["section_id"] for entry in removed if not re.fullmatch(r"qz\d{3}", entry["section_id"])]
    if unexpected:
        raise RuntimeError(
            "Refusing to remove non-quiz pages: " + ", ".join(unexpected)
        )

    removed_sections = {entry["section_id"] for entry in removed}
    kept = [entry for entry in pages if entry["section_id"] not in removed_sections]
    pages_path.write_text(
        json.dumps(kept, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    for page_number, entry in enumerate(kept, start=1):
        html_path = ROOT / entry["href"]
        source = html_path.read_text(encoding="utf-8")
        source, count = re.subn(
            r'(<meta\s+name="page-section-id"\s+content=")\d+("\s*/>)',
            rf"\g<1>{page_number}\g<2>",
            source,
            count=1,
        )
        if count != 1:
            raise RuntimeError(f"Could not renumber {html_path.name}")
        html_path.write_text(source, encoding="utf-8", newline="\n")

    manifest_path = ROOT / "imsmanifest.xml"
    manifest = manifest_path.read_text(encoding="utf-8")
    for entry in removed:
        manifest, count = re.subn(
            rf'^\s*<file href="{re.escape(entry["href"])}"/>\r?\n',
            "",
            manifest,
            count=1,
            flags=re.M,
        )
        if count != 1:
            raise RuntimeError(f"Could not remove {entry['href']} from imsmanifest.xml")
    manifest_path.write_text(manifest, encoding="utf-8", newline="\n")

    preloader_path = ROOT / "assets" / "offline-preloader.js"
    preloader = preloader_path.read_text(encoding="utf-8")
    match = re.search(r"var INLINE = (\{.*\});\n  var BASE_DIR", preloader, re.S)
    if not match:
        raise RuntimeError("Could not locate INLINE data in offline-preloader.js")
    inline = json.loads(match.group(1))
    inline["./content/pages.json"] = kept
    for entry in removed:
        inline.pop(f'./{entry["href"]}', None)
    for entry in kept:
        relative = entry["href"]
        inline[f"./{relative}"] = (ROOT / relative).read_text(encoding="utf-8")
    replacement = (
        "var INLINE = "
        + json.dumps(inline, ensure_ascii=False, separators=(",", ":"))
        + ";\n  var BASE_DIR"
    )
    preloader = preloader[: match.start()] + replacement + preloader[match.end() :]
    preloader_path.write_text(preloader, encoding="utf-8", newline="\n")

    print(f"Removed {len(removed)} generated quiz pages from the reading order.")
    print(f"Reader page count: {len(pages)} -> {len(kept)}")
    print("Kept source files: " + ", ".join(entry["href"] for entry in removed))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
