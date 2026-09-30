.DEFAULT_GOAL := all

APP_NAME := inbe
APP_TITLE := Inner Breeze
# `make install` installs the production desktop app for this user.
PREFIX ?= $(HOME)/.local
ANDROID_APP_ID := xyz.waozi.inbe
ANDROID_DEBUG_APP_ID := $(ANDROID_APP_ID).debug
ANDROID_ACTIVITY := xyz.waozi.inbe.MainActivity

CC ?= cc
CMAKE ?= $(shell if [ -x /usr/bin/cmake ]; then echo /usr/bin/cmake; else command -v cmake; fi)
GRADLE ?= droid/gradlew
ADB ?= adb
UNAME_S := $(shell uname -s)
UNAME_M := $(shell uname -m)
NATIVE_PLATFORM := $(if $(filter FreeBSD,$(UNAME_S)),freebsd,$(if $(filter Linux,$(UNAME_S)),linux,$(shell printf '%s' "$(UNAME_S)" | tr '[:upper:]' '[:lower:]')))
ARCH := $(if $(filter amd64,$(UNAME_M)),x86_64,$(UNAME_M))
ANDROID_SDK ?= $(if $(ANDROID_SDK_ROOT),$(ANDROID_SDK_ROOT),$(if $(ANDROID_HOME),$(ANDROID_HOME),$(shell sed -n 's/^sdk\.dir=//p' droid/local.properties 2>/dev/null | head -n 1)))
ANDROID_CMAKE_DIR ?= $(ANDROID_SDK)/cmake/3.22.1
ANDROID_AAPT2 ?= $(shell if [ -n "$(ANDROID_SDK)" ]; then find "$(ANDROID_SDK)/build-tools" -mindepth 2 -maxdepth 2 -type f -name aapt2 -perm -111 2>/dev/null | sort | tail -n 1; fi)
ANDROID_GRADLE_ARGS := $(if $(ANDROID_AAPT2),-Pandroid.aapt2FromMavenOverride="$(ANDROID_AAPT2)",)
ANDROID_JAVA_HOME ?= $(shell for dir in /usr/local/openjdk17 /usr/lib/jvm/java-17-openjdk-amd64 /usr/lib/jvm/java-17-openjdk; do if [ -x "$$dir/bin/java" ]; then printf "%s\n" "$$dir"; break; fi; done)
ANDROID_GRADLE_ENV := unset ANDROID_HOME; $(if $(ANDROID_JAVA_HOME),JAVA_HOME="$(ANDROID_JAVA_HOME)" PATH="$(ANDROID_JAVA_HOME)/bin:$$PATH")
ANDROID_KEYSTORE ?= $(HOME)/.android/kryon-release.keystore
ANDROID_KEY_ALIAS ?= breathing-key

BUILD_DIR := build

# Dependencies and the Ziran toolchain are pinned in ziran.lock and linked
# under build/packages/<name>. Make refreshes the links before reading the rest
# of this file whenever the manifest or lock changes. PACKAGE_FLAGS=--locked
# ignores ziran.local.toml overrides for release builds.
PACKAGE_FLAGS ?=
PACKAGES_MK := $(BUILD_DIR)/packages.mk
$(PACKAGES_MK): ziran.toml ziran.lock scripts/packages.sh
	sh scripts/packages.sh $(PACKAGE_FLAGS)
	printf 'PACKAGES_READY := 1\n' > $@
ifneq ($(filter-out clean distclean,$(or $(MAKECMDGOALS),all)),)
include $(PACKAGES_MK)
endif

.PHONY: packages
packages: $(PACKAGES_MK)

ZIRAN_DIR := build/packages/ziran
ZIRAN_BUILD_DIR := $(abspath $(BUILD_DIR)/ziran-toolchain)
KRYON_LIBRARY_BUILD_DIR := $(abspath $(BUILD_DIR)/kryon-library)
ZI2C_BIN := $(ZIRAN_BUILD_DIR)/bin/zi2c
ZIRAN_BIN := $(ZIRAN_BUILD_DIR)/bin/ziran
ZI2ZIR_BIN := $(ZIRAN_BUILD_DIR)/bin/zi2zir
ZI_CHECK_STAMP := $(BUILD_DIR)/zi-check/native.fresh
ZIRAN_SOURCES := $(wildcard $(ZIRAN_DIR)/cmd/zir/*.[ch]) $(wildcard $(ZIRAN_DIR)/cmd/zir-c/*.[ch]) $(wildcard $(ZIRAN_DIR)/cmd/zir-ir/*.[ch]) $(ZIRAN_DIR)/Makefile
BUILD_OBJ_DIR := $(BUILD_DIR)/obj
BUILD_BIN_DIR := $(BUILD_DIR)/bin
BUILD_DIST_DIR := $(BUILD_DIR)/dist
VENDOR_BUILD_DIR := vendor-builds
NATIVE_OBJ_DIR := $(BUILD_OBJ_DIR)/$(NATIVE_PLATFORM)
NATIVE_BIN_DIR := $(BUILD_BIN_DIR)/$(NATIVE_PLATFORM)
NATIVE_DIST_DIR := $(BUILD_DIST_DIR)/$(NATIVE_PLATFORM)
NATIVE_VENDOR_BUILD_DIR := $(VENDOR_BUILD_DIR)/$(NATIVE_PLATFORM)/$(ARCH)
LINUX_OBJ_DIR := $(BUILD_OBJ_DIR)/linux
LINUX_BIN_DIR := $(BUILD_BIN_DIR)/linux
LINUX_DIST_DIR := $(BUILD_DIST_DIR)/linux
LINUX_APPIMAGE_BUILD_DIR := $(BUILD_OBJ_DIR)/appimage/linux
LINUX_APPDIR := $(LINUX_APPIMAGE_BUILD_DIR)/$(APP_NAME).AppDir
LINUX_APPIMAGE_DIR := packaging/linux/appimage
LINUX_APPIMAGE_APPRUN := $(LINUX_APPIMAGE_DIR)/AppRun
LINUX_APPIMAGE_DESKTOP := $(LINUX_APPIMAGE_DIR)/$(APP_NAME).desktop
LINUX_APPIMAGE_ICON := $(LINUX_APPIMAGE_DIR)/$(APP_NAME).png
LINUX_APPIMAGE_APPDATA := $(LINUX_APPIMAGE_DIR)/$(APP_NAME).appdata.xml

# Desktop install configuration for the kryon-provided install suite
# (mk/package-freebsd.mk: install / install-user / uninstall / stage).
# Without these the install ships a bare binary -- no menu entry, no icon.
# Everything the app needs ships inside the executable (UI_EMBEDDED_ONLY=1).
APP_ID := $(ANDROID_APP_ID)
APP_DESKTOP := $(LINUX_APPIMAGE_DESKTOP)
APP_METAINFO := $(LINUX_APPIMAGE_APPDATA)
APP_ICON := $(LINUX_APPIMAGE_ICON)

DEB_BUILD_DIR := $(BUILD_OBJ_DIR)/deb
DEB_ROOT := $(DEB_BUILD_DIR)/root
DEB_DIST_DIR := $(BUILD_DIST_DIR)/deb
DEB_ARCH ?= $(if $(filter x86_64 amd64,$(ARCH)),amd64,$(if $(filter aarch64 arm64,$(ARCH)),arm64,$(ARCH)))
DEB_BIN_SOURCE ?=
DEB_BIN_INPUT = $(if $(strip $(DEB_BIN_SOURCE)),$(DEB_BIN_SOURCE),$(if $(filter linux,$(NATIVE_PLATFORM)),$(TARGET),))
DEB_PACKAGE_NAME ?= $(APP_NAME)
DEB_MAINTAINER ?= $(APP_MAINTAINER)
DEB_SECTION ?= utils
DEB_PRIORITY ?= optional
DEB_DEPENDS ?= libc6, libsdl2-2.0-0, libgtk-3-0, libcurl4, libdrm2, libgbm1, libegl1, libgles2, hicolor-icon-theme
DEB_TARGET = $(DEB_DIST_DIR)/$(DEB_PACKAGE_NAME)_$(APP_VERSION)_$(DEB_ARCH).deb
DEB_TARGET_PREREQS = Makefile $(LINUX_APPIMAGE_DESKTOP) $(LINUX_APPIMAGE_ICON) $(LINUX_APPIMAGE_APPDATA) $(VERSION_FILE) $(if $(filter linux,$(NATIVE_PLATFORM)),$(TARGET),)
RPM_BUILD_DIR := $(BUILD_OBJ_DIR)/rpm
RPM_TOPDIR := $(RPM_BUILD_DIR)/rpmbuild
RPM_DIST_DIR := $(BUILD_DIST_DIR)/rpm
RPM_ARCH ?= $(if $(filter x86_64 amd64,$(ARCH)),x86_64,$(if $(filter aarch64 arm64,$(ARCH)),aarch64,$(ARCH)))
RPM_BIN_SOURCE ?=
RPM_BIN_INPUT = $(if $(strip $(RPM_BIN_SOURCE)),$(RPM_BIN_SOURCE),$(if $(filter linux,$(NATIVE_PLATFORM)),$(TARGET),))
RPM_PACKAGE_NAME ?= $(APP_NAME)
RPM_RELEASE ?= 1
RPM_LICENSE ?= BSD-3-Clause
RPM_REQUIRES ?= glibc, SDL2, gtk3, libcurl, libdrm, mesa-libgbm, mesa-libEGL, mesa-libGLES, hicolor-icon-theme
RPM_SPEC := $(RPM_BUILD_DIR)/$(RPM_PACKAGE_NAME).spec
RPM_TARGET = $(RPM_DIST_DIR)/$(RPM_PACKAGE_NAME)-$(APP_VERSION)-$(RPM_RELEASE).$(RPM_ARCH).rpm
RPM_TARGET_PREREQS = Makefile $(LINUX_APPIMAGE_DESKTOP) $(LINUX_APPIMAGE_ICON) $(LINUX_APPIMAGE_APPDATA) $(VERSION_FILE) $(if $(filter linux,$(NATIVE_PLATFORM)),$(TARGET),)
PODMAN ?= $(shell if [ "$(UNAME_S)" = "FreeBSD" ] && [ "$$(id -u)" != "0" ]; then \
	if command -v doas >/dev/null 2>&1; then printf 'doas podman'; \
	elif command -v sudo >/dev/null 2>&1; then printf 'sudo podman'; \
	else printf 'podman'; fi; \
else printf 'podman'; fi)
PODMAN_RUN_PLATFORM ?= $(if $(filter FreeBSD,$(UNAME_S)),--os linux --arch amd64,)
PODMAN_RUN_NETWORK ?= $(if $(filter FreeBSD,$(UNAME_S)),--network host,)
SNAP_BUILD_DIR := $(BUILD_OBJ_DIR)/snap
SNAP_DIST_DIR := $(BUILD_DIST_DIR)/snap
SNAP_IMAGE ?= ghcr.io/canonical/snapcraft:8_core22
SNAP_ENTRYPOINT ?= /bin/sh
SNAP_APT_CACHE_VOLUME ?= $(APP_NAME)-snap-apt-cache
SNAP_ROOT_CACHE_VOLUME ?= $(APP_NAME)-snap-root-cache
SNAP_CACHE_VOLUMES := $(SNAP_APT_CACHE_VOLUME) $(SNAP_ROOT_CACHE_VOLUME)
SNAP_TARGET = $(SNAP_DIST_DIR)/$(APP_NAME)_$(APP_VERSION)_$(ARCH).snap
FLATPAK_BUILD_DIR := $(BUILD_OBJ_DIR)/flatpak
FLATPAK_DIST_DIR := $(BUILD_DIST_DIR)/flatpak
FLATPAK_IMAGE ?= ghcr.io/flathub-infra/flatpak-github-actions:gnome-46
FLATPAK_MANIFEST = packaging/flatpak/$(APP_ID).yml
FLATPAK_TARGET = $(FLATPAK_DIST_DIR)/$(APP_NAME)-$(APP_VERSION)-$(ARCH).flatpak
APP_ID := $(ANDROID_APP_ID)
APP_COMMENT := Syncable breathing, meditation, and habit practice app
APP_DESC := Inner Breeze is a free, open-source practice app for breathing, meditation, and habit tracking.
APP_CATEGORIES := Utility;Education;
APP_MAINTAINER := Waozi <waozi@waozi.xyz>
APP_WWW := https://inbe.waozi.xyz/
APP_ORIGIN := games/inbe
APP_LICENSE := BSD3CLAUSE
APP_DESKTOP := $(LINUX_APPIMAGE_DESKTOP)
APP_ICON := $(LINUX_APPIMAGE_ICON)
APP_DESKTOP_ID := $(APP_ID)
APP_ICON_NAME := $(APP_ID)
APP_ICON_SIZE := 512x512
APP_METAINFO := $(LINUX_APPIMAGE_APPDATA)
FREEBSD_PKG_DEPS := curl:ftp/curl gtk3:x11-toolkits/gtk30 hicolor-icon-theme:misc/hicolor-icon-theme libdrm:graphics/libdrm mesa-libs:graphics/mesa-libs sdl2:devel/sdl20 sqlite3:databases/sqlite3
CLICK_PACKAGE ?= inbe
CLICK_ID ?= inbe
CLICK_TITLE ?= $(APP_TITLE)
CLICK_MAINTAINER ?= Waozi <waozi@waozi.xyz>
CLICK_ARCH ?= arm64
CLICK_FRAMEWORK ?= ubuntu-sdk-20.04
CLICK_POLICY_VERSION ?= 20.04
CLICK_INCLUDE_METAINFO ?= 1
CLICK_DIR := packaging/click
CLICK_RUNNER := $(CLICK_DIR)/run-inbe.sh
CLICK_BUILD_DIR := $(BUILD_OBJ_DIR)/click/$(CLICK_ARCH)
CLICK_ROOT := $(CLICK_BUILD_DIR)/$(CLICK_PACKAGE)
CLICK_CONTROL_DIR := $(CLICK_BUILD_DIR)/control
CLICK_BIN_DIR := $(BUILD_BIN_DIR)/click/$(CLICK_ARCH)
CLICK_DIST_DIR := $(BUILD_DIST_DIR)/click
CLICK_TARGET = $(CLICK_DIST_DIR)/$(CLICK_PACKAGE)_$(APP_VERSION)_$(CLICK_ARCH).click
CLICK_BIN := $(CLICK_BIN_DIR)/$(APP_NAME)
CLICK_BIN_INPUT := $(if $(strip $(CLICK_BIN_SOURCE)),$(CLICK_BIN_SOURCE),$(CLICK_BIN))
CLICK_RAYLIB_BUILD_DIR := $(VENDOR_BUILD_DIR)/click/$(CLICK_ARCH)/raylib
CLICK_RAYLIB_A := $(CLICK_RAYLIB_BUILD_DIR)/libraylib.a
CLICK_LIBOQS_BUILD_DIR := $(VENDOR_BUILD_DIR)/click/$(CLICK_ARCH)/liboqs
CLICK_LIBOQS_A := $(CLICK_LIBOQS_BUILD_DIR)/lib/liboqs.a
CLICK_LIBOQS_INCLUDE := -I$(CLICK_LIBOQS_BUILD_DIR)/include
CLICK_PATCHELF_INTERPRETER ?= /lib/ld-linux-aarch64.so.1
CLICK_RUNTIME_LIBS ?= $(AARCH64_CLICK_RUNTIME_LIBS)
AARCH64_CC ?= $(shell command -v aarch64-linux-gnu-gcc 2>/dev/null || command -v aarch64-linux-musl-gcc 2>/dev/null)
AARCH64_AR ?= $(shell command -v aarch64-linux-gnu-ar 2>/dev/null || command -v aarch64-linux-musl-ar 2>/dev/null)
AARCH64_RANLIB ?= $(shell command -v aarch64-linux-gnu-ranlib 2>/dev/null || command -v aarch64-linux-musl-ranlib 2>/dev/null)
WINDOWS_OBJ_DIR := $(BUILD_OBJ_DIR)/windows
WINDOWS_BIN_DIR := $(BUILD_BIN_DIR)/windows
WINDOWS_DIST_DIR := $(BUILD_DIST_DIR)/windows
ANDROID_BUILD_DIR := $(BUILD_DIR)/android
WEB_OBJ_DIR := $(BUILD_OBJ_DIR)/web
WEB_DIST_DIR := $(BUILD_DIST_DIR)/web
CHROME_WEB_STORE_DIR := $(BUILD_DIST_DIR)/chrome-web-store
VERSION_FILE := src/core/version.h
APP_VERSION := $(shell awk '/APP_VERSION_STRING/ { print $$3; exit }' $(VERSION_FILE) 2>/dev/null | tr -d '"')
SOCIAL_PY ?= $(if $(wildcard .local/social-venv/bin/python),.local/social-venv/bin/python,python3)

KRYON_DIR ?= build/packages/kryon
KSS_DIR ?= build/packages/kss
KRYON_BACKEND ?= raylib
ifeq ($(KRYON_BACKEND),tui)
KRYON_BACKEND := termi
endif
PLAN9PORT_DIR ?= /mnt/storage/Projects/plan9port
RAYLIB_DIR = build/packages/raylib/src
RAYLIB_BUILD_DIR := $(NATIVE_VENDOR_BUILD_DIR)/raylib
RAYLIB_A := $(RAYLIB_BUILD_DIR)/libraylib.a
WIN64_ARCH := x86_64
WIN64_CC ?= $(or $(WIN_CC),x86_64-w64-mingw32-gcc)
WIN64_AR ?= $(or $(WIN_AR),x86_64-w64-mingw32-ar)
WIN64_RANLIB ?= $(or $(WIN_RANLIB),x86_64-w64-mingw32-ranlib)
WIN64_STRIP ?= $(or $(WIN_STRIP),x86_64-w64-mingw32-strip)
WIN64_WINDRES ?= x86_64-w64-mingw32-windres
WIN64_CMAKE_SYSTEM_PROCESSOR ?= x86_64
WIN64_CC_PATH := $(shell command -v $(WIN64_CC) 2>/dev/null || printf '%s' $(WIN64_CC))
WIN64_AR_PATH := $(shell command -v $(WIN64_AR) 2>/dev/null || printf '%s' $(WIN64_AR))
WIN64_RANLIB_PATH := $(shell command -v $(WIN64_RANLIB) 2>/dev/null || printf '%s' $(WIN64_RANLIB))
WIN32_ARCH := i686
WIN32_CC ?= i686-w64-mingw32-gcc
WIN32_AR ?= i686-w64-mingw32-ar
WIN32_RANLIB ?= i686-w64-mingw32-ranlib
WIN32_STRIP ?= i686-w64-mingw32-strip
WIN32_WINDRES ?= i686-w64-mingw32-windres
WIN32_CMAKE_SYSTEM_PROCESSOR ?= x86
WIN32_CC_PATH := $(shell command -v $(WIN32_CC) 2>/dev/null || printf '%s' $(WIN32_CC))
WIN32_AR_PATH := $(shell command -v $(WIN32_AR) 2>/dev/null || printf '%s' $(WIN32_AR))
WIN32_RANLIB_PATH := $(shell command -v $(WIN32_RANLIB) 2>/dev/null || printf '%s' $(WIN32_RANLIB))
WIN64_RAYLIB_BUILD_DIR := $(VENDOR_BUILD_DIR)/windows/$(WIN64_ARCH)/raylib
WIN64_RAYLIB_A := $(WIN64_RAYLIB_BUILD_DIR)/libraylib.a
WIN32_RAYLIB_BUILD_DIR := $(VENDOR_BUILD_DIR)/windows/$(WIN32_ARCH)/raylib
WIN32_RAYLIB_A := $(WIN32_RAYLIB_BUILD_DIR)/libraylib.a
WIN64_CURL_BUILD_DIR := $(VENDOR_BUILD_DIR)/windows/$(WIN64_ARCH)/curl
WIN64_CURL_INCLUDE_DIR := $(WIN64_CURL_BUILD_DIR)/include
WIN64_CURL_A := $(WIN64_CURL_BUILD_DIR)/lib/libcurl.a
WIN64_LIBOQS_BUILD_DIR := $(VENDOR_BUILD_DIR)/windows/$(WIN64_ARCH)/liboqs
WIN64_LIBOQS_A := $(WIN64_LIBOQS_BUILD_DIR)/lib/liboqs.a
WIN64_LIBOQS_INCLUDE := -I$(WIN64_LIBOQS_BUILD_DIR)/include
WIN32_CURL_BUILD_DIR := $(VENDOR_BUILD_DIR)/windows/$(WIN32_ARCH)/curl
WIN32_CURL_INCLUDE_DIR := $(WIN32_CURL_BUILD_DIR)/include
WIN32_CURL_A := $(WIN32_CURL_BUILD_DIR)/lib/libcurl.a
WIN32_LIBOQS_BUILD_DIR := $(VENDOR_BUILD_DIR)/windows/$(WIN32_ARCH)/liboqs
WIN32_LIBOQS_A := $(WIN32_LIBOQS_BUILD_DIR)/lib/liboqs.a
WIN32_LIBOQS_INCLUDE := -I$(WIN32_LIBOQS_BUILD_DIR)/include
WIN64_RESOURCE := $(BUILD_OBJ_DIR)/windows/$(WIN64_ARCH)/$(APP_NAME).res
WIN32_RESOURCE := $(BUILD_OBJ_DIR)/windows/$(WIN32_ARCH)/$(APP_NAME).res
RAYLIB_SOURCES := $(if $(wildcard $(RAYLIB_DIR)),$(shell find $(RAYLIB_DIR) -type f \( -name '*.c' -o -name '*.h' \)))

KRYON_ICON_DIR := icons
KRYON_ICON_FILES := $(shell find $(KRYON_DIR)/$(KRYON_ICON_DIR) -path '*/review/*' -prune -o -type f \( -name '*.png' -o -name '*.json' \) -print 2>/dev/null | LC_ALL=C sort)
KRYON_GENERATED_INCLUDE_DIR := $(BUILD_OBJ_DIR)/kryon/generated/include
KRYON_GENERATED_SRC_DIR := $(BUILD_OBJ_DIR)/kryon/generated/src
KRYON_UI_ZI := $(addprefix $(KRYON_DIR)/src/ui/,$(shell cat $(KRYON_DIR)/src/ui/modules.txt))
KRYON_UI_C := $(patsubst $(KRYON_DIR)/src/ui/%.zi,$(KRYON_GENERATED_SRC_DIR)/ui/%.c,$(KRYON_UI_ZI))
KRYON_UI_H := $(KRYON_UI_C:.c=.h)
KRYON_UI_STAMP := $(KRYON_GENERATED_SRC_DIR)/ui/.fresh
KRYON_KSS_ZI := $(wildcard $(KSS_DIR)/src/*.zi)
KRYON_KSS_C := $(patsubst $(KSS_DIR)/src/%.zi,$(KRYON_GENERATED_SRC_DIR)/kss/%.c,$(KRYON_KSS_ZI))
KRYON_KSS_H := $(KRYON_KSS_C:.c=.h)
KRYON_KSS_STAMP := $(KRYON_GENERATED_SRC_DIR)/kss/.fresh
KRYON_ICON_ASSETS_C := $(KRYON_GENERATED_SRC_DIR)/ui/ui_icon_assets.c
KRYON_ICON_NAMES_C := $(KRYON_GENERATED_SRC_DIR)/ui/ui_icon_names.c
KRYON_ICON_TYPES_H := $(KRYON_GENERATED_INCLUDE_DIR)/ui_icon_types.h
KRYON_SRCS := $(filter-out $(KRYON_DIR)/src/ui/ui_icon_assets.c $(KRYON_DIR)/src/ui/ui_icon_names.c,$(shell find $(KRYON_DIR)/src -type f -name '*.c' | LC_ALL=C sort)) $(KRYON_ICON_ASSETS_C) $(KRYON_ICON_NAMES_C) $(KRYON_UI_C) $(KRYON_KSS_C)
KRYON_SYNC_ICONS := $(KRYON_DIR)/scripts/sync-icons.sh
WEB_SHARED_ICON_SHEETS := platforms language tiles
KRYON_LIBDRAW_SRCS := $(filter $(KRYON_DIR)/src/backend/libdraw_%.c,$(KRYON_SRCS))
KRYON_TERMI_SRCS := $(filter $(KRYON_DIR)/src/backend/termi_%.c,$(KRYON_SRCS))
KRYON_SRCS := $(filter-out $(KRYON_LIBDRAW_SRCS),$(KRYON_SRCS))
KRYON_SRCS := $(filter-out $(KRYON_TERMI_SRCS),$(KRYON_SRCS))
ifneq ($(KRYON_BACKEND),libdraw)
KRYON_SRCS := $(filter-out $(KRYON_DIR)/src/platform/plan9/%.c,$(KRYON_SRCS))
endif
# The web build uses kryon's Canvas2D backend directly: no raylib, no WebGL.
KRYON_WEB_SRCS := $(KRYON_SRCS)
KRYON_WEB_SRCS := $(filter-out $(KRYON_DIR)/src/backend/dom_%.c,$(KRYON_WEB_SRCS))
KRYON_WINDOWS_SRCS := $(filter-out $(KRYON_DIR)/src/file_dialog/file_dialog.c,$(KRYON_SRCS))
KRYON_CLICK_SRCS := $(filter-out $(KRYON_DIR)/src/file_dialog/file_dialog.c,$(KRYON_SRCS))
KRYON_INCLUDE := -I$(KRYON_GENERATED_INCLUDE_DIR) -I$(KRYON_GENERATED_SRC_DIR) -I$(KRYON_DIR)/include -I$(KRYON_DIR)/src/ui -I$(KRYON_DIR)/src/platform -I$(KRYON_DIR)/src/backend -I$(KRYON_GENERATED_SRC_DIR)/runtime
KRYON_INCLUDE += -I$(ZIRAN_DIR)/include
KRYON_SYNC_ACCOUNT_C := $(KRYON_DIR)/src/sync/sync_account.c
KRYON_SYNC_C := $(KRYON_DIR)/src/sync/sync.c
KRYON_SYNC_TRANSPORT_C := $(KRYON_DIR)/src/sync/sync_transport.c
KRYON_SYNC_ACCOUNT_H := $(KRYON_DIR)/include/sync/account.h
KRYON_VENDOR_BUILD_DIR := $(NATIVE_VENDOR_BUILD_DIR)
KRYON_LIBOQS_BUILD_DIR := $(KRYON_VENDOR_BUILD_DIR)/liboqs
KRYON_WEB_LIBOQS_BUILD_DIR := $(VENDOR_BUILD_DIR)/web/liboqs
KRYON_CURL_BUILD_DIR := $(KRYON_VENDOR_BUILD_DIR)/curl
KRYON_CURL_REQUIRE_WEBSOCKETS := 1
KRYON_CURL_EXTRA_CMAKE_FLAGS := \
	-DCURL_DISABLE_WEBSOCKETS=OFF \
	-DCURL_DISABLE_INSTALL=OFF \
	-DCURL_DISABLE_DICT=ON \
	-DCURL_DISABLE_FILE=ON \
	-DCURL_DISABLE_FTP=ON \
	-DCURL_DISABLE_GOPHER=ON \
	-DCURL_DISABLE_IMAP=ON \
	-DCURL_DISABLE_MQTT=ON \
	-DCURL_DISABLE_POP3=ON \
	-DCURL_DISABLE_RTSP=ON \
	-DCURL_DISABLE_SMTP=ON \
	-DCURL_DISABLE_TELNET=ON \
	-DCURL_DISABLE_TFTP=ON \
	-DCURL_DISABLE_LIBCURL_OPTION=ON \
	-DCURL_ZLIB=OFF \
	-DCURL_BROTLI=OFF \
	-DCURL_ZSTD=OFF
# breathing is a UI-only app: drop the 2D physics subsystem (Box2D) entirely.
# := on purpose: this is a property of the app, not a knob. Setting it to 1
# would also require linking $(KRYON_PHYSICS_DEPS) (libbox2d), which this
# Makefile does not wire up -- so a ?= here would invite a broken build.
# The filter is applied to every variant below; KRYON_WEB/WINDOWS/CLICK_SRCS
# were snapshotted from KRYON_SRCS above (before this filter), so re-apply it
# to keep the kryon physics .c files (which need box2d.h) out of every build.
KRYON_WITH_PHYSICS := 0
include mk/sync.mk
KRYON_INCLUDE += $(KRYON_PHYSICS_CPPFLAGS)
KRYON_SRCS := $(filter-out $(KRYON_PHYSICS_SRCS),$(KRYON_SRCS))
KRYON_WEB_SRCS := $(filter-out $(KRYON_PHYSICS_SRCS),$(KRYON_WEB_SRCS))
KRYON_WINDOWS_SRCS := $(filter-out $(KRYON_PHYSICS_SRCS),$(KRYON_WINDOWS_SRCS))
KRYON_CLICK_SRCS := $(filter-out $(KRYON_PHYSICS_SRCS),$(KRYON_CLICK_SRCS))
KRYON_LIBOQS_CPU_FEATURE_CMAKE_FLAGS ?= \
	-DOQS_USE_ADX_INSTRUCTIONS=OFF \
	-DOQS_USE_AES_INSTRUCTIONS=OFF \
	-DOQS_USE_AVX_INSTRUCTIONS=OFF \
	-DOQS_USE_AVX2_INSTRUCTIONS=OFF \
	-DOQS_USE_AVX512_INSTRUCTIONS=OFF \
	-DOQS_USE_AVX512BW_INSTRUCTIONS=OFF \
	-DOQS_USE_AVX512DQ_INSTRUCTIONS=OFF \
	-DOQS_USE_AVX512F_INSTRUCTIONS=OFF \
	-DOQS_USE_BMI1_INSTRUCTIONS=OFF \
	-DOQS_USE_BMI2_INSTRUCTIONS=OFF \
	-DOQS_USE_FMA_INSTRUCTIONS=OFF \
	-DOQS_USE_PCLMULQDQ_INSTRUCTIONS=OFF \
	-DOQS_USE_POPCNT_INSTRUCTIONS=OFF \
	-DOQS_USE_SSE_INSTRUCTIONS=OFF \
	-DOQS_USE_SSE2_INSTRUCTIONS=OFF \
	-DOQS_USE_SSE3_INSTRUCTIONS=OFF \
	-DOQS_USE_VPCLMULQDQ_INSTRUCTIONS=OFF
CURL_DIR := $(KRYON_CURL_DIR)
CURL_BUILD_DIR := $(KRYON_CURL_BUILD_DIR)
CURL_INCLUDE_DIR := $(KRYON_CURL_INCLUDE_DIR)
CURL_LIB_DIR := $(KRYON_CURL_LIB_DIR)
CURL_SO := $(KRYON_CURL_SO)
CURL_PROTOCOL_CHECK := $(KRYON_CURL_PROTOCOL_CHECK)
KRYON_CURL_VERSION_NUM ?= $(shell printf '%b\n' '\043include <curl/curlver.h>' 'LIBCURL_VERSION_NUM' | $(CC) -I$(KRYON_CURL_DIR)/include -E -P - 2>/dev/null | tail -n 1)
# Lazy on purpose: := would run the preprocessor above at parse time on every
# invocation (make clean included). The only consumer is the version guard in
# the NEEDS_NATIVE_ENV block, which expands this only for build goals.
KRYON_CURL_VERSION_HEX = $(patsubst 0x%,%,$(KRYON_CURL_VERSION_NUM))
SQLITE_DIR := build/packages/sqlite
SQLITE_BUILD_DIR := $(VENDOR_BUILD_DIR)/sqlite
SQLITE_AMALGAMATION_C := $(SQLITE_BUILD_DIR)/sqlite3.c
SQLITE_AMALGAMATION_H := $(SQLITE_BUILD_DIR)/sqlite3.h
SQLITE_SRC := $(SQLITE_AMALGAMATION_C)
SQLITE_INCLUDE := -I$(SQLITE_BUILD_DIR)
LIBOQS_DIR := $(KRYON_LIBOQS_DIR)
LIBOQS_BUILD_DIR := $(KRYON_LIBOQS_BUILD_DIR)
LIBOQS_A := $(KRYON_LIBOQS_A)
LIBOQS_INCLUDE := $(KRYON_LIBOQS_INCLUDE)
WEB_LIBOQS_BUILD_DIR := $(KRYON_WEB_LIBOQS_BUILD_DIR)
WEB_LIBOQS_A := $(KRYON_WEB_LIBOQS_A)
WEB_LIBOQS_INCLUDE := -I$(WEB_LIBOQS_BUILD_DIR)/include
TEST_BIN_DIR := $(BUILD_BIN_DIR)/tests
FONT_ASSETS_GEN_DIR := $(BUILD_DIR)/font-assets-test/generated
BREATH_TIMING_GEN_DIR := $(BUILD_DIR)/breath-timing-test/generated
BREAK_RULES_GEN_DIR := $(BUILD_DIR)/break-rules-test/generated
RUNTIME_ASSET_CFLAGS := -DHAS_LIBCURL=1 $(KRYON_CURL_CFLAGS)
RUNTIME_ASSET_LDLIBS := $(KRYON_CURL_LDLIBS)
STORAGE_CORE_SRCS = $(KRY_GEN_DIR)/src/storage/json.c $(KRY_GEN_DIR)/src/storage/storage_core.c $(KRY_GEN_DIR)/src/storage/storage_habits.c $(KRY_GEN_DIR)/src/storage/storage_habit_materialize.c $(KRY_GEN_DIR)/src/storage/storage_habit_sync.c

MONOCYPHER_DIR := build/packages/monocypher/src
MONOCYPHER_SRCS := $(MONOCYPHER_DIR)/monocypher.c \
	$(MONOCYPHER_DIR)/optional/monocypher-ed25519.c

APP_SRCS := \
	$(sort $(wildcard src/app/*.c)) \
	$(MONOCYPHER_SRCS)

# Kryon's tray loads GTK and AppIndicator with dlopen only when the tray opens
# (APP_NO_TRAY=1 skips it), preferring a StatusNotifierItem and falling back
# to a GTK status icon, so nothing tray-related is compiled in or linked.
ifneq ($(filter linux freebsd,$(NATIVE_PLATFORM)),)
DESKTOP_TRAY_DEFINE := DESKTOP_TRAY_ENABLED
endif
ZI_NATIVE_DEFINES := PLATFORM_DESKTOP $(DESKTOP_TRAY_DEFINE)
# Ziran preprocessing must see the libc choice used by the native C compiler.
NATIVE_GLIBC := $(shell printf '#include <stdlib.h>\n' | $(CC) -dM -E - 2>/dev/null | grep -q '^\#define __GLIBC__ ' && printf yes)
ifeq ($(NATIVE_GLIBC),yes)
ZI_NATIVE_DEFINES += __GLIBC__
endif
ifneq ($(filter aarch64 arm64,$(ARCH)),)
ZI_NATIVE_DEFINES += __aarch64__
else ifneq ($(filter x86_64 amd64,$(ARCH)),)
ZI_NATIVE_DEFINES += __x86_64__
else ifneq ($(filter i386 i486 i586 i686 x86,$(ARCH)),)
ZI_NATIVE_DEFINES += __i386__
endif
ifeq ($(NATIVE_PLATFORM),freebsd)
ZI_NATIVE_DEFINES += __FreeBSD__
endif
ifeq ($(NATIVE_PLATFORM),darwin)
ZI_NATIVE_DEFINES += __APPLE__
endif

# No in-process GTK anywhere else either: the system theme uses kryon's
# built-in palettes, and native file dialogs prefer xdg-desktop-portal through
# GIO before falling back to zenity/kdialog/yad.
SYSTEM_THEME_CFLAGS :=
SYSTEM_THEME_LDLIBS :=

LOCALE_FILES := $(wildcard locales/*.txt)
IMAGE_FILES := assets/app/icon.png assets/easteregg/art.png assets/easteregg/waozi.png assets/practices/whm/1.png assets/practices/whm/2.png assets/practices/meditation/1.png assets/pet/egg1.png $(wildcard assets/practices/*/banner*.png) assets/practices/sunsalutation/poses_man_sheet.png assets/practices/sunsalutation/poses_woman_sheet.png assets/practices/sunsalutation/transition_01_01_to_02_man_sheet.png assets/practices/sunsalutation/transition_02_02_to_03_man_sheet.png
SOUND_FILES := $(wildcard assets/sounds/*.ogg)
FONT_SUBSET_DIR := assets/fonts/subset
FONT_SUBSET_CORPUS := locales assets/fonts/input_common.txt
FONT_FILES := \
	$(FONT_SUBSET_DIR)/NotoSans-App-Regular.ttf \
	$(FONT_SUBSET_DIR)/NotoSansSC-App-Regular.otf \
	$(FONT_SUBSET_DIR)/NotoSansJP-App-Regular.otf \
	$(FONT_SUBSET_DIR)/NotoSansKR-App-Regular.otf \
	$(FONT_SUBSET_DIR)/NotoSansTC-App-Regular.otf
EMBEDDED_ASSETS_C := $(BUILD_OBJ_DIR)/$(APP_NAME)_embedded_assets.c
STYLE_FILES := $(wildcard $(KSS_DIR)/styles/*.kss) \
	$(wildcard assets/styles/*.kss) \
	$(wildcard themes/catalog_*.kss)
IMAGE_FILES += assets/app/icon-sky-cradle.png assets/app/icon-ink-and-air.png
IMAGE_FILES += $(wildcard assets/social/*.png)
IMAGE_FILES += $(KRYON_DIR)/icons/ui.png $(KRYON_DIR)/icons/pfp.png
EMBEDDED_ASSET_FILES := $(STYLE_FILES) $(LOCALE_FILES) $(IMAGE_FILES) $(SOUND_FILES) $(FONT_FILES)
KRY_GEN_DIR := $(BUILD_DIR)/kryon/generated
ZI_SRCS := $(shell find src -type f -name '*.zi' 2>/dev/null | LC_ALL=C sort)
GAME2D_DIR := build/packages/game2d
GAME2D_MODULES := $(wildcard $(GAME2D_DIR)/src/*/*.zi)
DAOCHI_CLIENT_MODULES := $(wildcard build/packages/daochi-client/*.zi)
ZIRAN_STD_MODULES := $(wildcard $(ZIRAN_DIR)/std/*.zi)
KRYON_ZI_MODULES := $(shell find $(KRYON_DIR)/src -type f -name '*.zi' | LC_ALL=C sort)
KRY_GEN_SRCS := $(patsubst %.zi,$(KRY_GEN_DIR)/%.c,$(ZI_SRCS))
KRY_GEN_SRCS += $(addprefix $(KRY_GEN_DIR)/,account.c auth.c byte_text_linux.c \
	c_string.c client.c date_parse.c date_time.c events.c json_scan.c net_http_curl_linux.c \
	net_ws_curl_linux.c social.c sync.c \
	text.c text_buffer.c transaction.c update.c url.c wire.c)
KRY_GEN_HDRS := $(patsubst %.zi,$(KRY_GEN_DIR)/%.h,$(ZI_SRCS))
KRY_GEN_GAME_C := $(KRY_GEN_DIR)/Raylib.c
KRY_GEN_STAMP := $(KRY_GEN_DIR)/.fresh
WEB_GEN_DIR := $(BUILD_DIR)/kryon/generated-web
WEB_GEN_SRCS := $(patsubst $(KRY_GEN_DIR)/%,$(WEB_GEN_DIR)/%,$(KRY_GEN_SRCS))
WEB_GEN_GAME_C := $(WEB_GEN_DIR)/Raylib.c
WEB_GEN_STAMP := $(WEB_GEN_DIR)/.fresh
WINDOWS_GEN_DIR := $(BUILD_DIR)/kryon/generated-windows
WINDOWS_GEN_SRCS := $(patsubst $(KRY_GEN_DIR)/%,$(WINDOWS_GEN_DIR)/%,$(KRY_GEN_SRCS))
WINDOWS_GEN_GAME_C := $(WINDOWS_GEN_DIR)/Raylib.c
WINDOWS_GEN_STAMP := $(WINDOWS_GEN_DIR)/.fresh
SRC := $(APP_SRCS) $(KRY_GEN_STAMP) $(EMBEDDED_ASSETS_C)
GENERATED_NATIVE_C = $(shell find $(KRY_GEN_DIR) -type f -name '*.c' | LC_ALL=C sort)
WINDOWS_SRC := $(APP_SRCS) $(EMBEDDED_ASSETS_C)
GENERATED_WINDOWS_C = $(shell find $(WINDOWS_GEN_DIR) -type f -name '*.c' | LC_ALL=C sort)
KRYON_HOST_APP_SRCS := $(APP_SRCS) $(KRY_GEN_SRCS) $(KRY_GEN_GAME_C)
KRYON_HOST_SRC := $(KRYON_HOST_APP_SRCS) $(EMBEDDED_ASSETS_C)
WEB_APP_SRCS := $(APP_SRCS)
WEB_SRC := $(WEB_APP_SRCS) $(EMBEDDED_ASSETS_C)
GENERATED_WEB_C = $(shell find $(WEB_GEN_DIR) -type f -name '*.c' | LC_ALL=C sort)

APP_INCLUDE := -Isrc -Isrc/app -Isrc/core -Isrc/screens -Isrc/screens/settings -Isrc/practices -Isrc/practices/whm -Isrc/practices/meditation -Isrc/practices/sun_salutation -Isrc/storage -Isrc/platform -Isrc/platform/android -Isrc/third_party
APP_INCLUDE += -iquote$(KRY_GEN_DIR)
APP_INCLUDE += -I$(RAYLIB_DIR)
APP_INCLUDE += $(foreach dir,$(sort $(dir $(ZI_SRCS))),-iquote$(KRY_GEN_DIR)/$(dir))
APP_INCLUDE += $(KRYON_INCLUDE)
APP_INCLUDE += -I$(MONOCYPHER_DIR) -I$(MONOCYPHER_DIR)/optional
WEB_APP_INCLUDE = $(filter-out -iquote$(KRY_GEN_DIR)%,$(APP_INCLUDE)) \
	-iquote$(WEB_GEN_DIR) \
	$(foreach dir,$(sort $(dir $(ZI_SRCS))),-iquote$(WEB_GEN_DIR)/$(dir))
WINDOWS_APP_INCLUDE = $(filter-out -iquote$(KRY_GEN_DIR)%,$(APP_INCLUDE)) \
	-iquote$(WINDOWS_GEN_DIR) \
	$(foreach dir,$(sort $(dir $(ZI_SRCS))),-iquote$(WINDOWS_GEN_DIR)/$(dir))
SYNC_RETRY_SOURCE := src/app/sync_retry.zi
STORAGE_LAYOUT_HEADER := tests/storage_layout.h
LAW_MODULES := src/app/sync_retry_laws.zi src/app/practice_lifecycle_laws.zi \
	src/app/modal_rules_laws.zi \
	src/app/sync_recovery_policy_laws.zi src/storage/habit_merge_laws.zi \
	src/storage/sync_restore_laws.zi src/storage/storage_layout_laws.zi
RAY_PKGS ?= sdl2 libdrm gbm egl glesv2
RAY_SDL_CFLAGS ?= $(shell pkg-config --cflags sdl2 2>/dev/null)
RAY_SDL_LDLIBS ?= $(shell pkg-config --libs sdl2 2>/dev/null)
ZI_NATIVE_DEFINES += $(if $(strip $(RAY_SDL_LDLIBS)),NATIVE_WINDOW_HAVE_SDL,)
APP_GIO_CFLAGS ?= $(shell pkg-config --cflags gio-2.0 2>/dev/null)
APP_GIO_LDLIBS ?= $(shell pkg-config --libs gio-2.0 2>/dev/null)
ZI_NATIVE_DEFINES += $(if $(strip $(APP_GIO_LDLIBS)),APP_HAVE_GIO,)
RAY_GL_CFLAGS ?= $(shell pkg-config --cflags libdrm gbm egl glesv2 2>/dev/null)
RAY_GL_LDLIBS ?= $(shell pkg-config --libs libdrm gbm egl glesv2 2>/dev/null)
RAY_CFLAGS ?= $(strip $(RAY_SDL_CFLAGS) $(RAY_GL_CFLAGS))
RAY_LDLIBS ?= $(strip $(RAY_SDL_LDLIBS) $(RAY_GL_LDLIBS))
RAY_SDL_INCLUDE_DIR ?= $(shell pkg-config --variable=includedir sdl2 2>/dev/null | sed 's,/SDL2$$,,')
RAY_RAYLIB_CONFIG ?= -DSUPPORT_SCREEN_CAPTURE=0 -DSUPPORT_COMPRESSION_API=0 -DSUPPORT_AUTOMATION_EVENTS=0 -DSUPPORT_CLIPBOARD_IMAGE=0 -DSUPPORT_FILEFORMAT_BMP=0 -DSUPPORT_FILEFORMAT_GIF=0 -DSUPPORT_FILEFORMAT_QOI=0 -DSUPPORT_FILEFORMAT_DDS=0 -DSUPPORT_FILEFORMAT_TTF=1
ifeq ($(NATIVE_PLATFORM),freebsd)
KRYON_RAYLIB_AUDIO_PERIOD_FRAMES ?= 128
KRYON_RAYLIB_AUDIO_PERIODS ?= 2
endif
KRYON_RAYLIB_AUDIO_PERIOD_CONFIG := $(if $(strip $(KRYON_RAYLIB_AUDIO_PERIOD_FRAMES)),-DAUDIO_DEVICE_PERIOD_SIZE_IN_FRAMES=$(KRYON_RAYLIB_AUDIO_PERIOD_FRAMES),)
KRYON_RAYLIB_AUDIO_PERIODS_CONFIG := $(if $(strip $(KRYON_RAYLIB_AUDIO_PERIODS)),-DAUDIO_DEVICE_PERIODS=$(KRYON_RAYLIB_AUDIO_PERIODS),)
APP_RAYLIB_CONFIG := $(filter-out -DSUPPORT_MODULE_RAUDIO=0 -DSUPPORT_FILEFORMAT_PNG=0 -DSUPPORT_FILEFORMAT_JPG=0 -DSUPPORT_FILEFORMAT_OGG=0 -DSUPPORT_FILEFORMAT_MP3=%,$(RAY_RAYLIB_CONFIG)) -DSUPPORT_MODULE_RAUDIO=1 -DSUPPORT_FILEFORMAT_JPG=1 -DSUPPORT_FILEFORMAT_OGG=1 -DSUPPORT_FILEFORMAT_MP3=0 $(KRYON_RAYLIB_AUDIO_PERIOD_CONFIG) $(KRYON_RAYLIB_AUDIO_PERIODS_CONFIG)
COMMON_CFLAGS := -Wall -Wextra -Os -D_DEFAULT_SOURCE -D_GNU_SOURCE -ffunction-sections -fdata-sections -DSUPPORT_FILEFORMAT_JPG=1 -DUI_EMBEDDED_ONLY=1 -DNATIVE_WINDOW_HAVE_SDL -DKRYON_WITH_SYNC=1
CFLAGS := $(COMMON_CFLAGS) -std=c99 $(RUNTIME_ASSET_CFLAGS) $(SYSTEM_THEME_CFLAGS) $(KRYON_NOTIFICATION_CPPFLAGS) $(KRYON_NOTIFICATION_CFLAGS)
NATIVE_SYSTEM_LDLIBS := $(KRYON_NOTIFICATION_LDLIBS) -lz -lm -lpthread -latomic $(if $(filter linux,$(NATIVE_PLATFORM)),-ldl -lrt,) $(SYSTEM_THEME_LDLIBS)
WINDOWS_CFLAGS := -Wall -Wextra -std=c99 -Os -D_DEFAULT_SOURCE -D_GNU_SOURCE -ffunction-sections -fdata-sections -DSUPPORT_FILEFORMAT_JPG=1 -DUI_EMBEDDED_ONLY=1 -DKRYON_WITH_SYNC=1
WEB_CFLAGS := $(filter-out -Os -DNATIVE_WINDOW_HAVE_SDL,$(COMMON_CFLAGS)) -Oz -std=gnu99
CLICK_CFLAGS := -Wall -Wextra -std=c99 -Os -D_DEFAULT_SOURCE -D_GNU_SOURCE -ffunction-sections -fdata-sections -DSUPPORT_FILEFORMAT_JPG=1 -DUI_EMBEDDED_ONLY=1 -DDISABLE_KRYON_FILE_DIALOG -DHAS_LIBCURL=1 -DKRYON_WITH_SYNC=1 $(AARCH64_KRYON_CURL_CFLAGS)
LDFLAGS := -Wl,--gc-sections -s
WINDOWS_LDFLAGS := -Wl,--gc-sections -static -static-libgcc -mwindows
# GNU ld's i686 stdcall fixups synthesize an undecorated glReadPixels alias,
# but its decorated import can otherwise be discarded before fixup resolution.
WIN32_WINDOWS_LDFLAGS := -Wl,--undefined=_glReadPixels@28 -static -static-libgcc -mwindows
WINDOWS_LDLIBS := -lgdi32 -lwinmm -lopengl32 -luser32 -lshell32 -lole32 -lcomdlg32 -lcomctl32 -luuid -lwininet -lws2_32 -liphlpapi -lcrypt32 -lsecur32 -lbcrypt -ladvapi32 -lm -latomic
ifneq ($(strip $(MCFGTHREADS)),)
WIN64_THREAD_LDFLAGS := -L$(MCFGTHREADS)/lib
else
WIN64_THREAD_LDFLAGS :=
endif
ifneq ($(strip $(WIN32_MCFGTHREADS)),)
WIN32_THREAD_LDFLAGS := -L$(WIN32_MCFGTHREADS)/lib
else
WIN32_THREAD_LDFLAGS :=
endif

BINARY_NAME := $(APP_NAME)-$(NATIVE_PLATFORM)-$(ARCH)
TARGET := $(NATIVE_BIN_DIR)/$(BINARY_NAME)
# Native sources compile to per-file objects through mk/native-objects.mk.
NATIVE_OBJ_DIR := $(abspath $(BUILD_OBJ_DIR)/native)
NATIVE_JOBS ?= $(shell nproc 2>/dev/null || echo 4)
NATIVE_COMPILE_FLAGS = $(KRYON_NATIVE_CFLAGS) $(APP_INCLUDE) $(KRYON_INCLUDE) \
	-iquote$(KRYON_LIBRARY_BUILD_DIR)/c $(SQLITE_INCLUDE) $(LIBOQS_INCLUDE) \
	$(KRYON_NATIVE_BACKEND_CFLAGS) -DHAS_LIBOQS=1 -DSUPPORT_MODULE_RAUDIO=1 \
	-DSUPPORT_FILEFORMAT_OGG=1 -DSUPPORT_FILEFORMAT_MP3=0
KRYON_HOST_TARGET := $(BUILD_DIR)/kryon/app_host.so
WIN64_BINARY_NAME := $(APP_NAME)-windows-$(WIN64_ARCH).exe
WIN64_TARGET := $(WINDOWS_BIN_DIR)/$(WIN64_ARCH)/$(WIN64_BINARY_NAME)
WIN32_BINARY_NAME := $(APP_NAME)-windows-$(WIN32_ARCH).exe
WIN32_TARGET := $(WINDOWS_BIN_DIR)/$(WIN32_ARCH)/$(WIN32_BINARY_NAME)
WINDOWS_DIST := $(WINDOWS_DIST_DIR)/$(APP_NAME)-windows.zip
APPIMAGE_NAME := $(APP_NAME)-linux-$(ARCH).AppImage
APPIMAGE_TARGET := $(LINUX_DIST_DIR)/$(APPIMAGE_NAME)
APPIMAGE_INTERPRETER ?= $(if $(filter x86_64 amd64,$(ARCH)),/lib64/ld-linux-x86-64.so.2,$(if $(filter aarch64 arm64,$(ARCH)),/lib/ld-linux-aarch64.so.1,))
LINUXDEPLOY ?= linuxdeploy
WEB_EMSDK_BIN ?= $(HOME)/emsdk/upstream/emscripten
WEB_CC ?= $(if $(wildcard $(WEB_EMSDK_BIN)/emcc),$(WEB_EMSDK_BIN)/emcc,emcc)
WEB_AR ?= $(if $(wildcard $(WEB_EMSDK_BIN)/emar),$(WEB_EMSDK_BIN)/emar,emar)
WEB_RANLIB ?= $(if $(wildcard $(WEB_EMSDK_BIN)/emranlib),$(WEB_EMSDK_BIN)/emranlib,emranlib)
WEB_EMCMAKE ?= $(if $(wildcard $(WEB_EMSDK_BIN)/emcmake),$(WEB_EMSDK_BIN)/emcmake,emcmake)
ifneq ($(wildcard $(WEB_EMSDK_BIN)/emcc),)
export PATH := $(WEB_EMSDK_BIN):$(PATH)
endif
$(RAYLIB_A): $(RAYLIB_SOURCES) $(RAYLIB_DIR)/Makefile
	@test -f $(RAYLIB_DIR)/raylib.h || { echo "Initialize Kryon's raylib submodule" >&2; exit 1; }
	mkdir -p $(RAYLIB_BUILD_DIR)
	rm -rf $(RAYLIB_BUILD_DIR)/source
	mkdir -p $(RAYLIB_BUILD_DIR)/source
	cp -R $(RAYLIB_DIR)/. $(RAYLIB_BUILD_DIR)/source/
	$(MAKE) -j4 -C $(RAYLIB_BUILD_DIR)/source \
		RAYLIB_SRC_PATH=. RAYLIB_RELEASE_PATH=.. \
		PLATFORM=PLATFORM_DESKTOP_SDL GRAPHICS=GRAPHICS_API_OPENGL_ES2 \
		RAYLIB_LIBTYPE=STATIC RAYLIB_MODULE_AUDIO=TRUE \
		RAYLIB_MODULE_MODELS=TRUE \
		SDL_INCLUDE_PATH=$(shell pkg-config --variable=includedir sdl2) \
		CUSTOM_CFLAGS="-DUSING_SDL2_PROJECT $(RAY_CFLAGS) $(APP_RAYLIB_CONFIG) -O2 -ffunction-sections -fdata-sections"
	@test -f $@
KRYON_NATIVE_BACKEND_DEPS :=
KRYON_NATIVE_BACKEND_LIBS :=
KRYON_NATIVE_CFLAGS := $(CFLAGS)
KRYON_NATIVE_BACKEND_CFLAGS :=
KRYON_NATIVE_BACKEND_LDLIBS :=
ifeq ($(KRYON_BACKEND),raylib)
KRYON_SRCS += $(KRYON_RAYLIB_WRAPPERS_C)
KRYON_NATIVE_BACKEND_DEPS := $(RAYLIB_A)
KRYON_NATIVE_BACKEND_LIBS := $(RAYLIB_A)
KRYON_NATIVE_BACKEND_CFLAGS := -DKRYON_BACKEND_RAYLIB=1 $(RAY_CFLAGS)
KRYON_NATIVE_BACKEND_LDLIBS := $(RAY_LDLIBS)
else ifeq ($(KRYON_BACKEND),libdraw)
KRYON_SRCS += $(KRYON_LIBDRAW_SRCS)
KRYON_NATIVE_CFLAGS := $(filter-out -DNATIVE_WINDOW_HAVE_SDL,$(COMMON_CFLAGS)) -std=c99 $(RUNTIME_ASSET_CFLAGS) $(SYSTEM_THEME_CFLAGS) $(KRYON_NOTIFICATION_CPPFLAGS) $(KRYON_NOTIFICATION_CFLAGS)
KRYON_NATIVE_BACKEND_CFLAGS := -DKRYON_BACKEND_LIBDRAW=1 -I$(PLAN9PORT_DIR)/include -idirafter $(RAYLIB_DIR)/external
KRYON_NATIVE_BACKEND_LDLIBS := -L$(PLAN9PORT_DIR)/lib -ldraw -lmemdraw -lmux -lthread -l9 -lpthread -lm
else ifeq ($(KRYON_BACKEND),termi)
KRYON_SRCS += $(KRYON_TERMI_SRCS) $(KRYON_NULL_BACKEND_C)
KRYON_NATIVE_CFLAGS := $(filter-out -DNATIVE_WINDOW_HAVE_SDL,$(COMMON_CFLAGS)) -std=c99 $(RUNTIME_ASSET_CFLAGS) $(SYSTEM_THEME_CFLAGS) $(KRYON_NOTIFICATION_CPPFLAGS) $(KRYON_NOTIFICATION_CFLAGS)
KRYON_NATIVE_BACKEND_CFLAGS := -DKRYON_BACKEND_TERMI=1
else
$(error Unknown KRYON_BACKEND '$(KRYON_BACKEND)' (expected raylib, libdraw, or termi))
endif
ifneq ($(strip $(APP_GIO_LDLIBS)),)
KRYON_NATIVE_BACKEND_CFLAGS += -DAPP_HAVE_GIO $(APP_GIO_CFLAGS)
NATIVE_SYSTEM_LDLIBS += $(APP_GIO_LDLIBS)
endif
KRYON_WINDOWS_SRCS += $(KRYON_RAYLIB_WRAPPERS_C)
KRYON_CLICK_SRCS += $(KRYON_RAYLIB_WRAPPERS_C)
WEB_CACHE_BUSTER ?= $(shell if git diff --quiet --ignore-submodules HEAD -- 2>/dev/null; then git rev-parse --short HEAD 2>/dev/null; else date +%s; fi)
WEB_CACHE_BUSTER := $(WEB_CACHE_BUSTER)
WEB_TARGET := $(WEB_DIST_DIR)/index.html
WEB_APP_SCRIPT := <script>window.__inbeRenderer="canvas";window.__inbeLoadApp("index.js?v=$(WEB_CACHE_BUSTER)")</script>
WEB_JS_TARGET := $(WEB_DIST_DIR)/index.js
WEB_BOOT_JS := src/web_boot.js
WEB_HOST_JS := src/web_host.js scripts/browser_network.js
# Kryon's canvas hosts are Ziran modules on Ziran's web bridge; its runtime is the only JS they need.
WEB_CANVAS_HOST_JS := $(ZIRAN_DIR)/web/ziran_web.js
WEB_HOST_JS += $(WEB_CANVAS_HOST_JS)
# Canvas-only web build: Kryon's HTML5 Canvas2D Tier A backend. The app and
# support libraries are still Emscripten/WASM, including sync/liboqs for
# sync-account parity.
WEB_CANVAS_DIR := $(BUILD_DIST_DIR)/web-canvas
WEB_CANVAS_TARGET := $(WEB_CANVAS_DIR)/index.html
WEB_CANVAS_APP_SCRIPT := <script>window.__inbeRenderer="canvas";window.__inbeLoadApp("index.js?v=$(WEB_CACHE_BUSTER)")</script>
KRYON_CANVAS_SRCS := $(filter-out $(KRYON_DIR)/src/backend/dom_%.c,$(filter-out $(KRYON_RAYLIB_WRAPPERS_C),$(KRYON_SRCS)))
WEB_DIST_ZIP := $(BUILD_DIST_DIR)/$(APP_NAME)-web.zip
WEB_SMOKE_BROWSER ?= auto
WEB_SMOKE_TEST := scripts/web-smoke-test.mjs
WEB_SIDE_BY_SIDE_TEST := scripts/web-side-by-side-test.sh
WEB_APP_URL ?= https://inbe.waozi.xyz/
CHROME_WEB_STORE_ZIP := $(BUILD_DIST_DIR)/$(APP_NAME)-chrome-web-store.zip
CHROME_WEB_STORE_MANIFEST := packaging/chrome-web-store/manifest.json
CHROME_WEB_STORE_WORKER := packaging/chrome-web-store/service_worker.js
CHROME_WEB_STORE_EXTENSION_BOOT := packaging/chrome-web-store/extension_boot.js
CHROME_WEB_STORE_EXTENSION_APP := packaging/chrome-web-store/extension_app.js
CHROME_WEB_STORE_EXTENSION_CANVAS_APP := packaging/chrome-web-store/extension_canvas_app.js
CHROME_WEB_STORE_ICON_DIR := packaging/chrome-web-store/icons
CHROME_WEB_STORE_ICONS := \
	$(CHROME_WEB_STORE_ICON_DIR)/icon-16.png \
	$(CHROME_WEB_STORE_ICON_DIR)/icon-32.png \
	$(CHROME_WEB_STORE_ICON_DIR)/icon-48.png \
	$(CHROME_WEB_STORE_ICON_DIR)/icon-128.png
FIREFOX_ADDONS_DIR := $(BUILD_DIST_DIR)/firefox-addons
FIREFOX_ADDONS_ZIP := $(BUILD_DIST_DIR)/$(APP_NAME)-firefox-addons.zip
FIREFOX_ADDONS_SOURCE_ZIP := $(BUILD_DIST_DIR)/$(APP_NAME)-firefox-addons-source.zip
FIREFOX_ADDONS_MANIFEST := packaging/firefox-addons/manifest.json
FIREFOX_ADDONS_BACKGROUND := packaging/firefox-addons/background.js
FIREFOX_ADDONS_LOADER := packaging/firefox-addons/extension_loader.js
FIREFOX_ADDONS_INDEX := $(FIREFOX_ADDONS_DIR)/index.html
FIREFOX_ADDONS_APP_SCRIPT := <script src="extension_loader.js"></script>
FIREFOX_ADDONS_ICON_DIR := $(CHROME_WEB_STORE_ICON_DIR)
FIREFOX_ADDONS_ICONS := $(CHROME_WEB_STORE_ICONS)
ADDONS_LINTER ?= npx --yes addons-linter
WEB_ASSET_FILES := $(filter-out web-assets/dl/% web-assets/canvas_index.html,$(shell find web-assets site-icons -type f 2>/dev/null))
UNPACKAGED_AUDIO_DIR := unpackaged_assets/audio
UNPACKAGED_AUDIO_FILES := $(shell find $(UNPACKAGED_AUDIO_DIR) -type f 2>/dev/null)
MEDITATION_AUDIO_ZIP := web-assets/dl/breathing-meditation-audio-v1.zip
MEDITATION_AUDIO_TRACKS := \
	Elijah_K/deep-meditation.ogg \
	Elijah_K/path-of-meditation.ogg \
	Elijah_K/truth-of-silence.ogg

-include $(KRYON_DIR)/mk/package-freebsd.mk

.PHONY: web-canvas web-canvas-smoke-test web-compare-test web-side-by-side-test all native kryon-host install install-user uninstall stage package-freebsd deb package-deb deb-check rpm package-rpm rpm-check snap package-snap snap-cache-clean flatpak package-flatpak podman-check validate-desktop run tui run-tui run-termi run-termi-direct run-fresh screenshot test ci dist appimage click click-verify vendor-prebuilds vendor-prebuilds-native vendor-prebuilds-web vendor-prebuilds-windows font-subsets font-bundle-check clean clean-linux clean-native clean-vendor-builds windows-setup windows-setup-check android-avd android-audio-e2e android-check-keystore android-copy-assets android-copy-debug-apks android-copy-release-apks android-copy-bundle android-smoke android-local-properties android-debug android-release android-bundle android-install android-install-release android-clean android-rebuild validate-meditation-audio package-unpackaged-assets windows-runtime-assets-check windows windows64 windows32 web web-tools-check web-smoke-test web-smoke-test-firefox web-smoke-test-librewolf site site-release-assets-check chrome-web-store chrome-web-store-test firefox-addons firefox-addons-lint firefox-addons-source-zip verify-firefox-addons sync-web-icons social-install social-login social-draft social-x-draft social-post social-x-post social-x-post-dry-run social-post-dry-run
.PHONY: zi-check
.PHONY: clean-text-api-check package-check secret-check secret-check-history hooks-install test-tui-screenshot test-termi-screenshot test-termi-screenshot-direct
.NOTPARALLEL: all native test ci zi-check dist windows windows64 windows32 android-release android-bundle click deb package-deb rpm package-rpm snap package-snap flatpak package-flatpak

all: native

# Tests take the whole toolchain directory, so every tool rebuilds together;
# mixing a new zi2zir with an old ziran fails on the ZIR version.
ZIRAN_TOOLS := $(addprefix $(ZIRAN_BUILD_DIR)/bin/,zi2c zi2zir zi2zib zi2cpp zi2go ziran)

$(ZI2C_BIN): $(ZIRAN_SOURCES)
	$(MAKE) -C $(ZIRAN_DIR) BUILD_DIR=$(ZIRAN_BUILD_DIR) $(ZIRAN_TOOLS)

zi-check: $(ZI_CHECK_STAMP) | build-laws

$(ZI_CHECK_STAMP): Makefile scripts/check-zi-sources.py $(ZI2C_BIN) \
	$(ZI_SRCS) $(DAOCHI_CLIENT_MODULES) $(ZIRAN_STD_MODULES) \
	$(KRYON_UI_ZI) $(KRYON_KSS_ZI) $(GAME2D_MODULES) | build-laws
	@ZI_CHECK_DEFINES="$(ZI_NATIVE_DEFINES)" python3 scripts/check-zi-sources.py $(ZI2ZIR_BIN) $(KRYON_DIR)/src/ui $(ZIRAN_DIR)/std $(KSS_DIR)/src
	@mkdir -p $(dir $@)
	@touch $@

.PHONY: kryon-library-check
kryon-library-check: $(KRYON_LIBRARY_BUILD_DIR)/libkryon.a

$(KRYON_LIBRARY_BUILD_DIR)/libkryon.a: $(KRYON_UI_ZI) $(KRYON_DIR)/src/ui/modules.txt $(KRYON_DIR)/Makefile $(ZI2C_BIN)
	$(MAKE) -C $(KRYON_DIR) BUILD_DIR=$(KRYON_LIBRARY_BUILD_DIR) \
		ZIRAN_DIR=$(abspath $(ZIRAN_DIR)) ZIRAN_BUILD_DIR=$(ZIRAN_BUILD_DIR) all

.PHONY: uri-link-test
uri-link-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u GDK_DISPLAY \
		python3 tests/uri_host_zi_test.py $(ZIRAN_BUILD_DIR)/bin

.PHONY: frame-activity-test
frame-activity-test: $(ZI2C_BIN)
	@sh tests/frame_activity_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

.PHONY: frame-pacing-zi-test
frame-pacing-zi-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/frame_pacing_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

test: frame-pacing-zi-test

.PHONY: breath-timing-test
breath-timing-test: $(ZI2C_BIN)
	@sh tests/breath_timing_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

.PHONY: break-rules-test
break-rules-test: $(ZI2C_BIN)
	@sh tests/break_rules_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

.PHONY: sun-salutation-test
sun-salutation-test: $(ZI2C_BIN)
	@sh tests/sun_salutation_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

.PHONY: break-engine-test
break-engine-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY sh tests/break_engine_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

.PHONY: breath-engine-test
breath-engine-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY sh tests/breath_rounds_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

.PHONY: route-host-test
route-host-test: $(ZI2C_BIN)
	@mkdir -p $(BUILD_DIR)/route-host-test/generated
	@$(ZI2C_BIN) --no-main --root src \
		--module-path $(KRYON_DIR)/src/ui \
		--module-path $(ZIRAN_DIR)/std \
		-o $(BUILD_DIR)/route-host-test/generated src/app/route_catalog.zi
	@$(ZI2C_BIN) --no-main --root src \
		--module-path $(ZIRAN_DIR)/std \
		-o $(BUILD_DIR)/route-host-test/generated src/app/route_log.zi
	@$(ZI2C_BIN) --no-main --root src --define PLATFORM_WEB \
		--module-path $(ZIRAN_DIR)/std \
		-o $(BUILD_DIR)/route-host-test/generated src/app/route_host.zi
	@$(CC) -std=c11 -ffunction-sections -fdata-sections \
		-Wl,--gc-sections -I$(ZIRAN_DIR)/include \
		-I$(BUILD_DIR)/route-host-test/generated -Isrc/app \
		tests/route_host_test.c \
		$(BUILD_DIR)/route-host-test/generated/c_string.c \
		$(BUILD_DIR)/route-host-test/generated/text_buffers.c \
		$(BUILD_DIR)/route-host-test/generated/byte_text_linux.c \
		$(BUILD_DIR)/route-host-test/generated/app/route_log.c \
		$(BUILD_DIR)/route-host-test/generated/app/route_host.c \
		-I$(KRYON_DIR)/include \
		-o $(BUILD_DIR)/route-host-test/test
	@env -u DISPLAY -u WAYLAND_DISPLAY $(BUILD_DIR)/route-host-test/test

.PHONY: profile-host-test
profile-host-test: $(ZI2C_BIN)
	@mkdir -p $(BUILD_DIR)/profile-host-test/generated
	@$(ZI2C_BIN) --no-main --root src \
		--module-path $(ZIRAN_DIR)/std \
		-o $(BUILD_DIR)/profile-host-test/generated src/app/app_profile.zi
	@$(CC) -std=c11 -ffunction-sections -fdata-sections \
		-Wl,--gc-sections -I$(ZIRAN_DIR)/include \
		-I$(BUILD_DIR)/profile-host-test/generated -Isrc/app \
		-I$(KRYON_DIR)/include \
		tests/profile_host_test.c \
		$(BUILD_DIR)/profile-host-test/generated/c_string.c \
		$(BUILD_DIR)/profile-host-test/generated/app/app_profile.c \
		-o $(BUILD_DIR)/profile-host-test/test
	@env -u DISPLAY -u WAYLAND_DISPLAY $(BUILD_DIR)/profile-host-test/test disabled
	@env -u DISPLAY -u WAYLAND_DISPLAY $(BUILD_DIR)/profile-host-test/test

.PHONY: route-catalog-test
route-catalog-test: $(ZI2C_BIN)
	@sh tests/route_catalog_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

.PHONY: sync-retry-zi-test
sync-retry-zi-test: build-laws $(ZI2C_BIN)
	@sh tests/sync_retry_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

test: sync-retry-zi-test

.PHONY: sync-crypto-zi-test
sync-crypto-zi-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/sync_crypto_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

test: sync-crypto-zi-test

.PHONY: sync-account-crypto-zi-test
sync-account-crypto-zi-test: $(ZI2C_BIN) $(LIBOQS_A)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/sync_account_crypto_zi_test.sh $(ZIRAN_BUILD_DIR)/bin $(LIBOQS_A)

test: sync-account-crypto-zi-test

.PHONY: sync-account-zi-test
sync-account-zi-test: $(ZI2C_BIN) $(SQLITE_SRC) $(LIBOQS_A)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/sync_account_zi_test.sh $(ZIRAN_BUILD_DIR)/bin/ziran $(LIBOQS_A)

test: sync-account-zi-test

.PHONY: storage-import-zi-test
storage-import-zi-test: $(ZI2C_BIN) $(SQLITE_SRC) $(LIBOQS_A)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/storage_import_zi_test.sh $(ZIRAN_BUILD_DIR)/bin/ziran $(LIBOQS_A)

test: storage-import-zi-test

.PHONY: storage-habits-zi-test
storage-habits-zi-test: $(ZI2C_BIN) $(SQLITE_SRC) $(LIBOQS_A)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/storage_habits_zi_test.sh $(ZIRAN_BUILD_DIR)/bin/ziran $(LIBOQS_A)

test: storage-habits-zi-test

.PHONY: storage-sync-zi-test
storage-sync-zi-test: $(ZI2C_BIN) $(SQLITE_SRC) $(LIBOQS_A)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/storage_sync_zi_test.sh $(ZIRAN_BUILD_DIR)/bin/ziran $(LIBOQS_A)

test: storage-sync-zi-test

.PHONY: sync-url-zi-test
sync-url-zi-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/sync_url_zi_test.sh $(ZIRAN_BUILD_DIR)/bin/ziran

test: sync-url-zi-test

.PHONY: sync-review-zi-test
sync-review-zi-test: $(ZI2C_BIN) $(SQLITE_SRC) | build-laws
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/sync_review_zi_test.sh $(ZIRAN_BUILD_DIR)/bin/ziran

test: sync-review-zi-test

.PHONY: ziran-behavior-tests
ziran-behavior-tests: $(ZI2C_BIN) $(SQLITE_SRC) $(LIBOQS_A) $(RAYLIB_A)
	@set -e; for t in storage_more habit_model habit_sessions habit_form practice_carousel; do \
		env -u DISPLAY -u WAYLAND_DISPLAY sh tests/$${t}_zi_test.sh $(ZIRAN_BUILD_DIR)/bin/ziran $(LIBOQS_A); \
	done
	@env -u DISPLAY -u WAYLAND_DISPLAY sh tests/storage_paths_scenarios_zi_test.sh $(ZIRAN_BUILD_DIR)/bin/ziran
	@env -u DISPLAY -u WAYLAND_DISPLAY sh tests/breath_rounds_zi_test.sh $(ZIRAN_BUILD_DIR)/bin
	@env -u DISPLAY -u WAYLAND_DISPLAY sh tests/break_engine_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

.PHONY: asset-text-tests
asset-text-tests:
	@python3 tests/font_glyph_coverage_test.py
	@python3 tests/locale_keys_test.py
	@python3 tests/settings_keys_test.py

test: ziran-behavior-tests asset-text-tests
test: route-host-test
test: profile-host-test

native: $(TARGET)

.PHONY: native-screenshot-test
native-screenshot-test: $(TARGET)
	sh tests/native_screenshot_test.sh $(abspath $(TARGET))

.PHONY: native-navigation-test
native-navigation-test: $(TARGET)
	sh tests/native_navigation_test.sh $(abspath $(TARGET))

.PHONY: native-zoom-test
native-zoom-test: $(TARGET)
	sh tests/native_zoom_test.sh $(abspath $(TARGET))

kryon-host: $(KRYON_HOST_TARGET)

# Generate Kryon's checked Ziran modules into Inbe's build tree.
$(KRYON_UI_STAMP): Makefile $(ZI2C_BIN) $(KRYON_UI_ZI) $(KRYON_DIR)/src/ui/modules.txt
	mkdir -p $(dir $@)
	$(ZI2C_BIN) --no-main --root $(KRYON_DIR)/src/ui \
		-o $(dir $@) $(KRYON_UI_ZI)
	touch $@

$(KRYON_UI_C) $(KRYON_UI_H): $(KRYON_UI_STAMP)
	@test -f $@

$(KRYON_KSS_STAMP): Makefile $(ZI2C_BIN) $(KRYON_KSS_ZI) $(KRYON_DIR)/src/ui/modules.txt
	mkdir -p $(dir $@)
	$(ZI2C_BIN) --no-main --root $(KSS_DIR)/src \
		--module-path $(KRYON_DIR)/src/ui --module-path kryon=$(KRYON_DIR)/src/ui \
		-o $(dir $@) $(KRYON_KSS_ZI)
	touch $@

$(KRYON_KSS_C) $(KRYON_KSS_H): $(KRYON_KSS_STAMP)
	@test -f $@

$(KRY_GEN_STAMP): Makefile $(ZI2C_BIN) $(ZI_SRCS) $(KRYON_ZI_MODULES) $(GAME2D_MODULES) $(DAOCHI_CLIENT_MODULES) $(ZIRAN_STD_MODULES) $(SYNC_RETRY_SOURCE) | build-laws zi-check
	mkdir -p $(KRY_GEN_DIR)
	sh scripts/run-ziran.sh $(ZI2C_BIN) --no-main --prune-stale --root . \
		$(foreach define,$(ZI_NATIVE_DEFINES),--define $(define)) \
		--module-path src --module-path $(KRYON_DIR)/src/ui \
		--module-path $(KSS_DIR)/src --module-path kryon=$(KRYON_DIR)/src/ui \
		--module-path $(KRYON_DIR)/src/backend \
		--module-path $(GAME2D_DIR)/src \
		--module-path $(ZIRAN_DIR)/std \
		--module-path build/packages/daochi-client \
		-o $(KRY_GEN_DIR) $(ZI_SRCS)
	touch $@

$(WEB_GEN_STAMP): Makefile $(ZI2C_BIN) $(ZI_SRCS) $(KRYON_ZI_MODULES) $(GAME2D_MODULES) $(DAOCHI_CLIENT_MODULES) $(ZIRAN_STD_MODULES) $(SYNC_RETRY_SOURCE) | build-laws zi-check
	rm -rf $(WEB_GEN_DIR)
	mkdir -p $(WEB_GEN_DIR)
	sh scripts/run-ziran.sh $(ZI2C_BIN) --no-main --root . \
		--define PLATFORM_WEB --define __EMSCRIPTEN__ \
		--module-path src --module-path $(KRYON_DIR)/src/ui \
		--module-path $(KSS_DIR)/src --module-path kryon=$(KRYON_DIR)/src/ui \
		--module-path $(KRYON_DIR)/src/backend \
		--module-path $(GAME2D_DIR)/src \
		--module-path $(ZIRAN_DIR)/std \
		--module-path build/packages/daochi-client \
		-o $(WEB_GEN_DIR) $(ZI_SRCS) $(KRYON_DIR)/src/backend/canvas_raster.zi $(KRYON_DIR)/src/backend/canvas_audio.zi $(KRYON_DIR)/src/backend/page_route.zi
	touch $@
	find $(WEB_GEN_DIR) -type f \( -name '*.c' -o -name '*.h' \) -exec touch -r $@ {} +

$(WEB_GEN_SRCS) $(WEB_GEN_GAME_C): $(WEB_GEN_STAMP)
	@test -f $@

$(WINDOWS_GEN_STAMP): Makefile $(ZI2C_BIN) $(ZI_SRCS) $(KRYON_ZI_MODULES) $(GAME2D_MODULES) $(DAOCHI_CLIENT_MODULES) $(ZIRAN_STD_MODULES) $(SYNC_RETRY_SOURCE) | build-laws zi-check
	rm -rf $(WINDOWS_GEN_DIR)
	mkdir -p $(WINDOWS_GEN_DIR)
	sh scripts/run-ziran.sh $(ZI2C_BIN) --no-main --root . \
		--define PLATFORM_DESKTOP --define _WIN32 \
		--define DESKTOP_TRAY_ENABLED \
		--module-path src --module-path $(KRYON_DIR)/src/ui \
		--module-path $(KSS_DIR)/src --module-path kryon=$(KRYON_DIR)/src/ui \
		--module-path $(KRYON_DIR)/src/backend \
		--module-path $(GAME2D_DIR)/src \
		--module-path $(ZIRAN_DIR)/std \
		--module-path build/packages/daochi-client \
		-o $(WINDOWS_GEN_DIR) $(ZI_SRCS)
	touch $@
	find $(WINDOWS_GEN_DIR) -type f \( -name '*.c' -o -name '*.h' \) -exec touch -r $@ {} +

$(WINDOWS_GEN_SRCS) $(WINDOWS_GEN_GAME_C): $(WINDOWS_GEN_STAMP)
	@test -f $@

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
		--module-path $(KSS_DIR)/src --module-path kryon=$(KRYON_DIR)/src/ui \
		--module-path $(KRYON_DIR)/src/backend \
		--module-path $(GAME2D_DIR)/src \
		--module-path $(ZIRAN_DIR)/std \
		--include-dir build/packages/kryon/include --include-dir src \
		--include-dir $(KRY_GEN_DIR) --include-dir vendor-builds/sqlite \
		-o $(PLAN9_GENERATED) $(ZI_SRCS)
	cp $(STORAGE_LAYOUT_HEADER) $(PLAN9_GENERATED)/storage_layout.h
	find $(PLAN9_GENERATED) -type f -name '*.c' | LC_ALL=C sort > $(PLAN9_FILE_LIST)
	sh build/packages/kryon/scripts/embed-assets.sh $(PLAN9_EMBEDDED_ASSETS_C) \
		$(STYLE_FILES) $(LOCALE_FILES) $(IMAGE_FILES) $(FONT_FILES)

$(KRY_GEN_SRCS) $(KRY_GEN_HDRS) $(KRY_GEN_GAME_C): $(KRY_GEN_STAMP)

dist:
	@password="$(PASSWORD)"; \
	if [ -z "$$password" ]; then \
		printf "Android release keystore password: "; \
		stty -echo; \
		read password; \
		stty echo; \
		printf "\n"; \
	fi; \
	if [ -z "$$password" ]; then \
		echo "Set PASSWORD=your-keystore-password for release builds"; \
		exit 1; \
	fi; \
	$(MAKE) android-check-keystore PASSWORD="$$password" && \
	$(MAKE) package-unpackaged-assets && \
	$(MAKE) web && \
	$(MAKE) chrome-web-store && \
	$(MAKE) firefox-addons && \
	$(MAKE) click && \
	$(MAKE) appimage && \
	$(MAKE) windows && \
	$(MAKE) android-release PASSWORD="$$password" && \
	$(MAKE) android-bundle PASSWORD="$$password"

appimage: $(APPIMAGE_TARGET)

deb package-deb: $(DEB_TARGET)

rpm package-rpm: $(RPM_TARGET)

snap package-snap: $(SNAP_TARGET)

snap-cache-clean: podman-check
	$(PODMAN) volume rm -f $(SNAP_CACHE_VOLUMES)

flatpak package-flatpak: $(FLATPAK_TARGET)

click: $(CLICK_TARGET)

click-verify: $(CLICK_TARGET)
	@command -v clickable >/dev/null || { \
		echo "clickable is missing. Install clickable or put it on PATH."; \
		exit 1; \
	}
	clickable review $(CLICK_TARGET)

web-tools-check:
	@missing=0; \
	for tool in "$(WEB_CC)" "$(WEB_AR)" "$(WEB_RANLIB)" "$(WEB_EMCMAKE)"; do \
		if ! command -v "$$tool" >/dev/null 2>&1; then \
			echo "Missing web build tool: $$tool"; \
			missing=1; \
		fi; \
	done; \
	if [ "$$missing" -ne 0 ]; then \
		echo ""; \
		echo "Install Emscripten for this host or run the web build from an environment where Emscripten is on PATH."; \
		echo ""; \
		echo "Required tools: WEB_CC=$(WEB_CC), WEB_AR=$(WEB_AR), WEB_RANLIB=$(WEB_RANLIB), WEB_EMCMAKE=$(WEB_EMCMAKE)."; \
		exit 1; \
	fi

vendor-prebuilds: vendor-prebuilds-native vendor-prebuilds-web vendor-prebuilds-windows

vendor-prebuilds-native: $(KRYON_NATIVE_BACKEND_DEPS) $(SQLITE_AMALGAMATION_C) $(SQLITE_AMALGAMATION_H) $(LIBOQS_A) $(CURL_PROTOCOL_CHECK)

vendor-prebuilds-web: web-tools-check $(SQLITE_AMALGAMATION_C) $(SQLITE_AMALGAMATION_H) $(WEB_LIBOQS_A)

vendor-prebuilds-windows: $(WIN64_RAYLIB_A) $(WIN32_RAYLIB_A) $(WIN64_CURL_A) $(WIN32_CURL_A) $(WIN64_LIBOQS_A) $(WIN32_LIBOQS_A) $(SQLITE_AMALGAMATION_C) $(SQLITE_AMALGAMATION_H)

run: $(TARGET)
	@root="$${XDG_DATA_HOME:-$$HOME/.local/share}/inbe-debug"; \
	APP_DATA_ROOT="$$root" ./$(TARGET)

tui run-tui run-termi:
	@$(MAKE) --no-print-directory KRYON_BACKEND=termi run-termi-direct

run-termi-direct: $(TARGET)
	@root="$${XDG_DATA_HOME:-$$HOME/.local/share}/inbe-debug"; \
	APP_DATA_ROOT="$$root" ./$(TARGET)

run-fresh: $(TARGET)
	@root=$$(mktemp -d /tmp/$(APP_NAME)-fresh.XXXXXX); \
	echo "APP_DATA_ROOT=$$root"; \
	APP_FORCE_DARK_MODE=1 APP_DATA_ROOT="$$root" ./$(TARGET)

social-install:
	python3 -m venv .local/social-venv
	.local/social-venv/bin/python -m pip install -r requirements-social.txt

social-login:
	$(SOCIAL_PY) scripts/inner-breeze-social.py login

social-draft:
	$(SOCIAL_PY) scripts/inner-breeze-social.py draft

social-x-draft:
	$(SOCIAL_PY) scripts/inner-breeze-social.py x-draft

social-post:
	$(SOCIAL_PY) scripts/inner-breeze-social.py post

social-x-post:
	$(SOCIAL_PY) scripts/inner-breeze-social.py x-post

social-x-post-dry-run:
	$(SOCIAL_PY) scripts/inner-breeze-social.py x-post --dry-run

social-post-dry-run:
	$(SOCIAL_PY) scripts/inner-breeze-social.py post --dry-run

screenshot: $(TARGET)
	./scripts/generate-screenshots.sh "$(TARGET)"

test-tui-screenshot test-termi-screenshot:
	@$(MAKE) --no-print-directory KRYON_BACKEND=termi test-termi-screenshot-direct

test-termi-screenshot-direct: $(TARGET)
	bash ./tests/termi_screenshot_test.sh "$(TARGET)"


.SILENT: package-check test font-bundle-check audio-test-fixture-check embedded-image-assets-check

## Local parity with the ci.yml gate: unit tests plus the web build (emcc).
## Run before pushing to catch web-only breakage -- e.g. code under
## #if defined(PLATFORM_WEB) -- that `make test` (desktop-native) misses.
ci: test web

## End-to-end desktop window-mode tests on a private Xvfb display: window
## close across startup/keep-running/ask modes.
## Requires Xvfb, xfwm4, xdotool, x11-utils and sqlite3.
test-desktop-windows:
	./scripts/test-desktop-windows.sh "$(TARGET)"

package-check:
	sh scripts/check-packages.sh

clean-text-api-check:
	python3 scripts/check-clean-text-api.py src tests

.PHONY: button-api-check
button-api-check:
	bash scripts/check-button-api.sh

test: button-api-check

.PHONY: version-check version-test
version-check:
	python3 scripts/check-version.py

version-test:
	python3 tests/version_test.py

test: version-check version-test

# Laws are checked by the Ziran compiler on every invocation. `ziran check`
# exits nonzero on any disproved or unwaived unknown law.
.PHONY: proofs proof-test build-laws
proofs: $(ZI2C_BIN)
	@for module in $(LAW_MODULES); do \
		$(ZIRAN_BIN) check --root src $$module > /dev/null || exit 1; \
	done

# Deliberately broken implementations must be rejected by the laws.
proof-test: $(ZI2C_BIN)
	sh tests/law_mutation_test.sh $(ZIRAN_BIN)

# The real merge SQL must satisfy the laws stated for its model.
.PHONY: habit-merge-sql-test sync-restore-sql-test
habit-merge-sql-test:
	python3 tests/habit_merge_sql_test.py

sync-restore-sql-test:
	python3 tests/sync_restore_sql_test.py

test: habit-merge-sql-test sync-restore-sql-test

build-laws: version-check proofs

test: proof-test

secret-check:
	python3 ./scripts/check-secrets.py --working-tree

secret-check-history:
	python3 ./scripts/check-secrets.py --history

hooks-install:
	sh ./scripts/install-git-hooks.sh

embedded-image-assets-check: $(EMBEDDED_ASSETS_C)
	bash ./tests/embedded_image_assets_test.sh

.PHONY: habits-cards-ui-test
habits-cards-ui-test: $(TARGET)
	bash tests/habits_cards_ui_test.sh "$(abspath $(TARGET))"

.PHONY: lists-ui-test
lists-ui-test: $(TARGET)
	bash tests/lists_ui_test.sh "$(abspath $(TARGET))"

.PHONY: storage-literals-check
storage-literals-check:
	bash ./scripts/check-storage-literals.sh

test: clean-text-api-check package-check secret-check storage-literals-check font-bundle-check audio-test-fixture-check embedded-image-assets-check
test: screenshot-scene-test

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

font-subsets:
	sh $(KRYON_DIR)/scripts/subset-fonts.sh "$(FONT_SUBSET_DIR)" \
		"$(KRYON_DIR)/fonts/noto" App locales assets/fonts/input_common.txt


.PHONY: sync-server-test
sync-server-test: $(ZI2C_BIN) $(SQLITE_SRC) $(LIBOQS_A)
	@sh tests/sync_server_zi_test.sh $(ZIRAN_BUILD_DIR)/bin/ziran $(LIBOQS_A)
	node scripts/sync-server-test.mjs

$(FONT_ASSETS_GEN_DIR)/app/font_assets.c: src/app/font_assets.zi $(ZI2C_BIN)
	@mkdir -p $(FONT_ASSETS_GEN_DIR)
	$(ZI2C_BIN) --no-main --root src \
		-o $(FONT_ASSETS_GEN_DIR) src/app/font_assets.zi

.PHONY: font-assets-test
font-assets-test: build-laws $(ZI2C_BIN)
	@sh tests/font_assets_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

.PHONY: navigation-routes-test
navigation-routes-test: build-laws $(ZI2C_BIN)
	@sh tests/navigation_routes_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

.PHONY: exercise-types-test
exercise-types-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/exercise_types_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

test: exercise-types-test

.PHONY: patterns-rules-zi-test
patterns-rules-zi-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/patterns_rules_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

test: patterns-rules-zi-test

.PHONY: patterns-session-zi-test
patterns-session-zi-test: $(ZI2C_BIN)
	@sh tests/patterns_session_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

test: patterns-session-zi-test

.PHONY: session-results-zi-test
session-results-zi-test: $(ZI2C_BIN) $(SQLITE_SRC) $(LIBOQS_A)
	@sh tests/session_results_zi_test.sh $(ZIRAN_BUILD_DIR)/bin/ziran $(LIBOQS_A)
	@$(ZI2C_BIN) --no-main --root tests --module-path build/packages/ziran/std \
		-o $(BUILD_DIR)/session-mood-generated tests/session_result_storage_behavior.zi
	@$(CC) -std=c11 -Isrc/storage -Ibuild/packages/ziran/include \
		-I$(BUILD_DIR)/session-mood-generated \
		$(BUILD_DIR)/session-mood-generated/*.c -o $(BUILD_DIR)/session-result-host-test
	@env -u DISPLAY -u WAYLAND_DISPLAY $(BUILD_DIR)/session-result-host-test

test: session-results-zi-test

.PHONY: settings-cache-test
settings-cache-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/settings_cache_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

test: settings-cache-test

.PHONY: web-storage-bridge-test
web-storage-bridge-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/web_storage_bridge_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

test: web-storage-bridge-test

.PHONY: device-policy-test
device-policy-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/device_policy_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

test: device-policy-test

.PHONY: device-preferences-zi-test device-host-sdl-test
device-preferences-zi-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/device_preferences_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

device-host-sdl-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/device_host_sdl_test.sh $(ZIRAN_BUILD_DIR)/bin

test: device-preferences-zi-test device-host-sdl-test

.PHONY: fonts-zi-test
fonts-zi-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/fonts_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

test: fonts-zi-test

.PHONY: metrics-zi-test
metrics-zi-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/metrics_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

test: metrics-zi-test

.PHONY: mood-average-zi-test
mood-average-zi-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/mood_average_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

test: mood-average-zi-test

.PHONY: habit-session-rules-zi-test
habit-session-rules-zi-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/habit_session_rules_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

test: habit-session-rules-zi-test

.PHONY: locale-used-keys-test
locale-used-keys-test:
	@python3 tests/locale_used_keys_test.py

test: locale-used-keys-test

.PHONY: locale-translated-test
locale-translated-test:
	@python3 tests/locale_translated_test.py

test: locale-translated-test

.PHONY: music-library-zi-test
music-library-zi-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/music_library_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

test: music-library-zi-test

.PHONY: screenshot-request-zi-test
screenshot-request-zi-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/screenshot_request_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

test: screenshot-request-zi-test

.PHONY: app-chrome-zi-test
app-chrome-zi-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/app_chrome_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

test: app-chrome-zi-test

.PHONY: schema-zi-test
schema-zi-test: $(ZI2C_BIN) $(SQLITE_SRC)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/schema_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

test: schema-zi-test

.PHONY: root-upgrade-zi-test
root-upgrade-zi-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/root_upgrade_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

test: root-upgrade-zi-test

.PHONY: database-upgrade-zi-test
database-upgrade-zi-test: $(ZI2C_BIN) $(SQLITE_SRC)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/database_upgrade_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

test: database-upgrade-zi-test

.PHONY: legacy-session-zi-test
legacy-session-zi-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/legacy_session_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

test: legacy-session-zi-test

.PHONY: archive-file-linux-zi-test
archive-file-linux-zi-test: $(ZI2C_BIN) $(SQLITE_SRC) | build-laws
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/archive_file_linux_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

test: archive-file-linux-zi-test

.PHONY: export-filename-test
export-filename-test: $(ZI2C_BIN) | build-laws
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/export_filename_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

test: export-filename-test

.PHONY: storage-state-zi-test
storage-state-zi-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/storage_state_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

test: storage-state-zi-test

.PHONY: storage-sql-zi-test
storage-sql-zi-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY $(ZI2ZIR_BIN) --check-only --root src \
		src/storage/sync_sql.zi src/storage/export_sql.zi \
		src/storage/habit_sync_sql.zi
	@env -u DISPLAY -u WAYLAND_DISPLAY python3 tests/storage_sql_behavior_test.py

test: storage-sql-zi-test

.PHONY: storage-json-builder-zi-test
storage-json-builder-zi-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/storage_json_builder_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

test: storage-json-builder-zi-test

.PHONY: storage-thread-buffer-zi-test
storage-thread-buffer-zi-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/storage_thread_buffer_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

test: storage-thread-buffer-zi-test

.PHONY: sqlite-text-zi-test
sqlite-text-zi-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/sqlite_text_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

test: sqlite-text-zi-test

.PHONY: sql-transaction-zi-test
sql-transaction-zi-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/sql_transaction_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

test: sql-transaction-zi-test

.PHONY: storage-paths-zi-test
storage-paths-zi-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/storage_paths_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

test: storage-paths-zi-test

.PHONY: daochi-client-zi-test
daochi-client-zi-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		ZI2C_BIN=$(abspath $(ZI2C_BIN)) ZIRAN_DIR=$(abspath $(ZIRAN_DIR)) \
		sh build/packages/daochi-client/tests/run.sh

test: daochi-client-zi-test

.PHONY: habit-days-memory-zi-test
habit-days-memory-zi-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/habit_days_memory_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

test: habit-days-memory-zi-test

.PHONY: locale-zi-test
.PHONY: host-services-zi-test
host-services-zi-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/host_services_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

test: host-services-zi-test

.PHONY: web-bridge-wasm-test
web-bridge-wasm-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/web_bridge_wasm_test.sh $(ZIRAN_BUILD_DIR)/bin $(WEB_CC)

locale-zi-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/locale_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

test: locale-zi-test

.PHONY: text-buffers-zi-test
text-buffers-zi-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/text_buffers_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

test: text-buffers-zi-test

.PHONY: raylib-text-input-zi-test
raylib-text-input-zi-test: $(ZI2C_BIN)
	@sh tests/raylib_text_input_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

test: raylib-text-input-zi-test

.PHONY: android-text-input-zi-test
android-text-input-zi-test: $(ZI2C_BIN)
	sh tests/android_text_input_zi_test.sh $(abspath $(dir $(ZI2C_BIN)))

test: android-text-input-zi-test

.PHONY: window-close-host-test
window-close-host-test: $(ZI2C_BIN)
	@mkdir -p $(BUILD_DIR)/window-close-host-test/c
	@$(ZI2C_BIN) --define PLATFORM_DESKTOP \
		--define NATIVE_WINDOW_HAVE_SDL \
		--entry window_close_behavior:main --root tests \
		--module-path src -o $(BUILD_DIR)/window-close-host-test/c \
		tests/window_close_behavior.zi
	@$(CC) -std=c11 -O2 -I$(ZIRAN_DIR)/include \
		-iquote $(BUILD_DIR)/window-close-host-test/c \
		$(BUILD_DIR)/window-close-host-test/c/*.c \
		$(RAY_SDL_LDLIBS) -o $(BUILD_DIR)/window-close-host-test/test
	@env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u GDK_DISPLAY \
		$(BUILD_DIR)/window-close-host-test/test

test: window-close-host-test

.PHONY: activity-host-test
activity-host-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u GDK_DISPLAY \
		DBUS_SESSION_BUS_ADDRESS=invalid: \
		sh tests/activity_host_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

test: activity-host-test

.PHONY: audio-picker-host-test
audio-picker-host-test: $(ZI2C_BIN)
	@mkdir -p $(BUILD_DIR)/audio-picker-host-test/c
	@cp tests/support/audio_picker_zenity.sh \
		$(BUILD_DIR)/audio-picker-host-test/zenity
	@chmod +x $(BUILD_DIR)/audio-picker-host-test/zenity
	@$(ZI2C_BIN) --no-main --define PLATFORM_DESKTOP --root src \
		--module-path $(ZIRAN_DIR)/std \
		-o $(BUILD_DIR)/audio-picker-host-test/c \
		src/platform/audio_picker_host.zi
	@$(CC) -std=c11 -D_DEFAULT_SOURCE -Wall -Wextra -Werror \
		-Wno-unused-function -I$(ZIRAN_DIR)/include \
		-iquote $(BUILD_DIR)/audio-picker-host-test/c \
		tests/audio_picker_host_test.c \
		$(BUILD_DIR)/audio-picker-host-test/c/*.c \
		$(BUILD_DIR)/audio-picker-host-test/c/platform/audio_picker_host.c \
		$(BUILD_DIR)/audio-picker-host-test/c/platform/file_picker.c \
		-o $(BUILD_DIR)/audio-picker-host-test/test
	@env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u GDK_DISPLAY \
		PATH="$(abspath $(BUILD_DIR)/audio-picker-host-test)" \
		$(abspath $(BUILD_DIR)/audio-picker-host-test/test)

.PHONY: file-picker-zi-test
file-picker-zi-test: $(ZI2C_BIN)
	@sh tests/file_picker_zi_test.sh $(abspath $(dir $(ZI2C_BIN)))

test: audio-picker-host-test file-picker-zi-test

.PHONY: main-platform-zi-test
main-platform-zi-test: $(ZI2C_BIN) $(RAYLIB_A)
	@RAY_LDLIBS='$(RAY_LDLIBS)' sh tests/main_platform_zi_test.sh \
		$(abspath $(dir $(ZI2C_BIN))) $(abspath $(RAYLIB_A))

test: main-platform-zi-test

.PHONY: web-window-zi-test
web-window-zi-test: $(ZI2C_BIN)
	@sh tests/web_window_zi_test.sh $(abspath $(dir $(ZI2C_BIN)))

test: web-window-zi-test

.PHONY: plan9-host-zi-test android-jni-zi-test update-transport-zi-test
plan9-host-zi-test: $(ZI2C_BIN)
	@sh tests/plan9_host_zi_test.sh $(abspath $(dir $(ZI2C_BIN)))

android-jni-zi-test: $(ZI2C_BIN)
	@python3 tests/android_jni_zi_test.py $(abspath $(dir $(ZI2C_BIN)))

update-transport-zi-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u GDK_DISPLAY \
		python3 tests/update_fetch_host_test.py
	@env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u GDK_DISPLAY \
		python3 tests/update_flow_zi_test.py

test: plan9-host-zi-test android-jni-zi-test update-transport-zi-test

.PHONY: secondary-window-host-test
secondary-window-host-test: $(ZI2C_BIN) $(RAYLIB_A)
	@sh tests/secondary_window_host_zi_test.sh \
		$(abspath $(dir $(ZI2C_BIN))) $(abspath $(RAYLIB_A))

.PHONY: raylib-log-host-test
raylib-log-host-test: $(ZI2C_BIN) $(RAYLIB_A)
	@mkdir -p $(BUILD_DIR)/raylib-log-host-test/c
	@$(ZI2C_BIN) --define PLATFORM_DESKTOP \
		--entry raylib_log_behavior:main --root tests \
		--module-path src --module-path $(ZIRAN_DIR)/std \
		-o $(BUILD_DIR)/raylib-log-host-test/c tests/raylib_log_behavior.zi
	@$(CC) -std=c11 -O2 -I$(ZIRAN_DIR)/include \
		-iquote $(BUILD_DIR)/raylib-log-host-test/c \
		$(BUILD_DIR)/raylib-log-host-test/c/*.c $(RAYLIB_A) \
		$(RAY_LDLIBS) -lm -ldl -pthread \
		-o $(BUILD_DIR)/raylib-log-host-test/test
	@env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u GDK_DISPLAY \
		$(BUILD_DIR)/raylib-log-host-test/test \
		> $(BUILD_DIR)/raylib-log-host-test/output 2>&1
	@grep -qF 'width=320 height=560 embedded=1' \
		$(BUILD_DIR)/raylib-log-host-test/output
	@grep -qF 'scale=1.50 layout=320x560' \
		$(BUILD_DIR)/raylib-log-host-test/output
	@grep -qF 'track=2 practice=3' \
		$(BUILD_DIR)/raylib-log-host-test/output

test: raylib-log-host-test

.PHONY: dpi-state-zi-test
dpi-state-zi-test: $(ZI2C_BIN)
	@sh tests/dpi_state_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

test: dpi-state-zi-test

.PHONY: settings-ui-zi-test
settings-ui-zi-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/settings_ui_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

test: settings-ui-zi-test

.PHONY: break-stats-zi-test
break-stats-zi-test: $(ZI2C_BIN) $(SQLITE_AMALGAMATION_C) $(SQLITE_AMALGAMATION_H)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/break_stats_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

test: break-stats-zi-test

.PHONY: android-health-zi-test
android-health-zi-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/android_health_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

test: android-health-zi-test

.PHONY: android-push-zi-test
android-push-zi-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/android_push_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

test: android-push-zi-test

.PHONY: android-wakelock-zi-test
android-wakelock-zi-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/android_wakelock_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

test: android-wakelock-zi-test

.PHONY: android-timer-zi-test
android-timer-zi-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/android_timer_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

test: android-timer-zi-test

.PHONY: android-import-zi-test
android-import-zi-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/android_import_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

test: android-import-zi-test

.PHONY: android-runtime-assets-zi-test
android-runtime-assets-zi-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/android_runtime_assets_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

test: android-runtime-assets-zi-test

.PHONY: android-lifecycle-zi-test
android-lifecycle-zi-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/android_lifecycle_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

test: android-lifecycle-zi-test

.PHONY: language-selection-zi-test
language-selection-zi-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/language_selection_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

test: language-selection-zi-test

.PHONY: audio-policy-test
audio-policy-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/audio_policy_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

test: audio-policy-test

.PHONY: audio-runtime-test
audio-runtime-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY \
		sh tests/audio_runtime_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

test: audio-runtime-test

.PHONY: audio-meter-zi-test
audio-meter-zi-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u GDK_DISPLAY \
		sh tests/audio_meter_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

test: audio-meter-zi-test

.PHONY: profile-picture-policy-test
profile-picture-policy-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/profile_picture_policy_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

test: profile-picture-policy-test

.PHONY: assets-zi-test
assets-zi-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/assets_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

test: assets-zi-test

.PHONY: asset-files-zi-test
asset-files-zi-test: $(ZI2C_BIN) $(RAYLIB_A)
	@sh tests/asset_files_zi_test.sh $(ZIRAN_BUILD_DIR)/bin $(RAYLIB_A)

test: asset-files-zi-test

.PHONY: settings-status-zi-test
settings-status-zi-test: $(ZI2C_BIN)
	@python3 tests/settings_status_test.py $(ZIRAN_BUILD_DIR)/bin

test: settings-status-zi-test

.PHONY: settings-mutation-zi-test
settings-mutation-zi-test: $(ZI2C_BIN)
	@sh tests/settings_mutation_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

test: settings-mutation-zi-test

.PHONY: theme-catalog-zi-test
theme-catalog-zi-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/theme_catalog_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

test: theme-catalog-zi-test

.PHONY: style-apply-zi-test
style-apply-zi-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/style_apply_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

test: style-apply-zi-test

.PHONY: audio-settings-test
audio-settings-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/audio_settings_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

test: audio-settings-test

.PHONY: bottom-nav-policy-test
bottom-nav-policy-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/bottom_nav_policy_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

test: bottom-nav-policy-test

.PHONY: mini-mode-policy-test
mini-mode-policy-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/mini_mode_policy_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

test: mini-mode-policy-test

.PHONY: app-nav-state-zi-test
app-nav-state-zi-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/app_nav_state_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

test: app-nav-state-zi-test

.PHONY: app-zoom-test
app-zoom-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/app_zoom_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

test: app-zoom-test

.PHONY: sync-safety-test
sync-safety-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/sync_safety_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

test: sync-safety-test

.PHONY: sync-status-policy-test
sync-status-policy-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/sync_status_policy_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

test: sync-status-policy-test

.PHONY: social-action-queue-test
social-action-queue-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/social_action_queue_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

test: social-action-queue-test

.PHONY: sync-worker-host-test
sync-worker-host-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/sync_worker_host_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

test: sync-worker-host-test

.PHONY: sync-status-test
sync-status-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/sync_status_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

test: sync-status-test

.PHONY: route-list-test
route-list-test: build-laws $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/route_list_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

.PHONY: habit-calendar-test
habit-calendar-test: build-laws $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/habit_calendar_zi_test.sh $(ZIRAN_BUILD_DIR)/bin \
		$(KRYON_DIR)/src/ui

test: habit-calendar-test

.PHONY: habit-linked-rules-zi-test
habit-linked-rules-zi-test: build-laws $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/habit_linked_rules_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

test: habit-linked-rules-zi-test

.PHONY: meditation-timing-test
meditation-timing-test: build-laws $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/meditation_timing_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

test: meditation-timing-test

.PHONY: app-clock-test
app-clock-test: $(ZI2C_BIN)
	@mkdir -p $(BUILD_DIR)/app-clock-test/generated
	@$(ZI2C_BIN) --no-main --root src \
		--module-path $(ZIRAN_DIR)/std \
		-o $(BUILD_DIR)/app-clock-test/generated \
		src/app/app_clock_host.zi
	@$(CC) -std=c11 -Wall -Wextra -Werror \
		-Wno-unused-function -I$(ZIRAN_DIR)/include \
		-iquote $(BUILD_DIR)/app-clock-test/generated \
		tests/app_clock_host_test.c \
		$(BUILD_DIR)/app-clock-test/generated/app/app_clock_host.c \
		$(BUILD_DIR)/app-clock-test/generated/time_parts.c \
		$(BUILD_DIR)/app-clock-test/generated/date_time.c \
		-o $(BUILD_DIR)/app-clock-test/test
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		$(BUILD_DIR)/app-clock-test/test

test: app-clock-test

.PHONY: friend-requests-test
friend-requests-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		ZIRAN_INCLUDE=$(ZIRAN_DIR)/include \
		sh tests/friend_requests_zi_test.sh $(ZIRAN_BUILD_DIR)/bin \
		$(ZIRAN_DIR)/std

test: friend-requests-test

.PHONY: modal-rules-test
modal-rules-test: build-laws $(ZI2C_BIN)
	@sh tests/modal_rules_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

test: modal-rules-test

.PHONY: direct-draw-plan-test
test: direct-draw-plan-test
direct-draw-plan-test: $(ZI2C_BIN)
	@sh tests/direct_draw_plan_test.sh $(ZIRAN_BUILD_DIR)/bin

.PHONY: elist-screen-test
test: elist-screen-test
elist-screen-test: $(ZI2C_BIN)
	@sh tests/elist_screen_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

$(BREATH_TIMING_GEN_DIR)/core/breath_timing.c: src/core/breath_timing.zi src/core/types.zi $(ZI2C_BIN)
	@mkdir -p $(BREATH_TIMING_GEN_DIR)
	$(ZI2C_BIN) --no-main --root src \
		-o $(BREATH_TIMING_GEN_DIR) src/core/breath_timing.zi

$(BREAK_RULES_GEN_DIR)/breaks/break_rules.c: src/breaks/break_rules.zi src/breaks/break_types.zi $(ZI2C_BIN)
	@mkdir -p $(BREAK_RULES_GEN_DIR)
	$(ZI2C_BIN) --no-main --root src \
		-o $(BREAK_RULES_GEN_DIR) src/breaks/break_rules.zi

$(sort $(BUILD_OBJ_DIR) $(NATIVE_OBJ_DIR) $(NATIVE_BIN_DIR) $(NATIVE_DIST_DIR) $(LINUX_BIN_DIR) $(LINUX_DIST_DIR) $(LINUX_APPIMAGE_BUILD_DIR) $(DEB_BUILD_DIR) $(DEB_DIST_DIR) $(RPM_BUILD_DIR) $(RPM_DIST_DIR) $(SNAP_BUILD_DIR) $(SNAP_DIST_DIR) $(FLATPAK_BUILD_DIR) $(FLATPAK_DIST_DIR) $(CLICK_BIN_DIR) $(CLICK_BUILD_DIR) $(CLICK_DIST_DIR) $(WINDOWS_DIST_DIR) $(ANDROID_BUILD_DIR) $(TEST_BIN_DIR) $(WEB_OBJ_DIR) $(WEB_DIST_DIR) $(CHROME_WEB_STORE_DIR) $(FIREFOX_ADDONS_DIR)):
	mkdir -p $@

$(WINDOWS_BIN_DIR)/$(WIN64_ARCH) $(WINDOWS_BIN_DIR)/$(WIN32_ARCH):
	mkdir -p $@

FORCE:

.PHONY: theme-catalog-bundle-check
theme-catalog-bundle-check:
	@cmp themes/catalog_light.kss $(KRYON_DIR)/themes/catalog_light.kss
	@cmp themes/catalog_dark.kss $(KRYON_DIR)/themes/catalog_dark.kss

test: theme-catalog-bundle-check

$(EMBEDDED_ASSETS_C): Makefile $(EMBEDDED_ASSET_FILES) scripts/embed-app-assets.py src/app/assets_host.h | $(BUILD_OBJ_DIR) theme-catalog-bundle-check
	python3 scripts/embed-app-assets.py $@ $(EMBEDDED_ASSET_FILES)

$(KRYON_ICON_ASSETS_C) $(KRYON_ICON_NAMES_C) $(KRYON_ICON_TYPES_H): $(KRYON_ICON_FILES) $(KRYON_DIR)/scripts/embed-icon-sheets.py  | $(BUILD_OBJ_DIR)
	cd $(KRYON_DIR) && python3 scripts/embed-icon-sheets.py "$(KRYON_ICON_DIR)" \
		"$(abspath $(KRYON_ICON_ASSETS_C))" \
		--types-output "$(abspath $(KRYON_ICON_TYPES_H))" \
		--names-output "$(abspath $(KRYON_ICON_NAMES_C))"

sync-web-icons: $(KRYON_SYNC_ICONS)
	sh $(KRYON_SYNC_ICONS) web-assets/icons $(WEB_SHARED_ICON_SHEETS)
	cp assets/app/icon.png web-assets/icons/$(APP_NAME).png

$(CLICK_LIBOQS_A): $(LIBOQS_DIR)/CMakeLists.txt
	rm -rf $(CLICK_LIBOQS_BUILD_DIR)
	$(CMAKE) -S $(LIBOQS_DIR) -B $(CLICK_LIBOQS_BUILD_DIR) \
		-DCMAKE_SYSTEM_NAME=Linux \
		-DCMAKE_SYSTEM_PROCESSOR=aarch64 \
		-DCMAKE_C_COMPILER=$(AARCH64_CC) \
		-DCMAKE_AR=$(AARCH64_AR) \
		-DCMAKE_RANLIB=$(AARCH64_RANLIB) \
		-DCMAKE_BUILD_TYPE=$(KRYON_LIBOQS_BUILD_TYPE) \
		-DBUILD_SHARED_LIBS=OFF \
		-DOQS_BUILD_ONLY_LIB=ON \
		-DOQS_USE_OPENSSL=OFF \
		-DOQS_DIST_BUILD=OFF \
		-DOQS_OPT_TARGET=generic \
		$(KRYON_LIBOQS_CPU_FEATURE_CMAKE_FLAGS) \
		-DOQS_MINIMAL_BUILD=$(KRYON_LIBOQS_MINIMAL_BUILD)
	$(CMAKE) --build $(CLICK_LIBOQS_BUILD_DIR) --target oqs

$(SQLITE_AMALGAMATION_C) $(SQLITE_AMALGAMATION_H): $(SQLITE_DIR)/configure $(SQLITE_DIR)/manifest | $(BUILD_OBJ_DIR)
	mkdir -p $(SQLITE_BUILD_DIR)
	cd $(SQLITE_BUILD_DIR) && $(abspath $(SQLITE_DIR))/configure
	$(MAKE) -C $(SQLITE_BUILD_DIR) sqlite3.c sqlite3.h

$(WIN64_CURL_A): $(CURL_DIR)/CMakeLists.txt
	rm -rf $(WIN64_CURL_BUILD_DIR)
	$(CMAKE) -S $(CURL_DIR) -B $(WIN64_CURL_BUILD_DIR) \
		-DCMAKE_SYSTEM_NAME=Windows \
		-DCMAKE_C_COMPILER=$(WIN64_CC_PATH) \
		-DCMAKE_AR=$(WIN64_AR_PATH) \
		-DCMAKE_RANLIB=$(WIN64_RANLIB_PATH) \
		-DCMAKE_EXE_LINKER_FLAGS="$(WIN64_THREAD_LDFLAGS)" \
		-DCMAKE_INSTALL_PREFIX=$(abspath $(WIN64_CURL_BUILD_DIR)) \
		-DCMAKE_BUILD_TYPE=Release \
		-DBUILD_SHARED_LIBS=OFF \
		-DBUILD_STATIC_LIBS=ON \
		-DBUILD_CURL_EXE=OFF \
		-DCURL_STATICLIB=ON \
		-DCURL_USE_SCHANNEL=ON \
		-DCURL_USE_OPENSSL=OFF \
		-DCURL_USE_LIBPSL=OFF \
		-DCURL_USE_LIBSSH2=OFF \
		-DCURL_USE_GSSAPI=OFF \
		-DUSE_NGHTTP2=OFF \
		-DUSE_LIBIDN2=OFF \
		-DCURL_DISABLE_LDAP=ON \
		-DCURL_DISABLE_LDAPS=ON \
		-DCURL_DISABLE_SMB=ON \
		-DENABLE_CURL_MANUAL=OFF \
		-DBUILD_EXAMPLES=OFF \
		-DBUILD_LIBCURL_DOCS=OFF \
		-DBUILD_MISC_DOCS=OFF \
		-DBUILD_TESTING=OFF
	$(CMAKE) --build $(WIN64_CURL_BUILD_DIR) --target install

$(WIN64_LIBOQS_A): $(LIBOQS_DIR)/CMakeLists.txt
	rm -rf $(WIN64_LIBOQS_BUILD_DIR)
	$(CMAKE) -S $(LIBOQS_DIR) -B $(WIN64_LIBOQS_BUILD_DIR) \
		-DCMAKE_SYSTEM_NAME=Windows \
		-DCMAKE_SYSTEM_PROCESSOR=$(WIN64_CMAKE_SYSTEM_PROCESSOR) \
		-DCMAKE_C_COMPILER=$(WIN64_CC_PATH) \
		-DCMAKE_AR=$(WIN64_AR_PATH) \
		-DCMAKE_RANLIB=$(WIN64_RANLIB_PATH) \
		-DCMAKE_EXE_LINKER_FLAGS="$(WIN64_THREAD_LDFLAGS)" \
		-DCMAKE_BUILD_TYPE=$(KRYON_LIBOQS_BUILD_TYPE) \
		-DBUILD_SHARED_LIBS=OFF \
		-DOQS_BUILD_ONLY_LIB=ON \
		-DOQS_USE_OPENSSL=OFF \
		-DOQS_DIST_BUILD=OFF \
		-DOQS_OPT_TARGET=generic \
		$(KRYON_LIBOQS_CPU_FEATURE_CMAKE_FLAGS) \
		-DOQS_MINIMAL_BUILD=$(KRYON_LIBOQS_MINIMAL_BUILD)
	$(CMAKE) --build $(WIN64_LIBOQS_BUILD_DIR) --target oqs

$(WIN32_CURL_A): $(CURL_DIR)/CMakeLists.txt
	rm -rf $(WIN32_CURL_BUILD_DIR)
	$(CMAKE) -S $(CURL_DIR) -B $(WIN32_CURL_BUILD_DIR) \
		-DCMAKE_SYSTEM_NAME=Windows \
		-DCMAKE_C_COMPILER=$(WIN32_CC_PATH) \
		-DCMAKE_AR=$(WIN32_AR_PATH) \
		-DCMAKE_RANLIB=$(WIN32_RANLIB_PATH) \
		-DCMAKE_EXE_LINKER_FLAGS="$(WIN32_THREAD_LDFLAGS)" \
		-DCMAKE_INSTALL_PREFIX=$(abspath $(WIN32_CURL_BUILD_DIR)) \
		-DCMAKE_BUILD_TYPE=Release \
		-DBUILD_SHARED_LIBS=OFF \
		-DBUILD_STATIC_LIBS=ON \
		-DBUILD_CURL_EXE=OFF \
		-DCURL_STATICLIB=ON \
		-DCURL_USE_SCHANNEL=ON \
		-DCURL_USE_OPENSSL=OFF \
		-DCURL_USE_LIBPSL=OFF \
		-DCURL_USE_LIBSSH2=OFF \
		-DCURL_USE_GSSAPI=OFF \
		-DUSE_NGHTTP2=OFF \
		-DUSE_LIBIDN2=OFF \
		-DCURL_DISABLE_LDAP=ON \
		-DCURL_DISABLE_LDAPS=ON \
		-DCURL_DISABLE_SMB=ON \
		-DENABLE_CURL_MANUAL=OFF \
		-DBUILD_EXAMPLES=OFF \
		-DBUILD_LIBCURL_DOCS=OFF \
		-DBUILD_MISC_DOCS=OFF \
		-DBUILD_TESTING=OFF
	$(CMAKE) --build $(WIN32_CURL_BUILD_DIR) --target install

$(WIN32_LIBOQS_A): $(LIBOQS_DIR)/CMakeLists.txt
	rm -rf $(WIN32_LIBOQS_BUILD_DIR)
	$(CMAKE) -S $(LIBOQS_DIR) -B $(WIN32_LIBOQS_BUILD_DIR) \
		-DCMAKE_SYSTEM_NAME=Windows \
		-DCMAKE_SYSTEM_PROCESSOR=$(WIN32_CMAKE_SYSTEM_PROCESSOR) \
		-DCMAKE_C_COMPILER=$(WIN32_CC_PATH) \
		-DCMAKE_AR=$(WIN32_AR_PATH) \
		-DCMAKE_RANLIB=$(WIN32_RANLIB_PATH) \
		-DCMAKE_EXE_LINKER_FLAGS="$(WIN32_THREAD_LDFLAGS)" \
		-DCMAKE_BUILD_TYPE=$(KRYON_LIBOQS_BUILD_TYPE) \
		-DBUILD_SHARED_LIBS=OFF \
		-DOQS_BUILD_ONLY_LIB=ON \
		-DOQS_USE_OPENSSL=OFF \
		-DOQS_DIST_BUILD=OFF \
		-DOQS_OPT_TARGET=generic \
		$(KRYON_LIBOQS_CPU_FEATURE_CMAKE_FLAGS) \
		-DOQS_MINIMAL_BUILD=$(KRYON_LIBOQS_MINIMAL_BUILD)
	$(CMAKE) --build $(WIN32_LIBOQS_BUILD_DIR) --target oqs

$(TARGET): Makefile $(SRC) $(KRYON_LIBRARY_BUILD_DIR)/libkryon.a $(SQLITE_SRC) $(SQLITE_AMALGAMATION_H) $(FONT_FILES) $(EMBEDDED_ASSETS_C) $(KRYON_NATIVE_BACKEND_DEPS) $(LIBOQS_A) $(CURL_PROTOCOL_CHECK) | $(NATIVE_BIN_DIR)
$(TARGET): | zi-check
	$(shell mkdir -p $(NATIVE_OBJ_DIR))
	$(file >$(NATIVE_OBJ_DIR)/inputs.mk,NATIVE_SOURCES := $(APP_SRCS) $(GENERATED_NATIVE_C) $(EMBEDDED_ASSETS_C) $(SQLITE_SRC))
	$(file >>$(NATIVE_OBJ_DIR)/inputs.mk,NATIVE_CFLAGS := $(NATIVE_COMPILE_FLAGS))
	+@$(MAKE) --no-print-directory -f mk/native-objects.mk \
		$(if $(filter -j%,$(MAKEFLAGS)),,-j$(NATIVE_JOBS)) \
		CC='$(CC)' OBJ_DIR=$(NATIVE_OBJ_DIR)
	$(CC) $(KRYON_NATIVE_CFLAGS) \
		-o $@ \
		@$(NATIVE_OBJ_DIR)/objects.rsp \
		$(KRYON_LIBRARY_BUILD_DIR)/libkryon.a \
		$(KRYON_NATIVE_BACKEND_LIBS) \
		$(LIBOQS_A) \
		$(KRYON_NATIVE_BACKEND_LDLIBS) \
		$(RUNTIME_ASSET_LDLIBS) \
		$(NATIVE_SYSTEM_LDLIBS) \
		$(LDFLAGS)

$(KRYON_HOST_TARGET): Makefile $(KRYON_HOST_SRC) $(SQLITE_SRC) $(SQLITE_AMALGAMATION_H) $(FONT_FILES) $(EMBEDDED_ASSETS_C) | $(BUILD_DIR)
	mkdir -p $(dir $@)
	$(CC) $(CFLAGS) -fPIC -shared \
		$(APP_INCLUDE) \
		$(KRYON_INCLUDE) \
		$(SQLITE_INCLUDE) \
		$(LIBOQS_INCLUDE) \
		$(RAY_CFLAGS) \
		-DHAS_LIBOQS=1 \
		-DSUPPORT_MODULE_RAUDIO=1 \
		-DSUPPORT_FILEFORMAT_OGG=1 \
		-DSUPPORT_FILEFORMAT_MP3=0 \
		-o $@ \
		$(KRYON_HOST_SRC) \
		$(SQLITE_SRC) \
		$(NATIVE_SYSTEM_LDLIBS) \
		-Wl,-Bsymbolic \
		-Wl,--allow-shlib-undefined \
		$(LDFLAGS)

$(CLICK_BIN): Makefile $(SRC) $(KRYON_CLICK_SRCS) $(SQLITE_SRC) $(SQLITE_AMALGAMATION_H) $(FONT_FILES) $(EMBEDDED_ASSETS_C) $(CLICK_RAYLIB_A) $(CLICK_LIBOQS_A) | $(CLICK_BIN_DIR)
	$(AARCH64_CC) $(CLICK_CFLAGS) \
		$(APP_INCLUDE) \
		$(KRYON_INCLUDE) \
		$(SQLITE_INCLUDE) \
		$(CLICK_LIBOQS_INCLUDE) \
		$(AARCH64_RAY_CFLAGS) \
		-DHAS_LIBOQS=1 \
		-DPLATFORM_DESKTOP \
		-DSUPPORT_MODULE_RAUDIO=1 \
		-DSUPPORT_FILEFORMAT_OGG=1 \
		-DSUPPORT_FILEFORMAT_MP3=0 \
		-o $@ \
		$(APP_SRCS) $(GENERATED_NATIVE_C) $(EMBEDDED_ASSETS_C) \
		$(KRYON_CLICK_SRCS) \
		$(SQLITE_SRC) \
		$(CLICK_RAYLIB_A) \
		$(CLICK_LIBOQS_A) \
		$(AARCH64_RAY_LDLIBS) \
		$(AARCH64_KRYON_CURL_LDLIBS) \
		-lm -lpthread -ldl -lrt -latomic \
		$(LDFLAGS)
	@if command -v patchelf >/dev/null; then \
		patchelf --set-interpreter "$(CLICK_PATCHELF_INTERPRETER)" --set-rpath '$$ORIGIN/../lib' $@; \
	fi

$(CLICK_TARGET): Makefile $(CLICK_BIN_INPUT) $(CLICK_DIR)/$(APP_NAME).apparmor $(CLICK_DIR)/$(APP_NAME).desktop $(CLICK_DIR)/$(APP_NAME).metainfo.xml $(CLICK_RUNNER) $(LINUX_APPIMAGE_ICON) $(VERSION_FILE) | $(CLICK_BUILD_DIR) $(CLICK_DIST_DIR)
	@command -v click >/dev/null || { \
		echo "click is missing. Install click or put it on PATH."; \
		exit 1; \
	}
	rm -rf $(CLICK_ROOT)
	rm -f $(CLICK_DIST_DIR)/$(CLICK_PACKAGE)_*_$(CLICK_ARCH).click
	rm -f $(CLICK_DIST_DIR)/$(CLICK_ID)_*_$(CLICK_ARCH).click
	rm -f $(CLICK_ID)_$(APP_VERSION)_$(CLICK_ARCH).click
	mkdir -p $(CLICK_ROOT)/usr/bin $(CLICK_ROOT)/usr/lib $(CLICK_ROOT)/usr/share/applications $(CLICK_ROOT)/usr/share/icons/hicolor/512x512/apps $(CLICK_ROOT)/usr/share/metainfo
	cp $(CLICK_BIN_INPUT) $(CLICK_ROOT)/usr/bin/$(APP_NAME)
	cp $(CLICK_RUNNER) $(CLICK_ROOT)/run-$(APP_NAME).sh
	chmod +x $(CLICK_ROOT)/run-$(APP_NAME).sh $(CLICK_ROOT)/usr/bin/$(APP_NAME)
	@for lib in $(CLICK_RUNTIME_LIBS); do \
		if [ -f "$$lib" ]; then \
			cp -L "$$lib" $(CLICK_ROOT)/usr/lib/; \
		fi; \
	done
	@if command -v patchelf >/dev/null; then \
		for elf in $(CLICK_ROOT)/usr/lib/*.so*; do \
			if [ -f "$$elf" ]; then patchelf --set-rpath '$$ORIGIN' "$$elf" >/dev/null 2>&1 || true; fi; \
		done; \
	fi
	printf '%s\n' \
		'{' \
		'  "name": "$(CLICK_ID)",' \
		'  "title": "$(CLICK_TITLE)",' \
		'  "version": "$(APP_VERSION)",' \
		'  "architecture": "$(CLICK_ARCH)",' \
		'  "framework": "$(CLICK_FRAMEWORK)",' \
		'  "description": "Syncable breathing, meditation, and habit practice app.",' \
		'  "maintainer": "$(CLICK_MAINTAINER)",' \
		'  "hooks": {' \
		'    "$(APP_NAME)": {' \
		'      "apparmor": "$(APP_NAME).apparmor",' \
		'      "desktop": "$(APP_NAME).desktop"' \
		'    }' \
		'  }' \
		'}' \
		> $(CLICK_ROOT)/manifest.json
	cp $(CLICK_DIR)/$(APP_NAME).apparmor $(CLICK_ROOT)/$(APP_NAME).apparmor
	cp $(CLICK_DIR)/$(APP_NAME).desktop $(CLICK_ROOT)/$(APP_NAME).desktop
	@if [ "$(CLICK_INCLUDE_METAINFO)" = "1" ]; then \
		mkdir -p $(CLICK_ROOT)/usr/share/metainfo; \
		sed -e 's/<release version="[^"]*"/<release version="$(APP_VERSION)"/' $(CLICK_DIR)/$(APP_NAME).metainfo.xml > $(CLICK_ROOT)/usr/share/metainfo/$(CLICK_ID).metainfo.xml; \
	fi
	cp $(LINUX_APPIMAGE_ICON) $(CLICK_ROOT)/$(APP_NAME).png
	cp $(LINUX_APPIMAGE_ICON) $(CLICK_ROOT)/usr/share/icons/hicolor/512x512/apps/$(APP_NAME).png
	click build $(CLICK_ROOT) $(CLICK_DIST_DIR)
	@if [ -f "$(CLICK_DIST_DIR)/$(CLICK_ID)_$(APP_VERSION)_$(CLICK_ARCH).click" ]; then \
		mv "$(CLICK_DIST_DIR)/$(CLICK_ID)_$(APP_VERSION)_$(CLICK_ARCH).click" "$(CLICK_TARGET)"; \
	elif [ -f "$(CLICK_ID)_$(APP_VERSION)_$(CLICK_ARCH).click" ]; then \
		mv "$(CLICK_ID)_$(APP_VERSION)_$(CLICK_ARCH).click" "$(CLICK_TARGET)"; \
	fi
	test -f $@

$(WIN64_RESOURCE): windows/$(APP_NAME).rc windows/$(APP_NAME).ico
	mkdir -p $(dir $@)
	$(WIN64_WINDRES) -Iwindows -O coff $< $@

$(WIN32_RESOURCE): windows/$(APP_NAME).rc windows/$(APP_NAME).ico
	mkdir -p $(dir $@)
	$(WIN32_WINDRES) -Iwindows -O coff $< $@

$(WIN64_TARGET): Makefile $(WINDOWS_SRC) $(WINDOWS_GEN_STAMP) $(SQLITE_SRC) $(SQLITE_AMALGAMATION_H) $(FONT_FILES) $(EMBEDDED_ASSETS_C) $(WIN64_RAYLIB_A) $(WIN64_CURL_A) $(WIN64_LIBOQS_A) $(WIN64_RESOURCE) | $(WINDOWS_BIN_DIR)/$(WIN64_ARCH)
	$(WIN64_CC) $(WINDOWS_CFLAGS) \
		-iquote$(WINDOWS_GEN_DIR) -iquote$(WINDOWS_GEN_DIR)/src $(WINDOWS_APP_INCLUDE) \
		$(KRYON_INCLUDE) \
		$(SQLITE_INCLUDE) \
		$(WIN64_LIBOQS_INCLUDE) \
		-I$(WIN64_CURL_INCLUDE_DIR) \
		-DHAS_LIBOQS=1 \
		-DPLATFORM_DESKTOP \
		-DCURL_STATICLIB \
		-o $@ \
		$(WINDOWS_SRC) $(GENERATED_WINDOWS_C) \
		$(SQLITE_SRC) \
		$(WIN64_RAYLIB_A) \
		$(WIN64_CURL_A) \
		$(WIN64_LIBOQS_A) \
		$(WIN64_RESOURCE) $(WINDOWS_LDLIBS) \
		$(WIN64_THREAD_LDFLAGS) \
		$(WINDOWS_LDFLAGS)
	$(WIN64_STRIP) $@

$(WIN32_TARGET): Makefile $(WINDOWS_SRC) $(WINDOWS_GEN_STAMP) $(SQLITE_SRC) $(SQLITE_AMALGAMATION_H) $(FONT_FILES) $(EMBEDDED_ASSETS_C) $(WIN32_RAYLIB_A) $(WIN32_CURL_A) $(WIN32_LIBOQS_A) $(WIN32_RESOURCE) | $(WINDOWS_BIN_DIR)/$(WIN32_ARCH)
	$(WIN32_CC) $(WINDOWS_CFLAGS) \
		-iquote$(WINDOWS_GEN_DIR) -iquote$(WINDOWS_GEN_DIR)/src $(WINDOWS_APP_INCLUDE) \
		$(KRYON_INCLUDE) \
		$(SQLITE_INCLUDE) \
		$(WIN32_LIBOQS_INCLUDE) \
		-I$(WIN32_CURL_INCLUDE_DIR) \
		-DHAS_LIBOQS=1 \
		-DPLATFORM_DESKTOP \
		-DCURL_STATICLIB \
		-o $@ \
		$(WINDOWS_SRC) $(GENERATED_WINDOWS_C) \
		$(SQLITE_SRC) \
		$(WIN32_RAYLIB_A) \
		$(WIN32_CURL_A) \
		$(WIN32_LIBOQS_A) \
		$(WIN32_RESOURCE) $(WINDOWS_LDLIBS) \
		$(WIN32_THREAD_LDFLAGS) \
		$(WIN32_WINDOWS_LDFLAGS)
	$(WIN32_STRIP) $@

$(APPIMAGE_TARGET): $(TARGET) $(LINUX_APPIMAGE_APPRUN) $(LINUX_APPIMAGE_DESKTOP) $(LINUX_APPIMAGE_ICON) $(LINUX_APPIMAGE_APPDATA) | $(LINUX_DIST_DIR) $(LINUX_APPIMAGE_BUILD_DIR)
	@test -n "$(strip $(APPIMAGE_INTERPRETER))" || { \
		echo "No AppImage interpreter is configured for ARCH=$(ARCH)"; \
		exit 1; \
	}
	@command -v linuxdeploy-plugin-appimage >/dev/null || { \
		echo "linuxdeploy-plugin-appimage is missing. Install it or put it on PATH."; \
		exit 1; \
	}
	@command -v appimagetool >/dev/null || { \
		echo "appimagetool is missing. Install it or put it on PATH."; \
		exit 1; \
	}
	@command -v patchelf >/dev/null || { \
		echo "patchelf is missing. Install it or put it on PATH."; \
		exit 1; \
	}
	rm -rf $(LINUX_APPDIR)
	rm -rf $(LINUX_DIST_DIR)/*.AppDir
	rm -f $(LINUX_DIST_DIR)/*.AppImage
	mkdir -p $(LINUX_APPDIR)/usr/bin $(LINUX_APPDIR)/usr/lib $(LINUX_APPDIR)/usr/share/applications $(LINUX_APPDIR)/usr/share/icons/hicolor/512x512/apps $(LINUX_APPDIR)/usr/share/metainfo $(LINUX_APPDIR)/usr/share/appdata
	cp $(TARGET) $(LINUX_APPDIR)/usr/bin/$(APP_NAME)
	patchelf --set-interpreter $(APPIMAGE_INTERPRETER) $(LINUX_APPDIR)/usr/bin/$(APP_NAME)
	cp $(LINUX_APPIMAGE_APPRUN) $(LINUX_APPDIR)/AppRun
	chmod +x $(LINUX_APPDIR)/AppRun
	@loader=$$(LC_ALL=C readelf -l $(TARGET) | sed -n 's#.*Requesting program interpreter: \(.*\)]#\1#p'); \
	if printf '%s\n' "$$loader" | grep -q '^/nix/store/.*glibc.*/'; then \
		glibc_lib_dir=$$(dirname "$$loader"); \
		echo "Bundling glibc loader: $$loader"; \
		cp "$$loader" $(LINUX_APPDIR)/usr/lib/; \
		for lib in libc.so.6 libm.so.6 libpthread.so.0 libdl.so.2 librt.so.1 libresolv.so.2 libnss_files.so.2; do \
			if [ -f "$$glibc_lib_dir/$$lib" ]; then \
				cp "$$glibc_lib_dir/$$lib" $(LINUX_APPDIR)/usr/lib/; \
				chmod u+w $(LINUX_APPDIR)/usr/lib/$$lib; \
			fi; \
		done; \
		chmod u+w $(LINUX_APPDIR)/usr/lib/$$(basename "$$loader"); \
	else \
		echo "Not bundling glibc; build interpreter is $$loader"; \
	fi
	sed -e 's/^Icon=.*/Icon=$(APP_ICON_NAME)/' $(LINUX_APPIMAGE_DESKTOP) > $(LINUX_APPDIR)/$(APP_DESKTOP_ID).desktop
	cp $(LINUX_APPDIR)/$(APP_DESKTOP_ID).desktop $(LINUX_APPDIR)/usr/share/applications/$(APP_DESKTOP_ID).desktop
	sed -e 's/<release version="[^"]*"/<release version="$(APP_VERSION)"/' \
		-e 's#<launchable type="desktop-id">[^<]*</launchable>#<launchable type="desktop-id">$(APP_DESKTOP_ID).desktop</launchable>#' \
		$(LINUX_APPIMAGE_APPDATA) > $(LINUX_APPDIR)/usr/share/metainfo/$(ANDROID_APP_ID).metainfo.xml
	cp $(LINUX_APPDIR)/usr/share/metainfo/$(ANDROID_APP_ID).metainfo.xml $(LINUX_APPDIR)/usr/share/appdata/$(ANDROID_APP_ID).appdata.xml
	cp $(LINUX_APPIMAGE_ICON) $(LINUX_APPDIR)/$(APP_ICON_NAME).png
	cp $(LINUX_APPIMAGE_ICON) $(LINUX_APPDIR)/usr/share/icons/hicolor/512x512/apps/$(APP_ICON_NAME).png
	@# Manually copy critical X11/OpenGL libraries that linuxdeploy might miss
	@for lib in libX11.so.6 libXext.so.6 libdrm.so.2 libgbm.so.1 libEGL.so.1 libGLESv2.so.2 libGLdispatch.so.0 libglapi.so.0; do \
		found=$$(find /usr/lib /lib -name "$$lib" 2>/dev/null | head -n 1); \
		if [ -n "$$found" ]; then \
			echo "Copying $$lib from $$found"; \
			cp "$$found" $(LINUX_APPDIR)/usr/lib/ 2>/dev/null || true; \
		fi; \
	done
	@# Detect if running on NixOS (by checking if loader is in /nix/store)
	@loader=$$(LC_ALL=C readelf -l $(TARGET) | sed -n 's#.*Requesting program interpreter: \(.*\)]#\1#p'); \
	if printf '%s\n' "$$loader" | grep -q '^/nix/store/.*glibc.*/'; then \
		LIBRARY_FLAGS=""; \
		echo "Building on NixOS - linuxdeploy will auto-detect libraries from /nix/store"; \
	else \
		LIBRARY_FLAGS=""; \
		echo "Building on FHS system - linuxdeploy will auto-detect libraries"; \
	fi; \
	cd $(LINUX_APPIMAGE_BUILD_DIR) && env -u SOURCE_DATE_EPOCH ARCH=$(ARCH) LDAI_OUTPUT=$(abspath $(APPIMAGE_TARGET)) LDAI_UPDATE_INFORMATION='gh-releases-zsync|waozixyz|inbe|latest|$(APPIMAGE_NAME)' $(LINUXDEPLOY) \
		--appdir $(APP_NAME).AppDir \
		--executable $(abspath $(LINUX_APPDIR)/usr/bin/$(APP_NAME)) \
		--desktop-file $(abspath $(LINUX_APPDIR)/usr/share/applications/$(APP_DESKTOP_ID).desktop) \
		--icon-file $(abspath $(LINUX_APPDIR)/usr/share/icons/hicolor/512x512/apps/$(APP_ICON_NAME).png) \
		$$LIBRARY_FLAGS \
		--output appimage
	test -f $@

deb-check:
	@command -v dpkg-deb >/dev/null 2>&1 || { \
		echo "dpkg-deb is missing. On FreeBSD install it with: pkg install dpkg"; \
		echo "To build a Debian package on FreeBSD, pass DEB_BIN_SOURCE=/path/to/linux/inbe."; \
		exit 1; \
	}
	@if [ -z "$(strip $(DEB_BIN_INPUT))" ]; then \
		echo "No Linux binary is available for the Debian package."; \
		echo "Run this target on Linux, or on FreeBSD pass DEB_BIN_SOURCE=/path/to/linux/inbe."; \
		exit 1; \
	fi

$(DEB_TARGET): $(DEB_TARGET_PREREQS) deb-check | $(DEB_BUILD_DIR) $(DEB_DIST_DIR)
	rm -rf $(DEB_ROOT)
	mkdir -p $(DEB_ROOT)/DEBIAN $(DEB_ROOT)/usr/bin $(DEB_ROOT)/usr/share/applications $(DEB_ROOT)/usr/share/icons/hicolor/512x512/apps $(DEB_ROOT)/usr/share/metainfo
	cp $(DEB_BIN_INPUT) $(DEB_ROOT)/usr/bin/$(APP_NAME)
	chmod 755 $(DEB_ROOT)/usr/bin/$(APP_NAME)
	sed -e 's/^Icon=.*/Icon=$(APP_ICON_NAME)/' \
		$(LINUX_APPIMAGE_DESKTOP) > $(DEB_ROOT)/usr/share/applications/$(APP_DESKTOP_ID).desktop
	cp $(LINUX_APPIMAGE_ICON) $(DEB_ROOT)/usr/share/icons/hicolor/512x512/apps/$(APP_ICON_NAME).png
	sed -e 's/<release version="[^"]*"/<release version="$(APP_VERSION)"/' \
		-e 's#<launchable type="desktop-id">[^<]*</launchable>#<launchable type="desktop-id">$(APP_DESKTOP_ID).desktop</launchable>#' \
		$(LINUX_APPIMAGE_APPDATA) > $(DEB_ROOT)/usr/share/metainfo/$(ANDROID_APP_ID).metainfo.xml
	@installed_size=$$(find $(DEB_ROOT)/usr -type f -exec wc -c {} + | awk '$$2 != "total" { bytes += $$1 } END { print int((bytes + 1023) / 1024) }'); \
	{ \
		printf 'Package: %s\n' '$(DEB_PACKAGE_NAME)'; \
		printf 'Version: %s\n' '$(APP_VERSION)'; \
		printf 'Architecture: %s\n' '$(DEB_ARCH)'; \
		printf 'Maintainer: %s\n' '$(DEB_MAINTAINER)'; \
		printf 'Section: %s\n' '$(DEB_SECTION)'; \
		printf 'Priority: %s\n' '$(DEB_PRIORITY)'; \
		printf 'Installed-Size: %s\n' "$$installed_size"; \
		printf 'Depends: %s\n' '$(DEB_DEPENDS)'; \
		printf 'Homepage: %s\n' '$(APP_WWW)'; \
		printf 'Description: %s\n' '$(APP_COMMENT)'; \
		printf ' %s\n' '$(APP_DESC)'; \
	} > $(DEB_ROOT)/DEBIAN/control
	rm -f $(DEB_DIST_DIR)/$(DEB_PACKAGE_NAME)_*_$(DEB_ARCH).deb
	dpkg-deb --build --root-owner-group $(DEB_ROOT) $(DEB_TARGET)
	test -f $@

rpm-check:
	@command -v rpmbuild >/dev/null 2>&1 || { \
		echo "rpmbuild is missing. On FreeBSD install it with: pkg install rpm4"; \
		echo "To build an RPM package on FreeBSD, pass RPM_BIN_SOURCE=/path/to/linux/inbe."; \
		exit 1; \
	}
	@if [ -z "$(strip $(RPM_BIN_INPUT))" ]; then \
		echo "No Linux binary is available for the RPM package."; \
		echo "Run this target on Linux, or on FreeBSD pass RPM_BIN_SOURCE=/path/to/linux/inbe."; \
		exit 1; \
	fi

$(RPM_TARGET): $(RPM_TARGET_PREREQS) rpm-check | $(RPM_BUILD_DIR) $(RPM_DIST_DIR)
	rm -rf $(RPM_TOPDIR)
	mkdir -p $(RPM_TOPDIR)/BUILD $(RPM_TOPDIR)/BUILDROOT $(RPM_TOPDIR)/RPMS $(RPM_TOPDIR)/SOURCES $(RPM_TOPDIR)/SPECS $(RPM_TOPDIR)/SRPMS
	{ \
		printf '%s\n' 'Name: $(RPM_PACKAGE_NAME)'; \
		printf '%s\n' 'Version: $(APP_VERSION)'; \
		printf '%s\n' 'Release: $(RPM_RELEASE)%{?dist}'; \
		printf '%s\n' 'Summary: $(APP_COMMENT)'; \
		printf '%s\n' 'License: $(RPM_LICENSE)'; \
		printf '%s\n' 'URL: $(APP_WWW)'; \
		printf '%s\n' 'Requires: $(RPM_REQUIRES)'; \
		printf '%s\n' ''; \
		printf '%s\n' '%description'; \
		printf '%s\n' '$(APP_DESC)'; \
		printf '%s\n' ''; \
		printf '%s\n' '%prep'; \
		printf '%s\n' ''; \
		printf '%s\n' '%build'; \
		printf '%s\n' ''; \
		printf '%s\n' '%install'; \
		printf '%s\n' 'rm -rf %{buildroot}'; \
		printf '%s\n' 'mkdir -p %{buildroot}/usr/bin %{buildroot}/usr/share/applications %{buildroot}/usr/share/icons/hicolor/512x512/apps %{buildroot}/usr/share/metainfo'; \
		printf '%s\n' 'cp "$(abspath $(RPM_BIN_INPUT))" %{buildroot}/usr/bin/$(APP_NAME)'; \
		printf '%s\n' 'chmod 755 %{buildroot}/usr/bin/$(APP_NAME)'; \
		printf '%s\n' 'sed -e '\''s/^Icon=.*/Icon=$(APP_ICON_NAME)/'\'' "$(abspath $(LINUX_APPIMAGE_DESKTOP))" > %{buildroot}/usr/share/applications/$(APP_DESKTOP_ID).desktop'; \
		printf '%s\n' 'cp "$(abspath $(LINUX_APPIMAGE_ICON))" %{buildroot}/usr/share/icons/hicolor/512x512/apps/$(APP_ICON_NAME).png'; \
		printf '%s\n' 'sed -e '\''s/<release version="[^"]*"/<release version="$(APP_VERSION)"/'\'' -e '\''s#<launchable type="desktop-id">[^<]*</launchable>#<launchable type="desktop-id">$(APP_DESKTOP_ID).desktop</launchable>#'\'' "$(abspath $(LINUX_APPIMAGE_APPDATA))" > %{buildroot}/usr/share/metainfo/$(ANDROID_APP_ID).metainfo.xml'; \
		printf '%s\n' ''; \
		printf '%s\n' '%files'; \
		printf '%s\n' '/usr/bin/$(APP_NAME)'; \
		printf '%s\n' '/usr/share/applications/$(APP_DESKTOP_ID).desktop'; \
		printf '%s\n' '/usr/share/icons/hicolor/512x512/apps/$(APP_ICON_NAME).png'; \
		printf '%s\n' '/usr/share/metainfo/$(ANDROID_APP_ID).metainfo.xml'; \
	} > $(RPM_SPEC)
	rpmbuild -bb $(RPM_SPEC) \
		--target $(RPM_ARCH) \
		--define '_topdir $(abspath $(RPM_TOPDIR))' \
		--define '_build_id_links none'
	rm -f $(RPM_DIST_DIR)/$(RPM_PACKAGE_NAME)-*-$(RPM_RELEASE).$(RPM_ARCH).rpm
	created=$$(find $(RPM_TOPDIR)/RPMS -type f -name '$(RPM_PACKAGE_NAME)-$(APP_VERSION)-$(RPM_RELEASE)*.$(RPM_ARCH).rpm' | head -n 1); \
	if [ -z "$$created" ]; then echo "rpmbuild did not produce an RPM"; exit 1; fi; \
	cp "$$created" $(RPM_TARGET)
	test -f $@

podman-check:
	@$(PODMAN) --version >/dev/null 2>&1 || { \
		echo "podman check failed. Install podman, run with root privileges on FreeBSD, or set PODMAN=/path/to/podman."; \
		exit 1; \
	}

$(SNAP_TARGET): Makefile packaging/snap/snap/snapcraft.yaml | $(SNAP_BUILD_DIR) $(SNAP_DIST_DIR) podman-check
	rm -f $(SNAP_DIST_DIR)/*.snap
	$(PODMAN) run $(PODMAN_RUN_PLATFORM) $(PODMAN_RUN_NETWORK) --rm --privileged \
		-v "$(SNAP_APT_CACHE_VOLUME):/var/cache/apt/archives" \
		-v "$(SNAP_ROOT_CACHE_VOLUME):/root/.cache" \
		-v "$(abspath .):/work" \
		-w /work \
		--entrypoint "$(SNAP_ENTRYPOINT)" \
		$(SNAP_IMAGE) \
		-lc 'set -eu; printf "%s\n" "APT::Cache-Start \"100000000\";" > /etc/apt/apt.conf.d/99cache-start; apt-get update; rm -rf /tmp/inbe-snap; cp -a /work /tmp/inbe-snap; cd /tmp/inbe-snap; rm -rf build snap; mkdir snap; cp packaging/snap/snap/snapcraft.yaml snap/snapcraft.yaml; sed -i "s/^version:.*/version: '\''$(APP_VERSION)'\''/" snap/snapcraft.yaml; snapcraft pack --destructive-mode; cp *.snap /work/$(SNAP_DIST_DIR)/'
	created=$$(find $(SNAP_DIST_DIR) -maxdepth 1 -type f -name '*.snap' | head -n 1); \
	if [ -z "$$created" ]; then echo "snapcraft did not produce a snap"; exit 1; fi; \
	mv "$$created" $(SNAP_TARGET)
	test -f $@

$(FLATPAK_TARGET): Makefile $(FLATPAK_MANIFEST) | $(FLATPAK_BUILD_DIR) $(FLATPAK_DIST_DIR) podman-check
	rm -f $(FLATPAK_DIST_DIR)/*.flatpak
	$(PODMAN) run $(PODMAN_RUN_PLATFORM) $(PODMAN_RUN_NETWORK) --rm --privileged \
		-v "$(abspath .):/work" \
		-w /work \
		$(FLATPAK_IMAGE) \
		sh -lc 'set -eu; sh scripts/install-build-node.sh /tmp/inbe-build-node; export PATH=/tmp/inbe-build-node/bin:$$PATH; rm -rf .flatpak-builder $(FLATPAK_BUILD_DIR)/repo $(FLATPAK_BUILD_DIR)/build-dir; flatpak-builder --disable-rofiles-fuse --force-clean --repo=$(FLATPAK_BUILD_DIR)/repo $(FLATPAK_BUILD_DIR)/build-dir $(FLATPAK_MANIFEST) || { rm -rf $(FLATPAK_BUILD_DIR)/repo $(FLATPAK_BUILD_DIR)/build-dir vendor-builds/linux build/bin/linux; make vendor-prebuilds-native; make native; flatpak build-init $(FLATPAK_BUILD_DIR)/build-dir $(APP_ID) org.gnome.Sdk org.gnome.Platform 46; install -D -m755 "$$(find build/bin/linux -maxdepth 1 -type f -name '\''inbe-linux-*'\'' | head -n 1)" $(FLATPAK_BUILD_DIR)/build-dir/files/bin/inbe; install -D -m644 packaging/linux/appimage/inbe.desktop $(FLATPAK_BUILD_DIR)/build-dir/files/share/applications/$(APP_ID).desktop; sed -i '\''s/^Icon=.*/Icon=$(APP_ID)/'\'' $(FLATPAK_BUILD_DIR)/build-dir/files/share/applications/$(APP_ID).desktop; install -D -m644 packaging/linux/appimage/inbe.png $(FLATPAK_BUILD_DIR)/build-dir/files/share/icons/hicolor/512x512/apps/$(APP_ID).png; install -D -m644 packaging/linux/appimage/inbe.appdata.xml $(FLATPAK_BUILD_DIR)/build-dir/files/share/metainfo/$(APP_ID).metainfo.xml; flatpak build-finish --share=ipc --share=network --socket=fallback-x11 --socket=wayland --socket=pulseaudio --device=dri --filesystem=home $(FLATPAK_BUILD_DIR)/build-dir; flatpak build-export $(FLATPAK_BUILD_DIR)/repo $(FLATPAK_BUILD_DIR)/build-dir; }; flatpak build-bundle $(FLATPAK_BUILD_DIR)/repo $(FLATPAK_TARGET) $(APP_ID)'
	test -f $@

$(WEB_JS_TARGET): Makefile $(WEB_SRC) $(SQLITE_SRC) $(SQLITE_AMALGAMATION_H) $(FONT_FILES) $(EMBEDDED_ASSETS_C) $(WEB_GEN_STAMP) $(WEB_LIBOQS_A) $(WEB_HOST_JS) web-tools-check | $(WEB_DIST_DIR)
$(WEB_JS_TARGET): | zi-check
	rm -f $(WEB_DIST_DIR)/index.data
	$(WEB_CC) $(WEB_CFLAGS) \
		-iquote$(WEB_GEN_DIR) -iquote$(WEB_GEN_DIR)/src $(WEB_APP_INCLUDE) \
		-I$(SQLITE_BUILD_DIR) \
		$(WEB_LIBOQS_INCLUDE) \
		-DKRYON_BACKEND_CANVAS=1 \
		-DHAS_LIBOQS=1 \
		-DPLATFORM_WEB \
		-o $(WEB_JS_TARGET) \
		$(WEB_SRC) $(GENERATED_WEB_C) $(SQLITE_SRC) \
		$(foreach library,$(WEB_HOST_JS),--js-library $(library)) \
		$(WEB_LIBOQS_A) \
		-sASYNCIFY -sASYNCIFY_STACK_SIZE=1048576 -fexceptions \
		-sFORCE_FILESYSTEM=1 -sFETCH=1 -sUSE_ZLIB=1 -lidbfs.js \
		-sALLOW_MEMORY_GROWTH=1 -sINITIAL_MEMORY=268435456 -sSTACK_SIZE=33554432 \
		-sEXPORTED_RUNTIME_METHODS=Asyncify,FS \
		-sEXPORTED_FUNCTIONS=_main,_malloc,_free,_app_web_get_play_in_background,_app_web_set_backgrounded,_app_web_background_tick,_app_web_launch_practice,_app_web_extension_host,_app_web_extension_break_now,_app_web_extension_breaks_enabled,_app_web_extension_break_timer_enabled,_app_web_extension_break_timer_limit_s,_app_web_extension_break_timer_duration_s,_app_web_extension_break_timer_postpone_s,_app_web_extension_break_timer_max_prompts,_app_web_extension_break_timer_show_skip,_app_web_extension_break_timer_show_postpone,_app_web_extension_open_break_settings,_app_web_extension_open_habits,_app_web_test_save_onboarding_state,_app_web_test_onboarding_state,_app_web_test_show_first_run_guide,_app_web_test_first_run_guide_active,_app_web_test_first_run_guide_step,_app_web_test_first_run_guide_text_clipped,_app_web_test_first_run_guide_next_x,_app_web_test_first_run_guide_next_y,_app_web_test_first_run_guide_close_x,_app_web_test_first_run_guide_close_y,_app_web_test_first_run_guide_anchor_x,_app_web_test_first_run_guide_anchor_y,_app_web_test_first_run_guide_anchor_w,_app_web_test_first_run_guide_anchor_h,_app_web_test_sync_key_state,_app_web_test_import_sync_key,_app_web_test_habits_click_x,_app_web_test_habits_click_y,_app_web_test_show_practice_home,_app_web_test_practice_selected,_app_web_test_complete_practice,_app_web_test_completion_stage,_app_web_test_completed_practice_persisted,_app_web_test_screen,_app_web_test_route_transition_active,_app_web_test_practice_start_click_x,_app_web_test_practice_start_click_y,_app_web_test_enable_extension_breaks \
		--preload-file locales --preload-file assets

$(WEB_TARGET): src/web_shell.html $(WEB_BOOT_JS) $(WEB_JS_TARGET) manifest.json $(WEB_ASSET_FILES) | $(WEB_DIST_DIR)
	perl -0pe 's#\{\{\{ APP_SCRIPT \}\}\}#$(WEB_APP_SCRIPT)#g; s/WEB_CACHE_BUSTER/$(WEB_CACHE_BUSTER)/g' src/web_shell.html > $@
	cp $(WEB_BOOT_JS) $(WEB_DIST_DIR)/index_boot.js
	perl -0pi -e 's/WEB_CACHE_BUSTER/$(WEB_CACHE_BUSTER)/g' $(WEB_DIST_DIR)/index_boot.js
	rm -rf $(WEB_DIST_DIR)/canvas
	rm -rf $(WEB_DIST_DIR)/web-assets $(WEB_DIST_DIR)/site-icons
	cp -R web-assets $(WEB_DIST_DIR)/
	rm -rf $(WEB_DIST_DIR)/web-assets/dl
	rm -f $(WEB_DIST_DIR)/web-assets/canvas_index.html
	cp -R site-icons $(WEB_DIST_DIR)/
	perl -0pe 's/WEB_CACHE_BUSTER/$(WEB_CACHE_BUSTER)/g' manifest.json > $(WEB_DIST_DIR)/webmanifest.json

web-canvas: web

$(WEB_CANVAS_DIR):
	mkdir -p $@

$(WEB_CANVAS_TARGET): Makefile $(WEB_SRC) $(SQLITE_SRC) $(SQLITE_AMALGAMATION_H) $(FONT_FILES) $(EMBEDDED_ASSETS_C) $(WEB_GEN_STAMP) $(WEB_LIBOQS_A) $(WEB_HOST_JS) src/web_shell.html $(WEB_BOOT_JS) manifest.json $(WEB_ASSET_FILES) web-tools-check | $(WEB_CANVAS_DIR)
$(WEB_CANVAS_TARGET): | zi-check
	rm -f $(WEB_CANVAS_DIR)/index.data
	$(WEB_CC) $(WEB_CFLAGS) \
		-iquote$(WEB_GEN_DIR) -iquote$(WEB_GEN_DIR)/src $(WEB_APP_INCLUDE) \
		-I$(SQLITE_BUILD_DIR) \
		$(WEB_LIBOQS_INCLUDE) \
		-DKRYON_BACKEND_CANVAS=1 \
		-DHAS_LIBOQS=1 \
		-DPLATFORM_WEB \
		-o $(WEB_CANVAS_DIR)/index.js \
		$(WEB_SRC) $(GENERATED_WEB_C) $(SQLITE_SRC) \
		$(foreach library,$(WEB_HOST_JS),--js-library $(library)) \
		$(WEB_LIBOQS_A) \
		-sASYNCIFY -sASYNCIFY_STACK_SIZE=1048576 -fexceptions \
		-sFORCE_FILESYSTEM=1 -sFETCH=1 -sUSE_ZLIB=1 -lidbfs.js \
		-sALLOW_MEMORY_GROWTH=1 -sINITIAL_MEMORY=268435456 -sSTACK_SIZE=33554432 \
		-sEXPORTED_RUNTIME_METHODS=Asyncify,FS \
		-sEXPORTED_FUNCTIONS=_main,_malloc,_free,_app_web_get_play_in_background,_app_web_set_backgrounded,_app_web_background_tick,_app_web_launch_practice,_app_web_extension_host,_app_web_extension_break_now,_app_web_extension_breaks_enabled,_app_web_extension_break_timer_enabled,_app_web_extension_break_timer_limit_s,_app_web_extension_break_timer_duration_s,_app_web_extension_break_timer_postpone_s,_app_web_extension_break_timer_max_prompts,_app_web_extension_break_timer_show_skip,_app_web_extension_break_timer_show_postpone,_app_web_extension_open_break_settings,_app_web_extension_open_habits,_app_web_test_save_onboarding_state,_app_web_test_onboarding_state,_app_web_test_show_first_run_guide,_app_web_test_first_run_guide_active,_app_web_test_first_run_guide_step,_app_web_test_first_run_guide_text_clipped,_app_web_test_first_run_guide_next_x,_app_web_test_first_run_guide_next_y,_app_web_test_first_run_guide_close_x,_app_web_test_first_run_guide_close_y,_app_web_test_first_run_guide_anchor_x,_app_web_test_first_run_guide_anchor_y,_app_web_test_first_run_guide_anchor_w,_app_web_test_first_run_guide_anchor_h,_app_web_test_sync_key_state,_app_web_test_import_sync_key,_app_web_test_habits_click_x,_app_web_test_habits_click_y,_app_web_test_show_practice_home,_app_web_test_practice_selected,_app_web_test_complete_practice,_app_web_test_completion_stage,_app_web_test_completed_practice_persisted,_app_web_test_screen,_app_web_test_route_transition_active,_app_web_test_practice_start_click_x,_app_web_test_practice_start_click_y,_app_web_test_enable_extension_breaks \
		--preload-file locales --preload-file assets
	perl -0pe 's#\{\{\{ APP_SCRIPT \}\}\}#$(WEB_CANVAS_APP_SCRIPT)#g; s/WEB_CACHE_BUSTER/$(WEB_CACHE_BUSTER)/g' src/web_shell.html > $@
	cp $(WEB_BOOT_JS) $(WEB_CANVAS_DIR)/index_boot.js
	perl -0pi -e 's/WEB_CACHE_BUSTER/$(WEB_CACHE_BUSTER)/g' $(WEB_CANVAS_DIR)/index_boot.js
	rm -rf $(WEB_CANVAS_DIR)/web-assets $(WEB_CANVAS_DIR)/site-icons
	cp -R web-assets $(WEB_CANVAS_DIR)/
	rm -rf $(WEB_CANVAS_DIR)/web-assets/dl
	rm -f $(WEB_CANVAS_DIR)/web-assets/canvas_index.html
	cp -R site-icons $(WEB_CANVAS_DIR)/
	perl -0pe 's/WEB_CACHE_BUSTER/$(WEB_CACHE_BUSTER)/g' manifest.json > $(WEB_CANVAS_DIR)/webmanifest.json

android-copy-assets:
	$(MAKE) $(FONT_FILES)
	$(MAKE) $(EMBEDDED_ASSETS_C)
	rm -rf droid/app/src/main/assets
	mkdir -p droid/app/src/main/assets

android-check-keystore:
	@if [ -z "$(PASSWORD)" ]; then \
		echo "Set PASSWORD=your-keystore-password for release builds"; \
		exit 1; \
	fi
	@if [ ! -f "$(ANDROID_KEYSTORE)" ]; then \
		echo "Android release keystore not found: $(ANDROID_KEYSTORE)"; \
		exit 1; \
	fi
	@command -v keytool >/dev/null || { \
		echo "keytool is missing. Re-enter the Android/JDK build environment."; \
		exit 1; \
	}
	@if ! keytool -list -keystore "$(ANDROID_KEYSTORE)" -storepass "$(PASSWORD)" -alias "$(ANDROID_KEY_ALIAS)" >/dev/null 2>&1; then \
		echo "Android release keystore password or alias is invalid"; \
		echo "Checked keystore: $(ANDROID_KEYSTORE)"; \
		echo "Checked alias: $(ANDROID_KEY_ALIAS)"; \
		exit 1; \
	fi

android-local-properties:
	@if [ -z "$(ANDROID_SDK)" ]; then \
		echo "Set ANDROID_SDK_ROOT or ANDROID_HOME to your Android SDK path."; \
		exit 1; \
	fi
	@if [ ! -d "$(ANDROID_SDK)" ]; then \
		echo "Android SDK not found: $(ANDROID_SDK)"; \
		echo "Set ANDROID_SDK_ROOT or ANDROID_HOME to your Android SDK path."; \
		exit 1; \
	fi
	@printf 'sdk.dir=%s\ncmake.dir=%s\n' "$(ANDROID_SDK)" "$(ANDROID_CMAKE_DIR)" > droid/local.properties

android-debug: android-copy-assets android-local-properties
	$(ANDROID_GRADLE_ENV) $(GRADLE) -p droid assembleDebug $(ANDROID_GRADLE_ARGS)
	$(MAKE) android-copy-debug-apks

android-release:
	$(MAKE) android-check-keystore PASSWORD="$(PASSWORD)"
	$(MAKE) android-copy-assets
	$(MAKE) android-local-properties
	@if [ -n "$(PASSWORD)" ]; then \
		$(ANDROID_GRADLE_ENV) $(GRADLE) -p droid assembleRelease assembleGplay -Pkeystore.path="$(ANDROID_KEYSTORE)" -Pkeystore.alias="$(ANDROID_KEY_ALIAS)" -Pkeystore.password="$(PASSWORD)" $(ANDROID_GRADLE_ARGS) || exit $$?; \
	else \
		echo "Set PASSWORD=your-keystore-password for release builds"; \
		exit 1; \
	fi
	$(MAKE) android-copy-release-apks

android-bundle:
	$(MAKE) android-check-keystore PASSWORD="$(PASSWORD)"
	$(MAKE) android-copy-assets
	$(MAKE) android-local-properties
	@if [ -n "$(PASSWORD)" ]; then \
		$(ANDROID_GRADLE_ENV) $(GRADLE) -p droid bundleGplay -Pkeystore.path="$(ANDROID_KEYSTORE)" -Pkeystore.alias="$(ANDROID_KEY_ALIAS)" -Pkeystore.password="$(PASSWORD)" $(ANDROID_GRADLE_ARGS) || exit $$?; \
	else \
		echo "Set PASSWORD=your-keystore-password for bundle builds"; \
		exit 1; \
	fi
	$(MAKE) android-copy-bundle

android-copy-debug-apks: | $(ANDROID_BUILD_DIR)
	@found=0; \
	for apk in droid/app/build/outputs/apk/*/debug/*.apk droid/app/build/outputs/apk/debug/*.apk; do \
		if [ -f "$$apk" ]; then \
			cp "$$apk" "$(ANDROID_BUILD_DIR)/$$(basename "$$apk")"; \
			found=1; \
		fi; \
	done; \
	if [ "$$found" -eq 0 ]; then \
		echo "No debug APKs were produced"; \
		exit 1; \
	fi

android-copy-release-apks: | $(ANDROID_BUILD_DIR)
	@found=0; \
	for apk in droid/app/build/outputs/apk/release/*.apk droid/app/build/outputs/apk/gplay/*.apk; do \
		if [ -f "$$apk" ]; then \
			cp "$$apk" "$(ANDROID_BUILD_DIR)/$$(basename "$$apk")"; \
			found=1; \
		fi; \
	done; \
	if [ "$$found" -eq 0 ]; then \
		echo "No release APKs were produced"; \
		exit 1; \
	fi; \
	if [ -z "$(APP_VERSION)" ]; then \
		echo "Could not read APP_VERSION_STRING from $(VERSION_FILE)"; \
		exit 1; \
	fi; \
	release_universal="$$(find droid/app/build/outputs/apk -path '*/release/*' -name "app-universal-release*.apk" | head -n 1)"; \
	if [ -z "$$release_universal" ] || [ ! -f "$$release_universal" ]; then \
		echo "No universal release APK was produced"; \
		exit 1; \
	fi; \
	cp "$$release_universal" "$(ANDROID_BUILD_DIR)/$(APP_NAME)-$(APP_VERSION).apk"; \
	gplay_universal="$$(find droid/app/build/outputs/apk -path '*/gplay/*' -name "app-universal-gplay*.apk" | head -n 1)"; \
	if [ -z "$$gplay_universal" ] || [ ! -f "$$gplay_universal" ]; then \
		echo "No gplay universal release APK was produced"; \
		exit 1; \
	fi; \
	cp "$$gplay_universal" "$(ANDROID_BUILD_DIR)/$(APP_NAME)-$(APP_VERSION)-gplay.apk"

android-copy-bundle: | $(ANDROID_BUILD_DIR)
	bash scripts/check-android-optimization.sh droid/app/build/outputs/bundle/gplay/app-gplay.aab
	@found=0; \
	for bundle in droid/app/build/outputs/bundle/*Release/*.aab droid/app/build/outputs/bundle/release/*.aab droid/app/build/outputs/bundle/gplay/*.aab; do \
		if [ -f "$$bundle" ]; then \
			cp "$$bundle" "$(ANDROID_BUILD_DIR)/$$(basename "$$bundle")"; \
			found=1; \
		fi; \
	done; \
	if [ "$$found" -eq 0 ]; then \
		echo "No release AAB was produced"; \
		exit 1; \
	fi; \
	if [ -z "$(APP_VERSION)" ]; then \
		echo "Could not read APP_VERSION_STRING from $(VERSION_FILE)"; \
		exit 1; \
	fi; \
	gplay_bundle="$$(find droid/app/build/outputs/bundle -path "*gplay*" -name "app-gplay.aab" | head -n 1)"; \
	if [ -z "$$gplay_bundle" ] || [ ! -f "$$gplay_bundle" ]; then \
		echo "No gplay release AAB was produced"; \
		exit 1; \
	fi; \
	cp "$$gplay_bundle" "$(ANDROID_BUILD_DIR)/$(APP_NAME)-$(APP_VERSION)-gplay.aab"; \
	if [ -f "$(ANDROID_BUILD_DIR)/$(APP_NAME)-$(APP_VERSION)-gplay.apk" ]; then \
		cp "$(ANDROID_BUILD_DIR)/$(APP_NAME)-$(APP_VERSION)-gplay.apk" "$(ANDROID_BUILD_DIR)/$(APP_NAME)-latest.apk"; \
	fi

android-install: android-copy-assets android-local-properties
	@set -eu; \
	adb_cmd='$(ADB)'; \
	abi=$$($$adb_cmd shell getprop ro.product.cpu.abi 2>/dev/null | tr -d '\r' | head -n 1); \
	if [ -z "$$abi" ]; then \
		echo "Could not read Android device ABI. Connect one device, or run with ADB='adb -s SERIAL'."; \
		exit 1; \
	fi; \
	echo "Android target ABI: $$abi"; \
	$(ANDROID_GRADLE_ENV) $(GRADLE) -p droid assembleDebug -Papp.onlyAbi="$$abi" $(ANDROID_GRADLE_ARGS)
	$(MAKE) android-copy-debug-apks
	ADB='$(ADB)' sh scripts/android-install-apk.sh \
		"$(ANDROID_DEBUG_APP_ID)" "$(ANDROID_ACTIVITY)" \
		droid/app/build/outputs/apk debug

android-install-release: android-release
	ADB='$(ADB)' sh scripts/android-install-apk.sh \
		"$(ANDROID_APP_ID)" "$(ANDROID_ACTIVITY)" \
		droid/app/build/outputs/apk release

android-avd:
	@if [ "$(UNAME_S)" = "FreeBSD" ]; then \
		HOME="$${ANDROID_TOOL_HOME:-/tmp/$(APP_NAME)-android-home}" ANDROID_SDK_ROOT="$${ANDROID_SDK_WORK_ROOT:-$${ANDROID_SDK_ROOT:-$${ANDROID_HOME:-/tmp/android-sdk}}}" ANDROID_HOME="$${ANDROID_SDK_WORK_ROOT:-$${ANDROID_SDK_ROOT:-$${ANDROID_HOME:-/tmp/android-sdk}}}" bash scripts/emulator.sh; \
	else \
		bash scripts/emulator.sh; \
	fi
	@adb_cmd="$$HOME/.android-sdk-writable/platform-tools/adb"; \
	if [ "$(UNAME_S)" = "FreeBSD" ]; then adb_cmd="$${ANDROID_SDK_WORK_ROOT:-$${ANDROID_SDK_ROOT:-$${ANDROID_HOME:-/tmp/android-sdk}}}/platform-tools/adb"; fi; \
	if [ ! -x "$$adb_cmd" ]; then adb_cmd="$${ANDROID_SDK_ROOT:-$${ANDROID_HOME}}/platform-tools/adb"; fi; \
	if [ ! -x "$$adb_cmd" ]; then adb_cmd=adb; fi; \
	$(MAKE) android-install ADB="$$adb_cmd -e"

android-smoke:
	@mkdir -p build/android
	sh scripts/android-smoke-test.sh "$(ANDROID_SDK)" "$(ANDROID_APP_ID)" "$(ANDROID_ACTIVITY)"

android-audio-e2e:
	bash scripts/android-audio-e2e.sh

android-clean:
	$(GRADLE) -p droid clean $(ANDROID_GRADLE_ARGS)
	rm -rf $(ANDROID_BUILD_DIR)

android-rebuild:
	$(MAKE) android-clean
	$(MAKE) android-debug

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

windows-runtime-assets-check:
	@:

windows64: windows-runtime-assets-check $(WIN64_TARGET)

windows32: windows-runtime-assets-check $(WIN32_TARGET)

windows:
	$(MAKE) windows64
	$(MAKE) windows32
	mkdir -p $(WINDOWS_DIST_DIR)
	rm -f $(WINDOWS_DIST_DIR)/$(APP_NAME)-windows-*.zip
	rm -f $(WINDOWS_DIST)
	cd $(WINDOWS_BIN_DIR) && zip -9 -j $(abspath $(WINDOWS_DIST)) \
		$(WIN64_ARCH)/$(WIN64_BINARY_NAME) \
		$(WIN32_ARCH)/$(WIN32_BINARY_NAME)

WINDOWS_SETUP := $(WINDOWS_DIST_DIR)/$(APP_NAME)-windows-setup-$(APP_VERSION).exe
WINDOWS_SETUP_SCRIPT := packaging/windows/$(APP_NAME)-setup.nsi

windows-setup-check:
	@command -v makensis >/dev/null || { \
		echo "makensis is missing. Install NSIS (apt install nsis)."; \
		exit 1; \
	}

windows-setup: windows windows-setup-check
	rm -f $(WINDOWS_SETUP)
	makensis -DVERSION=$(APP_VERSION) \
		-DWIN64_EXE=$(abspath $(WINDOWS_BIN_DIR)/$(WIN64_ARCH)/$(WIN64_BINARY_NAME)) \
		-DWIN32_EXE=$(abspath $(WINDOWS_BIN_DIR)/$(WIN32_ARCH)/$(WIN32_BINARY_NAME)) \
		-DOUT=$(abspath $(WINDOWS_SETUP)) $(WINDOWS_SETUP_SCRIPT)
	test -f $(WINDOWS_SETUP)

web:
	$(MAKE) sync-web-icons
	$(MAKE) $(WEB_TARGET)
	$(MAKE) web-smoke-test
	rm -f $(WEB_DIST_ZIP)
	cd $(WEB_DIST_DIR) && zip -9 -r $(abspath $(WEB_DIST_ZIP)) .

web-smoke-test: $(WEB_SMOKE_TEST)
	node tests/web_storage_test.mjs
	WEB_SMOKE_RENDERER=canvas WEB_SMOKE_BROWSER="$(WEB_SMOKE_BROWSER)" node $(WEB_SMOKE_TEST) $(WEB_DIST_DIR)

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

site: package-unpackaged-assets web
	sh site/build.sh

site-release-assets-check:
	sh scripts/check-site-release-assets.sh

chrome-web-store: $(CHROME_WEB_STORE_ZIP)

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

$(CHROME_WEB_STORE_ZIP): $(WEB_TARGET) $(CHROME_WEB_STORE_MANIFEST) $(CHROME_WEB_STORE_WORKER) $(CHROME_WEB_STORE_EXTENSION_BOOT) $(CHROME_WEB_STORE_EXTENSION_APP) $(CHROME_WEB_STORE_ICONS) | $(CHROME_WEB_STORE_DIR)
	rm -rf $(CHROME_WEB_STORE_DIR)
	mkdir -p $(CHROME_WEB_STORE_DIR)/icons
	cp -R $(WEB_DIST_DIR)/. $(CHROME_WEB_STORE_DIR)/
	rm -rf $(CHROME_WEB_STORE_DIR)/canvas $(CHROME_WEB_STORE_DIR)/web-assets/dl
	cp $(CHROME_WEB_STORE_EXTENSION_BOOT) $(CHROME_WEB_STORE_DIR)/extension_boot.js
	cp $(CHROME_WEB_STORE_EXTENSION_APP) $(CHROME_WEB_STORE_DIR)/extension_app.js
	perl -0pi -e 's#(<script src="index_boot\.js\?v=[^"]+"></script>)#<script src="extension_boot.js"></script>\n    $$1#' $(CHROME_WEB_STORE_DIR)/index.html
	perl -0pi -e 's#<script>window\.__inbeRenderer="canvas";window\.__inbeLoadApp\("index\.js\?v=[^"]+"\)</script>#<script src="extension_app.js"></script>#' $(CHROME_WEB_STORE_DIR)/index.html
	sed -e 's#__APP_VERSION__#$(APP_VERSION)#g' \
		$(CHROME_WEB_STORE_MANIFEST) > $(CHROME_WEB_STORE_DIR)/manifest.json
	cp $(CHROME_WEB_STORE_WORKER) $(CHROME_WEB_STORE_DIR)/service_worker.js
	cp $(CHROME_WEB_STORE_ICONS) $(CHROME_WEB_STORE_DIR)/icons/
	rm -f $(CHROME_WEB_STORE_ZIP)
	cd $(CHROME_WEB_STORE_DIR) && zip -9 -r $(abspath $(CHROME_WEB_STORE_ZIP)) .

firefox-addons: $(FIREFOX_ADDONS_ZIP)

$(FIREFOX_ADDONS_ZIP): $(WEB_TARGET) src/web_shell.html $(FIREFOX_ADDONS_MANIFEST) $(FIREFOX_ADDONS_BACKGROUND) $(FIREFOX_ADDONS_LOADER) $(FIREFOX_ADDONS_ICONS) | $(FIREFOX_ADDONS_DIR)
	rm -rf $(FIREFOX_ADDONS_DIR)
	mkdir -p $(FIREFOX_ADDONS_DIR)/icons
	cp -R $(WEB_DIST_DIR)/. $(FIREFOX_ADDONS_DIR)/
	rm -rf $(FIREFOX_ADDONS_DIR)/canvas $(FIREFOX_ADDONS_DIR)/web-assets/dl
	sed -e 's#__APP_VERSION__#$(APP_VERSION)#g' \
		$(FIREFOX_ADDONS_MANIFEST) > $(FIREFOX_ADDONS_DIR)/manifest.json
	cp $(FIREFOX_ADDONS_BACKGROUND) $(FIREFOX_ADDONS_DIR)/background.js
	cp $(FIREFOX_ADDONS_LOADER) $(FIREFOX_ADDONS_DIR)/extension_loader.js
	perl -0pe 's#\{\{\{ APP_SCRIPT \}\}\}#$(FIREFOX_ADDONS_APP_SCRIPT)#g; s/WEB_CACHE_BUSTER/$(WEB_CACHE_BUSTER)/g' src/web_shell.html > $(FIREFOX_ADDONS_INDEX)
	cp $(FIREFOX_ADDONS_ICONS) $(FIREFOX_ADDONS_DIR)/icons/
	rm -f $(FIREFOX_ADDONS_ZIP)
	cd $(FIREFOX_ADDONS_DIR) && zip -9 -r $(abspath $(FIREFOX_ADDONS_ZIP)) .

firefox-addons-lint: $(FIREFOX_ADDONS_ZIP)
	$(ADDONS_LINTER) $(FIREFOX_ADDONS_ZIP)

firefox-addons-source-zip:
	sh scripts/build-firefox-addons-source-zip.sh $(FIREFOX_ADDONS_SOURCE_ZIP)

verify-firefox-addons: firefox-addons-lint firefox-addons-source-zip

clean:
	rm -rf build

clean-linux:
	rm -rf $(LINUX_OBJ_DIR) $(LINUX_BIN_DIR) $(LINUX_DIST_DIR)

clean-native:
	rm -rf $(NATIVE_OBJ_DIR) $(NATIVE_BIN_DIR) $(NATIVE_DIST_DIR) $(NATIVE_VENDOR_BUILD_DIR)

clean-vendor-builds:
	rm -rf $(VENDOR_BUILD_DIR)

NEEDS_DEB_NATIVE := $(if $(strip $(DEB_BIN_SOURCE)),,$(if $(filter linux,$(NATIVE_PLATFORM)),$(filter deb package-deb,$(MAKECMDGOALS))))
NEEDS_RPM_NATIVE := $(if $(strip $(RPM_BIN_SOURCE)),,$(if $(filter linux,$(NATIVE_PLATFORM)),$(filter rpm package-rpm,$(MAKECMDGOALS))))
NEEDS_NATIVE_ENV := $(if $(MAKECMDGOALS),$(filter all native install install-user stage package-freebsd run run-fresh dist appimage vendor-prebuilds vendor-prebuilds-native,$(MAKECMDGOALS)) $(NEEDS_DEB_NATIVE) $(NEEDS_RPM_NATIVE),native)
ifneq ($(strip $(NEEDS_NATIVE_ENV)),)
ifeq ($(KRYON_BACKEND),raylib)
ifeq ($(strip $(RAY_CFLAGS)),)
$(error RAY_CFLAGS is not set. Install pkg-config metadata for $(RAY_PKGS), or set RAY_CFLAGS explicitly)
endif
ifeq ($(strip $(RAY_LDLIBS)),)
$(error RAY_LDLIBS is not set. Install pkg-config metadata for $(RAY_PKGS), or set RAY_LDLIBS explicitly)
endif
ifeq ($(strip $(RAY_SDL_LDLIBS)),)
$(error RAY_SDL_LDLIBS is not set. Install SDL2 development files or set RAY_SDL_LDLIBS explicitly)
endif
ifeq ($(strip $(RAY_SDL_INCLUDE_DIR)),)
$(error RAY_SDL_INCLUDE_DIR is not set. Install SDL2 development files or set RAY_SDL_INCLUDE_DIR explicitly)
endif
ifeq ($(strip $(RAY_RAYLIB_CONFIG)),)
$(error RAY_RAYLIB_CONFIG is not set. Set RAY_RAYLIB_CONFIG explicitly)
endif
endif
ifeq ($(KRYON_BACKEND),libdraw)
ifeq ($(wildcard $(PLAN9PORT_DIR)/include/draw.h),)
$(error plan9port draw.h is missing. Set PLAN9PORT_DIR to a plan9port install with include/draw.h)
endif
ifeq ($(wildcard $(PLAN9PORT_DIR)/lib/libdraw.a),)
$(error plan9port libdraw.a is missing. Set PLAN9PORT_DIR to a plan9port install with lib/libdraw.a)
endif
endif
ifeq ($(strip $(KRYON_CURL_LDLIBS)),)
$(error libcurl metadata is missing. Install libcurl pkg-config metadata or set KRYON_CURL_CFLAGS/KRYON_CURL_LDLIBS explicitly)
endif
ifneq ($(shell v='$(KRYON_CURL_VERSION_HEX)'; if [ "$$v" = 075600 ] || [ "$$v" \> 075600 ]; then echo yes; fi),yes)
$(error libcurl >= 7.86.0 is required for websocket sync; found LIBCURL_VERSION_NUM=$(KRYON_CURL_VERSION_NUM))
endif
endif

NEEDS_CLICK_ENV := $(filter click click-verify,$(MAKECMDGOALS))
ifneq ($(strip $(NEEDS_CLICK_ENV)),)
ifeq ($(strip $(CLICK_BIN_SOURCE)),)
ifeq ($(strip $(AARCH64_CC)),)
$(error AARCH64_CC is not set. Install an AArch64 cross compiler, set AARCH64_CC, or pass CLICK_BIN_SOURCE=/path/to/breathing)
endif
ifeq ($(strip $(AARCH64_AR)),)
$(error AARCH64_AR is not set. Install AArch64 binutils, set AARCH64_AR, or pass CLICK_BIN_SOURCE=/path/to/breathing)
endif
ifeq ($(strip $(AARCH64_RANLIB)),)
$(error AARCH64_RANLIB is not set. Install AArch64 binutils, set AARCH64_RANLIB, or pass CLICK_BIN_SOURCE=/path/to/breathing)
endif
ifeq ($(strip $(AARCH64_RAY_CFLAGS)),)
$(error AARCH64_RAY_CFLAGS is not set. Set AARCH64_RAY_CFLAGS for your cross sysroot, or pass CLICK_BIN_SOURCE=/path/to/breathing)
endif
ifeq ($(strip $(AARCH64_RAY_LDLIBS)),)
$(error AARCH64_RAY_LDLIBS is not set. Set AARCH64_RAY_LDLIBS for your cross sysroot, or pass CLICK_BIN_SOURCE=/path/to/breathing)
endif
ifeq ($(strip $(AARCH64_RAY_SDL_INCLUDE_DIR)),)
$(error AARCH64_RAY_SDL_INCLUDE_DIR is not set. Set AARCH64_RAY_SDL_INCLUDE_DIR for your cross sysroot, or pass CLICK_BIN_SOURCE=/path/to/breathing)
endif
ifeq ($(strip $(AARCH64_KRYON_CURL_LDLIBS)),)
$(error AARCH64_KRYON_CURL_LDLIBS is not set. Set AARCH64_KRYON_CURL_LDLIBS for your cross sysroot, or pass CLICK_BIN_SOURCE=/path/to/breathing)
endif
endif
endif

.PHONY: sync-recovery-test
sync-recovery-test: build-laws $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/sync_recovery_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

test: sync-recovery-test

# Validate before producing release packages, including direct artifact targets.
$(APPIMAGE_TARGET) $(DEB_TARGET) $(RPM_TARGET) $(SNAP_TARGET) $(FLATPAK_TARGET) $(CLICK_TARGET) $(CHROME_WEB_STORE_ZIP) $(FIREFOX_ADDONS_ZIP): | version-check
android-release android-bundle android-copy-release-apks android-copy-bundle windows-setup site: version-check

# Actual artifacts are gated too, including direct and incremental builds.
$(TARGET) $(KRYON_HOST_TARGET) $(WIN64_TARGET) $(WIN32_TARGET) $(WEB_JS_TARGET) $(WEB_CANVAS_TARGET): $(SYNC_RETRY_SOURCE) | build-laws
