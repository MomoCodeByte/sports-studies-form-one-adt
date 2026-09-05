#!/usr/bin/env python3
"""Compare each source PDF page with the corresponding ADT text and spine entry."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import unicodedata

from pypdf import PdfReader


BOILERPLATE = (
    re.compile(r"^sport studies for secondary schools$", re.I),
    re.compile(r"^student'?s book\s+form one$", re.I),
    re.compile(r"^tanzania institute of education$", re.I),
    re.compile(r"^sports studies form one\.indd", re.I),
    re.compile(r"^[ivxlcdm]+$", re.I),
    re.compile(r"^\d+$"),
)


def clean_pdf_text(value: str) -> str:
    lines: list[str] = []
    for raw_line in value.splitlines():
        line = re.sub(r"\s+", " ", raw_line).strip()
        if not line or any(pattern.search(line) for pattern in BOILERPLATE):
            continue
        lines.append(line)
    return " ".join(lines)


def tokens(value: str) -> list[str]:
    value = unicodedata.normalize("NFKD", value)
    value = value.replace("\ufffd", "'")
    return re.findall(r"[a-z0-9]+", value.lower())


def counter_coverage(source: list[str], converted: list[str]) -> tuple[float, list[str]]:
    source_counts = Counter(source)
    converted_counts = Counter(converted)
    matched = sum((source_counts & converted_counts).values())
    missing = list((source_counts - converted_counts).elements())
    return (matched / len(source) if source else 1.0), missing


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--threshold", type=float, default=0.90)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.root.resolve()
    pdf_path = root / "book" / "SPORTS STUDIES FORM ONE.pdf"
    texts = json.loads((root / "content" / "i18n" / "en-US" / "texts.json").read_text(encoding="utf-8"))
    pages_manifest = json.loads((root / "content" / "pages.json").read_text(encoding="utf-8"))
    manifest_ids = {entry["section_id"] for entry in pages_manifest}
    reader = PdfReader(pdf_path)

    print("page,pdf_words,adt_words,coverage,html,manifest,missing_sample")
    low_coverage: list[int] = []
    missing_html: list[int] = []
    missing_manifest: list[int] = []
    for page_number, pdf_page in enumerate(reader.pages, start=1):
        prefix = f"pg{page_number:03d}_"
        adt_values = [str(value) for key, value in texts.items() if key.startswith(prefix)]
        pdf_tokens = tokens(clean_pdf_text(pdf_page.extract_text() or ""))
        adt_tokens = tokens(" ".join(adt_values))
        coverage, missing = counter_coverage(pdf_tokens, adt_tokens)
        html_exists = page_number == 1 and (root / "index.html").is_file()
        html_exists = html_exists or any(root.glob(f"pg{page_number:03d}_sec*.html"))
        manifest_exists = any(section_id.startswith(f"pg{page_number:03d}_") for section_id in manifest_ids)
        if coverage < args.threshold:
            low_coverage.append(page_number)
        if not html_exists:
            missing_html.append(page_number)
        if not manifest_exists:
            missing_manifest.append(page_number)
        missing_sample = " ".join(missing[:12]).replace(",", " ")
        print(
            f"{page_number},{len(pdf_tokens)},{len(adt_tokens)},{coverage:.3f},"
            f"{str(html_exists).lower()},{str(manifest_exists).lower()},{missing_sample}"
        )

    print(f"SUMMARY pdf_pages={len(reader.pages)} manifest_entries={len(pages_manifest)}")
    print("LOW_COVERAGE " + ",".join(map(str, low_coverage)))
    print("MISSING_HTML " + ",".join(map(str, missing_html)))
    print("MISSING_MANIFEST " + ",".join(map(str, missing_manifest)))
    return 1 if missing_html or missing_manifest or low_coverage else 0


if __name__ == "__main__":
    raise SystemExit(main())
