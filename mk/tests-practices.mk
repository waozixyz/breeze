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

.PHONY: break-activity-x11-test
break-activity-x11-test: $(ZI2C_BIN)
	@sh tests/break_activity_x11_test.sh $(ZIRAN_BUILD_DIR)/bin

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
session-results-zi-test: apps $(ZI2C_BIN) $(ZIRAN_BUILD_DIR)/libziran.a $(SQLITE_SRC) $(LIBOQS_A) $(AUDIO_MP3_A) $(AUDIO_VORBIS_LIBS)
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

# Real Ogg Opus narration and Lumi guide lines play to completion through
# Ziran's mixer and the audio package's libopus.
.PHONY: voice-audio-play-test
voice-audio-play-test: $(ZIRAN_BIN) $(AUDIO_OPUS_A)
	sh tests/voice_audio_play_test.sh $(ZIRAN_BUILD_DIR)/bin $(abspath $(AUDIO_OPUS_A))

# Defaults to every supported locale; select a completed set for focused local
# validation with ASTRAL_NARRATION_LOCALE=pt. Missing recordings fail explicitly.
ASTRAL_NARRATION_LOCALE ?= all
.PHONY: astral-voice-audio-play-test
astral-voice-audio-play-test: $(ZIRAN_BIN) $(AUDIO_OPUS_A)
	sh tests/voice_audio_play_test.sh $(ZIRAN_BUILD_DIR)/bin $(abspath $(AUDIO_OPUS_A)) \
		build/packages/practices astral $(ASTRAL_NARRATION_LOCALE)

.PHONY: practice-narration-keys-test
.PHONY: ming-narration-test
ming-narration-test:
	python3 tests/narration_segments_test.py
	python3 tests/ming_narration_test.py
	python3 tests/ming_verification_test.py
	python3 tests/narration_attempts_test.py
	python3 tests/narration_speaker_context_test.py
	python3 tests/context_narration_migration_test.py
	python3 tests/portuguese_count_context_test.py
	python3 tests/narration_encoding_headroom_test.py
	python3 tests/local_narration_pipeline_test.py
	python3 tests/local_narration_retry_test.py
	python3 tests/local_voice_adapters_test.py
	python3 tests/retired_locales_test.py

# Real waveform/cache/PCM fixtures need numpy and soundfile; no model is loaded.
.PHONY: ming-segment-pipeline-test
ming-segment-pipeline-test:
	python3 tests/ming_segment_pipeline_test.py

.PHONY: astral-projection-test
astral-projection-test: $(ZI2C_BIN)
	sh tests/astral_projection_test.sh $(ZIRAN_BUILD_DIR)/bin
	sh tests/astral_technique_test.sh $(ZIRAN_BUILD_DIR)/bin $(ZIRAN_DIR)/std
	python3 tests/astral_narration_test.py

.PHONY: practice-banner-motion-test
practice-banner-motion-test: $(ZIRAN_BIN)
	$(ZIRAN_BIN) tests/practice_banner_motion_test.zi

# Alpha GPU regression using the linked native test and the canonical banner art.
BANNER_SHADER_TEST_ASSETS ?= $(abspath $(BUILD_DIR)/packages/practices)
.PHONY: practice-banner-shader-test
practice-banner-shader-test:
	@test -n "$(BANNER_SHADER_TEST_EXE)" || { echo "Set BANNER_SHADER_TEST_EXE to the native shader test executable"; exit 2; }
	python3 tests/practice_banner_shader_test.py "$(abspath $(BANNER_SHADER_TEST_EXE))" "$(BANNER_SHADER_TEST_ASSETS)"

.PHONY: workout-test
workout-test: $(ZI2C_BIN)
	sh tests/practice_figure_test.sh $(ZIRAN_BUILD_DIR)/bin tests/workout_behavior.zi
	sh tests/practice_figure_test.sh $(ZIRAN_BUILD_DIR)/bin tests/workout_custom_behavior.zi

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
	python3 tests/practice_jungle_narration_test.py

.PHONY: astral-projection-ui-test
astral-projection-ui-test: $(TARGET) $(INBE_FULL_BUNDLE)
	@env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u DBUS_SESSION_BUS_ADDRESS \
		-u GDK_DISPLAY -u SESSION_MANAGER YUE_DESKTOP_RECOVERY=0 \
		python3 tests/astral_projection_ui_test.py $(abspath $(TARGET))

.PHONY: tai-chi-preview-test
tai-chi-preview-test:
	python3 tests/tai_chi_preview_test.py

test: tai-chi-preview-test
