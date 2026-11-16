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
- The longest desktop frames: one 100 ms wait per run while SDL tries the
  missing audio device (the benchmark has none; Breeze retries at most every
  10 s on the desktop host) and one 115 ms frame where a screen first lays
  out. Before the 10 s back-off every cue retried and stalled 100–200 ms.

## Port map: raylib call sites and their replacements

Kryon pieces (claude-kryon-desktop-host-for-breeze builds them as small new
modules and sends their names and calls as it pushes):

- K1 desktop window and input: events routed by window, a sideways wheel,
  key-down and repeat state, minimize/restore/raise/always-on-top, monitor
  size and DPI scale.
- K2 desktop secondary windows: the `raylib_secondary_window` calls, each
  window with its own Cairo surface, presenter, session input, click, drag,
  right-click and keyboard grab.
- K3 SDL2 audio: sounds, streamed music, pushed PCM streams, volume, pitch,
  a mix tap, and Vorbis/Opus/WAV decoding. MP3 waits on an owner decision.
- K4 Cairo raster hooks: an asset reader for embedded assets, font
  registration from memory, and a render scale for zoom.

Already in Kryon's desktop host (`desktop_runtime`, `desktop_loop`):
`OpenDesktopSized`, `CloseDesktop`, `PollDesktop`, `BeginDesktopFrame`,
`EndDesktopFrame`, `PauseDesktop`, `DesktopViewport`, `PollPointer`,
`PollSecondaryPointer`, `DesktopWheelMove`, `DesktopInputTake`, typed
codepoints, `DesktopCursor`, `EndFrameRetained` with `DesktopFrameReusable`
and `DesktopFrameUnchanged`, `frame_snapshot`, `DesktopSetTitle`,
`DesktopSetIcon`, `DesktopWindow`, `WindowVisibleHost`, `WindowFocusedHost`,
`WindowSetVisibleHost`, `SystemClipboard*Host`, `CaptureRequested`,
`CaptureConfigured`. Time comes from `std/timer_linux`.

The Linux desktop build selects its host modules at compile time; Windows,
Android and web keep today's raylib or canvas modules under the same names.

| Breeze file | raylib use today | Linux desktop replacement |
|---|---|---|
| `src/platform/app_host.zi` | `RunRaylibAppFrame`; `SetConfigFlags`, `SetExitKey`; `GetRenderWidth/Height`; `GetMousePosition`, `IsMouseButton*` (left, right); `GetMouseWheelMoveV`; `IsKeyPressed` (Esc, Tab, Enter, Space, arrows, Back, zoom keys); `RaylibModifiers`; `SetMouseCursor`; `SetTargetFPS`; `GetTime`; `Begin/EndRetainedFrame*`; `PumpSecondaryWindows`; `LoadImageFromScreen`, `UnloadImage`; `SetTraceLogLevel`, `RaylibTraceToConsole`; `kryon/Raylib` | A Breeze desktop loop: `PollDesktop`, `BeginDesktopFrame`, `DesktopViewport`, `PollPointer`, `PollSecondaryPointer`, `DesktopWheelMove` plus K1 sideways wheel, `DesktopInputTake` keys and modifiers plus K1 key state, `DesktopCursor`, `PauseDesktop` pacing, `EndFrameRetained`, K2 pump, `CaptureConfigured` for screenshots, `trace_log` |
| `src/platform/raylib_host.zi` | `InitWindow`, `CloseWindow`, `ExportImage`, `RaylibUseIconTextures` | `OpenDesktopSized`, `CloseDesktop`; Cairo draws icons itself; PNG through Kryon `png`. The raylib module stays for Windows and Android |
| `src/platform/main_platform.zi` | `TraceLog`, `IsWindowReady`, `GetWindowHandle`, `ChangeDirectory`, `GetTime`, `RaylibTraceToFile`, `RaylibTraceRecentErrors`, `RaylibTraceClose` | `trace_log` with an `inbe.log` sink and recent-error buffer; `OpenDesktopSized` result; `DesktopWindow`; `DesktopStartBeside` or libc `chdir`; timer |
| `src/platform/raylib_text_input.zi` | `GetCharPressed`, `IsKeyPressed`, `IsKeyPressedRepeat`, `IsKeyDown`, `GetClipboardText`, `SetClipboardText` | Typed codepoints and `KeyboardSend` as `desktop_loop` does, K1 repeat state, `SystemClipboard*Host`; the module stays for Windows and Android |
| `src/platform/practice_window_host.zi` | `raylib_secondary_window`; `RestoreWindow`, `SetWindowFocused`, `ClearWindowState` | K2; K1 restore and raise |
| `src/breaks/app_breaks.zi` | `raylib_secondary_window`; `GetMouseWheelMove`, `GetMouseDelta`, `IsKeyPressed`, `IsWindowFocused`, `ClearWindowState`, `RestoreWindow`, `SetWindowFocused`, `GetCurrentMonitor`, `GetMonitorWidth/Height`, `GetTime` | K2 with per-window input; `WindowFocusedHost`; K1 restore, raise and monitor size; timer |
| `src/screens/break_overlay.zi` | `IsMouseButtonPressed`, `GetMousePosition` | The break window's K2 session pointer |
| `src/platform/desktop_tray.zi` | `IsWindowHidden`, `SetWindowState`, `ClearWindowState`, `RestoreWindow`, `MinimizeWindow`, `TraceLog`, `GetTime` | `WindowVisibleHost`, `WindowSetVisibleHost`, K1 minimize and restore, `trace_log`, timer |
| `src/app/app_launcher_pins.zi` | `SetWindowTitle` | `DesktopSetTitle` |
| `src/apps/node_app_tree.zi` | `IsWindowFocused`, `raylib_trace` | `WindowFocusedHost`, `trace_log` |
| `src/app/application_update.zi` | `IsKeyPressed`, `IsKeyDown` | K1 key state |
| `src/app/application_frame.zi` | `BeginMode2D`/`EndMode2D` (camera zoom), `BeginScissorMode`/`EndScissorMode`, `RetainedPreviousFrameTexture`, `InvalidateRaylibAssets(Under)`, `ResetRaylibGraphics` (Android), `kryon/raylib_runtime`, `raylib_trace` | K4 render scale; paint-queue clips; `frame_snapshot`; the Cairo image cache's clear; Android keeps its reset; `trace_log` |
| `src/app/app_frame_transition.zi`, `src/app/media_compression_dialog.zi` | `Texture2D` and `FrameSurface` from retained raylib targets | `frame_snapshot` images |
| `src/app/dpi_state.zi` | `IsWindowReady`, `GetWindowScaleDPI`, `RaylibSetZoom`, `kryon/Raylib` | K1 DPI scale, K4 render scale |
| `src/platform/asset_files.zi` | `SetLoadFileDataCallback`, `MemAlloc`, `MemFree`, `GetFileLength` | K4 asset reader |
| `src/app/fonts.zi` | none directly: `typeface_source` (`RegisterFontAsset`, `RegisterSystemTypeface`), which raylib implements today | K4 font registration behind the same calls |
| `src/platform/launcher_icon.zi` | `ExportImageToMemory`, `MemFree` | Kryon `png` encoder |
| `src/app/screenshots.zi` | `GetTime`, `WaitTime` | timer, `SleepMilliseconds` |
| `src/app/lumi_guide.zi`, `src/screens/habits_screen.zi` | `GetTime` | timer |
| `src/platform/trace_log.zi`, `src/app/audio_meter_host.zi` | `TraceLog` | `trace_log` on stderr and `inbe.log` |
| `raylib_trace` importers: `src/main.zi`, `src/apps/module_host.zi`, `src/apps/node_apps.zi`, `src/screens/practice_screen.zi`, `src/app/application_init.zi`, `src/app/app_launcher_apps.zi`, `src/app/device_link_session.zi`, `src/app/app_sync.zi`, `src/app/application_modals.zi` | `TraceLog` | `trace_log` |
| `src/platform/audio_runtime.zi` | raudio: `InitAudioDevice`, `IsAudioDeviceReady`, `CloseAudioDevice`, `LoadWave(FromMemory)`, `WaveFormat`, `LoadSound(FromWave)`, `Play/Stop/PauseSound`, `SetSoundVolume/Pitch`, `LoadMusicStream(FromMemory)`, `Play/Stop/Pause/ResumeMusicStream`, `UpdateMusicStream`, `SetMusicVolume`, `Attach/DetachAudioMixedProcessor` | K3 |
| `src/platform/radio_native.zi` | `LoadAudioStream`, `UpdateAudioStream`, `IsAudioStreamProcessed`, `SetAudioStreamVolume`, `SetAudioStreamBufferSizeDefault`, `drmp3dec_*`, `GetTime` | K3 pushed stream; MP3 decoder per the owner's decision; timer |
| `src/platform/voice_audio.zi` | `media_audio_raylib`, `MediaAudioUseRaylib` | K3's media-audio sink |
| `src/screens/node_app_screen.zi` | imports `kryon/raylib_runtime`, `raylib_text_input` | Drop on Linux; bundled apps draw into Breeze's own session |
| `apps/practice/practice_probe.zi` | `raylib_trace`, `kryon/Raylib`, `CaptureRequested`, `CaptureConfigured` | Another lane's untracked probe; follow its owner |
| `Makefile` | builds `libraylib.a`, `KRYON_BACKEND_RAYLIB=1`, `RAY_*` flags and checks, `AVIF_RAYLIB`, raylib `SUPPORT_*` config | Native Linux links SDL2, Cairo, Pango, fontconfig and FreeType from pkg-config; Windows keeps `WIN64_RAYLIB_A`; Android and web unchanged |

Unchanged: Android's `GetAndroidApp` and window-state calls, and the web
canvas host (`src/platform/web_window.zi`).

## Breeze's host modules

The Linux desktop build defines `DESKTOP_HOST` (compile time; no run-time
flag). Breeze reaches its host through these modules, each with a raylib
branch for the other platforms and a desktop branch:

- `src/platform/app_trace.zi`: the log (stderr or `inbe.log`, recent errors).
- `src/platform/host_clock.zi`: `HostSeconds`, `HostFrameSeconds`, `HostWait`.
- `src/platform/host_input.zi`: keys, repeats, pointer, right button, wheel
  X/Y, pointer movement, modifiers, cursor.
- `src/platform/host_window.zi`: open, size, retained pixels, PNG capture,
  render scale, close request, hidden/minimized, close. Light: no runtime.
- `src/platform/host_window_state.zi`: focus, title, tray hide/show,
  minimize, restore, monitor size.
- `src/platform/host_frame.zi`: the frame loop and picture invalidation; the
  only module that imports `kryon/raylib_runtime` or `kryon/canvas_host`.
- `src/platform/icon_png.zi`: RGBA to PNG (Ziran's encoder, every native
  host) and, on the desktop host, pictures decoded to RGBA by the raster.
- Desktop branches in `audio_runtime.zi` (Kryon's mixer, SDL sink, Opus,
  WAV, MP3, Vorbis), `radio_native.zi` (dr_mp3 push decoding from the audio
  package, mixer PCM stream), `raylib_text_input.zi` (desktop keyboard, the
  window's text per frame, clipboard) and `asset_files.zi` (`cairo_assets`).

## Per-platform checklist

Linux desktop:
- [x] Every raylib call site above ported and committed (307e3c05); the
  desktop graph generates, compiles and links with no raylib and no GLES.
- [ ] Kryon K5–K8 (with the parent coordinator): Cairo picture-cache
  invalidation; `DisposeFrameTexture` and route-fade frames;
  `ImagePreviewDecode`/`ImagePreviewRelease`; `notification_desktop`'s
  raylib `IsWindowFocused`. Until then the private link needs a throwaway
  stub file outside the repository.
- [ ] Switch the shared Makefile's native build to `DESKTOP_HOST`
  (desktop libraries from pkg-config, the audio package's MP3 and Vorbis
  archives) once the link needs no stubs.
- [x] The scripted session runs on a private Xvfb; after benchmark above.
- [ ] Delete the Linux path's raylib build rules (`RAYLIB_A` for native,
  `KRYON_BACKEND_RAYLIB`, `AVIF_RAYLIB`, raylib `SUPPORT_*` flags).
- [ ] Rename `raylib_text_input.zi` and move the key constants out of
  `raylib_host.zi` once no platform uses raylib.
- Known desktop gaps: no route fade (K6); updated pictures need a restart
  (K5); window focus for notifications (K8).

Windows, web, Android: every remaining raylib use and Kryon's replacement
is mapped in `plans/2026-11-16-breeze-raylib-other-platforms.md`. Kryon gaps
sent to the parent coordinator on 2026-11-16:
- [ ] Web W1: the browser MediaAudio provider out of `media_audio_raylib`.
- [ ] Web W2: Canvas-named clip and trace calls for `raylib_clip` and
  `raylib_trace`.
- [ ] Android A1: app ticks while paused or windowless (practices, audio,
  timers, PiP) in `android_run`.
- [ ] Android A2: a mixer sink (AAudio or OpenSL ES), or SDL2 on Android.
- [ ] Android A3: picture registration for embedded, disk and practice
  bytes, with orientation and invalidation.
- [ ] Android A4: a non-raylib `window_runtime` branch.
- [ ] Windows X1: platform-selected timer, image, video and accessibility
  modules for the desktop host, and Windows SDL2/Cairo/Pango/FreeType builds.
- [ ] Windows X2: a raylib-free picture-to-PNG path (`ImageExport`,
  `window_icon`).

## Steps

1. Kryon K5–K8, routed by the parent coordinator, pushed, then pinned here.
2. Switch the shared Linux build to the desktop host and delete its raylib
   rules (checklist above); rerun the after benchmark on that build.
3. Windows, web and Android, platform by platform, each with its raylib code
   deleted as it moves.
