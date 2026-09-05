#!/usr/bin/env python3
"""Regenerate all reachable ADT read-aloud audio with Tanzanian English Imani."""

from __future__ import annotations

import argparse
import asyncio
from collections import defaultdict
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import shutil

import edge_tts


ROOT = Path(__file__).resolve().parents[1]
VOICE = "en-TZ-ImaniNeural"
LANGUAGES = ("en-US", "en-KE")
SPEAKABLE_TAGS = {
    "div", "figcaption", "h1", "h2", "h3", "h4", "h5", "h6", "img",
    "label", "li", "p", "span", "td", "th",
}


class DataIdParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.ids: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag not in SPEAKABLE_TAGS:
            return
        attributes = dict(attrs)
        text_id = attributes.get("data-id")
        if not text_id:
            return
        if tag == "img" and (
            attributes.get("role") == "presentation" or attributes.get("aria-hidden") == "true"
        ):
            return
        self.ids.append(text_id)


def canonical_ids() -> set[str]:
    pages = json.loads((ROOT / "content/pages.json").read_text(encoding="utf-8"))
    found: set[str] = set()
    for page in pages:
        parser = DataIdParser()
        parser.feed((ROOT / page["href"]).read_text(encoding="utf-8"))
        found.update(parser.ids)
    return found


def targets_by_language() -> dict[str, dict[str, str]]:
    base_ids = canonical_ids()
    targets: dict[str, dict[str, str]] = {}
    for language in LANGUAGES:
        folder = ROOT / "content/i18n" / language
        speech = json.loads((folder / "speech_texts.json").read_text(encoding="utf-8"))
        wanted = set(base_ids)
        wanted.update(f"{text_id}_easy_read" for text_id in base_ids)
        wanted.update(key for key in speech if re.fullmatch(r"gl\d+(?:_def)?", key))
        targets[language] = {
            text_id: str(speech[text_id]).strip()
            for text_id in sorted(wanted)
            if text_id in speech and str(speech[text_id]).strip()
        }
    return targets


async def synthesize_unique(
    grouped: dict[str, list[tuple[str, str]]], staging: Path, concurrency: int
) -> None:
    semaphore = asyncio.Semaphore(concurrency)
    completed = 0
    total = len(grouped)

    async def one(text: str, destinations: list[tuple[str, str]]) -> None:
        nonlocal completed
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        master = staging / "masters" / f"{digest}.mp3"
        async with semaphore:
            error: Exception | None = None
            for attempt in range(1, 5):
                try:
                    await edge_tts.Communicate(text, VOICE).save(str(master))
                    error = None
                    break
                except Exception as exc:  # network service may occasionally throttle
                    error = exc
                    await asyncio.sleep(attempt * 1.5)
            if error is not None:
                raise RuntimeError(f"Failed to synthesize after retries: {text[:80]!r}") from error
        for language, text_id in destinations:
            destination = staging / language / f"{text_id}.mp3"
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(master, destination)
        completed += 1
        if completed % 50 == 0 or completed == total:
            print(f"synthesized {completed}/{total} unique texts", flush=True)

    await asyncio.gather(*(one(text, destinations) for text, destinations in grouped.items()))


def update_bundle(targets: dict[str, dict[str, str]], staging: Path) -> None:
    backup = ROOT / "backups/before-imani-audio"
    backup.mkdir(parents=True, exist_ok=True)
    for language, items in targets.items():
        folder = ROOT / "content/i18n" / language
        audio_folder = folder / "audio"
        backup_language = backup / language
        backup_audio = backup_language / "audio"
        backup_audio.mkdir(parents=True, exist_ok=True)
        shutil.copy2(folder / "audios.json", backup_language / "audios.json")
        mapping = json.loads((folder / "audios.json").read_text(encoding="utf-8"))
        for text_id in items:
            destination = audio_folder / f"{text_id}.mp3"
            if destination.exists():
                shutil.copy2(destination, backup_audio / destination.name)
            shutil.copy2(staging / language / destination.name, destination)
            mapping[text_id] = destination.name
        (folder / "audios.json").write_text(
            json.dumps(mapping, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Generate and install the audio files")
    parser.add_argument("--concurrency", type=int, default=8)
    args = parser.parse_args()

    targets = targets_by_language()
    grouped: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for language, items in targets.items():
        for text_id, text in items.items():
            grouped[text].append((language, text_id))
    for language, items in targets.items():
        print(f"{language}: {len(items)} reachable audio items")
    print(f"unique synthesis requests: {len(grouped)}")
    print(f"voice: {VOICE}")
    if not args.apply:
        return 0

    staging = ROOT / "tmp/imani-audio"
    resolved_staging = staging.resolve()
    if not resolved_staging.is_relative_to(ROOT.resolve()) or resolved_staging.name != "imani-audio":
        raise RuntimeError(f"Unsafe staging directory: {resolved_staging}")
    if staging.exists():
        shutil.rmtree(staging)
    (staging / "masters").mkdir(parents=True)
    asyncio.run(synthesize_unique(grouped, staging, max(1, args.concurrency)))
    update_bundle(targets, staging)
    print("Imani audio installed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
