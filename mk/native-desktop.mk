# Kryon's desktop host and the codecs its raster and mixer link.
DESKTOP_HOST_PKGS := sdl2 cairo freetype2 pangocairo fontconfig gio-2.0 x11
DESKTOP_HOST_CFLAGS ?= $(shell pkg-config --cflags $(DESKTOP_HOST_PKGS) 2>/dev/null)
DESKTOP_HOST_LDLIBS ?= $(shell pkg-config --libs $(DESKTOP_HOST_PKGS) 2>/dev/null)
KRYON_NATIVE_BACKEND_DEPS := $(WEBP_A) $(AVIF_A) $(AOM_A) $(AUDIO_MP3_A) $(AUDIO_VORBIS_A)
KRYON_NATIVE_BACKEND_LIBS := $(WEBP_A) $(AVIF_A) $(AOM_A) $(AUDIO_MP3_A) $(AUDIO_VORBIS_LIBS)
KRYON_NATIVE_BACKEND_CFLAGS := $(DESKTOP_HOST_CFLAGS)
KRYON_NATIVE_BACKEND_LDLIBS := $(DESKTOP_HOST_LDLIBS)
ifneq ($(strip $(APP_GIO_LDLIBS)),)
KRYON_NATIVE_BACKEND_CFLAGS += -DAPP_HAVE_GIO $(APP_GIO_CFLAGS)
NATIVE_SYSTEM_LDLIBS += $(APP_GIO_LDLIBS)
endif
# Kryon decodes Ogg Opus narration with static libopus; Windows links its own
# MinGW build (mk/windows.mk) and Apple has no native Opus provider yet.
ifneq ($(NATIVE_PLATFORM),darwin)
KRYON_NATIVE_BACKEND_DEPS += $(AUDIO_OPUS_A)
NATIVE_SYSTEM_LDLIBS := $(AUDIO_OPUS_A) $(NATIVE_SYSTEM_LDLIBS)
endif

$(TARGET): mk/native-desktop.mk
