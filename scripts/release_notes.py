#!/usr/bin/env python3
"""Package Breeze's latest core changes for Lumi, F-Droid and Play.

Translations of each release live in locales/changelog/LANGUAGE.md, written
like CHANGELOG.md. They become release-notes-LANGUAGE.json beside the English
notes, and with --play CODE the F-Droid/Play notes of every listing.
Game changes belong in their package changelogs. Legacy game sections and
bullets are excluded here before any output is written.
"""
import argparse
import json
from pathlib import Path
import re


MAX_NOTES = 3
# Brands can adjoin Japanese/Chinese/Korean text without a word boundary.
# Generic game terms cover every language in locales/changelog.
GAME_NOTES = re.compile(
    r"arcade|shovey|(?:apfel)?wurm|"
    r"\b(?:games?|gaming|gameplay|hry|her|hru|spiel\w*|juegos?|jeu|jeux|"
    r"permainan|giochi|gioco|jogos?|игр\w*)\b|游戏|遊戲|ゲーム|게임",
    re.I,
)


def release_notes(changelog):
    heading = re.search(r"^## \[(\d+\.\d+\.\d+)\] - \d{4}-\d{2}-\d{2}\s*$",
                        changelog, re.M)
    if not heading:
        raise ValueError("changelog needs a numeric release")
    body = changelog[heading.end():].split("\n## [", 1)[0]
    notes = []
    game_section = None
    for line in body.splitlines():
        section = re.match(r"^(#{3,6})\s+(.+)$", line)
        if section:
            depth = len(section[1])
            if game_section is not None and depth <= game_section:
                game_section = None
            if game_section is None and GAME_NOTES.search(section[2]):
                game_section = depth
        elif line.startswith("- "):
            # Keep section ownership until the whole entry (including wrapped
            # lines) is assembled, so continuations cannot leak into core notes.
            notes.append([line[2:].strip(), game_section is not None])
        elif line.startswith("  ") and notes:
            notes[-1][0] += " " + line.strip()
    notes = [text for text, game in notes if not game and not GAME_NOTES.search(text)]
    if not notes:
        raise ValueError("release needs core Breeze changelog notes")
    return {"version": heading[1], "notes": notes[:MAX_NOTES]}


# Play listing folder of each translated language.
PLAY_LISTINGS = {"cs": "cs-CZ", "de": "de-DE", "es": "es-ES", "fr": "fr-FR", "id": "id",
                 "it": "it-IT", "ja": "ja-JP", "ko": "ko-KR", "pt": "pt-BR", "ru": "ru-RU",
                 "zh": "zh-CN"}


def translations(folder, english):
    """The notes of each language that translates the latest release."""
    result = {}
    for path in sorted(folder.glob("*.md")):
        notes = release_notes(path.read_text(encoding="utf-8"))
        if notes["version"] != english["version"]:
            continue
        if len(notes["notes"]) != len(english["notes"]):
            raise ValueError(f"{path.name} translates {len(notes['notes'])} of "
                             f"{len(english['notes'])} notes for {english['version']}")
        result[path.stem] = notes
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("changelog", type=Path)
    parser.add_argument("output", type=Path, nargs="?")
    parser.add_argument("--play", metavar="CODE", help="write Play notes for this versionCode")
    args = parser.parse_args()
    result = release_notes(args.changelog.read_text(encoding="utf-8"))
    root = args.changelog.resolve().parent
    translated = translations(root / "locales/changelog", result)
    if args.play:
        listings = {"en-US": result}
        listings.update({PLAY_LISTINGS[language]: notes for language, notes in translated.items()})
        for locale, notes in listings.items():
            listing = root / "fastlane/metadata/android" / locale / "changelogs"
            listing.mkdir(parents=True, exist_ok=True)
            text = "".join(f"- {note}\n" for note in notes["notes"])
            (listing / f"{args.play}.txt").write_text(text, encoding="utf-8")
        return
    if args.output is None:
        parser.error("an output file is required without --play")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")
    for stale in args.output.parent.glob("release-notes-*.json"):
        stale.unlink()
    for language, notes in translated.items():
        target = args.output.parent / f"release-notes-{language}.json"
        target.write_text(json.dumps(notes, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
