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

## Open

- **Labels rasterized again on every banner frame.** `PixmapDrawText` is
  29% of the app thread on the idle home, 20% of it in `AndroidFontRaster`
  through the single-entry `android_pixmap_mask_*` cache; the live sky
  repaints about ten times a second and each repaint flushes the labels over
  the banner. Keep a small cache of rasterized runs (text, font, face, style,
  colour) in Kryon `pixmap_typefaces_android.zi` and blend the kept mask.
  Another lane has uncommitted work in that file.
- **Glyph width measured through JNI every frame.** `GlyphWidth`
  (Kryon `src/ui/font_metrics.zi`) calls the host for every measurement, and
  `TabBarFitFor` measures each label at each candidate size; the bottom dock
  and the Habits list add their own (13.9% of the Habits thread, with the Java
  method lookup about a third of it). Cache widths beside the existing
  `TextLineCache` pattern, keyed by revision, text hash, face, font and style,
  and invalidate on `GlyphMetricsChanged`.
- **Account snapshot each pump.** Entity `8d30188` builds the state once per
  pump; the pump still runs every frame through `ProviderBackedUpPump` and
  `ProviderBackupStatusPump` (13.8% of the Habits thread). Check the cheap
  owner and throttle conditions before building it, in
  `entity/src/native_management.zi`; keep the account and backup semantics.
- **Android font paint state.** `AndroidFontPaint` looks up its Java methods
  with `GetMethodID` on every call (about 7% alone); the paint reuse another
  lane is writing covers the rebuild, not the lookup.
- **Figure load time.** Off the UI thread now, but still about 10–20 s per
  model on the Moto (in the Tai Chi Customize the second card was still
  loading after 22 s): Ziran std PNG inflate decodes about 3 Mpx/s, mesh floats
  go through software `ScaleByPowerOfTwo`, and `AddImageTexture` copies texels
  byte by byte.
- **Scroll benchmark.** The verification profile has three habits and no
  long lists, so Habits and Lists cannot scroll; seed a profile with long
  lists before measuring scrolling fps.
