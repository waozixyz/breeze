# Pages uses the released web app and builds only the website's downloads.
UNPACKAGED_AUDIO_DIR := unpackaged_assets/audio
UNPACKAGED_AUDIO_FILES := $(shell git ls-files -- $(UNPACKAGED_AUDIO_DIR))
MEDITATION_AUDIO_TRACKS := $(patsubst $(UNPACKAGED_AUDIO_DIR)/%,%,$(filter %.ogg,$(UNPACKAGED_AUDIO_FILES)))
MEDITATION_AUDIO_ZIP := web-assets/dl/breathing-meditation-audio-v1.zip
ifeq ($(strip $(MEDITATION_AUDIO_TRACKS)),)
$(error No tracked meditation audio files)
endif

MAKE := $(MAKE) -f site/production.mk
.PHONY: validate-meditation-audio package-unpackaged-assets site-release-assets-check
include mk/site.mk
