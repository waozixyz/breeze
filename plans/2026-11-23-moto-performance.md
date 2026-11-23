# Moto performance: open items

Measured 2026-11-23 on the USB Moto (ZE2223BQZT, armv7, Android 9) with the
`xyz.waozi.inbe.verification` debug APK, SurfaceFlinger `--latency` and NDK
simpleperf (cpu-clock, 200 Hz, call graphs, symbols from the matching
unstripped `libmain.so`). Shares are of the native app thread. SurfaceFlinger
keeps 127 frames per layer, so a benchmark's `fps` is only a floor; the median
gap between presented frames is the pacing figure.

Already fixed (Kryon efeafd9c, 61963a58, 7e1a37e2 and 2d7d37ca; Entity
8d30188; Breeze 6affdbaa, 1039893c and 0d101a4f): the GLES presenter falling
back to software after a smaller picture upload, the per-pixel CPU path for
crops past an image edge by float rounding, decoding glTF images no material
samples, the synchronous figure loads that froze Customize (38 s) and Workout
start (17 s), the Practice tabs scrolling off the right edge, the one-row tabs
clipping their last letters, capsule outlines sampled pixel by pixel, the
account state built several times per pump, the window size queried over binder
more than once per frame (now 1–3%), and the settings cache, which now empties
only when the settings table is written instead of on every row change.

On the `1039893c` build: GLES presenter, no software fallback; idle Practice
home 21 fps at a 52 ms median gap (was 8.7 fps, 121 ms); tab switch 19 fps,
52 ms; Workout start 19.7 fps, 52 ms with a 121 ms worst gap (was 3.1 fps with
a 17.2 s stall); Habits drag 4.1 fps, 69 ms median, 1.3 s worst; Customize (Wim
Hof controls) opens at once and the Tai Chi Customize, which froze for 37 s,
opens with a 468 ms worst gap and streams the two figure previews in without
blocking. First frame 4.0 s cold, 2.9 s warm. The one-row tabs show every
label whole.

On the idle Workout tab the settings cache stayed inside the noise:
fresh-process runs of the verification APK measured a 34.63 ms median gap
before and 34.65 ms after, and a 51.90 ms before and 51.94 ms after. The screen
takes either of those two pacing modes with both builds, so the 7–12% of the
app thread the cached read used does not set the median gap; the change still
removes its SQL and the 8192-byte copies from every cached read.

## Profile 2026-11-23: idle Practice home

The verification APK was rebuilt from master 62bf9d26
(`make android-debug ANDROID_VERIFY_INSTANCE=1 ANDROID_ABI=armeabi-v7a`,
sha256 `3adb2150…`). NDK 28.2.13676358 simpleperf (`cpu-clock`, 200 Hz, DWARF
call graphs, unstripped `libmain.so` `25084dca…` through `--symfs`) recorded
32.93 s while `SurfaceFlinger --latency` counted 600 frames in 29.89 s: 20.0
fps, 51.93 ms median, 86.7 ms p95, 121.2 ms worst. A second run measured
51.90 ms with 492 frames in 24.58 s; the 34.6 ms mode did not recur.

Per presented frame the app thread has 4.32 samples = 21.6 ms CPU/frame; the
whole process 5.74 samples = 28.7 ms CPU/frame. The 60 Hz budget is 16.7 ms.

| accumulated app-thread cost | share | ms/frame |
| --- | --- | --- |
| RasterText -> PixmapDrawText (label rasterization) | 26.74% | 5.77 |
| AndroidFontRaster inside it | 17.98% | 3.88 |
| EndAndroidFrame (present) | 15.81% | 3.41 |
| ExecHostsCall / PracticeHomeCall | 14.48% | 3.12 |
| CheckJNI GetMethodID (font paint lookups) | 13.39% | 2.89 |
| GlyphWidth / MeasureGlyphWidth | 13.21% | 2.85 |
| Entity InbeManagementPump | 3.47% | 0.75 |
| SQLite inside the pump (sqlite3_step) | 2.35% | 0.51 |

Top self symbols: FindClassMethod 6.31% (1.36 ms), pixmap_gles_Draw 5.71%
(1.23), PixmapGpuPush 4.70% (1.01), strlen 4.35% (0.94), PixmapBlend 4.03%
(0.87), memset 3.54% (0.76).

The banner sky painter is a second thread (tid 8407): 12.91% of process
samples = 3.71 ms/frame of process CPU. Its PracticeSkyPaintOver contains
practice_sky_noise_at 28.57%, `__aeabi_d2ulz` 26.73%, `__aeabi_l2d` 6.73%,
`__fixdfdi` 5.92% and practice_sky_blend 4.90%. It is not the frame thread.

Frame cadence: the app renders continuously, not from a timer.
`src/app/app_frame_pacing.zi:77` sets `idle_fps = 30`; `:78-80` lowers it to
15 on Android when `PracticeBannerWantsFrames()` is false; `:81` sets
`active_fps = 60` (the engaged list is `:56`).
`src/app/application_frame.zi:226-228` applies the decision,
`src/platform/app_host.zi:612` calls `HostSetFrameTarget`, and
`src/platform/host_frame.zi:95-103` stores it. `src/platform/host_frame.zi:115-125`
returns the rest of the 1/fps budget as the Android poll timeout (0 once the
frame has spent it); `:52-86` runs `PollAndroidHost(wait_ms)`, draws and
presents. The banner asks for frames at `src/screens/practice_banner_draw.zi:393`
while the 30 Hz tick in `src/screens/practice_banner_motion.zi:14-34` moves the
sky; `PracticeBannerWantsFrames` consumes the request at `:442-446`. The idle
Practice home is therefore deliberately held at 30 fps; a 51.9 ms frame misses
that budget and lands every third 60 Hz vsync. With a held touch (the 60 fps
active target) the same screen still measured 51.95 ms, 499 frames in 24.9 s,
so cost, not the idle target alone, sets the gap.

## Optimized-build ceiling

`make android-release` stops at the keystore check: no `PASSWORD` and no
`~/.android/kryon-release.keystore`; `droid/app/build.gradle:35-40` also
rejects `app.verificationInstance` for release, so the signed shipping APK
cannot be installed as the verification instance. The unsigned release
(`-PfDroidBuild`) still asks for the aom example utilities, which do not
compile for armv7; the `main` target was built directly with ninja in the
RelWithDebInfo tree (`droid/app/.cxx/RelWithDebInfo/6t3w315f/armeabi-v7a`).
That 34.5 MB `libmain.so` was placed in a copy of the verification APK, signed
with the matching debug key and installed with `-r`: 590 frames in 29.58 s,
51.92 ms median, 20.0 fps; app thread 2826 samples = 21.4 ms/frame. The gap
did not move. The repacked APK is still `android:debuggable`, so ART CheckJNI
stays on (`CheckJNI::GetMethodIDInternal` 13.41%, `FindClassMethod` 6.83%
self) and dominates the JNI/Java work the release compiler cannot remove. The
true shipping ceiling is unmeasured until the keystore password, or a signed
release APK, is available.

## Open

- **Path to 60 fps.** The budget is 16.7 ms and the app thread measures
  21.6 ms. The label cache (-3.4 to -3.9 ms) and width cache (-2.5 ms) bring
  it to about 15.2-15.7 ms, just under budget. Only then raise the idle
  target: `src/app/app_frame_pacing.zi:77` `idle_fps = 30` is the deliberate
  30 fps cap; target 60 for the banner-moving home, or count
  `PracticeBannerWantsFrames` as engaged at `:56`. Raising it before the
  caches changes nothing: a held touch engages the 60 fps target and the
  screen still measured 51.95 ms.
- **Labels rasterized again on every banner frame.** Measured 5.77 ms/frame
  (`PixmapDrawText` 26.74% of the app thread), 3.88 ms of it in
  `AndroidFontRaster`, which the single-entry `android_pixmap_mask_*` cache
  misses because the labels alternate. Replace that entry (Kryon
  `src/backend/pixmap_typefaces_android.zi:40-47`, lookup `:250-254`, raster
  `:243-338`) with a small LRU of rasterized runs keyed by text hash/count,
  font, face and adjusted glyph style; each entry owns its coverage buffer,
  freed by `AndroidFontForgetMask`/`AndroidFontChanged` (`:101-108`). A hit
  skips the JNI bitmap/drawText/getPixels work and only blends the kept mask.
  Expected -3.4 to -3.9 ms/frame (the blend remains). Another lane has
  uncommitted work in that file.
- **Glyph width measured through JNI every frame.** Measured 2.85 ms/frame
  (`GlyphWidth` 13.21%). `GlyphWidth` (Kryon
  `src/ui/font_metrics.zi:104-110`) calls the host for every measurement, and
  `TabBarFitFor` (`src/ui/tabs/tabs.zi:197,211`) measures each label at each
  candidate size; the bottom dock and buttons add more. Cache widths beside
  the existing `TextLineCache` pattern (`src/ui/text_layout.zi:150-213`),
  keyed by `GlyphMetricsRevision` (`font_metrics.zi:96-102`), text hash/count,
  typeface hash, font and style; the revision already invalidates on
  `GlyphMetricsChanged`. Expected -2.5 ms/frame on the Practice home and
  -3.3 ms/frame on a Habits screen that presents frames.
- **Account snapshot each pump.** The current Entity pin 5b7ea85 (`8d30188`
  builds the state once per pump) measures `InbeManagementPump` at 3.47% of
  the 21.6 ms app thread on the idle Practice home (0.75 ms/frame) and 5.85%
  on the idle Habits screen, which stops presenting frames. It is not a
  top-five cost and a throttle cannot move a 51.9 ms gap; not changed. The
  earlier 13.8% Habits figure predates the current pin.
- **Android font paint state.** `AndroidFontPaint` looks up its Java methods
  with `GetMethodID` on every call (Kryon
  `src/backend/pixmap_typefaces_android.zi:65-75` `AndroidFontMethod`, calls
  at `:186-190`, `:228-229`, `:263-290`); measured 2.89 ms/frame (CheckJNI
  `GetMethodID` 13.39%). Cache the class refs and method IDs once per process.
  This overlaps the label and width caches above, which remove most of these
  calls; do it if either cache is deferred or other text still measures
  widths.
- **Figure load time.** Off the UI thread now, but still about 10–20 s per
  model on the Moto (in the Tai Chi Customize the second card was still
  loading after 22 s): Ziran std PNG inflate decodes about 3 Mpx/s, mesh floats
  go through software `ScaleByPowerOfTwo`, and `AddImageTexture` copies texels
  byte by byte.
- **Scroll benchmark.** The verification profile has three habits and no
  long lists, so Habits and Lists cannot scroll; seed a profile with long
  lists before measuring scrolling fps.
