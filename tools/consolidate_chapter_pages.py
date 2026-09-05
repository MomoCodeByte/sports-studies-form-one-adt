#!/usr/bin/env python3
"""Consolidate Chapter 2-5 section files into one reader entry per PDF page.

The retired section HTML files are kept on disk as recoverable source backups.
Their content is copied into the first section file for that PDF page.
"""

from __future__ import annotations

from collections import OrderedDict
from copy import deepcopy
import json
from pathlib import Path
import re
import shutil

from lxml import etree
from lxml import html as lhtml


ROOT = Path(__file__).resolve().parents[1]
FIRST_PAGE = 18
LAST_PAGE = 93
BACKUP_DIR = ROOT / "backups" / "before-chapter-2-5-consolidation"
PAGE_RE = re.compile(r"^pg(\d{3})_sec\d+$")
CORRECT_RE = re.compile(
    r"window\.correctAnswers\s*=\s*JSON\.parse\('(?P<data>.*?)'\)\s*;",
    re.S,
)


def source_page(section_id: str) -> int | None:
    match = PAGE_RE.fullmatch(section_id)
    return int(match.group(1)) if match else None


def parse_document(source: str):
    return lhtml.document_fromstring(source)


def content_element(document):
    matches = document.xpath('//*[@id="content"]')
    if len(matches) != 1:
        raise RuntimeError(f"Expected one #content element, found {len(matches)}")
    return matches[0]


def extract_correct_answers(source: str) -> dict[str, object]:
    result: dict[str, object] = {}
    for match in CORRECT_RE.finditer(source):
        raw = match.group("data").replace("\\'", "'")
        values = json.loads(raw)
        if not isinstance(values, dict):
            raise RuntimeError("correctAnswers must be a JSON object")
        result.update(values)
    return result


def remap_subtree(
    roots: list,
    section_id: str,
    item_counter: int,
    rename_element_ids: bool,
) -> tuple[int, dict[str, str]]:
    elements = [element for root in roots for element in root.iter()]

    item_map: dict[str, str] = {}
    for element in elements:
        old_item = element.get("data-activity-item")
        if old_item and old_item not in item_map:
            item_counter += 1
            item_map[old_item] = f"item-{item_counter}"

    for element in elements:
        old_item = element.get("data-activity-item")
        if old_item in item_map:
            element.set("data-activity-item", item_map[old_item])
        old_value = element.get("value")
        if old_value in item_map:
            element.set("value", item_map[old_value])
        for attr in ("name", "data-question-group"):
            value = element.get(attr)
            if value and ("question" in value or attr == "data-question-group"):
                element.set(attr, f"{section_id}-{value}")

    if rename_element_ids:
        id_map: dict[str, str] = {}
        for element in elements:
            old_id = element.get("id")
            if old_id:
                id_map[old_id] = f"{section_id}-{old_id}"
        for element in elements:
            old_id = element.get("id")
            if old_id in id_map:
                element.set("id", id_map[old_id])
            for attr in ("for", "aria-labelledby", "aria-describedby"):
                value = element.get(attr)
                if value:
                    element.set(attr, " ".join(id_map.get(token, token) for token in value.split()))
            href = element.get("href")
            if href and href.startswith("#") and href[1:] in id_map:
                element.set("href", "#" + id_map[href[1:]])

    return item_counter, item_map


def remove_correct_answer_scripts(document) -> None:
    for script in list(document.xpath("//script[not(@src)]")):
        if "window.correctAnswers" in (script.text or ""):
            script.getparent().remove(script)


def insert_correct_answer_script(document, correct_answers: dict[str, object]) -> None:
    if not correct_answers:
        return
    payload = json.dumps(correct_answers, ensure_ascii=False, separators=(",", ":"))
    payload = payload.replace("\\", "\\\\").replace("'", "\\'")
    script = etree.Element("script")
    script.text = f"window.correctAnswers = JSON.parse('{payload}');"
    body = document.xpath("//body")[0]
    external_scripts = body.xpath('.//script[@src]')
    if external_scripts:
        first = external_scripts[0]
        first.getparent().insert(first.getparent().index(first), script)
    else:
        body.append(script)


def merge_group(entries: list[dict]) -> tuple[str, dict[str, str]]:
    documents: list[tuple[dict, str, object]] = []
    for entry in entries:
        source = (ROOT / entry["href"]).read_text(encoding="utf-8")
        documents.append((entry, source, parse_document(source)))

    canonical_entry, _, canonical_document = documents[0]
    canonical_content = content_element(canonical_document)
    href_map: dict[str, str] = {}
    combined_answers: dict[str, object] = {}
    item_counter = 0

    for index, (entry, source, document) in enumerate(documents):
        content = content_element(document)
        roots = [deepcopy(child) for child in content]
        item_counter, item_map = remap_subtree(
            roots,
            entry["section_id"],
            item_counter,
            rename_element_ids=index > 0,
        )
        for old_key, value in extract_correct_answers(source).items():
            if old_key not in item_map:
                raise RuntimeError(f"Missing activity item {old_key} in {entry['href']}")
            combined_answers[item_map[old_key]] = value

        if index == 0:
            for old_child in list(canonical_content):
                canonical_content.remove(old_child)
            for child in roots:
                canonical_content.append(child)
            continue

        wrapper = etree.Element("div")
        wrapper.set("data-merged-content", entry["section_id"])
        classes = [name for name in (content.get("class") or "").split() if name != "opacity-0"]
        if classes:
            wrapper.set("class", " ".join(classes))
        style = content.get("style")
        if style:
            wrapper.set("style", style)
        for child in roots:
            wrapper.append(child)
        canonical_content.append(wrapper)
        href_map[entry["href"]] = canonical_entry["href"]

    remove_correct_answer_scripts(canonical_document)
    insert_correct_answer_script(canonical_document, combined_answers)
    output = etree.tostring(
        canonical_document,
        encoding="unicode",
        method="html",
        doctype="<!DOCTYPE html>",
        pretty_print=False,
    )
    return output + "\n", href_map


def renumber_page(source: str, page_number: int, href: str) -> str:
    updated, count = re.subn(
        r'(<meta\s+name="page-section-id"\s+content=")\d+("\s*/?>)',
        rf"\g<1>{page_number}\g<2>",
        source,
        count=1,
    )
    if count != 1:
        raise RuntimeError(f"Could not renumber {href}")
    return updated


def refresh_preloader(pages: list[dict], toc: list[dict], html_updates: dict[str, str], removed: list[dict]) -> str:
    path = ROOT / "assets" / "offline-preloader.js"
    source = path.read_text(encoding="utf-8")
    match = re.search(r"var INLINE = (\{.*\});\n  var BASE_DIR", source, re.S)
    if not match:
        raise RuntimeError("Could not locate INLINE data in offline-preloader.js")
    inline = json.loads(match.group(1))
    inline["./content/pages.json"] = pages
    inline["./content/toc.json"] = toc
    for entry in removed:
        inline.pop(f'./{entry["href"]}', None)
    for entry in pages:
        inline[f'./{entry["href"]}'] = html_updates[entry["href"]]
    replacement = "var INLINE = " + json.dumps(inline, ensure_ascii=False, separators=(",", ":")) + ";\n  var BASE_DIR"
    return source[: match.start()] + replacement + source[match.end() :]


def validate(
    original_pages: list[dict],
    pages: list[dict],
    html_updates: dict[str, str],
    removed: list[dict],
) -> None:
    expected = len(original_pages) - len(removed)
    if len(pages) != expected or len(pages) != 97:
        raise RuntimeError(f"Expected 97 reader pages, found {len(pages)}")
    if len(removed) != 32:
        raise RuntimeError(f"Expected 32 retired section entries, found {len(removed)}")

    for index, entry in enumerate(pages, start=1):
        source = html_updates[entry["href"]]
        if not re.search(rf'name="page-section-id"\s+content="{index}"', source):
            raise RuntimeError(f"Bad page-section-id in {entry['href']}")
        document = parse_document(source)
        content_element(document)
        ids = document.xpath('//*[@id]/@id')
        if len(ids) != len(set(ids)):
            raise RuntimeError(f"Duplicate element IDs in {entry['href']}")
        items = document.xpath('//*[@data-activity-item]/@data-activity-item')
        if len(items) != len(set(items)):
            raise RuntimeError(f"Duplicate activity item IDs in {entry['href']}")
        for image in document.xpath("//img[@src]"):
            src = image.get("src")
            if src and not src.startswith(("data:", "http://", "https://")) and not (ROOT / src).is_file():
                raise RuntimeError(f"Missing image {src} referenced by {entry['href']}")

    canonical_by_page = {
        source_page(entry["section_id"]): html_updates[entry["href"]]
        for entry in pages
        if source_page(entry["section_id"]) in range(FIRST_PAGE, LAST_PAGE + 1)
    }
    for entry in removed:
        page = source_page(entry["section_id"])
        if f'data-section-id="{entry["section_id"]}"' not in canonical_by_page[page]:
            raise RuntimeError(f"Merged section missing: {entry['section_id']}")


def backup_files(paths: set[Path]) -> None:
    if BACKUP_DIR.exists():
        raise RuntimeError(f"Backup directory already exists: {BACKUP_DIR}")
    for path in sorted(paths):
        relative = path.relative_to(ROOT)
        destination = BACKUP_DIR / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)


def main() -> int:
    pages_path = ROOT / "content" / "pages.json"
    toc_path = ROOT / "content" / "toc.json"
    manifest_path = ROOT / "imsmanifest.xml"
    preloader_path = ROOT / "assets" / "offline-preloader.js"

    original_pages = json.loads(pages_path.read_text(encoding="utf-8"))
    toc = json.loads(toc_path.read_text(encoding="utf-8"))
    manifest = manifest_path.read_text(encoding="utf-8")

    chapter_groups: OrderedDict[int, list[dict]] = OrderedDict()
    for entry in original_pages:
        page = source_page(entry["section_id"])
        if page is not None and FIRST_PAGE <= page <= LAST_PAGE:
            chapter_groups.setdefault(page, []).append(entry)

    if set(chapter_groups) != set(range(FIRST_PAGE, LAST_PAGE + 1)):
        raise RuntimeError("Chapter 2-5 source pages are not contiguous from 18 through 93")

    merged_sources: dict[str, str] = {}
    href_map: dict[str, str] = {}
    removed: list[dict] = []
    canonical_hrefs: set[str] = set()
    for entries in chapter_groups.values():
        canonical_hrefs.add(entries[0]["href"])
        if len(entries) > 1:
            merged, mapping = merge_group(entries)
            merged_sources[entries[0]["href"]] = merged
            href_map.update(mapping)
            removed.extend(entries[1:])

    pages = [entry for entry in original_pages if entry["href"] not in href_map]
    for item in toc:
        if item.get("href") in href_map:
            item["href"] = href_map[item["href"]]

    html_updates: dict[str, str] = {}
    for index, entry in enumerate(pages, start=1):
        source = merged_sources.get(entry["href"])
        if source is None:
            source = (ROOT / entry["href"]).read_text(encoding="utf-8")
        html_updates[entry["href"]] = renumber_page(source, index, entry["href"])

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

    validate(original_pages, pages, html_updates, removed)
    preloader = refresh_preloader(pages, toc, html_updates, removed)

    backup_paths = {
        pages_path,
        toc_path,
        manifest_path,
        preloader_path,
        *(ROOT / entry["href"] for entry in original_pages),
    }
    backup_files(backup_paths)

    pages_path.write_text(json.dumps(pages, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    toc_path.write_text(json.dumps(toc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    manifest_path.write_text(manifest, encoding="utf-8", newline="\n")
    for href, source in html_updates.items():
        (ROOT / href).write_text(source, encoding="utf-8", newline="\n")
    preloader_path.write_text(preloader, encoding="utf-8", newline="\n")

    print(f"Consolidated Chapter 2-5 reader entries: {len(original_pages)} -> {len(pages)}")
    print(f"Merged and retired {len(removed)} section entries; source files remain on disk.")
    print(f"Backup: {BACKUP_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
