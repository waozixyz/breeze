# Web build: the canvas app, its smoke test, and the Chrome and Firefox extensions.

$(WEB_GEN_STAMP): Makefile ziran.lock $(ZI2C_BIN) $(ZI_SRCS) $(KRYON_ZI_MODULES) $(GAME2D_MODULES) $(DAOCHI_CLIENT_MODULES) $(wildcard build/packages/self/src/*.zi) $(ZIRAN_STD_MODULES) $(SYNC_RETRY_SOURCE) | build-laws zi-check
	rm -rf $(WEB_GEN_DIR)
	mkdir -p $(WEB_GEN_DIR)
	sh scripts/run-ziran.sh $(ZI2C_BIN) --no-main --root . \
		--define PLATFORM_WEB --define __EMSCRIPTEN__ \
		--module-path src --module-path $(KRYON_DIR)/src/ui \
		--module-path $(KSS_DIR)/src --module-path oqs=$(OQS_DIR)/src --module-path kryon=$(KRYON_DIR)/src/ui --module-path kryon=$(KRYON_DIR)/src/backend \
		--module-path $(KRYON_DIR)/src/backend \
		--module-path $(GAME2D_DIR)/src \
		--module-path qrcode=build/packages/qrcode/src \
		--module-path plot=build/packages/plot/src \
		--module-path $(ZIRAN_DIR)/std \
		--module-path build/packages/daochi-client --module-path self=build/packages/self/src $(ZI_HANDOFF_PATHS) \
		-o $(WEB_GEN_DIR) $(ZI_SRCS) $(KRYON_DIR)/src/backend/canvas_raster.zi $(KRYON_DIR)/src/backend/canvas_audio.zi $(KRYON_DIR)/src/backend/page_route.zi
	touch $@
	find $(WEB_GEN_DIR) -type f \( -name '*.c' -o -name '*.h' \) -exec touch -r $@ {} +

$(WEB_GEN_SRCS) $(WEB_GEN_GAME_C): $(WEB_GEN_STAMP)
	@test -f $@

web-tools-check:
	@missing=0; \
	for tool in "$(WEB_CC)" "$(WEB_AR)" "$(WEB_RANLIB)" "$(WEB_EMCMAKE)"; do \
		if ! command -v "$$tool" >/dev/null 2>&1; then \
			echo "Missing web build tool: $$tool"; \
			missing=1; \
		fi; \
	done; \
	if [ "$$missing" -ne 0 ]; then \
		echo ""; \
		echo "Install Emscripten for this host or run the web build from an environment where Emscripten is on PATH."; \
		echo ""; \
		echo "Required tools: WEB_CC=$(WEB_CC), WEB_AR=$(WEB_AR), WEB_RANLIB=$(WEB_RANLIB), WEB_EMCMAKE=$(WEB_EMCMAKE)."; \
		exit 1; \
	fi

sync-web-icons: $(KRYON_SYNC_ICONS)
	sh $(KRYON_SYNC_ICONS) web-assets/icons $(WEB_SHARED_ICON_SHEETS)
	cp assets/app/icon.png web-assets/icons/$(APP_NAME).png

$(WEB_JS_TARGET): Makefile $(WEB_SRC) $(SQLITE_SRC) $(SQLITE_AMALGAMATION_H) $(FONT_FILES) $(EMBEDDED_ASSETS_C) $(WEB_GEN_STAMP) $(WEB_LIBOQS_A) $(WEB_HOST_JS) web-tools-check | $(WEB_DIST_DIR)
$(WEB_JS_TARGET): | zi-check
	rm -f $(WEB_DIST_DIR)/index.data
	$(WEB_CC) $(WEB_CFLAGS) \
		-iquote$(WEB_GEN_DIR) -iquote$(WEB_GEN_DIR)/src $(WEB_APP_INCLUDE) \
		-I$(SQLITE_BUILD_DIR) \
		$(WEB_LIBOQS_INCLUDE) \
		-DKRYON_BACKEND_CANVAS=1 \
		-DHAS_LIBOQS=1 \
		-DPLATFORM_WEB \
		-o $(WEB_JS_TARGET) \
		$(WEB_SRC) $(GENERATED_WEB_C) $(SQLITE_SRC) $(WEB_BUNDLE_RUNTIME) \
		$(foreach library,$(WEB_HOST_JS),--js-library $(library)) \
		$(WEB_LIBOQS_A) \
		-sASYNCIFY -sASYNCIFY_STACK_SIZE=1048576 -fexceptions \
		-sFORCE_FILESYSTEM=1 -sFETCH=1 -sUSE_ZLIB=1 -lidbfs.js \
		-sALLOW_MEMORY_GROWTH=1 -sINITIAL_MEMORY=268435456 -sSTACK_SIZE=33554432 \
		-sEXPORTED_RUNTIME_METHODS=Asyncify,FS \
		-sEXPORTED_FUNCTIONS=_main,_malloc,_free,_app_web_get_play_in_background,_app_web_set_backgrounded,_app_web_background_tick,_app_web_launch_practice,_app_web_extension_host,_app_web_extension_break_now,_app_web_extension_breaks_enabled,_app_web_extension_break_timer_enabled,_app_web_extension_break_timer_limit_s,_app_web_extension_break_timer_duration_s,_app_web_extension_break_timer_postpone_s,_app_web_extension_break_timer_max_prompts,_app_web_extension_break_timer_show_skip,_app_web_extension_break_timer_show_postpone,_app_web_extension_open_break_settings,_app_web_extension_open_habits,_app_web_test_save_onboarding_state,_app_web_test_onboarding_state,_app_web_test_show_first_run_guide,_app_web_test_first_run_guide_active,_app_web_test_first_run_guide_count,_app_web_test_first_run_guide_step,_app_web_test_first_run_guide_text_clipped,_app_web_test_first_run_guide_next_x,_app_web_test_first_run_guide_next_y,_app_web_test_first_run_guide_close_x,_app_web_test_first_run_guide_close_y,_app_web_test_first_run_guide_anchor_x,_app_web_test_first_run_guide_anchor_y,_app_web_test_first_run_guide_anchor_w,_app_web_test_first_run_guide_anchor_h,_app_web_test_sync_key_state,_app_web_test_import_sync_key,_app_web_test_habits_click_x,_app_web_test_habits_click_y,_app_web_test_show_practice_home,_app_web_test_review_practice_cache,_app_web_test_practice_selected,_app_web_test_practice_tab,_app_web_test_complete_practice,_app_web_test_completion_stage,_app_web_test_completed_practice_persisted,_app_web_test_screen,_app_web_test_tai_chi_course_open,_app_web_test_route_transition_active,_app_web_test_practice_start_click_x,_app_web_test_practice_start_click_y,_app_web_test_practice_action_click_x,_app_web_test_practice_action_click_y,_app_web_test_sun_salutation_control_x,_app_web_test_sun_salutation_control_y,_app_web_test_sun_salutation_step,_app_web_test_sun_salutation_ticks,_app_web_test_sun_salutation_paused,_app_web_test_sun_salutation_character,_app_web_test_show_appearance,_app_web_test_prepare_music,_app_web_test_music_button_x,_app_web_test_music_button_y,_app_web_test_control_x,_app_web_test_control_y,_app_web_test_control_width,_app_web_test_control_height,_app_web_test_enable_extension_breaks

$(WEB_TARGET): src/web_shell.html $(WEB_BOOT_JS) $(WEB_JS_TARGET) manifest.json $(WEB_ASSET_FILES) | $(WEB_DIST_DIR)
	perl -0pe 's#\{\{\{ APP_SCRIPT \}\}\}#$(WEB_APP_SCRIPT)#g; s/WEB_CACHE_BUSTER/$(WEB_CACHE_BUSTER)/g' src/web_shell.html > $@
	cp $(WEB_BOOT_JS) $(WEB_DIST_DIR)/index_boot.js
	perl -0pi -e 's/WEB_CACHE_BUSTER/$(WEB_CACHE_BUSTER)/g' $(WEB_DIST_DIR)/index_boot.js
	rm -rf $(WEB_DIST_DIR)/canvas
	rm -rf $(WEB_DIST_DIR)/web-assets $(WEB_DIST_DIR)/site-icons
	cp -R web-assets $(WEB_DIST_DIR)/
	rm -rf $(WEB_DIST_DIR)/web-assets/dl
	rm -f $(WEB_DIST_DIR)/web-assets/canvas_index.html
	cp -R site-icons $(WEB_DIST_DIR)/
	perl -0pe 's/WEB_CACHE_BUSTER/$(WEB_CACHE_BUSTER)/g' manifest.json > $(WEB_DIST_DIR)/webmanifest.json

web-canvas: web

$(WEB_CANVAS_DIR):
	mkdir -p $@

$(WEB_CANVAS_TARGET): Makefile $(WEB_SRC) $(SQLITE_SRC) $(SQLITE_AMALGAMATION_H) $(FONT_FILES) $(EMBEDDED_ASSETS_C) $(WEB_GEN_STAMP) $(WEB_LIBOQS_A) $(WEB_HOST_JS) src/web_shell.html $(WEB_BOOT_JS) manifest.json $(WEB_ASSET_FILES) web-tools-check | $(WEB_CANVAS_DIR)
$(WEB_CANVAS_TARGET): | zi-check
	rm -f $(WEB_CANVAS_DIR)/index.data
	$(WEB_CC) $(WEB_CFLAGS) \
		-iquote$(WEB_GEN_DIR) -iquote$(WEB_GEN_DIR)/src $(WEB_APP_INCLUDE) \
		-I$(SQLITE_BUILD_DIR) \
		$(WEB_LIBOQS_INCLUDE) \
		-DKRYON_BACKEND_CANVAS=1 \
		-DHAS_LIBOQS=1 \
		-DPLATFORM_WEB \
		-o $(WEB_CANVAS_DIR)/index.js \
		$(WEB_SRC) $(GENERATED_WEB_C) $(SQLITE_SRC) $(WEB_BUNDLE_RUNTIME) \
		$(foreach library,$(WEB_HOST_JS),--js-library $(library)) \
		$(WEB_LIBOQS_A) \
		-sASYNCIFY -sASYNCIFY_STACK_SIZE=1048576 -fexceptions \
		-sFORCE_FILESYSTEM=1 -sFETCH=1 -sUSE_ZLIB=1 -lidbfs.js \
		-sALLOW_MEMORY_GROWTH=1 -sINITIAL_MEMORY=268435456 -sSTACK_SIZE=33554432 \
		-sEXPORTED_RUNTIME_METHODS=Asyncify,FS \
		-sEXPORTED_FUNCTIONS=_main,_malloc,_free,_app_web_get_play_in_background,_app_web_set_backgrounded,_app_web_background_tick,_app_web_launch_practice,_app_web_extension_host,_app_web_extension_break_now,_app_web_extension_breaks_enabled,_app_web_extension_break_timer_enabled,_app_web_extension_break_timer_limit_s,_app_web_extension_break_timer_duration_s,_app_web_extension_break_timer_postpone_s,_app_web_extension_break_timer_max_prompts,_app_web_extension_break_timer_show_skip,_app_web_extension_break_timer_show_postpone,_app_web_extension_open_break_settings,_app_web_extension_open_habits,_app_web_test_save_onboarding_state,_app_web_test_onboarding_state,_app_web_test_show_first_run_guide,_app_web_test_first_run_guide_active,_app_web_test_first_run_guide_count,_app_web_test_first_run_guide_step,_app_web_test_first_run_guide_text_clipped,_app_web_test_first_run_guide_next_x,_app_web_test_first_run_guide_next_y,_app_web_test_first_run_guide_close_x,_app_web_test_first_run_guide_close_y,_app_web_test_first_run_guide_anchor_x,_app_web_test_first_run_guide_anchor_y,_app_web_test_first_run_guide_anchor_w,_app_web_test_first_run_guide_anchor_h,_app_web_test_sync_key_state,_app_web_test_import_sync_key,_app_web_test_habits_click_x,_app_web_test_habits_click_y,_app_web_test_show_practice_home,_app_web_test_review_practice_cache,_app_web_test_practice_selected,_app_web_test_practice_tab,_app_web_test_complete_practice,_app_web_test_completion_stage,_app_web_test_completed_practice_persisted,_app_web_test_screen,_app_web_test_tai_chi_course_open,_app_web_test_route_transition_active,_app_web_test_practice_start_click_x,_app_web_test_practice_start_click_y,_app_web_test_practice_action_click_x,_app_web_test_practice_action_click_y,_app_web_test_sun_salutation_control_x,_app_web_test_sun_salutation_control_y,_app_web_test_sun_salutation_step,_app_web_test_sun_salutation_ticks,_app_web_test_sun_salutation_paused,_app_web_test_sun_salutation_character,_app_web_test_show_appearance,_app_web_test_prepare_music,_app_web_test_music_button_x,_app_web_test_music_button_y,_app_web_test_control_x,_app_web_test_control_y,_app_web_test_control_width,_app_web_test_control_height,_app_web_test_enable_extension_breaks
	perl -0pe 's#\{\{\{ APP_SCRIPT \}\}\}#$(WEB_CANVAS_APP_SCRIPT)#g; s/WEB_CACHE_BUSTER/$(WEB_CACHE_BUSTER)/g' src/web_shell.html > $@
	cp $(WEB_BOOT_JS) $(WEB_CANVAS_DIR)/index_boot.js
	perl -0pi -e 's/WEB_CACHE_BUSTER/$(WEB_CACHE_BUSTER)/g' $(WEB_CANVAS_DIR)/index_boot.js
	rm -rf $(WEB_CANVAS_DIR)/web-assets $(WEB_CANVAS_DIR)/site-icons
	cp -R web-assets $(WEB_CANVAS_DIR)/
	rm -rf $(WEB_CANVAS_DIR)/web-assets/dl
	rm -f $(WEB_CANVAS_DIR)/web-assets/canvas_index.html
	cp -R site-icons $(WEB_CANVAS_DIR)/
	perl -0pe 's/WEB_CACHE_BUSTER/$(WEB_CACHE_BUSTER)/g' manifest.json > $(WEB_CANVAS_DIR)/webmanifest.json

web:
	$(MAKE) sync-web-icons
	$(MAKE) $(WEB_TARGET)
	$(MAKE) web-smoke-test
	rm -f $(WEB_DIST_ZIP)
	cd $(WEB_DIST_DIR) && zip -9 -r $(abspath $(WEB_DIST_ZIP)) .

web-smoke-test: $(WEB_SMOKE_TEST)
	node tests/web_storage_test.mjs
	WEB_SMOKE_RENDERER=canvas WEB_SMOKE_BROWSER="$(WEB_SMOKE_BROWSER)" node $(WEB_SMOKE_TEST) $(WEB_DIST_DIR)

chrome-web-store: $(CHROME_WEB_STORE_ZIP)

$(CHROME_WEB_STORE_ZIP): $(WEB_TARGET) $(CHROME_WEB_STORE_MANIFEST) $(CHROME_WEB_STORE_WORKER) $(CHROME_WEB_STORE_EXTENSION_BOOT) $(CHROME_WEB_STORE_EXTENSION_APP) $(CHROME_WEB_STORE_ICONS) | $(CHROME_WEB_STORE_DIR)
	rm -rf $(CHROME_WEB_STORE_DIR)
	mkdir -p $(CHROME_WEB_STORE_DIR)/icons
	cp -R $(WEB_DIST_DIR)/. $(CHROME_WEB_STORE_DIR)/
	rm -rf $(CHROME_WEB_STORE_DIR)/canvas $(CHROME_WEB_STORE_DIR)/web-assets/dl
	cp $(CHROME_WEB_STORE_EXTENSION_BOOT) $(CHROME_WEB_STORE_DIR)/extension_boot.js
	cp $(CHROME_WEB_STORE_EXTENSION_APP) $(CHROME_WEB_STORE_DIR)/extension_app.js
	perl -0pi -e 's#(<script src="index_boot\.js\?v=[^"]+"></script>)#<script src="extension_boot.js"></script>\n    $$1#' $(CHROME_WEB_STORE_DIR)/index.html
	perl -0pi -e 's#<script>window\.__inbeRenderer="canvas";window\.__inbeLoadApp\("index\.js\?v=[^"]+"\)</script>#<script src="extension_app.js"></script>#' $(CHROME_WEB_STORE_DIR)/index.html
	sed -e 's#__APP_VERSION__#$(APP_VERSION)#g' \
		$(CHROME_WEB_STORE_MANIFEST) > $(CHROME_WEB_STORE_DIR)/manifest.json
	cp $(CHROME_WEB_STORE_WORKER) $(CHROME_WEB_STORE_DIR)/service_worker.js
	cp $(CHROME_WEB_STORE_ICONS) $(CHROME_WEB_STORE_DIR)/icons/
	rm -f $(CHROME_WEB_STORE_ZIP)
	cd $(CHROME_WEB_STORE_DIR) && zip -9 -r $(abspath $(CHROME_WEB_STORE_ZIP)) .

firefox-addons: $(FIREFOX_ADDONS_ZIP)

$(FIREFOX_ADDONS_ZIP): $(WEB_TARGET) src/web_shell.html $(FIREFOX_ADDONS_MANIFEST) $(FIREFOX_ADDONS_BACKGROUND) $(FIREFOX_ADDONS_LOADER) $(FIREFOX_ADDONS_ICONS) | $(FIREFOX_ADDONS_DIR)
	rm -rf $(FIREFOX_ADDONS_DIR)
	mkdir -p $(FIREFOX_ADDONS_DIR)/icons
	cp -R $(WEB_DIST_DIR)/. $(FIREFOX_ADDONS_DIR)/
	rm -rf $(FIREFOX_ADDONS_DIR)/canvas $(FIREFOX_ADDONS_DIR)/web-assets/dl
	sed -e 's#__APP_VERSION__#$(APP_VERSION)#g' \
		$(FIREFOX_ADDONS_MANIFEST) > $(FIREFOX_ADDONS_DIR)/manifest.json
	cp $(FIREFOX_ADDONS_BACKGROUND) $(FIREFOX_ADDONS_DIR)/background.js
	cp $(FIREFOX_ADDONS_LOADER) $(FIREFOX_ADDONS_DIR)/extension_loader.js
	perl -0pe 's#\{\{\{ APP_SCRIPT \}\}\}#$(FIREFOX_ADDONS_APP_SCRIPT)#g; s/WEB_CACHE_BUSTER/$(WEB_CACHE_BUSTER)/g' src/web_shell.html > $(FIREFOX_ADDONS_INDEX)
	cp $(FIREFOX_ADDONS_ICONS) $(FIREFOX_ADDONS_DIR)/icons/
	rm -f $(FIREFOX_ADDONS_ZIP)
	cd $(FIREFOX_ADDONS_DIR) && zip -9 -r $(abspath $(FIREFOX_ADDONS_ZIP)) .

firefox-addons-lint: $(FIREFOX_ADDONS_ZIP)
	$(ADDONS_LINTER) $(FIREFOX_ADDONS_ZIP)

firefox-addons-source-zip:
	sh scripts/build-firefox-addons-source-zip.sh $(FIREFOX_ADDONS_SOURCE_ZIP)

verify-firefox-addons: firefox-addons-lint firefox-addons-source-zip

.PHONY: device-key-wasm-test
device-key-wasm-test: $(ZI2C_BIN)
	python3 tests/device_key_zi_test.py $(ZI2C_BIN) --wasm --emcc $(WEB_CC)

web-smoke-test: device-key-wasm-test
