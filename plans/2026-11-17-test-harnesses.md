# Test harnesses on Ziran 0.6 — open work

`make -k test` on a clean export of master still fails 54 targets. CI stops
each shard at its first failure, so most of these never show there. The
Browser Add-ons job also stops at the web build.

- Module-path builds cannot reach Kryon's export names (`kryon/text_area`,
  `kryon/text_field`, `kryon/title_bar`) or resolve an `#if` enum member
  imported through them: accessibility, account-activity,
  android-geometry-probe, android-text-input-zi, app-chrome-zi, app-clock,
  audio-runtime, dpi-state-zi, entity-photos, language-selection-zi,
  lists-sharing, lumi-connection, lumi-delegate-scope,
  lumi-feedback-delivery, lumi-telegram-input, main-platform-zi,
  media-store, notification-lifecycle, raylib-text-input-zi,
  settings-telegram-ui, settings-ui-zi, storage-sync-zi, sync-account-zi,
  sync-connection, telegram-account-flow, telegram-account-ui and
  theme-catalog-zi. Build them in project mode like
  `tests/storage_sync_zi_test.sh`, or from the export map `ziran pkg list`
  prints. Project mode also needs qualified test imports (`kryon/tree`) and a
  C link that provides Kryon's raster host (`ImageWidth`, `ImageHeight`,
  `RasterLine`).
- C link tests name generated headers or files that are now package-prefixed
  (`p<hash>_typeface_source.h`) or header-only: fonts-zi, metrics-zi,
  legacy-session-zi, database-upgrade-zi, daochi-client-zi, daochi-native-zi,
  lumi-narration, node-app-loading and voice-audio-play.
- media-compression: its test host imports `kryon/raylib_image_decode`, which
  Kryon does not export.
- The web build generates C for Linux, but Kryon defines its canvas events
  only for `OS == .WEB`. With `--target-os web`, Breeze's own window runtime
  (`practice_probe.zi`) does not resolve. Port the web build to the web target.
- Practice media: astral-projection and patterns-session read
  `astral_projection/drafts/bruce-practices.json`, which the pinned practices
  package lacks. practice-narration-keys and practice-narration-snapshot find
  Sun Salutation recordings missing or older than their text.
- embedded-image-assets-check and test-references-check reject a resource
  bundle format; audio-meter-zi imports `raylib_trace`; and update-transport-zi,
  node-app-snapshot, app-click-block-zi, visual-runner, settings-mutation-zi,
  small-app-bundling, device-preferences-zi, ziran-behavior-tests,
  android-text-selection (Gradle) and fdroid-build (ThinLTO output differs
  between checkout locations) each need a look at their own failure.
