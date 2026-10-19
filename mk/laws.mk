# Build laws: the version, proof and locale checks every artifact build runs first.

.PHONY: asset-text-tests
asset-text-tests:
	@python3 tests/font_glyph_coverage_test.py
	@python3 tests/locale_keys_test.py
	@python3 tests/settings_keys_test.py

.PHONY: version-check
version-check:
	python3 scripts/check-version.py

# Laws are checked by the Ziran compiler on every invocation. `ziran check`
# exits nonzero on any disproved or unwaived unknown law.
.PHONY: proofs build-laws
proofs: $(ZI2C_BIN)
	@for module in $(LAW_MODULES); do \
		$(ZIRAN_BIN) check --root src --module-path $(KRYON_DIR)/src/ui \
			--module-path $(ZIRAN_DIR)/std $$module > /dev/null || exit 1; \
	done

build-laws: version-check proofs locale-check

.PHONY: locale-check
locale-check: asset-text-tests locale-translated-test locale-used-keys-test

.PHONY: locale-used-keys-test
locale-used-keys-test:
	@python3 tests/locale_used_keys_test.py

.PHONY: locale-translated-test
locale-translated-test:
	@python3 tests/locale_translated_test.py
