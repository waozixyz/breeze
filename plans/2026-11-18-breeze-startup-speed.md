# Breeze startup speed

Owner, 2026-11-18: "can you optimze all things that are lslow". Measured on
the Pixel 4a with the arm64 debug APK and NDK simpleperf. The app's own code
builds at -O2 there as in release; only libwebp is unoptimized in debug. A
start spends about 1.9 s opening the root package before its first frame,
then about 3 s drawing that frame.

## Open work

- [ ] Asset digests hash one byte at a time (Ziran). `AppsOpenPackage` →
  `ZxExecRead` → `AssetsDigest` feeds every asset byte through `ShaByte`,
  about 40 MB/s. The root package is 75 MB because it nests the apps
  (`cells/practices.zx` 36.6 MB, `assets/apps/bundled/library.zx` 18.3 MB),
  and the preload hashes each nested app again when it opens. Ziran should
  hash whole blocks, or use the hasher in `cmd/zir/zir_sha256.c`.
- [ ] Android native cache misses (Ziran). Breeze points
  `ZIRAN_NATIVE_CACHE` at `cache/ziran-native`. Entries are stored, but every
  start rejects and rewrites them, so compiling apps
  (`NativeBundleSlotCode` under `AppsFeatureFinish` and
  `AchievementCatalogsLoad`) stays in the first frames. Linux hits the same
  cache on its second start.
- [ ] Verify Kryon's cache-folder setup in an installed app after removing
  Breeze's duplicate `AndroidNativeCachePrepare` helper.
- [ ] Practice banners are 2048×1024 WebP for a card a few hundred pixels
  tall: about 760 ms each in the debug build. Decode at the drawn size
  (Kryon's Pixmap) or ship smaller banners.
- [ ] Measure the updated gplay debug build on the USB development Moto,
  including true native first paint and cache files across process restarts.
  Debug picture-load probes now exclude the deferred decode; they cannot
  substitute for native first-frame timing.

## Integration follow-up

- Breeze now relies on Kryon's Android native-cache setup. The pinned
  `android_runtime` calls it before the application's main function, so the
  duplicate 512-byte app helper and its call were removed. The local startup
  contract passed both normal and test-driver variants (command
  `8ab7215d28d60d8d13dcd698d707cc74f353`). Full Android validation and an
  installed-device cache-reuse measurement remain pending.
- The prior Android debug CMake output has no optimization flag for
  `kryonwebp`, `webpdecode`, `webpdspdecode` or `webputilsdecode`. The app now
  compiles all four with `-O2` in Debug, matching its host while retaining
  symbols. Release flags stay as configured. Verify the regenerated flags,
  Android build and actual first-paint timing before claiming a speedup.

- Local desktop baseline: three private-Xvfb runs with the previous dependency
  pins measured a median 404.2 ms to first frame (403.0–421.3 ms), 59.7 fps
  during interaction, and 397.1 MiB steady RSS. Results are under ignored
  `build/desktop-benchmark/startup-before/`. These are Linux measurements,
  not phone startup results.
- A desktop integration regression was identified while validating the port:
  host state/actions still looked up `SDL_GL_GetCurrentWindow`, which is null
  on the Cairo host. All three paths now use Kryon's owned desktop window.
  Lumi/Appearance and desktop-window validation remains pending. The fresh
  integrated build found conflicting old/new Kryon Session identities through
  Apps and Plot; the shared integration lane is aligning dependencies.
- A focused bridge regression is also queued as command
  `a24b1acffb7f63c87a04f9f9eefe1eeb6da6`. It opens Kryon's actual desktop
  window with the software SDL renderer on a private Xvfb display, asserts
  there is no current GL window, then checks state publication and one-time
  consumption of both action and feature properties through external X11.
  It does not rebuild the stable application binary or use the real desktop.

- The duplicate banner decode is fixed: the initial practice-catalog load no
  longer invalidates pictures when there were no previous packs. The downloads
  regression fails at assertion 132 with the old unconditional notification.
- Ziran's ARM native-cache reload fix is committed upstream and included in
  the new toolchain pin. A local compiler override is being used to diagnose
  further integration failures. Final validation must use published pins
  before committing; the cache fix still needs installed-app evidence.
- The next integration must align Kryon, Ziran, CSS, Plot, Game2D, Entity and
  Apps, then run package validation and the application platform tests before
  committing. The coordinator is preparing the aligned set.
- Local live ADB currently exposes the USB Moto only. AArch64 Pixel cache
  evidence cannot be inferred from the Moto's ARMv7 results or from an APK
  build. Use the current development Moto; a personal Pixel measurement needs
  its actual current task scope.
- The PID-scoped first-paint/cache baseline is command
  `f98ddb0cfaedfac624da9f88746054109645`, with ignored helper
  `backup/startup-integration/moto-startup.py` and receipts under
  `backup/moto-performance/`. It preserves app data and rejects an existing
  app process or another foreground app. It completed locally: actual native
  first-frame times were 9966, 9157 and 7142 ms (median 9157 ms), on the old
  installed APK identified in the receipt. No `.zxn` files were present under
  `cache/ziran-native` before or after these runs. These are process restarts,
  not cleared-data or cold-storage launches; do not infer a 5× gain yet.
  The helper stopped its own verified processes; the Moto reservation is free.
  The ARMv7 Android build is command
  `1ee4beec9b0b7f1f3e0fc716648599be0545`; neither is installation evidence.
  The Android attempt finished with code 2 before Gradle: package assembly
  rejected the Apps controller's reviewed native digest. Resolve the aligned
  Apps graph and its reviewed artifact; do not weaken that digest check.
- The guarded current/committed-style comparison completed. Both native builds
  succeeded; both private-Xvfb UI runs failed at the same category target
  assertion. All four tabs are fully visible and 40 px high at 390×844;
  the test requires at least 44 px. Widths are 107, 72, 112 and 51 px.
  The two runs' tab geometry is identical, so the uncommitted highlight-color
  additions in `inbe.css` and `app_style.zi` do not cause this failure. Both
  original files were restored and their SHA-256 hashes verified.
- This is not evidence of a Kryon regression: Breeze's `Tabs` explicitly
  passes `home.top - 8` as the bar height. The current implementation uses
  text tabs, whereas the test also still expects the former category
  medallion images. Resolve the app target-height requirement and update those
  obsolete artwork assertions together; do not attribute this to peer styles.
- Comparison evidence is under ignored `build/review/`:
  `style-comparison.json`, `current-tabs.json`, and `committed-tabs.json`.
  Original style backups and the reproduction scripts are under ignored
  `backup/startup-style-comparison/`. The build output is uninstalled; the
  stable native executable currently contains committed styles and the UI
  test driver. No installation or new dependency integration was claimed.
