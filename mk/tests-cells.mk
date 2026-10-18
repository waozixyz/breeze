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

.PHONY: chess-engine-test chess-app-test node-app-records-test node-app-codec-check
.PHONY: photos-app-test media-store-test media-metadata-test
# Photos and the account's media library it shows.
media-metadata-test: $(ZI2C_BIN)
	sh tests/media_metadata_test.sh $(ZIRAN_BUILD_DIR)/bin

media-store-test: $(ZI2C_BIN) $(SQLITE_SRC) $(LIBOQS_A)
	sh tests/media_store_zi_test.sh $(ZIRAN_BIN) $(LIBOQS_A)

photos-app-test: $(ZIRAN_BIN) $(SQLITE_SRC) $(LIBOQS_A)
	sh tests/photos_app_test.sh $(ZIRAN_BIN) $(LIBOQS_A)

chess-engine-test: $(ZI2C_BIN)
	sh tests/chess_engine_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

node-app-records-test: $(ZI2C_BIN)
	sh tests/node_app_records_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

chess-app-test: $(ZIRAN_BIN)
	sh tests/chess_app_test.sh $(ZIRAN_BIN)

node-app-codec-check:
	python3 scripts/generate-node-app-codec.py --check

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
