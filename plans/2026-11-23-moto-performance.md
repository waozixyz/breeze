# Moto performance: open items

Measured 2026-11-23 on the USB Moto (ZE2223BQZT, armv7, Android 9) with the
`xyz.waozi.inbe.verification` debug APK, SurfaceFlinger `--latency` and NDK
simpleperf (cpu-clock, 200 Hz, call graphs, symbols from the matching
unstripped `libmain.so`). Shares are of the native app thread.

Already fixed (Kryon efeafd9c and 61963a58, Breeze 6affdbaa): the GLES
presenter falling back to software after a smaller picture upload, the
per-pixel CPU path for crops past an image edge by float rounding, decoding
glTF images no material samples, the synchronous figure loads that froze
Customize (38 s) and Workout start (17 s), and the Practice tabs scrolling
off the right edge.

## Open

- **Account snapshot every frame, several times.** `InbeManagementPump` →
  Entity `ProviderPump` runs `ProviderBackedUpPump` and
  `ProviderBackupStatusPump`, and each builds the whole `ProviderState` through
  Breeze's `InbeManagementSnapshot` (settings, sync status, node storage). That
  is 16–28% of the app thread on Habits and in a Workout. Build the state once
  per pump, or check the cheap owner and throttle conditions before it, in
  `entity/src/native_management.zi`; keep the account and backup semantics.
- **Settings cache emptied by any write.** `SettingsCacheFind` drops all 64
  entries when `storage_data_revision()` moves, and the revision follows the
  connection's total changes, so a Workout's progress drafts or a sync write
  flush every setting. The cached path also copies through 8192-byte buffers
  (`AppTextFromCString`, `AppCopyText`: 7–12%). Invalidate on settings writes
  only, and return cached values without the copy.
- **Android text via JNI each frame.** `AndroidFontWidth` and
  `AndroidFontPaint` (Kryon `pixmap_typefaces_android.zi`) look up their Java
  methods with `GetMethodID` on every call (about 7% alone) and measure and
  raster labels again each frame (14–24%). Cache the method IDs and the
  measured widths; another lane has uncommitted work in that file.
- **Window size over binder.** `AndroidNativeSurfaceSize` →
  `ANativeWindow_getHeight` queries SurfaceFlinger several times per frame
  (about 18% of wall time on the idle home). Keep the size from the window
  events (Kryon `android_native.zi`).
- **Rounded outlines on the CPU in GLES frames** (`PixmapStrokeRounded`,
  about 15% on the idle home): draw them as GPU geometry in `pixmap_gpu`.
- **Figure load time.** Off the UI thread now, but still about 10–15 s per
  model on the Moto: Ziran std PNG inflate decodes about 3 Mpx/s, mesh floats
  go through software `ScaleByPowerOfTwo`, and `AddImageTexture` copies texels
  byte by byte.
- **Scroll benchmark.** The verification profile has three habits and no
  long lists, so Habits and Lists cannot scroll; seed a profile with long
  lists before measuring scrolling fps.
