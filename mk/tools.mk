# Developer tools: store screenshots, promo, narration, font subsets and git hooks.

screenshot: $(TARGET)
	./scripts/generate-screenshots.sh "$(TARGET)"

.PHONY: screenshot-verify screenshot-review screenshot-export screenshot-source-check play-preflight lumi-promo lumi-narration
screenshot-source-check: $(ZI2C_BIN) | build-laws
	@ZI_CHECK_DEFINES="$(ZI_NATIVE_DEFINES)" python3 scripts/check-zi-sources.py $(ZI2ZIR_BIN) $(KRYON_DIR)/src/ui $(ZIRAN_DIR)/std $(KSS_DIR)/src

screenshot-verify:
	python3 scripts/screenshot-harness.py verify

screenshot-review:
	python3 scripts/screenshot-harness.py review --reviewer "$(REVIEWER)"

screenshot-export:
	python3 scripts/screenshot-harness.py export

play-preflight:
	python3 scripts/upload-play-screenshots.py --preflight-only

lumi-promo:
	python3 scripts/render-lumi-promo.py

lumi-narration:
	python3 scripts/generate-lumi-narration.py

hooks-install:
	sh ./scripts/install-git-hooks.sh

font-subsets:
	sh $(KRYON_DIR)/scripts/subset-fonts.sh "$(FONT_SUBSET_DIR)" \
		"$(KRYON_DIR)/fonts/noto" App $(FONT_SUBSET_CORPUS)
