# UI tests that run the desktop app on a private display, and the visual gate.

.PHONY: tai-chi-ui-test
tai-chi-ui-test: $(TARGET)
	@env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u DBUS_SESSION_BUS_ADDRESS \
		python3 tests/tai_chi_ui_test.py $(TARGET)

.PHONY: launcher-ui-test
launcher-ui-test: $(TARGET)
	env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u DBUS_SESSION_BUS_ADDRESS YUE_DESKTOP_RECOVERY=0 \
		python3 tests/launcher_ui_test.py $(abspath $(TARGET))
	env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u DBUS_SESSION_BUS_ADDRESS YUE_DESKTOP_RECOVERY=0 \
		python3 tests/launcher_ui_test.py $(abspath $(TARGET)) --dock-only
	env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u DBUS_SESSION_BUS_ADDRESS YUE_DESKTOP_RECOVERY=0 \
		python3 tests/launcher_ui_test.py $(abspath $(TARGET)) --properties-only

	env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u DBUS_SESSION_BUS_ADDRESS YUE_DESKTOP_RECOVERY=0 \
		python3 tests/launcher_ui_test.py $(abspath $(TARGET)) --views-only

.PHONY: native-screenshot-test
native-screenshot-test: $(TARGET)
	sh tests/native_screenshot_test.sh $(abspath $(TARGET))

.PHONY: native-navigation-test
native-navigation-test: $(TARGET)
	sh tests/native_navigation_test.sh $(abspath $(TARGET))

.PHONY: tab-switch-performance-test
tab-switch-performance-test: $(TARGET)
	env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u DBUS_SESSION_BUS_ADDRESS YUE_DESKTOP_RECOVERY=0 \
		python3 tests/tab_switch_performance_test.py $(abspath $(TARGET)) desktop-rapid --rapid
	env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u DBUS_SESSION_BUS_ADDRESS YUE_DESKTOP_RECOVERY=0 \
		python3 tests/tab_switch_performance_test.py $(abspath $(TARGET)) mobile-rapid --mobile --rapid

.PHONY: music-navigation-test
music-navigation-test: $(TARGET)
	@python3 tests/music_navigation_test.py '$(CC)' '$(NATIVE_COMPILE_FLAGS)' \
		'$(KRYON_LIBRARY_BUILD_DIR)/libkryon.a $(ZIRAN_BUILD_DIR)/libziran.a $(KRYON_NATIVE_BACKEND_LIBS) $(LIBOQS_A) $(KRYON_NATIVE_BACKEND_LDLIBS) $(RUNTIME_ASSET_LDLIBS) $(NATIVE_SYSTEM_LDLIBS) $(LDFLAGS)' \
		'$(NATIVE_OBJ_DIR)/objects.rsp'

.PHONY: native-zoom-test
native-zoom-test: $(TARGET)
	sh tests/native_zoom_test.sh $(abspath $(TARGET))

.PHONY: native-visual-test visual-test
native-visual-test: $(TARGET)
	env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u DBUS_SESSION_BUS_ADDRESS YUE_DESKTOP_RECOVERY=0 \
		python3 tests/native_visual_test.py $(abspath $(TARGET))

.PHONY: entity-profile-ui-test
entity-profile-ui-test: $(TARGET)
	env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u DBUS_SESSION_BUS_ADDRESS \
		-u SESSION_MANAGER -u GDK_DISPLAY YUE_DESKTOP_RECOVERY=0 \
		python3 tests/entity_profile_ui_test.py $(abspath $(TARGET))

.PHONY: native-text-pixels-test
native-text-pixels-test: $(TARGET)
	env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u DBUS_SESSION_BUS_ADDRESS YUE_DESKTOP_RECOVERY=0 \
		ZIRAN_ROOT=$(abspath $(ZIRAN_DIR)) ZIRAN_BIN=$(ZIRAN_BIN) \
		RAYLIB_A=$(abspath $(RAYLIB_A)) \
		KRYON_TEXT_TEST_OUTPUT=$(abspath $(BUILD_DIR)/native-text-pixels-test) \
		sh $(KRYON_DIR)/tests/raylib_text_pixels_test.sh

# Run every visual suite and retain a receipt even when an earlier suite fails.
VISUAL_TEST_TARGETS := practice-images-ui-test leaderboard-ui-test native-screenshot-test native-text-pixels-test native-zoom-test native-visual-test launcher-ui-test settings-sidebar-ui-test startup-quit-ui-test locale-render-ui-test lumi-ui-test lumi-history-ui-test habits-table-ui-test habits-count-ui-test habit-schedule-tool-test habit-tracking-tool-test lists-ui-test sync-review-ui-test data-back-ui-test lumi-selection-ui-test lumi-harness-ui-test lumi-guide-ui-test lumi-emphasis-ui-test customize-nav-ui-test
VISUAL_TEST_TARGETS += audio-setup-ui-test cells-onboarding-test practice-downloads-ui-test tab-switch-performance-test habit-unsaved-ui-test
VISUAL_TEST_TARGETS += entity-profile-ui-test
VISUAL_TEST_TARGETS += music-navigation-test
visual-test: $(TARGET) $(INBE_FULL_BUNDLE)
	env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u GDK_DISPLAY \
		-u DBUS_SESSION_BUS_ADDRESS -u SESSION_MANAGER YUE_DESKTOP_RECOVERY=0 \
		python3 tests/visual_test.py $(abspath $(TARGET)) $(VISUAL_TEST_TARGETS)

.PHONY: customize-nav-ui-test
customize-nav-ui-test: $(TARGET)
	sh tests/customize_nav_ui_test.sh $(abspath $(TARGET))
	INBE_TEST_NARROW=1 sh tests/customize_nav_ui_test.sh $(abspath $(TARGET))

.PHONY: settings-sidebar-ui-test
settings-sidebar-ui-test: $(TARGET)
	env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u DBUS_SESSION_BUS_ADDRESS YUE_DESKTOP_RECOVERY=0 \
		python3 tests/settings_sidebar_ui_test.py $(abspath $(TARGET))

.PHONY: startup-quit-ui-test
startup-quit-ui-test: $(TARGET) $(INBE_FULL_BUNDLE)
	env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u DBUS_SESSION_BUS_ADDRESS YUE_DESKTOP_RECOVERY=0 \
		python3 tests/startup_quit_ui_test.py $(abspath $(TARGET))

test-tui-screenshot test-termi-screenshot:
	@$(MAKE) --no-print-directory KRYON_BACKEND=termi test-termi-screenshot-direct

test-termi-screenshot-direct: $(TARGET)
	bash ./tests/termi_screenshot_test.sh "$(TARGET)"

## End-to-end desktop window-mode tests on a private Xvfb display: window
## close across startup/keep-running/ask modes.
## Requires Xvfb, xfwm4, xdotool, x11-utils and sqlite3.
test-desktop-windows:
	./scripts/test-desktop-windows.sh "$(TARGET)"

.PHONY: habits-table-ui-test
habits-table-ui-test: $(TARGET)
	bash tests/habits_table_ui_test.sh "$(abspath $(TARGET))"

.PHONY: habits-count-ui-test
habits-count-ui-test: $(TARGET)
	bash tests/habits_count_ui_test.sh "$(abspath $(TARGET))"

.PHONY: lists-ui-test
lists-ui-test: $(TARGET)
	bash tests/lists_ui_test.sh "$(abspath $(TARGET))"

.PHONY: appearance-ui-test
appearance-ui-test: $(TARGET) $(INBE_FULL_BUNDLE)
	sh tests/appearance_ui_test.sh $(abspath $(TARGET))

.PHONY: habit-schedule-tool-test
habit-schedule-tool-test: $(TARGET) $(INBE_FULL_BUNDLE)
	sh tests/habit_schedule_tool_test.sh $(abspath $(TARGET))

.PHONY: habit-tracking-tool-test
habit-tracking-tool-test: $(TARGET) $(INBE_FULL_BUNDLE)
	sh tests/habit_tracking_tool_test.sh $(abspath $(TARGET))

.PHONY: lumi-habit-tools-test
lumi-habit-tools-test: $(TARGET) $(INBE_FULL_BUNDLE)
	sh tests/lumi_habit_tools_test.sh $(abspath $(TARGET))

VISUAL_TEST_TARGETS += lumi-habit-tools-test

.PHONY: account-activity-ui-test
account-activity-ui-test: $(TARGET) $(INBE_FULL_BUNDLE) account-activity-test
	sh tests/account_activity_ui_test.sh $(abspath $(TARGET))

.PHONY: cells-navigation-test
cells-navigation-test: $(TARGET)
	sh tests/cells_navigation_test.sh $(abspath $(TARGET))

.PHONY: host-actions-test
host-actions-test: $(TARGET)
	env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u DBUS_SESSION_BUS_ADDRESS YUE_DESKTOP_RECOVERY=0 python3 tests/host_actions_test.py $(abspath $(TARGET))

.PHONY: hosted-feature-test
hosted-feature-test: $(TARGET) $(INBE_FULL_BUNDLE)
	env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u DBUS_SESSION_BUS_ADDRESS -u GDK_DISPLAY \
		-u SESSION_MANAGER YUE_DESKTOP_RECOVERY=0 LIBGL_ALWAYS_SOFTWARE=1 SDL_VIDEODRIVER=x11 SDL_AUDIODRIVER=dummy \
		xvfb-run -a -n 300 -s '-screen 0 1280x1024x24 -nolisten tcp' \
		python3 tests/hosted_feature_test.py $(abspath $(TARGET))

VISUAL_TEST_TARGETS += hosted-feature-test

.PHONY: cells-artifact-test
cells-artifact-test: $(TARGET) $(CELL_BUNDLES)
	python3 tests/cells_artifact_test.py $(abspath $(TARGET))

.PHONY: cells-onboarding-test
cells-onboarding-test: $(TARGET)
	sh tests/cells_onboarding_test.sh $(abspath $(TARGET))

.PHONY: locale-render-ui-test
locale-render-ui-test: $(TARGET) $(INBE_BUNDLE)
	sh tests/locale_render_ui_test.sh $(abspath $(TARGET))

.PHONY: sync-review-ui-test
sync-review-ui-test: $(TARGET)
	@sh tests/sync_review_ui_test.sh $(TARGET)

# Two devices link through scanned QR codes; needs detect_qr from the
# Photos repository's build.
DEVICE_LINK_DETECT_QR ?= ../photos/build/detect-qr/detect_qr
.PHONY: device-link-ui-test
device-link-ui-test: $(TARGET) $(INBE_FULL_BUNDLE) $(BUILD_DIR)/cells/lumi.zib
	@env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u DBUS_SESSION_BUS_ADDRESS -u GDK_DISPLAY \
		-u SESSION_MANAGER YUE_DESKTOP_RECOVERY=0 SDL_AUDIODRIVER=dummy APP_NO_TRAY=1 \
		timeout 300s xvfb-run -a -n 340 -s '-screen 0 1920x900x24' \
		python3 tests/device_link_ui_test.py $(abspath $(TARGET)) $(abspath $(DEVICE_LINK_DETECT_QR))

# Needs a Harmony checkout beside Inbe with its app-control test build.
.PHONY: sync-review-harmony-test
sync-review-harmony-test: $(TARGET)
	sh tests/sync_review_harmony_test.sh $(abspath $(TARGET))

.PHONY: data-back-ui-test
data-back-ui-test: $(TARGET)
	@sh tests/data_back_ui_test.sh $(abspath $(TARGET))

.PHONY: leaderboard-ui-test
leaderboard-ui-test: $(TARGET)
	@sh tests/leaderboard_ui_test.sh $(abspath $(TARGET))

.PHONY: photos-ui-test
photos-ui-test: $(TARGET) $(NODE_APP_BUNDLES)
	@sh tests/photos_ui_test.sh $(abspath $(TARGET)) $(abspath $(BUILD_DIR)/node-apps/photos.zib)

.PHONY: library-ui-test
library-ui-test: $(TARGET) $(NODE_APP_BUNDLES)
	@sh tests/library_ui_test.sh $(abspath $(TARGET)) $(abspath $(BUILD_DIR)/node-apps/library.zib)

.PHONY: habit-unsaved-ui-test
habit-unsaved-ui-test: $(TARGET)
	@sh tests/habit_unsaved_ui_test.sh $(abspath $(TARGET))

.PHONY: chess-ui-test
CHESS_BUNDLE ?=
chess-ui-test: $(TARGET)
	@test -n "$(CHESS_BUNDLE)" || { echo "Set CHESS_BUNDLE to the Chess package built by Arcade"; exit 2; }
	@sh tests/chess_ui_test.sh $(abspath $(TARGET)) $(abspath $(CHESS_BUNDLE))

# Arcade carries Chess: its collection in More apps, and Chess's replacement.
.PHONY: arcade-ui-test
ARCADE_BUNDLE ?=
arcade-ui-test: $(TARGET)
	@test -n "$(ARCADE_BUNDLE)" || { echo "Set ARCADE_BUNDLE to the arcade.zib collection built by Arcade"; exit 2; }
	@sh tests/arcade_ui_test.sh $(abspath $(TARGET)) $(abspath $(ARCADE_BUNDLE))

# Missing practice pictures fail the visual gate in CI and releases.
.PHONY: practice-images-ui-test
practice-images-ui-test: $(TARGET)
	@sh tests/practice_images_ui_test.sh $(abspath $(TARGET))

.PHONY: cells-diary-test
cells-diary-test: $(TARGET)
	sh tests/cells_diary_test.sh $(abspath $(TARGET))

.PHONY: practice-downloads-ui-test
practice-downloads-ui-test: $(TARGET)
	env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u DBUS_SESSION_BUS_ADDRESS -u GDK_DISPLAY \
		YUE_DESKTOP_RECOVERY=0 SDL_AUDIODRIVER=dummy APP_NO_TRAY=1 \
		xvfb-run -a -n 900 -s '-screen 0 1600x1000x24 -nolisten tcp' \
		python3 tests/practice_downloads_ui_test.py $(abspath $(TARGET))

.PHONY: audio-setup-ui-test
audio-setup-ui-test: $(TARGET) $(INBE_FULL_BUNDLE)
	env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u DBUS_SESSION_BUS_ADDRESS \
		YUE_DESKTOP_RECOVERY=0 LIBGL_ALWAYS_SOFTWARE=1 \
		xvfb-run -a -n 300 -s '-screen 0 1280x1000x24' \
		python3 tests/audio_setup_ui_test.py $(abspath $(TARGET))

.PHONY: launcher-shortcut-ui-test
launcher-shortcut-ui-test: $(TARGET) node-apps
	env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u DBUS_SESSION_BUS_ADDRESS YUE_DESKTOP_RECOVERY=0 \
		python3 tests/launcher_shortcut_ui_test.py $(abspath $(TARGET))

VISUAL_TEST_TARGETS += launcher-shortcut-ui-test

# Apps from the node open only once they are on the device.
.PHONY: node-app-not-installed-ui-test
node-app-not-installed-ui-test: $(TARGET)
	env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u DBUS_SESSION_BUS_ADDRESS YUE_DESKTOP_RECOVERY=0 \
		python3 tests/node_app_not_installed_ui_test.py $(abspath $(TARGET))

VISUAL_TEST_TARGETS += node-app-not-installed-ui-test

.PHONY: habit-shop-ui-test
habit-shop-ui-test: $(TARGET)
	sh tests/habit_shop_ui_test.sh $(abspath $(TARGET))

VISUAL_TEST_TARGETS += habit-shop-ui-test library-ui-test
