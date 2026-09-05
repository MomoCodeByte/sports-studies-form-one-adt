#!/usr/bin/env python3
"""Add meaningful image and table descriptions with Imani read-aloud audio."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import html
import json
from pathlib import Path
import re
import shutil

import edge_tts


ROOT = Path(__file__).resolve().parents[1]
VOICE = "en-TZ-ImaniNeural"
LANGUAGES = ("en-US", "en-KE")

IMAGE_DESCRIPTIONS = {
    "pg007_im001": "Think icon: a learner rests the chin on one hand, indicating a question to consider.",
    "pg011_im001": "Two learners play table tennis singles across a table. The girl on the far side returns the ball while the boy on the near side holds his paddle ready.",
    "pg011_im002": "Four players take positions on a tennis court for a doubles match. One player serves from the baseline while the partner and two opponents prepare across the net.",
    "pg018_im001": "Think icon: a learner rests the chin on one hand, indicating a question to consider.",
    "pg023_im001": "A side view of an ankle shows a strained Achilles tendon. A circular close-up shows torn tendon fibres above the heel.",
    "pg023_im002": "A forearm has a red, open skin cut with swelling around the injured area.",
    "pg023_im003": "An elbow and forearm have a scraped abrasion, bruising, and reddened skin.",
    "pg024_im001": "A person pinches the nostrils while holding cotton wool at the nose to help stop a nosebleed.",
    "pg026_im001": "A bandaged lower leg and ankle rest on a pillow in an elevated position to help reduce swelling.",
    "pg029_im001": "Think icon: a learner rests the chin on one hand, indicating a question to consider.",
    "pg031_im001": "A learner stretches the triceps by bending one arm behind the head and using the other hand to press the elbow gently downward.",
    "pg034_im001": "Two stages of a sit-up: the learner lies with knees bent and arms crossed, then raises the upper body to a seated position.",
    "pg034_im002": "Two stages of a crunch: the learner lies with knees bent and hands behind the head, then lifts the shoulders and upper back slightly from the mat.",
    "pg035_im001": "Three stages of a push-up show a straight-body plank, lowering the chest by bending the elbows, and pushing back to the starting position. Arrows show the downward and upward movement.",
    "pg035_im002": "Five stages of a burpee show standing, squatting with hands on the floor, extending the legs into a plank, returning to a squat, and standing upright. Arrows show the direction of movement.",
    "pg036_im001": "A forward-lunge sequence shows the learner stepping one leg forward, lowering the rear knee toward the floor while keeping the torso upright, and returning to stand before changing legs.",
    "pg037_im001": "A learner performs a standing quadriceps stretch by holding a wall for balance and pulling one foot toward the buttocks while keeping the knees close together.",
    "pg038_im001": "A learner sits with both legs spread wide and reaches forward to hold one foot during a seated side-straddle stretch.",
    "pg039_im001": "Two knees-to-chest stretches: the first pulls both knees toward the chest, and the second pulls one knee in while the other leg remains straight on the mat.",
    "pg043_im001": "The three-hop jump test is shown with three numbered curved paths from a take-off line. The learner makes three consecutive forward jumps and lands after the third jump, where the total distance is measured.",
    "pg047_im004": "Think icon: a learner rests the chin on one hand, indicating a question to consider.",
    "pg048_im001": "A top-view diagram of a standard football pitch shows the touchlines, goal lines, halfway line, centre circle, penalty areas, goal areas, penalty spots, corner arcs, and goals. Dimension arrows indicate a length of 90 to 120 metres, a width of 45 to 90 metres, penalty areas extending 16.5 metres, goal areas extending 5.5 metres, penalty spots 11 metres from the goal line, centre-circle and penalty-arc radii of 9.15 metres, and goals 7.3 metres wide by 2.4 metres high.",
    "pg048_im002": "Basic football clothing and footwear: a long-sleeved blue jersey, orange shorts, and a studded football boot.",
    "pg053_im001": "A football player leans the upper body backward with arms out for balance as the ball drops toward the chest for chest control. An arrow shows the ball moving down and forward.",
    "pg054_im001": "A football player stands under a descending ball and watches it closely, preparing to control it with the forehead.",
    "pg056_im001": "A football player performs an instep pass. The non-kicking foot is planted beside the ball while the kicking leg swings forward to strike the ball with the laced upper part of the shoe.",
    "pg056_im002": "Close-up of an instep pass showing the laced upper part of the kicking shoe contacting the centre of the football while the supporting foot is beside it.",
    "pg057_im001": "A football player executes a heel pass by placing one foot beyond the ball and using the heel of the other foot to send the ball backward.",
    "pg060_im001": "A defender performs a sliding tackle and reaches the ball with an extended foot while the opposing player jumps over the challenge.",
    "pg061_im001": "A goalkeeper dives horizontally across the goal and reaches both gloved hands toward a ball travelling near the upper side of the goal.",
    "pg061_im002": "A goalkeeper dives low inside the goal, bends the knees, and secures the ball with both gloved hands against the body.",
    "pg066_im001": "Think icon: a learner rests the chin on one hand, indicating a question to consider.",
    "pg068_im001": "Top view of an oval 400-metre running track with several marked lanes. Direction arrows show counter-clockwise running around two straights and two bends, and coloured sections mark different starting positions.",
    "pg070_im001": "Close-up of a sprinter's legs in the set position. Both feet press against the starting blocks, the rear knee is raised, and the hips are higher than the shoulders.",
    "pg070_im002": "A sprinter demonstrates the full set position with feet braced in the starting blocks, fingertips on the track behind the start line, arms straight, hips raised, and eyes looking down.",
    "pg076_im001": "Top view of a 400-metre track showing staggered starting marks and the coloured acceleration and baton-exchange zones used in a four-by-100-metre relay. Arrows show the running direction around the track.",
    "pg079_im001": "Top view of a 400-metre track showing the staggered starts and marked baton-exchange zones for a four-by-400-metre relay. Arrows show the running direction around the oval track.",
    "pg087_im001": "Six runners use a standing start in separate curved lanes. Each runner leans forward with one foot near the start line and the opposite arm ready to drive forward.",
    "pg087_im002": "Six runners accelerate from a standing start on a curved track, leaning forward and driving their arms as they begin an 800-metre race.",
}

TABLE_DESCRIPTIONS = {
    "pg005_tb001": "Publishing team roles and names: writer, editors, designer, illustrator, and coordinator.",
    "pg095_tb001": "Glossary terms and their definitions for key words used in the book.",
}


def backup_files() -> None:
    backup = ROOT / "backups/before-visual-accessibility"
    files = [
        ROOT / "pg005_sec001.html",
        ROOT / "pg007_sec001.html",
        ROOT / "pg018_sec001.html",
        ROOT / "pg023_sec001.html",
        ROOT / "pg024_sec001.html",
        ROOT / "pg026_sec001.html",
        ROOT / "pg029_sec001.html",
        ROOT / "pg031_sec001.html",
        ROOT / "pg034_sec001.html",
        ROOT / "pg035_sec001.html",
        ROOT / "pg036_sec001.html",
        ROOT / "pg037_sec001.html",
        ROOT / "pg038_sec001.html",
        ROOT / "pg039_sec001.html",
        ROOT / "pg043_sec001.html",
        ROOT / "pg047_sec001.html",
        ROOT / "pg048_sec001.html",
        ROOT / "pg053_sec001.html",
        ROOT / "pg054_sec001.html",
        ROOT / "pg056_sec001.html",
        ROOT / "pg057_sec001.html",
        ROOT / "pg060_sec001.html",
        ROOT / "pg061_sec001.html",
        ROOT / "pg066_sec001.html",
        ROOT / "pg068_sec001.html",
        ROOT / "pg070_sec001.html",
        ROOT / "pg076_sec001.html",
        ROOT / "pg079_sec001.html",
        ROOT / "pg087_sec001.html",
        ROOT / "pg095_sec001.html",
        ROOT / "assets/offline-preloader.js",
    ]
    for language in LANGUAGES:
        locale = ROOT / "content/i18n" / language
        files.extend(locale / name for name in ("texts.json", "speech_texts.json", "audios.json"))
    for source in files:
        relative = source.relative_to(ROOT)
        destination = backup / relative
        if destination.exists():
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


def update_html() -> None:
    pages = json.loads((ROOT / "content/pages.json").read_text(encoding="utf-8"))
    image_tag = re.compile(r"<img\b[^>]*>", re.I)

    def improve_tag(match: re.Match[str]) -> str:
        tag = match.group(0)
        id_match = re.search(r'\bdata-id="([^"]+)"', tag)
        if not id_match or id_match.group(1) not in IMAGE_DESCRIPTIONS:
            return tag
        description = html.escape(IMAGE_DESCRIPTIONS[id_match.group(1)], quote=True)
        if re.search(r'\balt="[^"]*"', tag):
            tag = re.sub(r'\balt="[^"]*"', f'alt="{description}"', tag, count=1)
        else:
            tag = tag[:-1] + f' alt="{description}">'
        tag = re.sub(r'\s+role="presentation"', "", tag)
        tag = re.sub(r'\s+aria-hidden="true"', "", tag)
        return tag

    for page in pages:
        path = ROOT / page["href"]
        source = path.read_text(encoding="utf-8")
        source = re.sub(
            r"\s*<img\b[^>]*\bdata-id=\"pg007_im060\"[^>]*>\s*",
            "\n",
            source,
            count=1,
        )
        source = re.sub(
            r"\s*<div class=\"pt-2\">\s*<img\b[^>]*\bdata-id=\"pg047_im001\"[^>]*>\s*</div>",
            "",
            source,
            count=1,
        )
        source = image_tag.sub(improve_tag, source)
        if path.name == "pg005_sec001.html" and "pg005_tb001" not in source:
            source = source.replace(
                '<table class="w-full border-separate border-spacing-y-4">',
                '<table class="w-full border-separate border-spacing-y-4" aria-describedby="pg005_tb001_desc">\n'
                '      <caption class="sr-only"><span id="pg005_tb001_desc" data-id="pg005_tb001">'
                + TABLE_DESCRIPTIONS["pg005_tb001"]
                + "</span></caption>",
                1,
            )
        if path.name == "pg095_sec001.html" and "pg095_tb001" not in source:
            source = source.replace(
                '<table class="w-full border-separate border-spacing-y-4 max-sm:border-separate max-sm:border-spacing-y-3">\n'
                '        <caption class="sr-only">Glossary terms and definitions</caption>',
                '<table class="w-full border-separate border-spacing-y-4 max-sm:border-separate max-sm:border-spacing-y-3" aria-describedby="pg095_tb001_desc">\n'
                '        <caption class="sr-only"><span id="pg095_tb001_desc" data-id="pg095_tb001">'
                + TABLE_DESCRIPTIONS["pg095_tb001"]
                + "</span></caption>",
                1,
            )
        path.write_text(source, encoding="utf-8", newline="\n")


def update_locale_json() -> None:
    descriptions = IMAGE_DESCRIPTIONS | TABLE_DESCRIPTIONS
    for language in LANGUAGES:
        folder = ROOT / "content/i18n" / language
        for filename in ("texts.json", "speech_texts.json"):
            path = folder / filename
            data = json.loads(path.read_text(encoding="utf-8"))
            data.update(descriptions)
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        path = folder / "audios.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data.update({text_id: f"{text_id}.mp3" for text_id in descriptions})
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


async def synthesize_audio(concurrency: int) -> Path:
    descriptions = IMAGE_DESCRIPTIONS | TABLE_DESCRIPTIONS
    grouped: dict[str, list[str]] = {}
    for text_id, description in descriptions.items():
        grouped.setdefault(description, []).append(text_id)
    staging = ROOT / "tmp/accessibility-audio"
    if staging.exists():
        resolved = staging.resolve()
        if not resolved.is_relative_to(ROOT.resolve()) or resolved.name != "accessibility-audio":
            raise RuntimeError(f"Unsafe staging path: {resolved}")
        shutil.rmtree(staging)
    masters = staging / "masters"
    masters.mkdir(parents=True)
    semaphore = asyncio.Semaphore(max(1, concurrency))

    async def one(description: str, text_ids: list[str]) -> None:
        master = masters / f"{hashlib.sha256(description.encode('utf-8')).hexdigest()}.mp3"
        async with semaphore:
            error: Exception | None = None
            for attempt in range(1, 5):
                try:
                    await edge_tts.Communicate(description, VOICE).save(str(master))
                    error = None
                    break
                except Exception as exc:
                    error = exc
                    await asyncio.sleep(attempt * 1.5)
            if error is not None:
                raise RuntimeError(f"Could not synthesize {text_ids[0]}") from error
        for text_id in text_ids:
            shutil.copy2(master, staging / f"{text_id}.mp3")

    await asyncio.gather(*(one(description, ids) for description, ids in grouped.items()))
    return staging


def install_audio(staging: Path) -> None:
    descriptions = IMAGE_DESCRIPTIONS | TABLE_DESCRIPTIONS
    backup = ROOT / "backups/before-visual-accessibility"
    for language in LANGUAGES:
        audio_folder = ROOT / "content/i18n" / language / "audio"
        backup_audio = backup / "content/i18n" / language / "audio"
        backup_audio.mkdir(parents=True, exist_ok=True)
        for text_id in descriptions:
            destination = audio_folder / f"{text_id}.mp3"
            old_copy = backup_audio / destination.name
            if destination.exists() and not old_copy.exists():
                shutil.copy2(destination, old_copy)
            shutil.copy2(staging / destination.name, destination)


def refresh_offline_data() -> None:
    from convert_missing_pages_to_interactive_html import refresh_offline_preloader

    pages = json.loads((ROOT / "content/pages.json").read_text(encoding="utf-8"))
    refresh_offline_preloader(ROOT, pages)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--concurrency", type=int, default=8)
    args = parser.parse_args()
    descriptions = IMAGE_DESCRIPTIONS | TABLE_DESCRIPTIONS
    print(f"image descriptions: {len(IMAGE_DESCRIPTIONS)}")
    print(f"table descriptions: {len(TABLE_DESCRIPTIONS)}")
    print(f"voice: {VOICE}")
    if not args.apply:
        return 0
    backup_files()
    staging = asyncio.run(synthesize_audio(args.concurrency))
    update_html()
    update_locale_json()
    install_audio(staging)
    refresh_offline_data()
    print(f"Installed {len(descriptions)} accessible descriptions in {len(LANGUAGES)} locales.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
