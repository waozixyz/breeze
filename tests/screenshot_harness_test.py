"""Release gates reject missing, stale, blank, and unreviewed screenshots."""
import importlib.util
import json
from pathlib import Path
import tempfile
import os
import subprocess
import sys
from unittest.mock import patch

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("harness", ROOT / "scripts/screenshot-harness.py")
harness = importlib.util.module_from_spec(spec)
spec.loader.exec_module(harness)


def rejects(operation, message):
    try:
        operation()
    except (AssertionError, ValueError, FileNotFoundError):
        return
    raise AssertionError(message)


definition = harness.config()
assert len(definition["scenes"]) == 16 and len(definition["buckets"]) == 4
assert next(b for b in definition["buckets"] if b["name"] == "phone")["scale"] == 25
environment = os.environ.copy()
for name in ("DISPLAY", "WAYLAND_DISPLAY", "XAUTHORITY", "DBUS_SESSION_BUS_ADDRESS"):
    environment.pop(name, None)
with tempfile.TemporaryFile() as log:
    try:
        harness.run_capture([sys.executable, "-c", "import time; time.sleep(10)"], environment, log, timeout=.05)
    except subprocess.TimeoutExpired:
        pass
    else:
        raise AssertionError("capture deadline was ignored")
for bucket in definition["buckets"]:
    bucket.update(width=320, height=320)
with tempfile.TemporaryDirectory() as temporary:
    output = Path(temporary)
    image = output / "screen.png"
    Image.new("RGB", (320, 320), "white").save(image)
    rejects(lambda: harness.check_image(image, (320, 320)), "blank capture passed")
    picture = Image.open(image)
    ImageDraw.Draw(picture).rectangle((40, 40, 180, 180), fill="green")
    picture.save(image)
    harness.check_image(image, (320, 320))
    rejects(lambda: harness.check_image(image, (1080, 1920)), "wrong viewport passed")
    rows = [dict(s, bucket=b["name"], width=320, height=320, file="screen.png", store_dir=b["store"], sha256=harness.digest(image)) for b in definition["buckets"] for s in definition["scenes"]]
    binary = output / "binary"
    bundle = output / "build/inbe-full.zib"
    bundle.parent.mkdir()
    binary.write_bytes(b"binary")
    bundle.write_bytes(b"bundle")
    manifest = dict(rows=rows, binary=str(binary), binary_sha256=harness.digest(binary), bundle_sha256=harness.digest(bundle), config_sha256=harness.digest(harness.CONFIG), source_sha256="current", kryon_source=str(output), kryon_sha256=harness.dependency_digest(output))
    with patch.object(harness, "ROOT", output), patch.object(harness, "source_digest", return_value="current"), patch.object(harness, "config", return_value=definition):
        harness.write_json(output / "capture.json", manifest)
        harness.verify(output)
        rejects(lambda: harness.verify(output, reviewed=True), "unreviewed set passed")
        harness.write_json(output / "review.json", dict(capture_sha256=harness.digest(output / "capture.json"), reviewer="test"))
        harness.verify(output, reviewed=True)
        original = image.read_bytes()
        image.write_bytes(original + b"changed")
        rejects(lambda: harness.verify(output, reviewed=True), "modified image passed")
        image.write_bytes(original)
        binary.write_bytes(b"new build")
        rejects(lambda: harness.verify(output), "new binary passed old review")
        binary.write_bytes(b"binary")
        manifest["rows"] = rows[:-1]
        harness.write_json(output / "capture.json", manifest)
        rejects(lambda: harness.verify(output), "missing scene passed")
        manifest["rows"] = rows
        manifest["source_sha256"] = "old"
        harness.write_json(output / "capture.json", manifest)
        rejects(lambda: harness.verify(output), "stale source passed")
print("PASS screenshot coverage and release gates: blank, dimensions, review, tampering, build, completeness and source")
