# Source, asset and release tooling checks that make test runs.

.PHONY: fdroid-build-test
fdroid-build-test:
	python3 tests/fdroid_build_test.py

.SILENT: package-check test font-bundle-check audio-test-fixture-check embedded-image-assets-check

package-check:
	sh scripts/check-packages.sh

clean-text-api-check:
	python3 scripts/check-clean-text-api.py src tests

.PHONY: button-api-check
button-api-check:
	bash scripts/check-button-api.sh

.PHONY: version-test
version-test:
	python3 tests/version_test.py

.PHONY: proof-test
# Deliberately broken implementations must be rejected by the laws.
proof-test: $(ZI2C_BIN)
	sh tests/law_mutation_test.sh $(ZIRAN_BIN)

secret-check:
	python3 ./scripts/check-secrets.py --working-tree

secret-check-history:
	python3 ./scripts/check-secrets.py --history

embedded-image-assets-check: $(EMBEDDED_ASSETS_C)
	bash ./tests/embedded_image_assets_test.sh

# An icon from a Kryon sheet Inbe does not ship shows "Missing image".
.PHONY: icon-sheets-check
icon-sheets-check: $(PACKAGES_MK)
	python3 tests/icon_sheets_test.py $(KRYON_DIR)/src/ui/icon.zi

.PHONY: storage-literals-check
storage-literals-check:
	python3 tests/storage_literals_test.py
	bash ./scripts/check-storage-literals.sh

# Every test entry point in tests/ is run by a make target, workflow or script.
.PHONY: test-references-check
test-references-check:
	python3 scripts/check-test-references.py

.PHONY: screenshot-scene-test
screenshot-scene-test:
	bash ./tests/screenshot_scene_test.sh

audio-test-fixture-check:
	printf '%s  %s\n' \
		d1f25feccd8af5cfe22ca1ed6afa901a5f97cbf976b93fc46096a2bd83315034 \
		test-fixtures/audio/autumn-sunset.mp3 | sha256sum -c - >/dev/null

font-bundle-check:
	for font in $(FONT_FILES); do \
		case "$$font" in \
			$(KRYON_DIR)/fonts/noto/*) \
				echo "Full Noto font must not be embedded: $$font"; \
				exit 1; \
				;; \
		esac; \
	done

.PHONY: package-size-test
package-size-test:
	python3 tests/package_size_test.py

.PHONY: phone-check-gate-test
phone-check-gate-test:
	python3 tests/phone_check_gate_test.py

.PHONY: release-tooling-test
release-tooling-test:
	python3 tests/release_test.py
	python3 tests/file_size_test.py

.PHONY: play-screenshots-test
play-screenshots-test:
	python3 tests/play_screenshots_test.py
