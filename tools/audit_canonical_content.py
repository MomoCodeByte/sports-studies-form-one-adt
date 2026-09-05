#!/usr/bin/env python3
"""Audit canonical ADT pages against the source PDF and i18n/audio assets."""

from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import re
import unicodedata

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]

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


def words(value: str) -> list[str]:
    value = unicodedata.normalize("NFKD", value).lower()
    value = value.replace("\ufffd", "'")
    return re.findall(r"[a-z0-9]+", value)


def coverage(source: list[str], converted: list[str]) -> tuple[float, list[str]]:
    source_counts = Counter(source)
    converted_counts = Counter(converted)
    matched = sum((source_counts & converted_counts).values())
    missing = list((source_counts - converted_counts).elements())
    return (matched / len(source) if source else 1.0), missing


def ordered_unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


def html_data_ids(markup: str) -> list[str]:
    return re.findall(r'''\bdata-id=["']([^"']+)["']''', markup, flags=re.I)


def html_image_sources(markup: str) -> list[str]:
    return re.findall(r'''<img\b[^>]*?\bsrc=["']([^"']+)["']''', markup, flags=re.I | re.S)


def main() -> int:
    manifest = json.loads((ROOT / "content/pages.json").read_text(encoding="utf-8"))
    by_pdf_page: dict[int, list[dict[str, object]]] = {}
    for entry in manifest:
        match = re.match(r"pg(\d{3})_", str(entry.get("section_id", "")))
        if match:
            by_pdf_page.setdefault(int(match.group(1)), []).append(entry)
    pdf = PdfReader(ROOT / "book/SPORTS STUDIES FORM ONE.pdf")
    texts = json.loads((ROOT / "content/i18n/en-US/texts.json").read_text(encoding="utf-8"))

    low: list[int] = []
    print("page,coverage,pdf_words,adt_words,missing_sample")
    for number, pdf_page in enumerate(pdf.pages, 1):
        entries = by_pdf_page.get(number, [])
        if not entries:
            print(f"{number},0.000,0,0,NO_MANIFEST_ENTRY")
            low.append(number)
            continue
        ids: list[str] = []
        for entry in entries:
            markup = (ROOT / str(entry["href"])).read_text(encoding="utf-8")
            ids.extend(html_data_ids(markup))
        ids = ordered_unique(ids)
        adt_text = " ".join(str(texts.get(text_id, "")) for text_id in ids)
        pdf_tokens = words(clean_pdf_text(pdf_page.extract_text() or ""))
        adt_tokens = words(adt_text)
        score, missing = coverage(pdf_tokens, adt_tokens)
        if score < 0.90:
            low.append(number)
        print(
            f"{number},{score:.3f},{len(pdf_tokens)},{len(adt_tokens)},"
            + " ".join(missing[:15]).replace(",", " ")
        )

    canonical_ids: list[str] = []
    broken_images: list[str] = []
    duplicate_ids: list[str] = []
    for entry in manifest:
        path = ROOT / entry["href"]
        markup = path.read_text(encoding="utf-8")
        page_ids = html_data_ids(markup)
        duplicate_ids.extend(f"{entry['href']}:{item}" for item, count in Counter(page_ids).items() if count > 1)
        canonical_ids.extend(page_ids)
        for source in html_image_sources(markup):
            src = source.split("?", 1)[0]
            if src and not (ROOT / src).is_file():
                broken_images.append(f"{entry['href']}:{src}")

    id_set = set(canonical_ids)
    print(f"SUMMARY pdf_pages={len(pdf.pages)} manifest_entries={len(manifest)} canonical_ids={len(id_set)}")
    print("LOW_COVERAGE " + ",".join(map(str, low)))
    print("BROKEN_IMAGES " + ",".join(broken_images))
    print("DUPLICATE_PAGE_IDS " + ",".join(duplicate_ids))
    for language in ("en-US", "en-KE"):
        folder = ROOT / "content/i18n" / language
        language_texts = json.loads((folder / "texts.json").read_text(encoding="utf-8"))
        speech = json.loads((folder / "speech_texts.json").read_text(encoding="utf-8"))
        audio_map = json.loads((folder / "audios.json").read_text(encoding="utf-8"))
        files = {path.name for path in (folder / "audio").glob("*.mp3")}
        missing_text = sorted(id_set - set(language_texts))
        missing_speech = sorted(id_set - set(speech))
        missing_audio_map = sorted(id_set - set(audio_map))
        missing_audio_files = sorted(
            text_id for text_id in id_set if text_id in audio_map and audio_map[text_id] not in files
        )
        print(
            f"LANG {language} texts={len(language_texts)} speech={len(speech)} "
            f"audio_map={len(audio_map)} mp3={len(files)} missing_text={len(missing_text)} "
            f"missing_speech={len(missing_speech)} missing_audio_map={len(missing_audio_map)} "
            f"missing_audio_files={len(missing_audio_files)}"
        )
        if missing_text:
            print(f"{language}_MISSING_TEXT " + ",".join(missing_text[:30]))
        if missing_speech:
            print(f"{language}_MISSING_SPEECH " + ",".join(missing_speech[:30]))
        if missing_audio_map:
            print(f"{language}_MISSING_AUDIO_MAP " + ",".join(missing_audio_map[:30]))
        if missing_audio_files:
            print(f"{language}_MISSING_AUDIO_FILES " + ",".join(missing_audio_files[:30]))

    return 1 if low or broken_images or duplicate_ids else 0


if __name__ == "__main__":
    raise SystemExit(main())
