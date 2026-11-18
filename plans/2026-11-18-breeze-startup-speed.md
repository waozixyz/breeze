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
- [ ] Kryon's `AndroidProcessPrepare` sets `TMPDIR` for that compile but no
  cache folder. Once Kryon sets one for every app, drop
  `AndroidNativeCachePrepare` from `src/platform/main_platform.zi`.
- [ ] Practice banners are 2048×1024 WebP for a card a few hundred pixels
  tall: about 760 ms each in the debug build. Decode at the drawn size
  (Kryon's Pixmap) or ship smaller banners.
- [ ] The WHM banner decodes twice. When the Practices app opens after the
  start, `practice_downloads.zi` reports `assets/practices` as changed, which
  reloads pictures whose bytes stayed the same.
- [ ] Measure a gplay release on the owner's Pixel 3a once these land; debug
  builds log each picture's load time as `APP PROBE: picture`.
