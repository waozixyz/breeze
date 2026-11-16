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

Not measured before: build times and generated C, which need a checkout
that builds; per-frame intervals and CPU, which need the per-frame samples.
The 2026-11-16 09:27 working-tree build has those samples but exits at
startup (its embedded app bundle is in a ZX format the runtime rejects), so
it cannot serve as the baseline. Measure both with the last raylib state of
the checkout once it builds, before the port's commits land.

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

## Steps

1. Get a Breeze build to benchmark. The checkout does not build right now
   while its pins move to Kryon's namespaced widget API; the Breeze pin
   sessions (breeze-entity-kryon-master, breeze-one-format-pins) own that
   repair. Benchmark the first state that builds.
2. Measure and record the before table; commit and push the plan, the
   harness and the numbers.
3. Port the Linux desktop layer file by file as K1–K4 land, following the
   map above; delete the raylib code the Linux path no longer uses. Windows,
   web and Android builds must still pass.
4. Run the same benchmark after the port and add the after table and the
   comparison here.
