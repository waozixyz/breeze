"""Resolve achievement pictograms from the locked MingCute icon package."""
import json
from pathlib import Path
import re


def icon_shape(package: Path, source: str) -> str:
    if not re.fullmatch(r"mingcute_(?:regular|filled|extra)_[a-z0-9_]+", source):
        raise ValueError("invalid achievement icon source")
    module = package / "src" / (source + ".zi")
    match = re.search(r'^Shape :: (".*");$', module.read_text(), re.M)
    if not match:
        raise ValueError(f"missing icon shape in {source}")
    shape = json.loads(match[1])
    if not shape or len(shape.encode()) >= 1024 or shape[0] not in "SF":
        raise ValueError(f"achievement icon must fit the shared icon surface: {source}")
    return shape
