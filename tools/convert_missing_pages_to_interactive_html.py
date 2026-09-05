#!/usr/bin/env python3
"""Convert the previously missing PDF pages into native, interactive ADT HTML."""

from __future__ import annotations

from dataclasses import dataclass
import html
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import unicodedata

import pdfplumber
from PIL import Image
from pypdf import PdfReader
ROOT = Path(__file__).resolve().parents[1]
PDF_PATH = ROOT / "book" / "SPORTS STUDIES FORM ONE.pdf"
PAGES = [8, 10, 11, 14, 23, 24, 26, 28, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40,
         43, 46, 48, 50, 53, 54, 56, 57, 60, 61, 62, 64, 65, 68, 70, 75, 76, 79,
         81, 87, 88, 89]
TITLE = "Sport Studies for Secondary Schools: Student's Book Form One"
ACTIVITY_RE = re.compile(
    r"^(?:(?:Activity|Exercise)\s+\d+(?:\.\d+)?|Revision exercise\s+\d+|Project(?:\s+\d+)?)\b",
    re.I,
)
QUESTION_START_RE = re.compile(
    r"^(?:\(?\d+\)?[.)]?|\(?[ivxlcdm]+\)|[a-h][.)])?\s*"
    r"(?:what|why|how|which|who|where|when|explain|describe|mention|state|list|give|"
    r"differentiate|draw|identify|outline|discuss|define|name|compare|demonstrate)\b",
    re.I,
)
LIST_RE = re.compile(r"^(?:\(?\d+\)?[.)]|\(?[ivxlcdm]+\)|[a-h][.)])\s+", re.I)


@dataclass
class Line:
    text: str
    top: float
    bottom: float
    x0: float
    x1: float
    size: float
    bold: bool
    italic: bool
    color: str
    kind: str = "body"


@dataclass
class Block:
    text: str
    top: float
    bottom: float
    kind: str
    bold: bool = False
    italic: bool = False
    color: str = "slate"
    image_path: str | None = None
    image_width: float = 100.0


class ImageTextCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.images: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "img":
            return
        values = dict(attrs)
        item_id = values.get("data-id") or ""
        alt = values.get("alt") or ""
        if item_id.startswith("pg") and alt:
            self.images.append((item_id, alt))


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKC", value)
    value = value.replace("�", "'")
    value = re.sub(r"\bT he\b", "The", value)
    value = re.sub(r"\bH ow\b", "How", value)
    value = re.sub(r"\bY ou\b", "You", value)
    value = re.sub(r"\bW hat\b", "What", value)
    return re.sub(r"[ \t]+", " ", value).strip()


def css_color(raw: object) -> str:
    text = str(raw)
    if text in {"None", "0", "(0.0, 0.0, 0.0, 1.0)"}:
        return "slate"
    if "0.85, 0.5" in text or "0.0, 1.0, 0.0, 0.0" in text:
        return "emerald"
    if "1.0, 0.0, 0.0, 0.0" in text or "0.0, 1.0, 1.0, 0.0" in text:
        return "sky"
    if "0.0, 0.0, 0.0, 0.0" in text:
        return "white"
    return "slate"


def extract_lines(page: pdfplumber.page.Page) -> list[Line]:
    results: list[Line] = []
    for raw in page.extract_text_lines(layout=True, return_chars=True):
        text = normalize_text(raw["text"])
        if not text or raw["top"] < 60 or raw["top"] > 681:
            continue
        if re.match(r"^SPORTS STUDIES FORM ONE\.indd", text, re.I):
            continue
        chars = raw.get("chars") or []
        fonts = [str(char.get("fontname", "")) for char in chars]
        sizes = [float(char.get("size", 12)) for char in chars]
        bold = sum("Bold" in font for font in fonts) >= max(1, len(fonts) / 2)
        italic = sum("Italic" in font for font in fonts) >= max(1, len(fonts) / 2)
        color = css_color(next((char.get("non_stroking_color") for char in chars), None))
        size = max(sizes) if sizes else 12.0
        kind = "body"
        if ACTIVITY_RE.match(text):
            kind = "activity"
        elif re.match(r"^(Question|Questions):?$", text, re.I):
            kind = "question_label"
        elif re.match(r"^(Figure|Table)\s+\d", text, re.I):
            kind = "caption"
        elif bold and (color != "slate" or size >= 12):
            kind = "heading"
        elif LIST_RE.match(text):
            kind = "list"
        results.append(Line(text, raw["top"], raw["bottom"], raw["x0"], raw["x1"], size, bold, italic, color, kind))
    return results


def join_text(left: str, right: str) -> str:
    if left.endswith("-") and right and right[0].islower():
        return left[:-1] + right
    return left + " " + right


def group_lines(lines: list[Line]) -> list[Block]:
    blocks: list[Block] = []
    current: Line | None = None
    for line in lines:
        if current is None:
            current = line
            continue
        gap = line.top - current.bottom
        compatible = (
            (current.kind == line.kind == "body" or current.kind == "list" and line.kind == "body")
            and gap <= 7.5
            and abs(line.x0 - current.x0) < 28
            and current.bold == line.bold
            and current.italic == line.italic
            and "  " not in current.text
            and "  " not in line.text
        )
        if compatible:
            current.text = join_text(current.text, line.text)
            current.bottom = line.bottom
            current.x1 = max(current.x1, line.x1)
        else:
            blocks.append(Block(current.text, current.top, current.bottom, current.kind, current.bold, current.italic, current.color))
            current = line
    if current is not None:
        blocks.append(Block(current.text, current.top, current.bottom, current.kind, current.bold, current.italic, current.color))
    return blocks


def extract_images(pdf_page, layout_page, page_number: int, blocks: list[Block]) -> list[Block]:
    images_by_name = {image.name.rsplit(".", 1)[0]: image for image in pdf_page.images}
    image_blocks: list[Block] = []
    image_index = 0
    for layout_image in layout_page.images:
        if layout_image.get("width", 0) < 35 or layout_image.get("height", 0) < 25:
            continue
        image_index += 1
        relative = f"images/pg{page_number:03d}_im{image_index:03d}.png"
        output = ROOT / relative
        raw_source = images_by_name.get(str(layout_image.get("name", "")))
        use_raw = False
        if raw_source is not None:
            candidate = raw_source.image
            if candidate.mode == "RGBA":
                white = Image.new("RGBA", candidate.size, "white")
                white.alpha_composite(candidate)
                candidate = white.convert("RGB")
            else:
                candidate = candidate.convert("RGB")
            sample = candidate.copy()
            sample.thumbnail((180, 180))
            pixels = list(sample.getdata())
            dark_ratio = sum(r + g + b < 75 for r, g, b in pixels) / max(1, len(pixels))
            use_raw = dark_ratio < 0.35
            if use_raw:
                candidate.save(output, "PNG", optimize=True)
        if not use_raw:
            crop_box = (layout_image["x0"], layout_image["top"], layout_image["x1"], layout_image["bottom"])
            layout_page.crop(crop_box).to_image(resolution=144).save(output, format="PNG")
        caption = next(
            (block.text for block in blocks if block.kind == "caption" and layout_image["bottom"] <= block.top <= layout_image["bottom"] + 45),
            f"Illustration from textbook page {page_number - 6}",
        )
        width_percent = max(32.0, min(92.0, float(layout_image["width"]) / 415.0 * 100.0))
        image_blocks.append(
            Block(caption, float(layout_image["top"]), float(layout_image["bottom"]), "image", image_path=relative, image_width=width_percent)
        )
    return image_blocks


def apply_page_fixes(page: int, blocks: list[Block]) -> list[Block]:
    if page != 31:
        return blocks
    fragments = (
        "Grasp the elbow",
        "Gently pull down",
        "Hold stretch for 15-30",
        "middle of the upper",
        "seconds, then repeat",
    )
    cleaned = [block for block in blocks if not any(fragment in block.text for fragment in fragments)]
    caption = next((block for block in cleaned if block.kind == "caption" and "Figure 3.1" in block.text), None)
    top = (caption.top - 0.5) if caption else 275.0
    instructions = [
        "1. Hand reaches the middle of the upper back.",
        "2. Grasp the elbow with the other hand.",
        "3. Gently pull down on elbow with the other hand.",
        "4. Hold the stretch for 15-30 seconds, then repeat the exercise by changing hands.",
    ]
    for offset, instruction in enumerate(instructions):
        cleaned.append(Block(instruction, top + offset * 0.01, top + offset * 0.01, "list"))
    return cleaned


def make_page28_html(texts: dict[str, str]) -> str:
    values = [
        "Revision exercise 2",
        "1. Which of the following is a common sports injury characterised by overstretching or tearing of ligaments?",
        "(a) Concussion", "(b) Sprained ankle", "(c) Dislocated shoulder", "(d) Hamstring strain",
        "2. What is the term for a sudden crack of a bone during physical activities?",
        "(a) Strain", "(b) Sprain", "(c) Spasm", "(d) Fracture",
        "3. Maria is a science student who enjoys playing sports. When she saw Sport Studies students playing handball, she approached them and asked if she could join them. As soon as she entered the game, she quickly received the ball and sprinted in the direction of the opposing goal, but when she dived to score, she fell down and was injured. What do you think were the reasons for Maria's fall?",
        "4. Your friend, a Social Science student, got injured in his foot while running because he was wearing unfit shoes. What kind of injury did he get, and how would you assist if it happened in your presence?",
        "5. You are playing basketball, and you feel dizziness. What steps will you take to ensure your safety and well-being?",
    ]
    ids = [data_id(28, index) for index in range(1, len(values) + 1)]
    texts.update(dict(zip(ids, values)))
    option_groups = ((2, range(3, 7), 1), (7, range(8, 12), 2))
    groups: list[str] = []
    activity_item = 0
    for question_index, option_indexes, group_number in option_groups:
        question_id = ids[question_index - 1]
        option_html: list[str] = []
        for option_index in option_indexes:
            activity_item += 1
            option_id = ids[option_index - 1]
            option_html.append(
                f'<label class="activity-option flex min-h-11 items-start gap-3 rounded-lg px-3 py-2 cursor-pointer hover:bg-white/50">'
                f'<input type="radio" name="question-group-{group_number}" value="item-{activity_item}" '
                f'data-activity-item="item-{activity_item}" class="mt-1 h-5 w-5 shrink-0 accent-amber-700" '
                f'aria-label="{html.escape(values[option_index - 1])}">'
                f'<span data-id="{option_id}">{html.escape(values[option_index - 1])}</span></label>'
            )
        groups.append(
            f'<div class="space-y-3"><p class="adt-body font-semibold" data-id="{question_id}">{html.escape(values[question_index - 1])}</p>'
            f'<fieldset class="space-y-1"><legend class="sr-only">Question {group_number} options</legend>{"".join(option_html)}</fieldset></div>'
        )
    open_answers: list[str] = []
    for question_index in (12, 13, 14):
        activity_item += 1
        question_id = ids[question_index - 1]
        label = html.escape(values[question_index - 1])
        open_answers.append(
            f'<div class="space-y-3"><p class="adt-body leading-relaxed" data-id="{question_id}">{label}</p>'
            f'<label for="activity-answer-28-{activity_item}" class="sr-only">{label}</label>'
            f'<textarea id="activity-answer-28-{activity_item}" data-activity-item="item-{activity_item}" aria-label="{label}" '
            'class="w-full min-h-32 rounded-md border border-amber-300 bg-white px-4 py-3 adt-body outline-none focus:ring-2 focus:ring-amber-500 resize-y"></textarea></div>'
        )
    correct = json.dumps({f"item-{index}": index in {2, 8} for index in range(1, 9)}, separators=(",", ":"))
    return f'''<!DOCTYPE html>
<html lang="en-US"><head><meta charset="utf-8" /><meta name="viewport" content="width=device-width, initial-scale=1" />
<title>{html.escape(TITLE)}</title><meta name="title-id" content="pg028_sec001" /><meta name="page-section-id" content="0" />
<link href="./content/tailwind_output.css" rel="stylesheet"><link href="./assets/libs/fontawesome/css/all.min.css" rel="stylesheet"><link href="./assets/fonts.css" rel="stylesheet"></head>
<body class="min-h-screen flex items-center justify-center"><main class="w-full"><div id="content" class="container mx-auto max-w-5xl px-6 py-8 opacity-0">
<section role="group" data-section-type="activity_multiple_choice" data-section-id="pg028_sec001" class="overflow-hidden rounded-[1.75rem] border border-amber-300 bg-amber-50 shadow-sm">
<div class="bg-amber-700 px-8 py-4"><h1 class="adt-h2 text-white" data-id="{ids[0]}">{html.escape(values[0])}</h1></div>
<div class="space-y-9 px-8 py-8 max-sm:px-5">{"".join(groups)}{"".join(open_answers)}</div></section></div></main>
<script>window.correctAnswers = JSON.parse('{correct}');</script>
<div class="relative z-50" id="interface-container"></div><div class="relative z-50" id="nav-container"></div>
<script src="./assets/offline-preloader.js"></script><script src="./assets/scorm.js"></script><script src="./assets/base.bundle.local.js"></script>
</body></html>'''


def data_id(page: int, index: int) -> str:
    return f"pg{page:03d}_n{index:04d}"


def text_element(block: Block, item_id: str) -> str:
    value = html.escape(block.text)
    if block.kind == "heading":
        color = "text-emerald-700" if block.color == "emerald" else "text-sky-600" if block.color == "sky" else "text-rose-500"
        return f'<h2 class="adt-h3 font-bold {color} mt-7 mb-3" data-id="{item_id}">{value}</h2>'
    if block.kind == "caption":
        return f'<p class="adt-body text-center italic text-slate-700 mt-2 mb-6" data-id="{item_id}">{value}</p>'
    if block.kind == "question_label":
        return f'<p class="adt-body font-bold text-sky-600 mt-5 mb-2" data-id="{item_id}">{value}</p>'
    if block.kind == "list":
        return f'<p class="adt-body leading-relaxed pl-6 mb-2" data-id="{item_id}">{value}</p>'
    emphasis = " font-semibold" if block.bold else " italic" if block.italic else ""
    return f'<p class="adt-body leading-relaxed mb-4{emphasis}" data-id="{item_id}">{value}</p>'


def make_html(page: int, blocks: list[Block], texts: dict[str, str]) -> str:
    if page == 28:
        return make_page28_html(texts)
    section_id = f"pg{page:03d}_sec001"
    output: list[str] = []
    text_index = 0
    image_index = 0
    activity_index = 0
    activity_item = 0
    activity_open = False
    activity_has_item = False
    activity_title = ""
    pending_question = False

    def close_activity() -> None:
        nonlocal activity_open, activity_has_item, activity_item, activity_title
        if not activity_open:
            return
        if not activity_has_item:
            activity_item += 1
            output.append(
                f'<label class="mt-5 flex items-center gap-3 rounded-lg bg-white/80 p-3 adt-body">'
                f'<input type="checkbox" data-activity-item="item-{activity_item}" class="h-5 w-5 accent-sky-600">'
                'Mark this activity as completed</label>'
            )
        output.append("</div></aside>")
        activity_open = False
        activity_has_item = False
        activity_title = ""

    for block in sorted(blocks, key=lambda item: (item.top, 0 if item.kind == "image" else 1)):
        if block.kind == "image" and block.image_path:
            image_index += 1
            image_id = f"pg{page:03d}_im{image_index:03d}"
            texts[image_id] = block.text
            output.append(
                f'<figure class="mx-auto my-6" style="max-width:{block.image_width:.1f}%">'
                f'<img data-id="{image_id}" src="{html.escape(block.image_path)}" alt="{html.escape(block.text)}" '
                'class="block h-auto w-full object-contain" style="max-width:100%;height:auto">'
                '</figure>'
            )
            continue

        if block.kind == "activity":
            close_activity()
            activity_index += 1
            text_index += 1
            item_id = data_id(page, text_index)
            texts[item_id] = block.text
            output.append(
                f'<aside role="region" aria-labelledby="{item_id}" data-section-type="activity_open_ended_answer" '
                f'data-section-id="pg{page:03d}_activity{activity_index:03d}" '
                'class="my-7 overflow-hidden rounded-xl border border-sky-300 bg-sky-50 shadow-sm">'
                '<div class="bg-sky-500 px-6 py-3 text-white">'
                f'<h2 id="{item_id}" class="adt-h3 font-bold" data-id="{item_id}">{html.escape(block.text)}</h2>'
                '</div><div class="px-6 py-5 max-sm:px-4">'
            )
            activity_open = True
            activity_title = block.text.lower()
            pending_question = False
            continue

        if activity_open and block.kind == "heading" and not re.match(r"^List\s+[AB]\b", block.text, re.I):
            close_activity()

        text_index += 1
        item_id = data_id(page, text_index)
        texts[item_id] = block.text
        output.append(text_element(block, item_id))

        if activity_open:
            if block.kind == "question_label":
                pending_question = True
            if activity_title.startswith(("exercise", "revision exercise")):
                is_prompt = pending_question or re.match(r"^\d+[.)]\s+", block.text) is not None
            else:
                is_prompt = pending_question or (
                    (QUESTION_START_RE.match(block.text) is not None or block.text.endswith("?"))
                    and block.kind in {"body", "list"}
                )
            if is_prompt and block.kind not in {"question_label", "caption"}:
                activity_item += 1
                activity_has_item = True
                pending_question = False
                label = html.escape(block.text)
                output.append(
                    f'<label for="activity-answer-{page}-{activity_item}" class="sr-only">{label}</label>'
                    f'<textarea id="activity-answer-{page}-{activity_item}" data-activity-item="item-{activity_item}" '
                    f'aria-label="{label}" class="mt-2 mb-5 w-full min-h-28 rounded-md border border-sky-300 '
                    'bg-white px-4 py-3 adt-body text-slate-900 outline-none focus:ring-2 focus:ring-sky-500 resize-y"></textarea>'
                )
    close_activity()

    body = "\n".join(output)
    return f'''<!DOCTYPE html>
<html lang="en-US">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{html.escape(TITLE)}</title>
  <meta name="title-id" content="{section_id}" />
  <meta name="page-section-id" content="0" />
  <link href="./content/tailwind_output.css" rel="stylesheet">
  <link href="./assets/libs/fontawesome/css/all.min.css" rel="stylesheet">
  <link href="./assets/fonts.css" rel="stylesheet">
</head>
<body class="min-h-screen flex items-center justify-center">
  <main class="w-full">
    <div id="content" class="container opacity-0">
      <section data-section-type="text_and_images" data-section-id="{section_id}" class="mx-auto w-full max-w-5xl bg-white px-8 py-8 text-slate-900 max-sm:px-5">
        <div aria-hidden="true" class="mb-8 h-12 w-full rounded-t-sm border-b-4 border-rose-400 bg-rose-300/80"></div>
{body}
      </section>
    </div>
  </main>
  <div class="relative z-50" id="interface-container"></div>
  <div class="relative z-50" id="nav-container"></div>
  <script src="./assets/offline-preloader.js"></script>
  <script src="./assets/scorm.js"></script>
  <script src="./assets/base.bundle.local.js"></script>
</body>
</html>
'''


def update_page_section_ids(pages: list[dict]) -> None:
    for index, entry in enumerate(pages, start=1):
        path = ROOT / entry["href"]
        source = path.read_text(encoding="utf-8")
        source, count = re.subn(
            r'(<meta\s+name="page-section-id"\s+content=")\d+("\s*/?>)',
            rf"\g<1>{index}\g<2>",
            source,
            count=1,
        )
        if count != 1:
            raise RuntimeError(f"Could not update page-section-id in {path.name}")
        path.write_text(source, encoding="utf-8", newline="\n")


def repair_image_localization(locale_files: dict[tuple[str, str], dict[str, str]]) -> None:
    for path in ROOT.glob("pg*_sec*.html"):
        collector = ImageTextCollector()
        collector.feed(path.read_text(encoding="utf-8"))
        for item_id, alt in collector.images:
            for data in locale_files.values():
                data.setdefault(item_id, alt)


def refresh_offline_preloader(root: Path, pages: list[dict]) -> None:
    path = root / "assets" / "offline-preloader.js"
    source = path.read_text(encoding="utf-8")
    match = re.search(r"var INLINE = (\{.*\});\n  var BASE_DIR", source, re.S)
    if not match:
        raise RuntimeError("Could not locate INLINE data in offline-preloader.js")
    inline = json.loads(match.group(1))
    json_resources = (
        "content/pages.json",
        "content/toc.json",
        "content/i18n/en-US/texts.json",
        "content/i18n/en-US/speech_texts.json",
        "content/i18n/en-US/audios.json",
        "content/i18n/en-KE/texts.json",
        "content/i18n/en-KE/speech_texts.json",
        "content/i18n/en-KE/audios.json",
    )
    for relative in json_resources:
        inline[f"./{relative}"] = json.loads((root / relative).read_text(encoding="utf-8"))
    for entry in pages:
        relative = entry["href"]
        inline[f"./{relative}"] = (root / relative).read_text(encoding="utf-8")
    replacement = "var INLINE = " + json.dumps(inline, ensure_ascii=False, separators=(",", ":")) + ";\n  var BASE_DIR"
    updated = source[: match.start()] + replacement + source[match.end() :]
    path.write_text(updated, encoding="utf-8", newline="\n")


def main() -> int:
    pages = json.loads((ROOT / "content" / "pages.json").read_text(encoding="utf-8"))
    locale_files: dict[tuple[str, str], dict[str, str]] = {}
    for locale in ("en-US", "en-KE"):
        for filename in ("texts.json", "speech_texts.json"):
            path = ROOT / "content" / "i18n" / locale / filename
            locale_files[(locale, filename)] = json.loads(path.read_text(encoding="utf-8"))

    base_texts = locale_files[("en-US", "texts.json")]
    for page in PAGES:
        prefix = f"pg{page:03d}_"
        for data in locale_files.values():
            for key in [key for key in data if key.startswith(prefix)]:
                del data[key]

    pdf_reader = PdfReader(PDF_PATH)
    with pdfplumber.open(PDF_PATH) as layout_pdf:
        for page in PAGES:
            lines = extract_lines(layout_pdf.pages[page - 1])
            blocks = group_lines(lines)
            blocks.extend(extract_images(pdf_reader.pages[page - 1], layout_pdf.pages[page - 1], page, blocks))
            blocks = apply_page_fixes(page, blocks)
            page_texts: dict[str, str] = {}
            output = make_html(page, blocks, page_texts)
            (ROOT / f"pg{page:03d}_sec001.html").write_text(output, encoding="utf-8", newline="\n")
            for data in locale_files.values():
                data.update(page_texts)

    repair_image_localization(locale_files)
    for (locale, filename), data in locale_files.items():
        path = ROOT / "content" / "i18n" / locale / filename
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    update_page_section_ids(pages)
    refresh_offline_preloader(ROOT, pages)
    print(f"Converted {len(PAGES)} missing pages to native interactive HTML.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
