# Practice narration is Ogg Opus, decoded by the audio package's audio/opus.
# libopus is linked statically from the audio package's pinned source with
# its own native recipe, so no installed package needs a system libopus.
AUDIO_PACKAGE_DIR := build/packages/audio
AUDIO_OPUS_DIR := build/packages/libopus
AUDIO_SAMPLERATE_DIR := build/packages/libsamplerate
AUDIO_CODECS_BUILD_DIR := $(NATIVE_VENDOR_BUILD_DIR)/audio-codecs
AUDIO_OPUS_A := $(AUDIO_CODECS_BUILD_DIR)/libopus/libopus.a
# Ziran's mixer streams MP3 with dr_mp3 and Ogg Vorbis with libvorbisfile,
# built by Ziran's own recipes through the audio package's native project.
AUDIO_MP3_A := $(AUDIO_CODECS_BUILD_DIR)/libziran_mp3.a
AUDIO_VORBIS_A := $(AUDIO_CODECS_BUILD_DIR)/libvorbisfile.a
AUDIO_VORBIS_LIBS := $(AUDIO_VORBIS_A) $(AUDIO_CODECS_BUILD_DIR)/libvorbis.a $(AUDIO_CODECS_BUILD_DIR)/libogg.a

$(AUDIO_OPUS_A) $(AUDIO_MP3_A) $(AUDIO_VORBIS_LIBS) &: $(AUDIO_PACKAGE_DIR)/native/AudioCodecs.cmake $(AUDIO_PACKAGE_DIR)/native/CMakeLists.txt $(AUDIO_OPUS_DIR)/CMakeLists.txt $(ZIRAN_DIR)/std/native/AudioCodecs.cmake ziran.lock mk/audio-codecs.mk
	$(CMAKE) -S $(AUDIO_PACKAGE_DIR)/native -B $(AUDIO_CODECS_BUILD_DIR) \
		-DCMAKE_BUILD_TYPE=Release \
		-DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
		-DOPUS_DIR=$(abspath $(AUDIO_OPUS_DIR)) \
		-DSAMPLERATE_DIR=$(abspath $(AUDIO_SAMPLERATE_DIR)) \
		-DZIRAN_STDLIB=$(abspath $(ZIRAN_DIR))/std
	$(CMAKE) --build $(AUDIO_CODECS_BUILD_DIR) --target opus ziran_mp3 vorbisfile
	@for archive in $(AUDIO_OPUS_A) $(AUDIO_MP3_A) $(AUDIO_VORBIS_LIBS); do test -f $$archive || { echo "Missing $$archive" >&2; exit 1; }; done
