#!/usr/bin/env python3
"""Capture all bundled apps privately; export only a reviewed, unchanged set."""
import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import signal
import subprocess
import tempfile

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
CONFIG = Path(__file__).with_name("screenshot-scenes.json")
OUTPUT = Path(os.environ.get("SCREENSHOT_OUT_DIR", ROOT / "build/screenshots"))
IMAGES = Path(os.environ.get("SCREENSHOT_FASTLANE_IMAGES_DIR", ROOT / "fastlane/metadata/android/en-US/images"))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def source_digest():
    result = hashlib.sha256()
    paths = []
    for folder in ("src", "apps", "assets", "locales"):
        paths.extend(path for path in (ROOT / folder).rglob("*") if path.is_file())
    paths.extend(ROOT / name for name in ("ziran.toml", "ziran.lock", "CHANGELOG.md"))
    for path in sorted(paths):
        result.update(str(path.relative_to(ROOT)).encode())
        result.update(bytes.fromhex(digest(path)))
    return result.hexdigest()


def dependency_digest(root):
    result = hashlib.sha256()
    root = Path(root)
    for path in sorted((root / "src").rglob("*.zi")):
        result.update(str(path.relative_to(root)).encode())
        result.update(bytes.fromhex(digest(path)))
    return result.hexdigest()


def config():
    value = json.loads(CONFIG.read_text())
    scenes = value["scenes"]
    bundled = {name for name, app in json.loads((ROOT / "apps/versions.json").read_text())["apps"].items() if app["bundled"]}
    require({scene["app"] for scene in scenes} == bundled, "screenshot coverage does not match bundled apps")
    require(len({scene["slug"] for scene in scenes}) == len(scenes), "duplicate scene slug")
    require(sum(scene["store"] for scene in scenes) == 8, "Play requires at most eight screenshots per device type")
    return value


def check_image(path, size, expected=()):
    with Image.open(path) as image:
        require(image.format == "PNG", f"not PNG: {path}")
        require(image.size == tuple(size), f"wrong dimensions: {path}")
        require(path.stat().st_size <= 8 * 1024 * 1024, f"over 8 MB: {path}")
        rgb = image.convert("RGB")
        dominant = max(count for count, _ in rgb.getcolors(rgb.width * rgb.height))
        require(dominant < rgb.width * rgb.height * .97, f"blank UI: {path}")
    if expected:
        text = subprocess.check_output(["tesseract", str(path), "stdout", "--psm", "11"], stderr=subprocess.DEVNULL, text=True, timeout=30)
        normalized = " ".join(text.casefold().split())
        if any(phrase.casefold() not in normalized for phrase in expected):
            # Sparse-page OCR can miss a toolbar label next to icons; the
            # document layout pass reads those without changing the capture.
            text += "\n" + subprocess.check_output(["tesseract", str(path), "stdout", "--psm", "3"], stderr=subprocess.DEVNULL, text=True, timeout=30)
            normalized = " ".join(text.casefold().split())
        for phrase in expected:
            require(phrase.casefold() in normalized, f"missing rendered text {phrase!r}: {path}")
        return text
    return ""


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


def run_capture(command, env, log, timeout=45):
    # A dedicated process group contains only this capture's Xvfb and app.
    # A timeout must stop both, rather than leave the app writing afterwards.
    process = subprocess.Popen(command, cwd=ROOT, env=env, stdout=log,
                               stderr=subprocess.STDOUT, start_new_session=True)
    try:
        status = process.wait(timeout=timeout)
    except BaseException:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait(timeout=5)
        raise
    if status:
        raise subprocess.CalledProcessError(status, command)


def contact_sheet(rows, bucket, output):
    width, height = 384, 400
    sheet = Image.new("RGB", (width * 4, height * ((len(rows) + 3) // 4)), "#e5e8e0")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 15)
    for index, row in enumerate(rows):
        left, top = (index % 4) * width, (index // 4) * height
        with Image.open(output / row["file"]) as picture:
            picture.thumbnail((width - 16, height - 40))
            sheet.paste(picture, (left + (width - picture.width) // 2, top + 32))
        draw.text((left + 8, top + 8), row["slug"], font=font, fill="#263d2a")
    sheet.save(output / f"review-{bucket}.jpg", quality=95)


def capture(binary):
    binary = Path(binary).resolve()
    bundle = ROOT / "build/inbe-full.zib"
    require(binary.is_file() and os.access(binary, os.X_OK), "Run make native first")
    require(bundle.is_file(), "Run make cells first")
    require(binary.stat().st_mtime >= max(p.stat().st_mtime for p in (ROOT / "src").rglob("*.zi")), "native source is newer than the binary; rebuild")
    require(bundle.stat().st_mtime >= max(p.stat().st_mtime for p in (ROOT / "apps").rglob("*.zi")), "app source is newer than the bundle; rebuild cells")
    require(shutil.which("xvfb-run") and shutil.which("tesseract"), "Install xvfb and tesseract")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with (OUTPUT / ".capture.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        for name in ("capture.json", "review.json"):
            (OUTPUT / name).unlink(missing_ok=True)
        value = config()
        provenance = dict(binary=str(binary), binary_sha256=digest(binary), bundle_sha256=digest(bundle), source_sha256=source_digest(), config_sha256=digest(CONFIG))
        dependency = Path(os.environ.get("SCREENSHOT_KRYON_SOURCE", ROOT / "build/packages/kryon")).resolve()
        provenance.update(kryon_source=str(dependency), kryon_sha256=dependency_digest(dependency))
        rows = []
        errors = []
        for bucket in value["buckets"]:
            folder = OUTPUT / bucket["name"]
            folder.mkdir(exist_ok=True)
            bucket_rows = []
            for scene in value["scenes"]:
                path = folder / f'{scene["slug"]}.png'
                path.unlink(missing_ok=True)
                with tempfile.TemporaryDirectory(prefix="profile-", dir=OUTPUT) as profile:
                    env = dict(os.environ)
                    for name in ("DISPLAY", "WAYLAND_DISPLAY", "XAUTHORITY", "DBUS_SESSION_BUS_ADDRESS", "SESSION_MANAGER", "APP_SHOT_WINDOW", "INBE_DIARY_IMPORT", "APP_DATA_ROOT", "INBE_DATA_ROOT"):
                        env.pop(name, None)
                    env.update(INBE_SCREENSHOT_DATA_ROOT=str(Path(profile).resolve()), YUE_DESKTOP_RECOVERY="0", APP_NO_TRAY="1", SDL_VIDEODRIVER="x11", LIBGL_ALWAYS_SOFTWARE="1")
                    command = ["xvfb-run", "-a", "-n", "300", "-s", f'-screen 0 {bucket["width"]}x{bucket["height"]}x24', str(binary), "--bundle", str(bundle), "--screenshot", str(path.resolve()), "--screenshot-scene", scene["scene"], "--screenshot-width", str(bucket["width"]), "--screenshot-height", str(bucket["height"]), "--screenshot-ui-scale", str(bucket["scale"]), "--screenshot-theme", str(scene.get("theme", -1)), "--screenshot-dark", str(scene.get("dark", 0))]
                    with path.with_suffix(".log").open("w") as log:
                        run_capture(command, env, log)
                require("APP: frame rejected with status" not in path.with_suffix(".log").read_text(), f"render rejected: {path}")
                try:
                    text = check_image(path, (bucket["width"], bucket["height"]), scene["expected"])
                except ValueError as error:
                    errors.append(str(error))
                    text = str(error)
                path.with_suffix(".txt").write_text(text)
                row = dict(scene, bucket=bucket["name"], store_dir=bucket["store"], width=bucket["width"], height=bucket["height"], file=str(path.relative_to(OUTPUT)), sha256=digest(path))
                rows.append(row)
                bucket_rows.append(row)
                status = "FAIL" if text in errors else "PASS"
                print(f'{status} {bucket["name"]}/{scene["slug"]}', flush=True)
            contact_sheet(bucket_rows, bucket["name"], OUTPUT)
        require(not errors, "\n".join(errors))
        require(provenance["source_sha256"] == source_digest(), "source changed during capture; recapture")
        require(provenance["binary_sha256"] == digest(binary) and provenance["bundle_sha256"] == digest(bundle), "build changed during capture; recapture")
        require(provenance["kryon_sha256"] == dependency_digest(dependency), "Kryon changed during capture; recapture")
        write_json(OUTPUT / "capture.json", dict(provenance, captured_at=datetime.now(timezone.utc).isoformat(), rows=rows))
        print(f"Captured and checked {len(rows)} screenshots. Inspect review-*.jpg before review/export.")


def verify(output=OUTPUT, reviewed=False, current=True):
    manifest = output / "capture.json"
    value = json.loads(manifest.read_text())
    definition = config()
    expected = {(b["name"], s["slug"]) for b in definition["buckets"] for s in definition["scenes"]}
    require({(row["bucket"], row["slug"]) for row in value["rows"]} == expected and len(value["rows"]) == len(expected), "incomplete capture set")
    require(value["config_sha256"] == digest(CONFIG), "scene definitions changed; recapture")
    if current:
        require(value["source_sha256"] == source_digest(), "source changed; rebuild and recapture before Play publishing")
        require(value["binary_sha256"] == digest(value["binary"]) and value["bundle_sha256"] == digest(ROOT / "build/inbe-full.zib"), "build changed; recapture")
        require(value["kryon_sha256"] == dependency_digest(value["kryon_source"]), "Kryon changed; recapture")
    for row in value["rows"]:
        scene = next(s for s in definition["scenes"] if s["slug"] == row["slug"])
        bucket = next(b for b in definition["buckets"] if b["name"] == row["bucket"])
        require(all(row[key] == scene[key] for key in scene), "scene metadata changed")
        require((row["width"], row["height"], row["store_dir"]) == (bucket["width"], bucket["height"], bucket["store"]), "device metadata changed")
        path = output / row["file"]
        require(digest(path) == row["sha256"], f"capture changed: {path}")
        check_image(path, (row["width"], row["height"]))
    if reviewed:
        review = json.loads((output / "review.json").read_text())
        require(review["capture_sha256"] == digest(manifest) and review["reviewer"], "review does not match capture")
    return value


def review(reviewer):
    verify(current=False)
    require(reviewer.strip(), "name the visual reviewer")
    write_json(OUTPUT / "review.json", dict(capture_sha256=digest(OUTPUT / "capture.json"), reviewer=reviewer, reviewed_at=datetime.now(timezone.utc).isoformat()))
    print("Visual review recorded for the exact capture set.")


def export():
    value = verify(reviewed=True, current=False)
    IMAGES.mkdir(parents=True, exist_ok=True)
    receipt = dict(capture_sha256=digest(OUTPUT / "capture.json"), source_sha256=value["source_sha256"], files=[])
    with tempfile.TemporaryDirectory(prefix=".screenshot-export-", dir=IMAGES) as stage:
        for row in value["rows"]:
            if row["store"] and row["store_dir"]:
                relative = Path(row["store_dir"]) / f'{row["slug"]}.png'
                destination = Path(stage) / relative
                destination.parent.mkdir(exist_ok=True)
                shutil.copyfile(OUTPUT / row["file"], destination)
                receipt["files"].append(dict(file=str(relative), sha256=digest(destination), width=row["width"], height=row["height"]))
        (IMAGES / "screenshot-review.json").unlink(missing_ok=True)
        for folder in sorted({Path(item["file"]).parent for item in receipt["files"]}):
            existing = IMAGES / folder
            if existing.exists():
                shutil.rmtree(existing)
            shutil.move(str(Path(stage) / folder), existing)
    write_json(IMAGES / "screenshot-review.json", receipt)
    print("Exported 24 reviewed Play screenshots (eight per phone/tablet type).")


def store_preflight(images_root=IMAGES):
    value = verify(reviewed=True)
    require(Path(value["kryon_source"]).resolve() == (ROOT / "build/packages/kryon").resolve(), "captures used a local Kryon preview; rebuild and recapture with locked packages before Play publishing")
    receipt = json.loads((images_root / "screenshot-review.json").read_text())
    require(receipt["capture_sha256"] == digest(OUTPUT / "capture.json"), "store assets are from a different capture")
    selected = [row for row in value["rows"] if row["store"] and row["store_dir"]]
    expected = {f'{row["store_dir"]}/{row["slug"]}.png': row for row in selected}
    require(len(receipt["files"]) == len(expected) and {item["file"] for item in receipt["files"]} == set(expected), "incomplete store receipt")
    for item in receipt["files"]:
        path = images_root / item["file"]
        require(digest(path) == item["sha256"] == expected[item["file"]]["sha256"], f"unreviewed store asset: {path}")
        check_image(path, (item["width"], item["height"]))
    for folder in {Path(file).parent for file in expected}:
        actual = {str(path.relative_to(images_root)) for path in (images_root / folder).iterdir() if path.is_file()}
        require(actual == {file for file in expected if Path(file).parent == folder}, f"unexpected images in {folder}")
    print("PASS Play preflight: complete, current, visually reviewed screenshots.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    command = commands.add_parser("capture")
    command.add_argument("binary", nargs="?", default=ROOT / f"build/bin/{platform.system().lower()}/inbe-{platform.system().lower()}-{platform.machine()}")
    command = commands.add_parser("review")
    command.add_argument("--reviewer", required=True)
    for name in ("verify", "export", "preflight"):
        commands.add_parser(name)
    args = parser.parse_args()
    if args.command == "capture":
        capture(args.binary)
    elif args.command == "review":
        review(args.reviewer)
    elif args.command == "verify":
        verify()
    elif args.command == "export":
        export()
    else:
        store_preflight()


if __name__ == "__main__":
    try:
        main()
    except (ValueError, FileNotFoundError) as error:
        raise SystemExit(f"Screenshot gate blocked: {error}") from None
