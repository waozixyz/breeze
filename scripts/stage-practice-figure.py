#!/usr/bin/env python3
"""Stage the selected Practices figure modules for the app compiler."""
from pathlib import Path
from tempfile import NamedTemporaryFile

from practice_media import MEDIA, ROOT

source = MEDIA / "figure"
output = ROOT / "build/practice-figure"
modules = sorted(source.glob("*.zi"))
if not (source / "figure_stage.zi").is_file():
    raise SystemExit("Practice figure source is missing. Run make packages.")
output.mkdir(parents=True, exist_ok=True)
for module in modules:
    data = module.read_bytes()
    target = output / module.name
    if target.is_file() and target.read_bytes() == data:
        continue
    with NamedTemporaryFile(dir=output, delete=False) as temp:
        temp.write(data)
    Path(temp.name).replace(target)
for old in output.glob("*.zi"):
    if not (source / old.name).is_file():
        old.unlink(missing_ok=True)
