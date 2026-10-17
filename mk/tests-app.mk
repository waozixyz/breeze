# Tests of the app's screens, settings, habits, diary, navigation and locale rules.

.PHONY: habits-table-layout-test
habits-table-layout-test: $(ZI2C_BIN)
	@sh tests/habits_table_layout_test.sh $(ZIRAN_BUILD_DIR)/bin

.PHONY: route-catalog-test
route-catalog-test: $(ZI2C_BIN)
	@sh tests/route_catalog_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

.PHONY: ziran-behavior-tests
ziran-behavior-tests: cells $(ZI2C_BIN) $(ZIRAN_BUILD_DIR)/libziran.a $(SQLITE_SRC) $(LIBOQS_A) $(RAYLIB_A)
	@set -e; for t in storage_more habit_model habit_sessions habit_form practice_carousel; do \
		env -u DISPLAY -u WAYLAND_DISPLAY sh tests/$${t}_zi_test.sh $(ZIRAN_BUILD_DIR)/bin/ziran $(LIBOQS_A); \
	done
	@env -u DISPLAY -u WAYLAND_DISPLAY sh tests/storage_paths_scenarios_zi_test.sh $(ZIRAN_BUILD_DIR)/bin/ziran
	@env -u DISPLAY -u WAYLAND_DISPLAY sh tests/breath_rounds_zi_test.sh $(ZIRAN_BUILD_DIR)/bin
	@env -u DISPLAY -u WAYLAND_DISPLAY sh tests/break_engine_zi_test.sh $(ZIRAN_BUILD_DIR)/bin
	@env -u DISPLAY -u WAYLAND_DISPLAY sh tests/tai_chi_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

.PHONY: launcher-policy-test
launcher-policy-test: $(ZI2C_BIN)
	sh tests/launcher_policy_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

.PHONY: navigation-routes-test
navigation-routes-test: build-laws $(ZI2C_BIN)
	@sh tests/navigation_routes_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

.PHONY: settings-cache-test
settings-cache-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/settings_cache_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

.PHONY: metrics-zi-test
metrics-zi-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/metrics_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

.PHONY: mood-average-zi-test
mood-average-zi-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/mood_average_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

.PHONY: statistics-date-zi-test
statistics-date-zi-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/statistics_date_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

.PHONY: habit-session-rules-zi-test
habit-session-rules-zi-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/habit_session_rules_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

.PHONY: screenshot-request-zi-test
screenshot-request-zi-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/screenshot_request_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

.PHONY: app-chrome-zi-test
app-chrome-zi-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/app_chrome_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

.PHONY: habit-days-memory-zi-test
habit-days-memory-zi-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/habit_days_memory_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

.PHONY: locale-zi-test
locale-zi-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/locale_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

.PHONY: settings-ui-zi-test
settings-ui-zi-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/settings_ui_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

.PHONY: language-selection-zi-test
language-selection-zi-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/language_selection_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

.PHONY: profile-picture-policy-test
profile-picture-policy-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/profile_picture_policy_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

.PHONY: settings-status-zi-test
settings-status-zi-test: $(ZI2C_BIN)
	@python3 tests/settings_status_test.py $(ZIRAN_BUILD_DIR)/bin

.PHONY: settings-mutation-zi-test
settings-mutation-zi-test: $(ZI2C_BIN)
	@sh tests/settings_mutation_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

.PHONY: theme-catalog-zi-test
theme-catalog-zi-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/theme_catalog_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

.PHONY: style-apply-zi-test
style-apply-zi-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/style_apply_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

.PHONY: audio-settings-test
audio-settings-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/audio_settings_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

.PHONY: bottom-nav-policy-test
bottom-nav-policy-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/bottom_nav_policy_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

.PHONY: mini-mode-policy-test
mini-mode-policy-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/mini_mode_policy_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

.PHONY: app-nav-state-zi-test
app-nav-state-zi-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/app_nav_state_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

.PHONY: app-zoom-test
app-zoom-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/app_zoom_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

.PHONY: route-list-test
route-list-test: build-laws $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/route_list_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

.PHONY: habit-calendar-test
habit-calendar-test: build-laws $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/habit_calendar_zi_test.sh $(ZIRAN_BUILD_DIR)/bin \
		$(KRYON_DIR)/src/ui

.PHONY: habit-linked-rules-zi-test
habit-linked-rules-zi-test: build-laws $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/habit_linked_rules_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

.PHONY: friend-requests-test
friend-requests-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		ZIRAN_INCLUDE=$(ZIRAN_DIR)/include \
		sh tests/friend_requests_zi_test.sh $(ZIRAN_BUILD_DIR)/bin \
		$(ZIRAN_DIR)/std

.PHONY: modal-rules-test
modal-rules-test: build-laws $(ZI2C_BIN)
	@sh tests/modal_rules_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

.PHONY: elist-screen-test
elist-screen-test: cells $(ZI2C_BIN) $(ZIRAN_BUILD_DIR)/libziran.a
	@sh tests/elist_screen_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

.PHONY: app-click-block-zi-test
app-click-block-zi-test: $(ZI2C_BIN)
	@sh tests/app_click_block_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

.PHONY: diary-spelling-test diary-history-test diary-markdown-test
diary-spelling-test: $(ZIRAN_BIN) $(LIBOQS_A) $(SQLITE_SRC) $(SQLITE_AMALGAMATION_H) | build-laws
	@sh tests/diary_spelling_test.sh $(ZIRAN_BIN) $(LIBOQS_A)

diary-history-test: $(ZI2C_BIN)
	@sh tests/diary_history_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

diary-markdown-test: $(ZI2C_BIN) $(ZIRAN_BIN)
	@sh tests/diary_markdown_test.sh $(ZIRAN_BUILD_DIR)/bin
