"""Every Kryon icon Inbe draws comes from an icon sheet Inbe ships.

Kryon's ImageForIcon maps each IconType to a sheet such as icons/ui.png.
A sheet that is missing from the desktop embed or the app packages shows
"Missing image" instead of the icon, so this fails the build first."""
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
ICON_SOURCE = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "build/packages/kryon/src/ui/icon.zi"


def icon_values(source):
    block = source[source.index("IconType :: enum {"):]
    block = block[:block.index("}")]
    return {name: int(value) for name, value in re.findall(r"(Icon\w+) :: (\d+)", block)}


def icon_sheets(source):
    """The sheet ImageForIcon reads for each icon value."""
    body = source[source.index("ImageForIcon ::"):]
    sheets = {}
    values = []
    for line in body.splitlines():
        between = re.search(r"icon_type >= (\d+) && icon_type <= (\d+)", line)
        single = re.search(r"icon_type == (\d+) \{\s*$", line)
        if between:
            values = list(range(int(between.group(1)), int(between.group(2)) + 1))
        elif single:
            values = [int(single.group(1))]
        sheet = re.search(r'image\.asset_path = "(icons/[\w.-]+)"', line)
        if sheet:
            for value in values:
                sheets[value] = sheet.group(1)
        if line.startswith("}"):
            break
    return sheets


def shipped_sheets():
    """Sheets embedded in the desktop app and in the app packages."""
    makefile = (ROOT / "Makefile").read_text()
    packages = (ROOT / "scripts/prepare-package-assets.py").read_text()
    desktop = set(re.findall(r"\$\(KRYON_DIR\)/(icons/[\w.-]+\.png)", makefile))
    packaged = set(re.findall(r"build/packages/kryon/(icons/[\w.-]+\.png)", packages))
    return desktop, packaged


def used_icons(names):
    pattern = re.compile(r"\b(" + "|".join(sorted(names, key=len, reverse=True)) + r")\b")
    found = {}
    for folder in ("src", "apps"):
        for path in sorted((ROOT / folder).rglob("*.zi")):
            for number, line in enumerate(path.read_text(errors="ignore").splitlines(), 1):
                for name in pattern.findall(line):
                    found.setdefault(name, f"{path.relative_to(ROOT)}:{number}")
    return found


source = ICON_SOURCE.read_text()
values = icon_values(source)
sheets = icon_sheets(source)
desktop, packaged = shipped_sheets()
assert values and sheets and "icons/ui.png" in desktop and "icons/ui.png" in packaged, \
    "Could not read Kryon's icon sheets or Inbe's shipped assets"
failures = []
for name, place in sorted(used_icons(values).items()):
    value = values[name]
    if value == 0:
        continue
    sheet = sheets.get(value)
    if sheet is None:
        failures.append(f"{place}: {name} has no icon sheet in Kryon")
    elif sheet not in desktop or sheet not in packaged:
        failures.append(f"{place}: {name} is drawn from {sheet}, which Inbe does not ship")
if failures:
    print("\n".join(failures), file=sys.stderr)
    sys.exit(1)
print(f"Icon sheets: all {len(used_icons(values))} icons Inbe uses come from shipped sheets")
