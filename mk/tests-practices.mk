# Practice tests: breathing, breaks, patterns, meditation, sun salutation, narration.

BREATH_TIMING_GEN_DIR := $(BUILD_DIR)/breath-timing-test/generated
BREAK_RULES_GEN_DIR := $(BUILD_DIR)/break-rules-test/generated

.PHONY: breath-timing-test
breath-timing-test: $(ZI2C_BIN)
	@sh tests/breath_timing_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

.PHONY: break-rules-test
break-rules-test: $(ZI2C_BIN)
	@sh tests/break_rules_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

.PHONY: sun-salutation-test
sun-salutation-test: $(ZI2C_BIN)
	@sh tests/sun_salutation_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

.PHONY: sun-salutation-assets-test
sun-salutation-assets-test:
	python3 tests/sun_salutation_assets_test.py

.PHONY: break-engine-test
break-engine-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY sh tests/break_engine_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

.PHONY: breath-engine-test
breath-engine-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY sh tests/breath_rounds_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

.PHONY: exercise-types-test
exercise-types-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/exercise_types_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

.PHONY: patterns-rules-zi-test
patterns-rules-zi-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/patterns_rules_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

.PHONY: patterns-session-zi-test
patterns-session-zi-test: $(ZI2C_BIN)
	@sh tests/patterns_session_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

.PHONY: session-results-zi-test
session-results-zi-test: apps $(ZI2C_BIN) $(ZIRAN_BUILD_DIR)/libziran.a $(SQLITE_SRC) $(LIBOQS_A) $(RAYLIB_A)
	@sh tests/session_results_zi_test.sh $(ZIRAN_BUILD_DIR)/bin/ziran $(LIBOQS_A)
	@$(ZI2C_BIN) --no-main --root tests --module-path build/packages/ziran/std \
		-o $(BUILD_DIR)/session-mood-generated tests/session_result_storage_behavior.zi
	@$(CC) -std=c11 -Isrc/storage -Ibuild/packages/ziran/include \
		-I$(BUILD_DIR)/session-mood-generated \
		$(BUILD_DIR)/session-mood-generated/*.c -o $(BUILD_DIR)/session-result-host-test
	@env -u DISPLAY -u WAYLAND_DISPLAY $(BUILD_DIR)/session-result-host-test

.PHONY: music-library-zi-test
music-library-zi-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/music_library_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

.PHONY: break-stats-zi-test
break-stats-zi-test: $(ZI2C_BIN) $(SQLITE_AMALGAMATION_C) $(SQLITE_AMALGAMATION_H)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/break_stats_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

.PHONY: meditation-timing-test
meditation-timing-test: build-laws $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/meditation_timing_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

.PHONY: meditation-audio-archive-zi-test
meditation-audio-archive-zi-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/meditation_audio_archive_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

$(BREATH_TIMING_GEN_DIR)/core/breath_timing.c: src/core/breath_timing.zi src/core/types.zi $(ZI2C_BIN)
	@mkdir -p $(BREATH_TIMING_GEN_DIR)
	$(ZI2C_BIN) --no-main --root src \
		-o $(BREATH_TIMING_GEN_DIR) src/core/breath_timing.zi

$(BREAK_RULES_GEN_DIR)/breaks/break_rules.c: src/breaks/break_rules.zi src/breaks/break_types.zi $(ZI2C_BIN)
	@mkdir -p $(BREAK_RULES_GEN_DIR)
	$(ZI2C_BIN) --no-main --root src \
		-o $(BREAK_RULES_GEN_DIR) src/breaks/break_rules.zi

.PHONY: practice-downloads-test
practice-downloads-test: apps $(ZIRAN_BUILD_DIR)/libziran.a
	python3 tests/practice_downloads_test.py

.PHONY: practice-narration-test
practice-narration-test: $(ZI2C_BIN) $(ZIRAN_BUILD_DIR)/libziran.a
	sh tests/practice_narration_test.sh $(ZIRAN_BUILD_DIR)/bin

.PHONY: practice-narration-keys-test
.PHONY: astral-projection-test
astral-projection-test: $(ZI2C_BIN)
	sh tests/astral_projection_test.sh $(ZIRAN_BUILD_DIR)/bin

.PHONY: workout-test
workout-test: $(ZI2C_BIN)
	sh tests/practice_figure_test.sh $(ZIRAN_BUILD_DIR)/bin tests/workout_behavior.zi

.PHONY: sun-salutation-pose-test
sun-salutation-pose-test: $(ZI2C_BIN)
	sh tests/practice_figure_test.sh $(ZIRAN_BUILD_DIR)/bin tests/sun_salutation_pose_behavior.zi

test: sun-salutation-pose-test

.PHONY: sun-salutation-artwork-test
sun-salutation-artwork-test: $(ZI2C_BIN)
	sh tests/practice_figure_test.sh $(ZIRAN_BUILD_DIR)/bin tests/sun_salutation_artwork_behavior.zi

test: sun-salutation-artwork-test

.PHONY: sun-salutation-voice-test
sun-salutation-voice-test: $(ZI2C_BIN)
	sh tests/practice_figure_test.sh $(ZIRAN_BUILD_DIR)/bin tests/sun_salutation_voice_behavior.zi

test: sun-salutation-voice-test

practice-narration-keys-test:
	python3 tests/practice_narration_keys_test.py

.PHONY: practice-narration-snapshot-test
practice-narration-snapshot-test:
	python3 tests/practice_narration_snapshot_test.py
