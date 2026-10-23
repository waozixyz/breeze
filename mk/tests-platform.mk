# Desktop and shared host tests: frames, fonts, assets, audio, graphics, updates.

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

.PHONY: raylib-text-input-zi-test
raylib-text-input-zi-test: $(ZI2C_BIN)
	@sh tests/raylib_text_input_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

.PHONY: main-platform-zi-test
main-platform-zi-test: $(ZI2C_BIN) $(RAYLIB_A)
	@RAY_LDLIBS='$(RAY_LDLIBS)' sh tests/main_platform_zi_test.sh \
		$(abspath $(dir $(ZI2C_BIN))) $(abspath $(RAYLIB_A))

.PHONY: update-transport-zi-test

update-transport-zi-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u GDK_DISPLAY \
		python3 tests/update_fetch_host_test.py
	@env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u GDK_DISPLAY \
		python3 tests/update_flow_zi_test.py

.PHONY: update-policy-zi-test
update-policy-zi-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/update_policy_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

.PHONY: raylib-log-host-test
raylib-log-host-test: $(ZI2C_BIN) $(RAYLIB_A)
	@mkdir -p $(BUILD_DIR)/raylib-log-host-test/c
	@$(ZI2C_BIN) --define PLATFORM_DESKTOP \
		--entry raylib_log_behavior:main --root tests \
		--module-path src --module-path $(KRYON_DIR)/src/backend --module-path $(ZIRAN_DIR)/std \
		-o $(BUILD_DIR)/raylib-log-host-test/c tests/raylib_log_behavior.zi
	@$(CC) -std=c11 -O2 -I$(ZIRAN_DIR)/include \
		-iquote $(BUILD_DIR)/raylib-log-host-test/c \
		$(BUILD_DIR)/raylib-log-host-test/c/*.c $(RAYLIB_A) \
		$(RAY_LDLIBS) -lm -ldl -pthread \
		-o $(BUILD_DIR)/raylib-log-host-test/test
	@env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u GDK_DISPLAY \
		$(BUILD_DIR)/raylib-log-host-test/test \
		> $(BUILD_DIR)/raylib-log-host-test/output 2>&1
	@grep -qF 'width=320 height=560 embedded=1' \
		$(BUILD_DIR)/raylib-log-host-test/output
	@grep -qF 'scale=1.50 layout=320x560' \
		$(BUILD_DIR)/raylib-log-host-test/output
	@grep -qF 'track=2 practice=3' \
		$(BUILD_DIR)/raylib-log-host-test/output

.PHONY: dpi-state-zi-test
dpi-state-zi-test: $(ZI2C_BIN)
	@sh tests/dpi_state_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

.PHONY: raylib-graphics-test
raylib-graphics-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u DBUS_SESSION_BUS_ADDRESS \
		ZIRAN_ROOT="$(ZIRAN_DIR)" ZIRAN_BIN="$(ZIRAN_BUILD_DIR)/bin/ziran" \
		sh "$(KRYON_DIR)/tests/ziran_raylib_graphics_test.sh"

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
asset-files-zi-test: $(ZI2C_BIN) $(RAYLIB_A)
	@sh tests/asset_files_zi_test.sh $(ZIRAN_BUILD_DIR)/bin $(RAYLIB_A)

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
