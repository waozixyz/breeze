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


with tempfile.TemporaryDirectory() as temporary:
    root = Path(temporary)
    for name in ("kryon", "daochi-client", "ziran"):
        (root / "build/packages" / name).mkdir(parents=True)
    (root / "build/zi-check").mkdir()
    (root / "build/zi-check/native.fresh").touch()
    (root / "ziran.lock").write_text(json.dumps(dict(
        root=dict(dependencies=dict(kryon="ui", daochi_client="client")),
        packages=[dict(id="ui", name="Kryon", commit="pinned"),
                  dict(id="client", name="DaochiClient", commit="pinned")],
        toolchain=dict(commit="pinned"))))
    def git_result(command, **kwargs):
        return "pinned\n" if "rev-parse" in command else ""
    environment = dict(DISPLAY=":0", WAYLAND_DISPLAY="wayland-0",
                       XAUTHORITY="owner", DBUS_SESSION_BUS_ADDRESS="owner",
                       MAKEFLAGS="KRYON_DIR=preview")
    with patch.object(harness, "ROOT", root), patch.object(harness.subprocess,
        "check_output", side_effect=git_result), patch.dict(os.environ, environment), \
        patch.object(harness.subprocess, "run", return_value=subprocess.CompletedProcess(
            [], 0, "checked", "")) as compiler:
        harness.check_locked_sources()
        assert compiler.call_count == 1, "an incremental stamp skipped the fresh check"
        assert "screenshot-source-check" in compiler.call_args.args[0]
        assert "KRYON_DIR=build/packages/kryon" in compiler.call_args.args[0]
        assert not any(name in compiler.call_args.kwargs["env"] for name in environment)
        compiler.return_value = subprocess.CompletedProcess([], 1, "", "missing import")
        rejects(harness.check_locked_sources, "missing locked import passed preflight")
    for head, status in (("other commit\n", ""),
                         ("pinned\n", " M src/ui/scroll.zi\n")):
        def changed_git_result(command, **kwargs):
            return head if "rev-parse" in command else status
        with patch.object(harness, "ROOT", root), patch.object(harness.subprocess,
            "check_output", side_effect=changed_git_result), patch.object(harness.subprocess,
            "run") as compiler:
            rejects(harness.check_locked_sources, "wrong or dirty pin passed preflight")
            assert not compiler.called, "a wrong dependency reached the compiler"


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
print("PASS screenshot coverage and release gates: locked imports, pins, blank, dimensions, review, tampering, build, completeness and source")
