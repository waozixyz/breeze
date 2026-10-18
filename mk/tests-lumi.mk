# Lumi tests, and the session window and WHM frame tests that run the app.

.PHONY: lumi-updates-test
test: lumi-updates-test
lumi-updates-test: $(ZIRAN_BIN) $(LIBOQS_A) $(SQLITE_SRC) $(SQLITE_AMALGAMATION_H) | build-laws
	python3 tests/release_notes_test.py
	sh tests/lumi_updates_test.sh $(ZIRAN_BIN) $(LIBOQS_A)

.PHONY: lumi-test
lumi-test: cells
	sh tests/lumi_engine_test.sh
	python3 tests/lumi_habit_intent_test.py

.PHONY: lumi-ui-test
lumi-ui-test: $(TARGET)
	sh tests/lumi_ui_test.sh $(abspath $(TARGET))

.PHONY: lumi-history-ui-test
lumi-history-ui-test: $(TARGET)
	env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u DBUS_SESSION_BUS_ADDRESS \
		python3 tests/lumi_history_ui_test.py $(abspath $(TARGET))

.PHONY: lumi-selection-ui-test lumi-harness-ui-test lumi-guide-ui-test lumi-emphasis-ui-test
lumi-selection-ui-test: $(TARGET) $(CELL_BUNDLES)
	sh tests/lumi_selection_ui_test.sh $(abspath $(TARGET))

lumi-harness-ui-test: $(TARGET) $(INBE_FULL_BUNDLE)
	sh tests/lumi_harness_ui_test.sh $(abspath $(TARGET))

lumi-guide-ui-test: $(TARGET)
	env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u DBUS_SESSION_BUS_ADDRESS YUE_DESKTOP_RECOVERY=0 \
		dbus-run-session -- python3 tests/lumi_guide_ui_test.py $(abspath $(TARGET))

lumi-emphasis-ui-test: $(TARGET) $(CELL_BUNDLES) $(INBE_FULL_BUNDLE)
	env -u INBE_DIARY_IMPORT -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u DBUS_SESSION_BUS_ADDRESS \
		-u SESSION_MANAGER YUE_DESKTOP_RECOVERY=0 APP_NO_TRAY=1 SDL_VIDEODRIVER=x11 LIBGL_ALWAYS_SOFTWARE=1 \
		xvfb-run -a -n 300 -s '-screen 0 1280x900x24' \
		python3 tests/lumi_emphasis_ui_test.py $(abspath $(TARGET))

# Frame time and memory with a long Lumi history, saved per label to compare
# runs: make lumi-performance-test LUMI_PERFORMANCE_LABEL=before
LUMI_PERFORMANCE_LABEL ?= current
.PHONY: lumi-performance-test
lumi-performance-test: $(TARGET)
	env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u DBUS_SESSION_BUS_ADDRESS \
		python3 tests/lumi_performance_test.py $(abspath $(TARGET)) $(LUMI_PERFORMANCE_LABEL)
	env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u DBUS_SESSION_BUS_ADDRESS \
		python3 tests/lumi_performance_test.py $(abspath $(TARGET)) $(LUMI_PERFORMANCE_LABEL)-mobile --mobile

.PHONY: session-window-ui-test
session-window-ui-test: $(TARGET)
	env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u DBUS_SESSION_BUS_ADDRESS \
		python3 tests/session_window_ui_test.py $(abspath $(TARGET))

.PHONY: whm-frame-performance-test
whm-frame-performance-test: $(TARGET)
	env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u DBUS_SESSION_BUS_ADDRESS \
		python3 tests/whm_frame_performance_test.py $(abspath $(TARGET))

.PHONY: lumi-narration-test
lumi-narration-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u DBUS_SESSION_BUS_ADDRESS \
		sh tests/lumi_narration_test.sh $(ZIRAN_BUILD_DIR)/bin

.PHONY: lumi-telegram-input-test
lumi-telegram-input-test: $(ZIRAN_BIN) $(LIBOQS_A) $(SQLITE_SRC) $(SQLITE_AMALGAMATION_H) | build-laws
	@sh tests/lumi_telegram_input_zi_test.sh $(ZIRAN_BIN) $(LIBOQS_A)

.PHONY: lumi-feedback-delivery-test
lumi-feedback-delivery-test: $(ZIRAN_BIN) $(LIBOQS_A) $(SQLITE_SRC) $(SQLITE_AMALGAMATION_H) | build-laws
	@sh tests/lumi_feedback_delivery_test.sh $(ZIRAN_BIN) $(LIBOQS_A)

# Offline and before the agreement Lumi sends nothing; an own provider gets
# its key only in its Authorization header.
.PHONY: lumi-connection-test
lumi-connection-test: $(ZIRAN_BIN) $(LIBOQS_A) $(SQLITE_SRC) $(SQLITE_AMALGAMATION_H) | build-laws
	@sh tests/lumi_connection_test.sh $(ZIRAN_BIN) $(LIBOQS_A)
