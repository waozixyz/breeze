# Android tests: Ziran host modules, Gradle tests, smoke and device checks.

.PHONY: android-sdk-install-test
android-sdk-install-test:
	python3 tests/android_sdk_install_test.py

.PHONY: android-source-test
android-source-test: $(ZI2ZIR_BIN) | build-laws
	ZI_CHECK_DEFINES="ANDROID_BUILD KRYON_ANDROID_HOST __aarch64__" \
		python3 scripts/check-zi-sources.py $(ZI2ZIR_BIN) $(KRYON_DIR)/src/ui $(ZIRAN_DIR)/std $(KSS_DIR)/src

.PHONY: accessibility-test
accessibility-test: $(ZIRAN_BIN)
	$(ZIRAN_BIN) build --target=c --exe --root tests --module-path src \
		--module-path $(KRYON_DIR)/src/ui --module-path $(ZIRAN_DIR)/std \
		--entry accessibility_behavior:main -o $(BUILD_DIR)/accessibility-test \
		tests/accessibility_behavior.zi
	env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u DBUS_SESSION_BUS_ADDRESS \
		$(BUILD_DIR)/accessibility-test/accessibility_behavior

.PHONY: android-text-input-zi-test
android-text-input-zi-test: $(ZI2C_BIN)
	sh tests/android_text_input_zi_test.sh $(abspath $(dir $(ZI2C_BIN)))

.PHONY: android-text-selection-test
android-text-selection-test:
	env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u DBUS_SESSION_BUS_ADDRESS \
		$(GRADLE) --no-daemon --project-dir tests/android-text-selection test

.PHONY: android-jni-zi-test
android-jni-zi-test: $(ZI2C_BIN)
	@python3 tests/android_jni_zi_test.py $(abspath $(dir $(ZI2C_BIN)))

.PHONY: android-health-zi-test
android-health-zi-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/android_health_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

.PHONY: android-push-zi-test
android-push-zi-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/android_push_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

.PHONY: android-wakelock-zi-test
android-wakelock-zi-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/android_wakelock_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

.PHONY: android-timer-zi-test
android-timer-zi-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/android_timer_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

.PHONY: android-import-zi-test
android-import-zi-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/android_import_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

.PHONY: android-lifecycle-zi-test
android-lifecycle-zi-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/android_lifecycle_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

.PHONY: android-http-transport-test
android-http-transport-test:
	@env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u DBUS_SESSION_BUS_ADDRESS \
		python3 tests/android_http_transport_test.py

# Explicit device check; never part of the CI or ordinary test target.
# Inbe's Device settings must allow System orientation for real rotation.
.PHONY: android-graphics-device-test
android-graphics-device-test:
	@python3 tests/android_graphics_recovery_device.py $(ANDROID_GRAPHICS_ARGS)

.PHONY: android-package-assets-test
android-package-assets-test: $(ZI2C_BIN)
	sh tests/android_package_assets_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

android-smoke:
	@mkdir -p build/android
	sh scripts/android-smoke-test.sh "$(ANDROID_SDK)" "$(ANDROID_DEBUG_APP_ID)" "$(ANDROID_ACTIVITY)"

.PHONY: android-smoke-script-test
android-smoke-script-test:
	python3 tests/android_smoke_script_test.py

android-audio-e2e:
	bash scripts/android-audio-e2e.sh

.PHONY: android-diary-photo-test
android-diary-photo-test:
	sh tests/android_diary_photo_test.sh

.PHONY: android-geometry-probe-test
android-geometry-probe-test:
	@env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u DBUS_SESSION_BUS_ADDRESS sh tests/android_geometry_probe_test.sh

# Moto debug-profile isolation is explicit; this never runs in the CI suite.
.PHONY: android-launcher-device-test
android-launcher-device-test:
	@python3 tests/android_launcher_device.py $(ANDROID_LAUNCHER_ARGS)
