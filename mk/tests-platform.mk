# Desktop and shared host tests: frames, fonts, assets, audio, graphics, updates.

# Explicit test-linked host; production artifacts never include the fixture.
.PHONY: referral-host-test-binary referral-host-ui-test
referral-host-test-binary: $(CURL_SO)
	@mkdir -p $(BUILD_DIR)/referral-host-test
	$(CC) -O2 -fPIC -DREFERRAL_STATIC_CURL \
		-Ivendor-builds/linux/x86_64/inbe-curl/include \
		-c tests/referral_http_fixture.c -o $(BUILD_DIR)/referral-host-test/referral_http_fixture.o
	$(MAKE) native TARGET=$(BUILD_DIR)/referral-host-test/breeze \
		LDFLAGS="$(abspath $(BUILD_DIR)/referral-host-test/referral_http_fixture.o) -Wl,--wrap=curl_easy_setopt"

referral-host-ui-test: referral-host-test-binary
	env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u DBUS_SESSION_BUS_ADDRESS \
		-u SESSION_MANAGER -u GDK_DISPLAY YUE_DESKTOP_RECOVERY=0 \
		python3 tests/referral_hosts_ui_test.py --app breeze \
		--binary $(BUILD_DIR)/referral-host-test/breeze --static-curl

FONT_ASSETS_GEN_DIR := $(BUILD_DIR)/font-assets-test/generated

.PHONY: frame-activity-test
frame-activity-test: $(ZI2C_BIN)
	@sh tests/frame_activity_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

.PHONY: frame-pacing-zi-test
frame-pacing-zi-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/frame_pacing_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

.PHONY: desktop-frame-pacing-policy-test
desktop-frame-pacing-policy-test:
	@bash tests/desktop_frame_pacing_policy_test.sh

.PHONY: route-host-test
route-host-test: $(ZI2C_BIN)
	@mkdir -p $(BUILD_DIR)/route-host-test/generated
	@$(ZI2C_BIN) --no-main --root src \
		--module-path $(KRYON_DIR)/src/ui \
		--module-path $(ZIRAN_DIR)/std \
		-o $(BUILD_DIR)/route-host-test/generated src/app/route_catalog.zi
	@$(ZI2C_BIN) --no-main --root src \
		--module-path $(ZIRAN_DIR)/std \
		-o $(BUILD_DIR)/route-host-test/generated src/app/route_log.zi
	@$(ZI2C_BIN) --no-main --root src --define PLATFORM_WEB \
		--module-path $(ZIRAN_DIR)/std \
		-o $(BUILD_DIR)/route-host-test/generated src/app/route_host.zi
	@$(CC) -std=c11 -ffunction-sections -fdata-sections \
		-Wl,--gc-sections -I$(ZIRAN_DIR)/include \
		-I$(BUILD_DIR)/route-host-test/generated -Isrc/app \
		tests/route_host_test.c \
		$(BUILD_DIR)/route-host-test/generated/c_string.c \
		$(BUILD_DIR)/route-host-test/generated/text_buffers.c \
		$(BUILD_DIR)/route-host-test/generated/byte_text_linux.c \
		$(BUILD_DIR)/route-host-test/generated/app/route_log.c \
		$(BUILD_DIR)/route-host-test/generated/app/route_host.c \
		-I$(KRYON_DIR)/include \
		-o $(BUILD_DIR)/route-host-test/test
	@env -u DISPLAY -u WAYLAND_DISPLAY $(BUILD_DIR)/route-host-test/test

.PHONY: profile-host-test
profile-host-test: $(ZI2C_BIN)
	@mkdir -p $(BUILD_DIR)/profile-host-test/generated
	@$(ZI2C_BIN) --no-main --root src \
		--module-path $(ZIRAN_DIR)/std \
		-o $(BUILD_DIR)/profile-host-test/generated src/app/app_profile.zi
	@$(CC) -std=c11 -ffunction-sections -fdata-sections \
		-Wl,--gc-sections -I$(ZIRAN_DIR)/include \
		-I$(BUILD_DIR)/profile-host-test/generated -Isrc/app \
		-I$(KRYON_DIR)/include \
		tests/profile_host_test.c \
		$(BUILD_DIR)/profile-host-test/generated/c_string.c \
		$(BUILD_DIR)/profile-host-test/generated/app/app_profile.c \
		-o $(BUILD_DIR)/profile-host-test/test
	@env -u DISPLAY -u WAYLAND_DISPLAY $(BUILD_DIR)/profile-host-test/test disabled
	@env -u DISPLAY -u WAYLAND_DISPLAY $(BUILD_DIR)/profile-host-test/test

$(FONT_ASSETS_GEN_DIR)/app/font_assets.c: src/app/font_assets.zi $(ZI2C_BIN)
	@mkdir -p $(FONT_ASSETS_GEN_DIR)
	$(ZI2C_BIN) --no-main --root src \
		-o $(FONT_ASSETS_GEN_DIR) src/app/font_assets.zi

.PHONY: font-assets-test
font-assets-test: build-laws $(ZI2C_BIN)
	@sh tests/font_assets_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

.PHONY: device-policy-test
device-policy-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/device_policy_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

.PHONY: device-preferences-zi-test device-host-sdl-test
device-preferences-zi-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/device_preferences_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

device-host-sdl-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/device_host_sdl_test.sh $(ZIRAN_BUILD_DIR)/bin

.PHONY: fonts-zi-test
fonts-zi-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/fonts_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

.PHONY: host-services-zi-test
host-services-zi-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/host_services_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

.PHONY: text-buffers-zi-test
text-buffers-zi-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/text_buffers_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

.PHONY: main-platform-zi-test
main-platform-zi-test: $(ZI2C_BIN)
	@sh tests/main_platform_zi_test.sh $(abspath $(dir $(ZI2C_BIN)))

.PHONY: feature-request-zi-test
test: feature-request-zi-test
feature-request-zi-test: $(ZI2C_BIN)
	@sh tests/feature_request_zi_test.sh $(abspath $(dir $(ZI2C_BIN)))

.PHONY: update-transport-zi-test

update-transport-zi-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u GDK_DISPLAY \
		python3 tests/update_fetch_host_test.py
	@env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u GDK_DISPLAY \
		python3 tests/update_flow_zi_test.py

.PHONY: desktop-update-test
desktop-update-test:
	python3 tests/desktop_update_test.py

.PHONY: update-policy-zi-test
update-policy-zi-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/update_policy_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

.PHONY: app-log-test
app-log-test: $(ZI2C_BIN)
	@mkdir -p $(BUILD_DIR)/app-log-test/c
	@$(ZI2C_BIN) --define PLATFORM_DESKTOP --define DESKTOP_HOST \
		--entry app_log_behavior:main --root tests \
		--module-path src --module-path $(ZIRAN_DIR)/std \
		-o $(BUILD_DIR)/app-log-test/c tests/app_log_behavior.zi
	@$(CC) -std=c11 -O2 -I$(ZIRAN_DIR)/include \
		-iquote $(BUILD_DIR)/app-log-test/c \
		$(BUILD_DIR)/app-log-test/c/*.c -lm \
		-o $(BUILD_DIR)/app-log-test/test
	@env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u GDK_DISPLAY \
		$(BUILD_DIR)/app-log-test/test \
		> $(BUILD_DIR)/app-log-test/output 2>&1
	@grep -qxF 'WARNING: trace text' $(BUILD_DIR)/app-log-test/output
	@grep -qxF 'WARNING: width=320 height=560 embedded=1' \
		$(BUILD_DIR)/app-log-test/output
	@grep -qxF 'WARNING: scale=1.50 layout=320x560' \
		$(BUILD_DIR)/app-log-test/output
	@grep -qxF 'WARNING: viewport=320x560 layout=300x540 content_x=10 content=280x540 render_scale=1.50' \
		$(BUILD_DIR)/app-log-test/output
	@grep -qxF 'WARNING: result=7' $(BUILD_DIR)/app-log-test/output
	@grep -qxF 'WARNING: track=2 practice=3' \
		$(BUILD_DIR)/app-log-test/output

.PHONY: dpi-state-zi-test
dpi-state-zi-test: $(ZI2C_BIN)
	@sh tests/dpi_state_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

.PHONY: graphics-transition-test
graphics-transition-test: $(ZI2C_BIN)
	@sh tests/graphics_transition_test.sh $(ZIRAN_BUILD_DIR)/bin

.PHONY: audio-policy-test
audio-policy-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/audio_policy_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

.PHONY: audio-runtime-test
audio-runtime-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY \
		sh tests/audio_runtime_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

.PHONY: audio-meter-zi-test
audio-meter-zi-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u GDK_DISPLAY \
		sh tests/audio_meter_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

.PHONY: assets-zi-test
assets-zi-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/assets_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

.PHONY: asset-files-zi-test
asset-files-zi-test: $(ZI2C_BIN)
	@sh tests/asset_files_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

.PHONY: app-clock-test
app-clock-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		CC="$(CC)" WINDOWS_CC="$(WIN64_CC)" \
		sh tests/app_clock_host_test.sh $(ZIRAN_BUILD_DIR)/bin

# Lumi reports name the device, system and version (no identifiers).
.PHONY: device-info-test
device-info-test: $(ZIRAN_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY $(ZIRAN_BIN) build --target=c --define PLATFORM_DESKTOP --root tests \
		--module-path src --module-path build/packages/ziran/std --entry device_info_behavior:Main --exe \
		-o build/device-info-test tests/device_info_behavior.zi
	@build/device-info-test/device_info_behavior

# Explicit Pixel diagnostic, separate from the development Moto test suite.
.PHONY: pixel-rotation-geometry-test
pixel-rotation-geometry-test:
	@test -n "$(PIXEL_GEOMETRY_TRANSPORT)" || { \
		echo 'Set PIXEL_GEOMETRY_TRANSPORT to the selected Pixel ADB transport.'; exit 2; }
	python3 tests/android_rotation_geometry_device.py \
		--host "$(or $(PIXEL_GEOMETRY_HOST),local)" --transport "$(PIXEL_GEOMETRY_TRANSPORT)"
