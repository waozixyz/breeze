# The native Plan 9 build's generated inputs for the mkfile.

PLAN9_DIR := $(BUILD_DIR)/plan9
PLAN9_GENERATED := $(PLAN9_DIR)/generated
PLAN9_FILE_LIST := $(PLAN9_DIR)/generated-c-files.txt
PLAN9_EMBEDDED_ASSETS_C := $(PLAN9_DIR)/app_embedded_assets.c

# Native Plan 9 build inputs: Ziran emits 8c-safe C directly, the embedded
# table carries the locales, images, and subset fonts (audio stays
# stubbed on Plan 9, so the OGG sounds are not carried), and the file
# list feeds the mkfile.
.PHONY: zi-c-plan9
zi-c-plan9: $(KRY_GEN_STAMP)
	rm -rf $(PLAN9_GENERATED)
	sh scripts/run-ziran.sh $(ZI2C_BIN) --no-main --plan9 --define PLAN9_BUILD \
		--define KRYON_PLATFORM_PLAN9 --root . \
		--module-path src --module-path $(KRYON_DIR)/src/ui \
		--module-path $(KSS_DIR)/src --module-path oqs=$(OQS_DIR)/src --module-path kryon=$(KRYON_DIR)/src/ui --module-path kryon=$(KRYON_DIR)/src/backend \
		--module-path $(KRYON_DIR)/src/backend \
		--module-path $(GAME2D_DIR)/src \
		--module-path qrcode=build/packages/qrcode/src \
		--module-path plot=build/packages/plot/src \
		--module-path self=build/packages/self/src \
		--module-path $(ZIRAN_DIR)/std \
		--include-dir build/packages/kryon/include --include-dir src \
		--include-dir $(KRY_GEN_DIR) --include-dir vendor-builds/sqlite \
		-o $(PLAN9_GENERATED) $(ZI_SRCS)
	cp $(STORAGE_LAYOUT_HEADER) $(PLAN9_GENERATED)/storage_layout.h
	find $(PLAN9_GENERATED) -type f -name '*.c' | LC_ALL=C sort > $(PLAN9_FILE_LIST)
	sh build/packages/kryon/scripts/embed-assets.sh $(PLAN9_EMBEDDED_ASSETS_C) \
		$(STYLE_FILES) $(LOCALE_FILES) $(IMAGE_FILES) $(FONT_FILES)
