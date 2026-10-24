# make test runs these suites in this order; ci adds the web build.

test: app-codec-check
test: android-source-test
test: frame-pacing-zi-test
test: desktop-frame-pacing-policy-test
test: habits-table-layout-test
test: sync-retry-zi-test
test: liboqs-crypto-test
test: sync-account-zi-test
test: storage-import-zi-test
test: storage-habits-zi-test
test: achievements-test achievement-catalog-test
test: storage-settings-threads-zi-test
test: storage-sync-zi-test
test: sync-url-zi-test
test: sync-review-zi-test
test: lumi-narration-test
test: ziran-behavior-tests asset-text-tests
test: route-host-test
test: profile-host-test
test: entity-picker-test
test: launcher-policy-test launcher-entry-test android-text-selection-test
test: button-api-check
test: version-check version-test
test: fdroid-build-test
test: habit-merge-sql-test sync-restore-sql-test
test: proof-test
test: clean-text-api-check package-check secret-check storage-literals-check font-bundle-check audio-test-fixture-check embedded-image-assets-check icon-sheets-check
test: test-references-check
test: screenshot-scene-test
test: exercise-types-test
test: astral-projection-test
test: workout-test
test: patterns-rules-zi-test
test: patterns-session-zi-test
test: session-results-zi-test
test: settings-cache-test
test: web-storage-bridge-test
test: firefox-startup-test
test: device-policy-test
test: device-preferences-zi-test device-host-sdl-test
test: fonts-zi-test
test: metrics-zi-test
test: mood-average-zi-test
test: statistics-date-zi-test
test: habit-session-rules-zi-test
test: locale-used-keys-test
test: locale-translated-test
test: music-library-zi-test
test: screenshot-request-zi-test
test: app-chrome-zi-test
test: schema-zi-test
test: root-upgrade-zi-test
test: database-upgrade-zi-test
test: legacy-session-zi-test
test: archive-file-linux-zi-test
test: export-filename-test
test: storage-state-zi-test
test: storage-sql-zi-test
test: storage-json-builder-zi-test
test: storage-thread-buffer-zi-test
test: sqlite-text-zi-test
test: sql-transaction-zi-test
test: storage-paths-zi-test
test: daochi-client-zi-test
test: daochi-native-zi-test device-link-zi-test
test: habit-days-memory-zi-test
test: host-services-zi-test
test: locale-zi-test
test: text-buffers-zi-test
test: raylib-text-input-zi-test
test: android-text-input-zi-test
test: android-text-selection-test
test: accessibility-test
test: main-platform-zi-test
test: web-window-zi-test
test: android-jni-zi-test update-transport-zi-test
test: update-policy-zi-test
test: raylib-log-host-test
test: dpi-state-zi-test
test: settings-ui-zi-test
test: break-stats-zi-test
test: android-health-zi-test
test: android-push-zi-test
test: android-wakelock-zi-test
test: android-timer-zi-test
test: android-import-zi-test
test: android-lifecycle-zi-test
test: android-http-transport-test
test: raylib-graphics-test
test: graphics-transition-test
test: language-selection-zi-test
test: audio-policy-test
test: audio-runtime-test
test: audio-meter-zi-test
test: profile-picture-policy-test
test: assets-zi-test
test: android-package-assets-test package-size-test
test: asset-files-zi-test
test: settings-status-zi-test
test: settings-mutation-zi-test
test: theme-catalog-zi-test
test: style-apply-zi-test
test: audio-settings-test
test: bottom-nav-policy-test
test: mini-mode-policy-test
test: app-nav-state-zi-test
test: app-zoom-test
test: sync-safety-test
test: account-activity-test
test: sync-status-policy-test
test: social-action-queue-test
test: sync-worker-host-test
test: sync-status-test
test: habit-calendar-test
test: habit-linked-rules-zi-test
test: meditation-timing-test
test: meditation-audio-archive-zi-test
test: sun-salutation-test sun-salutation-assets-test
test: app-clock-test
test: friend-requests-test
test: modal-rules-test
test: elist-screen-test
test: theme-catalog-bundle-check
test: site-assets-test
test: android-smoke-script-test
test: sync-recovery-test
test: sync-connection-test
test: sync-record-fields-test
test: media-metadata-test media-store-test entity-photos-test photos-app-test
test: node-app-records-test node-app-snapshot-test
test: app-click-block-zi-test
test: phone-check-gate-test
test: release-tooling-test
test: package-release-test
test: app-preferences-sync-test
test: package-version-test
test: play-screenshots-test
test: package-workflow-test
test: package-manifest-test
test: package-upload-test
test: package-receiver-test
test: device-key-test
test: lumi-telegram-input-test
test: telegram-authorization-test
test: android-geometry-probe-test
test: lumi-feedback-delivery-test
test: lumi-connection-test
test: diary-spelling-test diary-history-test diary-markdown-test
test: cells-test
test: device-info-test
test: dew-test
test: lists-sharing-test
test: practice-downloads-test
test: practice-narration-test
test: practice-narration-keys-test
test: practice-narration-snapshot-test
test: android-sdk-install-test

## Local parity with the ci.yml gate: unit tests plus the web build (emcc).
## Run before pushing to catch web-only breakage -- e.g. code under
## #if defined(PLATFORM_WEB) -- that `make test` (desktop-native) misses.
ci: test web
