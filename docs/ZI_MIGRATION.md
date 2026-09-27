# Inbe Ziran migration status

Status on 2026-09-27: **the port is incomplete.** Inbe's `src/` contains no
handwritten `.c` files; replacing those files does not prove that all behavior
is restored or that every platform builds. Generated C,
third-party libraries, legacy headers, and C test harnesses are separate from
that source count.

## Current evidence

| Area | Verified | Still required |
| --- | --- | --- |
| Desktop | Full native build/link; home screenshot has visible text, icons, and full banner; private-display screenshot regression passes | Rebuild and rerun navigation after fixing discarded list records; integrated interactions and secondary windows |
| Browser | Real Wasm storage, file-picker, HTTP, WebSocket, bounded asset downloads; upstream Canvas pixel/input/reopen, text/OS, and audio lifecycle tests pass | Pin the combined Canvas backend, build the full app, and run browser smoke checks |
| Android | Four-ABI JNI checks; complete Java compilation; earlier arm64 app compilation reached link; API21 file links pass on four ABIs | Finish arm64 link after locale lookup fix; run the app with restored input, viewport, and bounded HTTPS transport |
| Windows | Focused source generation and ABI/syntax checks for platform adapters | Complete Windows build and runtime checks |
| Plan 9 | Converted entry, storage stubs, and SQLite VFS; focused behavior checks | Native libdraw/platform support and build rules; no native Plan 9 execution verified |

Inbe currently has 288 `.zi` source files. The last successful desktop build
produced `build/bin/linux/inbe-linux-x86_64` and passed the home screenshot
regression. Later list-storage and locale changes are being rebuilt. A
successful earlier build does not verify those later changes.

The first screenshot investigation identified an endless inner loop in
`practice_draw_title_crescent`. After that fix the process completed, but its
widget frame was rejected with `FrameDuplicateKey`: the desktop navigation
rail was submitted twice. Both defects are corrected and verified. The screenshot
regression now requires timely exit, no frame rejection, and visible content
beyond a mostly solid background. Actual navigation subsequently exposed a
separate Lists failure: the database loader filled local record copies,
leaving stored UUIDs and titles empty. Both list and item loaders now use
pointers into the app state; integrated navigation reverification is pending.

Upstream fixes also restore nested/transformed raylib clipping, embedded image
file callbacks, native callback comparisons, and pointer-sized borrowed string
descriptors. The string ABI regression runs source and saved IR through C/C++
on native 64-bit and real WebAssembly 32-bit targets.

A further real WebAssembly archive test exposed a compiler blocker:
`size_of` currently folds the build host's 64-bit layout into generated code.
For example, zlib receives 112 bytes for a stream that occupies 56 bytes on
Wasm32. A general Ziran fix is in progress. Four-ABI Android link checks do
not establish 32-bit runtime correctness while that defect remains.

The same audit corrected remaining Inbe allocator declarations to use
pointer-sized `usize`. Reminder and break-timer settings also had discarded
local-copy writes; they now update their app-owned records directly.

The loop audit also corrected missing progress in habit-session round rows and
in social rows without IDs.

## Platform work already exercised

- Process identity, screenshot data isolation, shutdown signals, variadic
  logging, file picker, URI handling, updater fetch/download verification,
  and secondary-window effects are authored in `.zi`.
- Private Xvfb tests exercised GTK tray lifecycle and secondary-window texture
  orientation, GL context restoration, and rejection of foreign window events.
- Updater tests cover redirects, bounds, failed downloads, SHA-256 rejection,
  atomic installation, and restart using disposable files.
- Android tests cover real JNI table dispatch, callback registration, UTF-8
  editing order, focus lifetime, timers, downloads, wake locks, and viewport
  structure layout. These are focused tests, not proof of a running APK.
- Browser hooks for background practices, extension controls, onboarding,
  guide targets, and storage were restored from disabled branches to current
  checked Ziran.

## Library boundaries

- Ziran owns the language, compiler, standard library, `.zir` representation,
  and `.zib` format. It contains no Inbe or Daochi policy.
- Kryon owns reusable UI, layout, input, and rendering. Its upstream changes
  are committed before moving Inbe's pristine submodule pointer.
- Daochi Client owns challenge/login, bearer retry, signed v6 sync,
  registration, social requests, and signed account deletion. Blocking and
  polled deletion share the same signing preparation. Its protocol tests and
  portable wire/URL tests pass with Inbe's pinned Ziran toolchain.
- Inbe owns account/device-key storage, payload construction, merging,
  lifecycle, settings, and platform transport adapters. Browser and Android
  network operations are being connected to the polled Daochi interface.

All installed database layouts and upgrade paths remain required behavior.
Do not remove data migrations as part of source conversion. Some older C test
recipes still name removed Kryon files and need migration to the maintained
Ziran/Daochi surfaces.

## Memory and display discipline

Large Make, source-check, and Android generation commands share
`build/ziran-compiler.lock` through `scripts/run-ziran.sh` and the source
checker. Heavy Make targets are serialized. This prevents overlapping builds
from multiplying compiler memory use; it does not establish that every
compiler or runtime memory issue is permanently fixed.

All graphical testing uses a private display, with inherited `DISPLAY`,
`WAYLAND_DISPLAY`, `XAUTHORITY`, and `GDK_DISPLAY` removed.

## Reproduction

```sh
PKG_CONFIG_PATH=/home/wao/.local/sdl2/lib/pkgconfig make -j1 native
make native-screenshot-test
make native-navigation-test
make no-vendor-edits
```

The screenshot test writes `build/native-screenshot-test/home.png` and
`build/native-screenshot-test/app.log`. Failed frame commits are logged rather
than being mistaken for successful screenshots.
