#!/usr/bin/env python3
"""Replay Breeze's frame prelude against retained Android raster pixels.

The actual BeginFrame block is compiled with Kryon's tree and Pixmap renderer.
An animated dock crosses each content edge; system-bar pixels must stay black
both while it crosses the edge and after its commands disappear.
"""
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "build/practice-frame-clip-test"
OUTPUT.mkdir(parents=True, exist_ok=True)
compiler = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "build/packages/ziran/build/bin/ziran"
source = (ROOT / "src/app/application_frame.zi").read_text()
start = source.index('    if cast(s32)BeginFrame(app.ui.session, Layout.KeyHash("inbe/frame"),')
end = source.index('    #if #defined(ANDROID_BUILD)', start)
prelude = source[start:end]
fixture = '''Pixels :: #import "pixmap";
Box :: #import "kryon/box";
Layout :: #import "kryon/layout";
#import "drawing_props"
#import "geometry"
#import "session"
#import "tree_draw"
#import "kryon/tree"
#import "paint_queue"
Ui :: struct { session: Session }
App :: struct { ui: Ui }
BeginViewport :: (app: *App, logical_frame: Rectangle) {
''' + prelude + '''}

WIDTH :: 48
HEIGHT :: 80
BLACK :: 0xff000000
CANVAS :: 0xfff4f8f7
pixels: [WIDTH * HEIGHT]u32;

OutsideClear :: () -> bool {
    for y: 0..HEIGHT - 1 {
        for x: 0..WIDTH - 1 {
            if (x < 6 || x >= 42 || y < 8 || y >= 64) &&
                pixels[y * WIDTH + x] != cast(u32)BLACK { return false }
        }
    }
    return true
}

#program_export
main :: () -> s32 {
    session := SessionOpen()
    if !SessionValid(session) { return 1 }
    defer { unused CloseSession(session); Pixels.PixmapCloseWorkers() }
    app := App.{.ui = Ui.{.session = session}}
    viewport := Rectangle.{6.0, 8.0, 36.0, 56.0}
    for edge: cast(s32)0..3 {
        for index: 0..pixels.count - 1 { pixels[index] = cast(u32)BLACK }
        // No whole-surface clear between frames, as in the retained app.
        for step: 0..6 {
            if !Pixels.PixmapScale(1.0, 1.0) ||
                !Pixels.PixmapResumeInto(WIDTH, HEIGHT, pixels[:], true) { return 2 }
            BeginViewport(*app, viewport)
            Box.Draw(session, Box.Props.{.bounds = viewport,
                .fill = Color.{.r = 244, .g = 248, .b = 247, .a = 255}})
            if step < 6 {
                offset := cast(float32)step * 2.0
                dock := Rectangle.{6.0, 56.0 + offset, 36.0, 8.0}
                if edge == 1 { dock = .{6.0, 8.0 - offset, 36.0, 8.0} }
                if edge == 2 { dock = .{6.0 - offset, 8.0, 8.0, 56.0} }
                if edge == 3 { dock = .{34.0 + offset, 8.0, 8.0, 56.0} }
                // Widget paint and the raw sidebar fill inherit the frame clip.
                Box.Draw(session, Box.Props.{.bounds = dock,
                    .fill = Color.{.r = 240, .g = 40, .b = 30, .a = 255}})
                PaintRoundedFill(session, -1, dock, 2.0, 4,
                    Color.{.r = 240, .g = 40, .b = 30, .a = 255})
            }
            result := EndFrameRetained(session, true)
            Pixels.PixmapEndInto()
            if cast(s32)result.status != 0 { return 3 }
            if !OutsideClear() { return 10 + edge }
        }
        // Once the dock is gone, every content pixel is clean canvas.
        for y: 8..63 {
            for x: 6..41 {
                if pixels[y * WIDTH + x] != cast(u32)CANVAS { return 20 + edge }
            }
        }
    }
    return 0
}
'''
path = OUTPUT / "practice_frame_clip.zi"
path.write_text(fixture)
env = {key: value for key, value in os.environ.items() if key not in (
    "DISPLAY", "WAYLAND_DISPLAY", "XAUTHORITY", "DBUS_SESSION_BUS_ADDRESS", "SESSION_MANAGER")}
env.update(HARMONY_DESKTOP_RECOVERY="0", YUE_DESKTOP_RECOVERY="0")
generated = OUTPUT / "c"
subprocess.run([str(compiler), "build", "--project", "--offline", "--target=c", "--define", "ANDROID_BUILD",
                "--root", str(ROOT), "--prune-stale", "-o", str(generated), str(path)],
               cwd=ROOT, env=env, check=True)
includes = [part for folder in sorted({p.parent for p in generated.rglob("*.h")} | {generated})
            for part in ("-iquote", str(folder))]
archive = compiler.resolve().parent.parent / "libziran.a"
subprocess.run([env.get("CC", "cc"), "-std=c11", "-O2", "-ffunction-sections", "-fdata-sections",
                *includes, *map(str, sorted(generated.rglob("*.c"))), str(archive),
                "-Wl,--gc-sections", "-ldl", "-lm", "-lpthread", "-o", str(OUTPUT / "test")],
               cwd=ROOT, env=env, check=True)
subprocess.run([str(OUTPUT / "test")], cwd=ROOT, env=env, check=True)
print("Retained Android practice frame: all dock edges stay within the viewport and clear after animation")
