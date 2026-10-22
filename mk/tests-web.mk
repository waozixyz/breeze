# Web tests: browser smoke runs, extensions, web hosts and site assets.

.PHONY: firefox-startup-test
firefox-startup-test:
	node --test tests/firefox_startup_test.mjs

.PHONY: web-storage-bridge-test
web-storage-bridge-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/web_storage_bridge_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

.PHONY: web-bridge-wasm-test
web-bridge-wasm-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/web_bridge_wasm_test.sh $(ZIRAN_BUILD_DIR)/bin $(WEB_CC)

.PHONY: web-window-zi-test
web-window-zi-test: $(ZI2C_BIN)
	@sh tests/web_window_zi_test.sh $(abspath $(dir $(ZI2C_BIN)))

.PHONY: site-assets-test
site-assets-test:
	node tests/site_assets_test.mjs

web-canvas-smoke-test: $(WEB_SMOKE_TEST)
	WEB_SMOKE_RENDERER=canvas WEB_SMOKE_BROWSER="$(WEB_SMOKE_BROWSER)" node $(WEB_SMOKE_TEST) $(WEB_DIST_DIR)

web-compare-test:
	$(MAKE) $(WEB_TARGET)
	$(MAKE) web-smoke-test

web-side-by-side-test: $(WEB_SIDE_BY_SIDE_TEST)
	bash $(WEB_SIDE_BY_SIDE_TEST)

web-smoke-test-firefox: $(WEB_SMOKE_TEST)
	WEB_SMOKE_RENDERER=canvas WEB_SMOKE_BROWSER="firefox" node $(WEB_SMOKE_TEST) $(WEB_DIST_DIR)

web-smoke-test-librewolf: $(WEB_SMOKE_TEST)
	WEB_SMOKE_RENDERER=canvas WEB_SMOKE_BROWSER="librewolf" node $(WEB_SMOKE_TEST) $(WEB_DIST_DIR)

chrome-web-store-test: chrome-web-store
	node scripts/chrome-extension-breaks-test.mjs
	node scripts/chrome-extension-live-test.mjs $(CHROME_WEB_STORE_DIR)
	unzip -t $(CHROME_WEB_STORE_ZIP) >/dev/null
	test -f $(CHROME_WEB_STORE_DIR)/web-assets/icons/chromewebstore.png
	test -f $(CHROME_WEB_STORE_DIR)/extension_boot.js
	test -f $(CHROME_WEB_STORE_DIR)/extension_app.js
	grep -q 'src="extension_boot.js"' $(CHROME_WEB_STORE_DIR)/index.html
	grep -q 'src="extension_app.js"' $(CHROME_WEB_STORE_DIR)/index.html
	! grep -q '<script>window.__inbeRenderer' $(CHROME_WEB_STORE_DIR)/index.html
	grep -q 'notifications' $(CHROME_WEB_STORE_DIR)/manifest.json

web-canvas-smoke-test: device-key-wasm-test
