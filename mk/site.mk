# The website and its meditation audio download.

validate-meditation-audio:
	@set -e; \
	for file in $(MEDITATION_AUDIO_TRACKS); do \
		path="$(UNPACKAGED_AUDIO_DIR)/$$file"; \
		if [ ! -f "$$path" ]; then \
			echo "Missing meditation audio track: $$path"; \
			exit 1; \
		fi; \
		size=$$(wc -c < "$$path" | tr -d ' '); \
		magic=$$(dd if="$$path" bs=4 count=1 2>/dev/null); \
		if [ "$$magic" != "OggS" ] || [ "$$size" -lt 4096 ]; then \
			echo "Invalid meditation audio track: $$path"; \
			echo "Expected a real Ogg file. If this is a Git LFS pointer, run git lfs pull."; \
			exit 1; \
		fi; \
	done

$(MEDITATION_AUDIO_ZIP): $(UNPACKAGED_AUDIO_FILES)
	$(MAKE) validate-meditation-audio
	mkdir -p $(dir $(MEDITATION_AUDIO_ZIP))
	rm -f $(MEDITATION_AUDIO_ZIP)
	cd $(UNPACKAGED_AUDIO_DIR) && zip -9 -r $(abspath $(MEDITATION_AUDIO_ZIP)) $(MEDITATION_AUDIO_TRACKS) LICENSE.md MANIFEST.txt

package-unpackaged-assets: validate-meditation-audio $(MEDITATION_AUDIO_ZIP)

site: package-unpackaged-assets web
	sh site/build.sh

site-release-assets-check:
	sh scripts/check-site-release-assets.sh
