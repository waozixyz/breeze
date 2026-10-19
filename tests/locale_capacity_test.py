"""Every language fits the app's text index with room to grow.

Past LocaleCatalogCapacity a language loses its index and each text reads the
whole file, which made every screen lag on phones."""
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
source = (ROOT / "src/app/locale.zi").read_text()
capacity = int(re.search(r"^LocaleCatalogCapacity :: (\d+)$", source, re.M)[1])
slots = int(re.search(r"^LocaleCatalogSlots :: (\d+)$", source, re.M)[1])
failed = slots < capacity * 2
if failed:
    print(f"LocaleCatalogSlots {slots} must be at least twice LocaleCatalogCapacity {capacity}")
for path in sorted((ROOT / "locales").glob("*.txt")):
    keys = len(re.findall(r"^\[[^\]]+\]$", path.read_text(), re.M))
    # Room for a quarter more keys before the index could fill.
    if keys * 5 > capacity * 4:
        print(f"{path.name}: {keys} keys leave too little room in the {capacity}-entry text index")
        failed = True
sys.exit(1 if failed else 0)
