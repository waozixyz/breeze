# App package tests: cells, node apps, codecs and package releases.

.PHONY: app-codec-check
app-codec-check:
	python3 scripts/generate-app-codec.py --check

.PHONY: cells-test
cells-test: cells $(ZIRAN_BUILD_DIR)/libziran.a $(LIBOQS_A) $(SQLITE_SRC) $(SQLITE_AMALGAMATION_H)
	sh tests/cells_zi_test.sh $(ZIRAN_BIN) $(LIBOQS_A)

.PHONY: cells-platform-test cells-android-probe
cells-platform-test: cells $(ZIRAN_BUILD_DIR)/libziran.a
	sh tests/cells_platform_test.sh $(ZIRAN_BIN) native

cells-android-probe: cells
	sh tests/cells_platform_test.sh $(ZIRAN_BIN) android

# Optional interoperability check against the current Kryon and Werkzeug builds.
.PHONY: portable-apps-ui-test
portable-apps-ui-test: $(TARGET) cells
	@test -n "$(APP_PLAYER)" -a -n "$(WERK_BINARY)" -a -n "$(CALCULATOR_BUNDLE)" || { \
		echo 'Set APP_PLAYER, WERK_BINARY and CALCULATOR_BUNDLE to the tested builds.' >&2; exit 2; }
	env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u DBUS_SESSION_BUS_ADDRESS -u SESSION_MANAGER \
		python3 tests/portable_apps_ui_test.py --inbe $(abspath $(TARGET)) \
		--player "$(APP_PLAYER)" --werk "$(WERK_BINARY)" \
		--diary $(abspath build/cells/diary.zib) --calculator "$(CALCULATOR_BUNDLE)"

.PHONY: node-app-records-test

# Apps location and node snapshot checks against the locked Apps and Crypto packages.
.PHONY: app-locations-test node-app-snapshot-test
app-locations-test: $(ZIRAN_BIN)
	python3 tests/app_locations_test.py --ziran '$(abspath $(ZIRAN_BIN))' \
		--toolchain '$(abspath $(ZIRAN_DIR))' --apps '$(abspath build/packages/apps)' \
		--daochi-client '$(abspath build/packages/daochi-client)'

node-app-snapshot-test: $(ZIRAN_BIN) $(ZIRAN_BUILD_DIR)/libziran.a $(SQLITE_SRC) $(LIBOQS_A)
	python3 tests/node_app_snapshot_test.py --ziran '$(abspath $(ZIRAN_BIN))' \
		--runtime '$(abspath $(ZIRAN_BUILD_DIR)/libziran.a)'
.PHONY: photos-app-test media-store-test media-metadata-test
# Photos and the account's media library it shows.
media-metadata-test: $(ZI2C_BIN)
	sh tests/media_metadata_test.sh $(ZIRAN_BUILD_DIR)/bin

media-store-test: $(ZI2C_BIN) $(SQLITE_SRC) $(LIBOQS_A)
	sh tests/media_store_zi_test.sh $(ZIRAN_BIN) $(LIBOQS_A)

photos-app-test: $(ZIRAN_BIN) $(SQLITE_SRC) $(LIBOQS_A)
	sh tests/photos_app_test.sh $(ZIRAN_BIN) $(LIBOQS_A)

node-app-records-test: $(ZI2C_BIN)
	sh tests/node_app_records_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

.PHONY: package-release-test
package-release-test: cells $(ZIRAN_BUILD_DIR)/libziran.a
	python3 tests/package_release_test.py

# This build runs the packages the node serves, and the last released app runs
# each new package that declares a host interface it has.
.PHONY: package-compat-test
package-compat-test: $(TARGET) $(CELL_BUNDLES) $(INBE_BUNDLE)
	python3 tests/package_compat_test.py $(abspath $(TARGET))

.PHONY: package-version-test
package-version-test:
	python3 scripts/check-package-versions.py
	python3 tests/package_versions_test.py

.PHONY: package-workflow-test
package-workflow-test:
	python3 tests/package_workflow_test.py

.PHONY: package-manifest-test
package-manifest-test:
	python3 tests/package_manifests_test.py

.PHONY: package-upload-test
package-upload-test:
	python3 tests/package_upload_test.py
	python3 tests/package_content_repair_test.py

.PHONY: package-receiver-test
package-receiver-test:
	python3 tests/package_receiver_test.py

# Radio's installable bundle, live decoder and browser audio effect.
.PHONY: radio-test radio-app-test radio-native-test radio-web-test radio-android-test
radio-app-test: $(ZIRAN_BIN) $(ZIRAN_BUILD_DIR)/libziran.a
	sh tests/radio_app_test.sh $(ZIRAN_BIN) $(ZIRAN_DIR)/std $(KRYON_DIR)/src/ui

radio-native-test: $(ZI2C_BIN) $(RAYLIB_A)
	sh tests/radio_native_test.sh $(ZIRAN_BUILD_DIR)/bin $(ZIRAN_DIR)/std
	@nm -g $(RAYLIB_A) | rg -q ' T drmp3dec_decode_frame$$'

radio-web-test:
	node tests/radio_web_test.mjs

radio-android-test:
	env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u DBUS_SESSION_BUS_ADDRESS \
		$(ANDROID_GRADLE_ENV) YUE_DESKTOP_RECOVERY=0 $(GRADLE) --no-daemon \
		--project-dir tests/android-text-selection test --tests xyz.waozi.inbe.RadioPlayerTest

radio-test: radio-app-test radio-native-test radio-web-test radio-android-test
test: radio-app-test radio-native-test radio-web-test
