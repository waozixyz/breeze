# Practice narration is Ogg Opus, decoded by Kryon's audio/opus. libopus is
# linked statically from the audio package's pinned source with its own
# native recipe, so no installed package needs a system libopus.
AUDIO_PACKAGE_DIR := build/packages/audio
AUDIO_OPUS_DIR := build/packages/libopus
AUDIO_SAMPLERATE_DIR := build/packages/libsamplerate
AUDIO_CODECS_BUILD_DIR := $(NATIVE_VENDOR_BUILD_DIR)/audio-codecs
AUDIO_OPUS_A := $(AUDIO_CODECS_BUILD_DIR)/libopus/libopus.a

$(AUDIO_OPUS_A): $(AUDIO_PACKAGE_DIR)/native/AudioCodecs.cmake $(AUDIO_OPUS_DIR)/CMakeLists.txt mk/audio-codecs.mk
	$(CMAKE) -S $(AUDIO_PACKAGE_DIR)/native -B $(AUDIO_CODECS_BUILD_DIR) \
		-DCMAKE_BUILD_TYPE=Release \
		-DOPUS_DIR=$(abspath $(AUDIO_OPUS_DIR)) \
		-DSAMPLERATE_DIR=$(abspath $(AUDIO_SAMPLERATE_DIR))
	$(CMAKE) --build $(AUDIO_CODECS_BUILD_DIR) --target opus
	@test -f $@
