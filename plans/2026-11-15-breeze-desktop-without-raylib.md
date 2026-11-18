# Breeze desktop without raylib

Owner, 2026-11-15: "im curiosu cna we run breez withou raylib?", then, after
hearing what it would take: "okay thats interesing i wanty ou to bencmark it
before relpanig ralyib and after fulyl eo ndkospt" (benchmark before
replacing raylib, and after, fully on desktop).

Goal: the Linux desktop build runs on Kryon's own desktop host (SDL2 window
and input, Cairo/Pango raster) with no raylib in its link or code path, and
every feature still works. Windows, web and Android keep their current hosts.
The same benchmark runs before and after.

## Benchmark method

Harness: `tests/desktop_benchmark*.zi` (Ziran), built and run by
`mk/tests-benchmark.mk`. It drives the app with the Kryon test driver
(`test_driver_client`), so the executable must be built with
`KRYON_TEST_DRIVER=1`.

```sh
build-queue -- make native KRYON_TEST_DRIVER=1
build-queue -- make desktop-benchmark BENCHMARK_LABEL=before        # 5 runs
build-queue -- make desktop-benchmark-build BENCHMARK_LABEL=before  # 5 builds
```

Conditions, identical for both hosts:

- A private Xvfb at 1280x1000x24 per run; the app's default 900x720 window.
  The desktop's display, session bus, audio servers and recovery services
  are removed from the app's environment.
- No audio device for either host: ALSA reads an empty configuration and the
  Pulse/PipeWire sockets are unreachable.
- A profile the app creates on its first start (past the audio offer), then
  seeded by SQLite: setup and guides done, no update checks, and one list of
  240 items. Every run copies it.
- `APP_PROFILE=1`: the app logs `PROFILE: sample wall_us= cpu_us=` as each
  host frame begins (`app_profile_frame_sample`, in the host-neutral
  `src/app/app_profile.zi`).

The scenario (`tests/desktop_benchmark_scenario.zi`): start up; twice through
Habits, Lumi, Practice, Apps, Lists and Diary; scroll the 240-item list down
40 wheel steps and back; open an app's Properties dialog from its options
menu and close it with Escape; start a practice, float it in its own window
for 3 s, bring it back and exit it; then 30 s idle on Habits.

Measurements, each over 5 runs, reported as median, range and spread
(half the range as a percentage of the median):

- Clean and incremental build time. Clean removes the generated C, objects,
  source-check stamp, executable and the raylib library built for it; the
  Ziran toolchain, curl, liboqs, SQLite and codecs stay built. Incremental
  touches `src/main.zi`.
- Generated C files and bytes, executable size, direct dynamic libraries
  (ELF `DT_NEEDED`), and raylib markers in the executable (rlgl's shader
  attribute names, miniaudio, dr_mp3), since the release executable has no
  symbol table.
- Time to first frame: process start to the `APP PROBE: drawing ended` line.
- Frame interval p50/p95 and CPU per frame p50/p95 during the interaction.
- Idle CPU % over 30 s, steady RSS (median of 2 Hz samples while idle) and
  peak RSS (`VmHWM`).

Caveats: on Xvfb raylib's OpenGL ES 2 runs on llvmpipe (software GL), while
Cairo draws on the CPU on any display, so these numbers compare two software
renderers and say nothing about a real GPU. The machine is shared with other
lanes' builds and tests; timings carry about 3–10% noise.

## Before (raylib host)

The checkout does not build at the moment, so the before numbers come from
existing raylib executables rather than a fresh build.

Installed build, measured 2026-11-16 12:17–12:46 (load average 13–17 on
32 CPUs): `/home/wao/.local/bin/breeze`, 88,609,512 bytes, built
2026-11-13 00:16 from 939593a1 plus that day's uncommitted changes (build ID
8247f20d57c98dacf8ab991cbdfaa0c0b842861e). It predates the per-frame samples,
so only the 120-frame reports measure its frames.

| Measurement | Median | Range | Spread |
|---|---|---|---|
| Time to first frame (ms) | 149.1 | 148.8–170 | ±7.1% |
| Frame rate while interacting, 120-frame reports (fps) | 60.5 | 60.5–60.5 | ±0% |
| App frame time, 120-frame report median (ms) | 0.83 | 0.82–0.96 | ±8.4% |
| Longest app frame while interacting (ms) | 212.3 | 47.3–333.5 | ±67.4% |
| Idle CPU over 30 s (%) | 63.75 | 60.66–66.39 | ±4.5% |
| Steady RSS, idle median (MiB) | 447.8 | 427.2–449.5 | ±2.5% |
| Peak RSS (MiB) | 447.8 | 430.4–449.5 | ±2.1% |

Idle CPU is about two thirds of one core: the raylib host keeps drawing
frames through llvmpipe while nothing changes.

| Executable | Value |
|---|---|
| Size | 84.5 MiB |
| raylib markers (rlgl shader names, miniaudio, dr_mp3) | 4 of 4 |
| Linked libraries (10) | libSDL2-2.0.so.0, libGLESv2.so.2, libssl.so.3, libcrypto.so.3, libz.so.1, libm.so.6, libatomic.so.1, libgio-2.0.so.0, libglib-2.0.so.0, libc.so.6 |

Current checkout, raylib host, measured 2026-11-16 12:55–13:08 under heavy
load from other lanes (load average 30–34 on 32 CPUs): built 12:50 by
`make native KRYON_TEST_DRIVER=1` from the working tree on 0dc9ba90 (Ziran
f9f92b46, Kryon b45cc524), 101.9 MB, build ID
784ea9795d70ff437c8c7de9f593e433dbf597f6. A copy is kept outside the
checkout so the after benchmark can run it again alternately with the new
host under the same load.

| Measurement | Median | Range | Spread |
|---|---|---|---|
| Time to first frame (ms) | 751.3 | 650.9–1928 | ±85% |
| Frame rate while interacting, 120-frame reports (fps) | 55.9 | 38–60.4 | ±20.1% |
| App frame time, 120-frame report median (ms) | 2.54 | 1.97–5.01 | ±59.8% |
| Longest app frame while interacting (ms) | 314.6 | 209.5–1095.1 | ±140.7% |
| Frame interval p50 (ms) | 16.72 | 16.68–20.01 | ±10% |
| Frame interval p95 (ms) | 33.39 | 33.35–52.38 | ±28.5% |
| CPU per frame p50 (ms) | 26.9 | 26.49–32.35 | ±10.9% |
| CPU per frame p95 (ms) | 34.79 | 33.94–42.66 | ±12.5% |
| Frames during interaction | 1297 | 1110–1334 | ±8.6% |
| Idle CPU over 30 s (%) | 62.09 | 59.55–65.02 | ±4.4% |
| Steady RSS, idle median (MiB) | 508.9 | 506.5–571.4 | ±6.4% |
| Peak RSS (MiB) | 509.2 | 506.7–570.1 | ±6.2% |

CPU per frame above the frame interval means more than one core works per
frame: llvmpipe rasterizes on its own threads.


## After: raylib host and Kryon's desktop host, same source

Measured 2026-11-16 19:18–19:44 on a private Xvfb (1280x1000x24, llvmpipe),
load average 13–24 on 32 CPUs. Both executables were built from the same
working tree on 307e3c05 with Ziran 0.6.0 (d17c7aa1), Kryon 1b290f19, the same
embedded bundles and `KRYON_TEST_DRIVER`. Each run is one copy of the
scripted session; the two builds alternated, five runs each, so both saw the
same load. The desktop host build still links a throwaway stub file for
K6–K8 (outside the repository).

| Measurement | raylib host, median (range) | desktop host, median (range) | Change |
|---|---|---|---|
| Time to first frame (ms) | 415.8 (377.4–459) | 474.3 (371.1–749.3) | +14% |
| Frame rate while interacting, 120-frame reports (fps) | 60.47 (60.44–60.48) | 60.43 (58.31–60.44) | 0% |
| App frame time, 120-frame report median (ms) | 0.92 (0.83–0.96) | 2.19 (1.83–2.50) | +138% |
| Longest app frame while interacting (ms) | 39.05 (37.43–40.79) | 101.5 (44.77–107.8) | +160% |
| Frame interval p50 (ms) | 16.68 (16.67–16.68) | 16.81 (16.79–16.86) | +1% |
| Frame interval p95 (ms) | 33.34 (33.34–33.34) | 67.06 (67.03–67.10) | +101% |
| CPU per frame p50 (ms) | 26.17 (25.21–27.09) | 2.54 (2.25–2.90) | −90% |
| CPU per frame p95 (ms) | 32.95 (31.55–34.58) | 4.30 (3.66–5.38) | −87% |
| Frames during interaction | 1336 (1330–1342) | 1191 (1188–1191) | −11% |
| Idle CPU over 30 s (%) | 61.72 (60.82–63.19) | 2.63 (1.90–3.86) | −96% |
| Steady RSS, idle median (MiB) | 494.8 (489.8–495.8) | 361.3 (327.6–381.0) | −27% |
| Peak RSS (MiB) | 494.7 (489.7–495.8) | 362.6 (329.1–380.5) | −27% |

| Executable | raylib host | desktop host |
|---|---|---|
| Size (bytes, stripped) | 100,296,744 | 99,303,400 |
| Generated C | 863 files, 432,234 lines | 873 files, 437,203 lines |
| raylib markers | 3 of 4 | 0 of 4 |
| Linked libraries | 10: SDL2, GLESv2, gio, glib, ssl, crypto, z, m, atomic, c | 15: SDL2, pangocairo, pango, cairo, fontconfig, freetype, gio, gobject, glib, ssl, crypto, z, m, atomic, c |

Build time of the same two private builds (Ziran C generation, `cc` on 8
jobs, link; embedded bundles and vendor libraries already built), alternating
two rounds, load average 18–34:

| Build | raylib host | desktop host |
|---|---|---|
| Clean (s) | 47.5, 45.6 | 51.0, 41.4 |
| No change (s) | 10.5, 8.8 | 14.0, 9.2 |

Within the noise of a shared machine, the two hosts build in the same time.

Reading the numbers:
- Xvfb has no GPU, so raylib draws through llvmpipe: about 26 ms of CPU per
  frame spread over llvmpipe's threads, and it keeps drawing at 60 fps while
  nothing changes. On a real GPU raylib's per-frame and idle CPU are far
  lower; the desktop host draws with Cairo on the CPU either way. The idle
  and memory results carry over best to real hardware: the desktop host
  reuses an unchanged frame and drops to 15 fps.
- App frame time on the desktop host includes Cairo's painting, which raylib
  hands to the GPU (llvmpipe) outside the app's frame.
- Frame interval p95 of 67 ms and fewer frames are the desktop frame clock
  pacing unchanged frames at 15 fps, not dropped frames; the 120-frame fps
  matches raylib.
- The longest desktop frames above are SDL's audio-device open waiting
  about 100 ms for a device that is not there (the benchmark has none):
  100–200 ms of wall time with 3–5 ms of CPU, right after "Audio device
  failed to initialize". Breeze tries the device again whenever a sound is
  wanted (`src/app/audio.zi` `app_audio_ensure_ready` → `audio_runtime`
  `audio_init` → Kryon `audio_sink_sdl` `AudioSinkOpen`); raylib's audio
  fails at once. The desktop branch tries again at most every 10 s, so one
  wait remains per run; Ziran's std audio (`std/audio_device.zi`, Ziran
  dd0aff64) opens the device on its own thread and removes it once Breeze
  moves to it.

With a working audio device (SDL's dummy driver for the desktop host, which
then opens it once at startup; raylib's audio is unchanged), 2026-11-16
21:55–22:07, load average 11–20, same builds, alternating 5 + 5:

| Measurement | raylib host, median (range) | desktop host, median (range) | Change |
|---|---|---|---|
| Time to first frame (ms) | 470.4 (391.3–563.5) | 667.2 (433–804.7) | +42% |
| Frame rate while interacting, 120-frame reports (fps) | 60.47 (60.47–60.48) | 60.41 (59.63–60.45) | 0% |
| App frame time, 120-frame report median (ms) | 0.79 (0.77–0.87) | 1.98 (1.72–2.22) | +151% |
| Longest app frame while interacting (ms) | 40.59 (38.05–102.2) | 46.33 (42.61–182.2) | +14% |
| Frame interval p50 (ms) | 16.67 (16.67–16.68) | 16.82 (16.79–16.83) | +1% |
| Frame interval p95 (ms) | 33.34 (33.34–33.34) | 67.06 (67.02–67.12) | +101% |
| CPU per frame p50 (ms) | 27.24 (26.45–27.49) | 2.43 (2.06–2.68) | −91% |
| CPU per frame p95 (ms) | 34.01 (32.94–34.02) | 4.74 (3.59–5.02) | −86% |
| Frames during interaction | 1337 (1335–1339) | 1192 (1190–1196) | −11% |
| Idle CPU over 30 s (%) | 63.55 (61.79–63.79) | 2.23 (1.93–2.53) | −96% |
| Steady RSS, idle median (MiB) | 521.8 (509.6–534.5) | 379.1 (329–444.2) | −27% |
| Peak RSS (MiB) | 521.8 (509.7–534.5) | 379.1 (368–444.2) | −27% |

What the longest frames then are, from a stack sampler on an unstripped
build (every one also exists on the raylib host): the first WebP picture
decoded on the frame thread (Kryon `cairo_raster` LoadPNG →
`image_decode_linux` OpenWebP, 41 ms), the first opening of an app bundle
(Ziran `ExecBundleOpen` hashing and linking, 40 ms), an icon first drawn
at a new size (`svg_shape` ShapeCoverEdges, 30 ms) and, at startup, the font
map (`pango_fc_font_map_get_config`, 33 ms). Kryon phase 5 takes the
picture, icon and font work off the first frames; the bundle hashing is
Ziran's.

## Open work

Owner, 2026-11-17: "are yo udonig this please finsh removing rayilb". Breeze
builds with no raylib on every host, on Ziran 0.7.0, Kryon 0.6.0 and
plot, entity, apps, css and game2d pinned to that Kryon. Linux and Windows
run on Kryon's SDL2 and Cairo desktop host, Android on its own-loop
`android_runtime` with Pixmap, and the browser on Kryon's canvas. Audio is
Ziran's std audio natively, with Kryon's Web Audio in the browser.

- [ ] AVIF from the linked codecs (Kryon K13): `KRYON_AVIF_LINKED` imports
  `avif/bridge/static`, which the pinned avif package does not export.
  Until then `make native` copies `libkryonavif.so` beside the binary, and
  the Linux packages must ship it. WebP already uses the linked libwebp.
- [ ] Windows text under Wine is cut off at the bottom of each line; check
  on real Windows (Kryon W1).
- [ ] Picture-in-picture: Kryon's `BeginAndroidFrame` skips paused
  activities, so a practice floating in PiP may not draw; check on the Pixel.
- [ ] Ubuntu Touch (Click) builds on the desktop host with ARM64 codecs and
  `AARCH64_DESKTOP_HOST_*`; not built yet (OpenStore workflow only).
- [ ] The browser still plays sound through Kryon's canvas audio; moving it to
  Ziran's std audio needs the MP3, Vorbis and Opus decoders built for wasm.
- [ ] Meditation music across navigation lost its check with the raylib
  audio wraps (music_navigation_test); cover it through the UI driver.
- [ ] settings-telegram-ui-test still generates with module paths, which no
  longer resolve Kryon's package modules; move it to project mode.
- [ ] Rerun the after benchmark on the shared build (on Alpha).
