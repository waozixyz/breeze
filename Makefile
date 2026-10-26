.DEFAULT_GOAL := all

APP_NAME := inbe
# The program people run; package, store and data names keep APP_NAME.
APP_EXECUTABLE := breeze
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
ANDROID_JAVA_HOME ?= $(shell for dir in "$(JAVA_HOME)" /usr/local/openjdk21 /usr/lib/jvm/java-21-openjdk-amd64 /usr/lib/jvm/java-21-openjdk /usr/local/openjdk17 /usr/lib/jvm/java-17-openjdk-amd64 /usr/lib/jvm/java-17-openjdk; do if [ -x "$$dir/bin/java" ]; then printf "%s\n" "$$dir"; break; fi; done)
ANDROID_GRADLE_ENV := env -u ANDROID_HOME $(if $(ANDROID_JAVA_HOME),JAVA_HOME="$(ANDROID_JAVA_HOME)" PATH="$(ANDROID_JAVA_HOME)/bin:$$PATH")
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

KRYON_DIR ?= build/packages/kryon
KSS_DIR ?= build/packages/kss
OQS_DIR ?= build/packages/oqs
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
WIN64_RAYLIB_BUILD_DIR := $(VENDOR_BUILD_DIR)/windows/$(WIN64_ARCH)/raylib
WIN64_RAYLIB_A := $(WIN64_RAYLIB_BUILD_DIR)/libraylib.a
WIN64_CURL_BUILD_DIR := $(VENDOR_BUILD_DIR)/windows/$(WIN64_ARCH)/curl
WIN64_CURL_INCLUDE_DIR := $(WIN64_CURL_BUILD_DIR)/include
WIN64_CURL_A := $(WIN64_CURL_BUILD_DIR)/lib/libcurl.a
WIN64_LIBOQS_BUILD_DIR := $(VENDOR_BUILD_DIR)/windows/$(WIN64_ARCH)/liboqs
WIN64_LIBOQS_A := $(WIN64_LIBOQS_BUILD_DIR)/lib/liboqs.a
WIN64_LIBOQS_INCLUDE := -I$(WIN64_LIBOQS_BUILD_DIR)/include
WIN64_RESOURCE := $(BUILD_OBJ_DIR)/windows/$(WIN64_ARCH)/$(APP_NAME).res
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
# Inbe's desktop uses Kryon's raylib backend, not its libdraw, terminal or
# Plan 9 hosts.
KRYON_SRCS := $(filter-out $(KRYON_DIR)/src/backend/libdraw_%.c $(KRYON_DIR)/src/backend/termi_%.c \
	$(KRYON_DIR)/src/platform/plan9/%.c,$(KRYON_SRCS))
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
# The practice media is the practices package, packaged under
# assets/practices/ (scripts/practice_media.py).
PRACTICE_MEDIA := build/packages/practices
IMAGE_FILES := assets/app/icon.png assets/easteregg/art.png assets/easteregg/waozi.png $(PRACTICE_MEDIA)/whm/1.png $(PRACTICE_MEDIA)/whm/2.png $(PRACTICE_MEDIA)/meditation/1.png assets/pet/egg1.png $(wildcard $(PRACTICE_MEDIA)/*/banner*.png) $(wildcard $(PRACTICE_MEDIA)/sunsalutation/characters/*/*.png) $(wildcard $(PRACTICE_MEDIA)/taichi/*.png $(PRACTICE_MEDIA)/taichi/*/*.png) $(PRACTICE_MEDIA)/taichi/course.tch
SOUND_FILES := $(wildcard assets/sounds/*.ogg)
FONT_SUBSET_DIR := assets/fonts/subset
FONT_SUBSET_CORPUS := locales assets/fonts/input_common.txt assets/fonts/ui_symbols.txt $(PRACTICE_MEDIA)/astral_projection/text $(PRACTICE_MEDIA)/workout/text
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
IMAGE_FILES += $(wildcard assets/profile-pictures/*.png)
IMAGE_FILES += $(KRYON_DIR)/icons/ui.png $(KRYON_DIR)/icons/pfp.png
APP_BUNDLES := $(addprefix $(BUILD_DIR)/apps/,lists.zx habits.zx practices.zx diary.zx lumi.zx leaderboard.zx)
INBE_BUNDLE := $(BUILD_DIR)/inbe.zx
INBE_FULL_BUNDLE := $(BUILD_DIR)/inbe-full.zx
APP_SOURCES := $(shell find apps src/apps -name '*.zi' | LC_ALL=C sort) src/core/types.zi src/core/breath_timing.zi $(wildcard src/practices/patterns/*rules.zi) src/practices/patterns/patterns_clock.zi src/practices/patterns/patterns_types.zi src/practices/sun_salutation/sun_salutation_rules.zi src/practices/meditation/meditation_timing.zi
APP_RESOURCES := $(shell rg --files assets/habits assets/lists assets/diary assets/lumi assets/mcp 2>/dev/null)
APP_RESOURCES += $(shell find -L $(PRACTICE_MEDIA) -type f -not -path '*/.git/*' 2>/dev/null) $(shell rg --files design/tai-chi/text 2>/dev/null) apps/practice/content.json design/tai-chi/narration.json design/tai-chi/narration-lines.json $(wildcard design/tai-chi/narration-receipt.json) $(wildcard design/sun-salutation/narration/*.json) $(wildcard design/sun-salutation/narration/text/*.txt) $(wildcard design/lumi-guide/*.json) scripts/practice_content.py scripts/generate-lumi-guide-narration.py
APP_RESOURCES += $(wildcard apps/*/achievements.json) $(wildcard apps/*/achievement-locales/*.json)
APP_RESOURCES += $(wildcard assets/*/sidebar.shape)

APPS_BUNDLE ?= build/apps-ui/apps.zx
EMBEDDED_ASSET_FILES := apps/publishers.json $(INBE_BUNDLE) $(APPS_BUNDLE) assets/app/icon.png
KRY_GEN_DIR := $(BUILD_DIR)/kryon/generated
# Dependencies are imported as PACKAGE/Module through their linked packages.
ZI_PACKAGE_PATHS := $(shell sh scripts/package-paths.sh)
ZI_SRCS := $(shell find src -type f -name '*.zi' 2>/dev/null | LC_ALL=C sort) apps/practice/hold_reminder.zi apps/practice/whm_controls.zi $(wildcard apps/practice/astral_projection*.zi) $(wildcard apps/practice/workout*.zi) $(wildcard apps/practice/sun_salutation*.zi)
GAME2D_DIR := build/packages/game2d
GAME2D_MODULES := $(wildcard $(GAME2D_DIR)/src/*/*.zi)
DAOCHI_CLIENT_DIR ?= build/packages/daochi-client
DAOCHI_CLIENT_MODULES := $(wildcard $(DAOCHI_CLIENT_DIR)/*.zi)
ZIRAN_STD_MODULES := $(wildcard $(ZIRAN_DIR)/std/*.zi)
KRYON_ZI_MODULES := $(shell find $(KRYON_DIR)/src -type f -name '*.zi' | LC_ALL=C sort)
KRY_GEN_SRCS := $(patsubst %.zi,$(KRY_GEN_DIR)/%.c,$(ZI_SRCS))
KRY_GEN_SRCS += $(addprefix $(KRY_GEN_DIR)/,account.c auth.c authorization.c authorization_owner.c delegated.c async_delegated.c envelope.c byte_text_linux.c \
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
# The Unix clock provider is generated only for the native app. Web and
# Windows source lists above retain their platform clock implementations.
KRY_GEN_SRCS += $(KRY_GEN_DIR)/date_time_linux.c
SRC := $(APP_SRCS) $(KRY_GEN_STAMP) $(EMBEDDED_ASSETS_C)
GENERATED_NATIVE_C = $(shell find $(KRY_GEN_DIR) -type f -name '*.c' | LC_ALL=C sort)
WINDOWS_SRC := $(APP_SRCS) $(EMBEDDED_ASSETS_C)
GENERATED_WINDOWS_C = $(shell find $(WINDOWS_GEN_DIR) -type f -name '*.c' | LC_ALL=C sort)
KRYON_HOST_APP_SRCS := $(APP_SRCS) $(KRY_GEN_SRCS) $(KRY_GEN_GAME_C)
KRYON_HOST_SRC := $(KRYON_HOST_APP_SRCS) $(EMBEDDED_ASSETS_C)
WEB_APP_SRCS := $(APP_SRCS)
WEB_SRC := $(WEB_APP_SRCS) $(EMBEDDED_ASSETS_C)
GENERATED_WEB_C = $(shell find $(WEB_GEN_DIR) -type f -name '*.c' | LC_ALL=C sort)

APP_INCLUDE := -Isrc -Isrc/app -Isrc/core -Isrc/screens -Isrc/screens/settings -Isrc/practices -Isrc/practices/whm -Isrc/practices/meditation -Isrc/practices/sun_salutation -Isrc/practices/tai_chi -Isrc/storage -Isrc/platform -Isrc/platform/android -Isrc/third_party
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
	src/storage/sync_restore_laws.zi src/storage/storage_layout_laws.zi \
	src/guide_laws.zi src/apps/node_app_input_laws.zi
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
# Inbe's fonts are TrueType and OpenType files, so every host keeps TTF
# support; without it raylib draws its fallback pixel font.
APP_RAYLIB_CONFIG := $(filter-out -DSUPPORT_MODULE_RAUDIO=0 -DSUPPORT_FILEFORMAT_PNG=0 -DSUPPORT_FILEFORMAT_JPG=0 -DSUPPORT_FILEFORMAT_OGG=0 -DSUPPORT_FILEFORMAT_MP3=% -DSUPPORT_FILEFORMAT_TTF=%,$(RAY_RAYLIB_CONFIG)) -DSUPPORT_MODULE_RAUDIO=1 -DSUPPORT_FILEFORMAT_JPG=1 -DSUPPORT_FILEFORMAT_OGG=1 -DSUPPORT_FILEFORMAT_MP3=1 -DSUPPORT_FILEFORMAT_TTF=1 $(KRYON_RAYLIB_AUDIO_PERIOD_CONFIG) $(KRYON_RAYLIB_AUDIO_PERIODS_CONFIG)
# Live radio uses raylib's MP3 push decoder on desktop hosts.
$(RAYLIB_A) $(WIN64_RAYLIB_A): Makefile

COMMON_CFLAGS := -Wall -Wextra -Os -D_DEFAULT_SOURCE -D_GNU_SOURCE -ffunction-sections -fdata-sections -DSUPPORT_FILEFORMAT_JPG=1 -DUI_EMBEDDED_ONLY=1 -DNATIVE_WINDOW_HAVE_SDL -DKRYON_WITH_SYNC=1
CFLAGS := $(COMMON_CFLAGS) -std=c99 $(RUNTIME_ASSET_CFLAGS) $(SYSTEM_THEME_CFLAGS) $(KRYON_NOTIFICATION_CPPFLAGS) $(KRYON_NOTIFICATION_CFLAGS)
NATIVE_SYSTEM_LDLIBS := $(KRYON_NOTIFICATION_LDLIBS) -lz -lm -lpthread -latomic $(if $(filter linux,$(NATIVE_PLATFORM)),-ldl -lrt,) $(SYSTEM_THEME_LDLIBS)
WINDOWS_CFLAGS := -Wall -Wextra -std=c99 -Os -D_DEFAULT_SOURCE -D_GNU_SOURCE -ffunction-sections -fdata-sections -DSUPPORT_FILEFORMAT_JPG=1 -DUI_EMBEDDED_ONLY=1 -DKRYON_WITH_SYNC=1
WEB_CFLAGS := $(filter-out -Os -DNATIVE_WINDOW_HAVE_SDL,$(COMMON_CFLAGS)) -O2 -std=gnu99
CLICK_CFLAGS := -Wall -Wextra -std=c99 -Os -D_DEFAULT_SOURCE -D_GNU_SOURCE -ffunction-sections -fdata-sections -DSUPPORT_FILEFORMAT_JPG=1 -DUI_EMBEDDED_ONLY=1 -DDISABLE_KRYON_FILE_DIALOG -DHAS_LIBCURL=1 -DKRYON_WITH_SYNC=1 $(AARCH64_KRYON_CURL_CFLAGS)
LDFLAGS := -Wl,--gc-sections -s
WINDOWS_LDFLAGS := -Wl,--gc-sections -static -static-libgcc -mwindows
WINDOWS_LDLIBS := -lgdi32 -lwinmm -lopengl32 -luser32 -lshell32 -lole32 -lcomdlg32 -lcomctl32 -luuid -lwininet -lws2_32 -liphlpapi -lcrypt32 -lsecur32 -lbcrypt -ladvapi32 -lz -lm -latomic -lpthread
ifneq ($(strip $(MCFGTHREADS)),)
WIN64_THREAD_LDFLAGS := -L$(MCFGTHREADS)/lib
else
WIN64_THREAD_LDFLAGS :=
endif

BINARY_NAME := $(APP_EXECUTABLE)-$(NATIVE_PLATFORM)-$(ARCH)
TARGET := $(NATIVE_BIN_DIR)/$(BINARY_NAME)
# Native sources compile to per-file objects through mk/native-objects.mk.
NATIVE_OBJ_DIR := $(abspath $(BUILD_OBJ_DIR)/native)
NATIVE_JOBS ?= $(shell nproc 2>/dev/null || echo 4)
NATIVE_COMPILE_FLAGS = $(KRYON_NATIVE_CFLAGS) $(APP_INCLUDE) $(KRYON_INCLUDE) \
	-iquote$(KRYON_LIBRARY_BUILD_DIR)/c $(SQLITE_INCLUDE) $(LIBOQS_INCLUDE) \
	$(KRYON_NATIVE_BACKEND_CFLAGS) -DHAS_LIBOQS=1 -DSUPPORT_MODULE_RAUDIO=1 \
	-DSUPPORT_FILEFORMAT_OGG=1 -DSUPPORT_FILEFORMAT_MP3=1
KRYON_HOST_TARGET := $(BUILD_DIR)/kryon/app_host.so
WIN64_BINARY_NAME := $(APP_EXECUTABLE)-windows-$(WIN64_ARCH).exe
WIN64_TARGET := $(WINDOWS_BIN_DIR)/$(WIN64_ARCH)/$(WIN64_BINARY_NAME)
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

KRYON_NATIVE_CFLAGS := $(CFLAGS)
KRYON_SRCS += $(KRYON_RAYLIB_WRAPPERS_C)
KRYON_NATIVE_BACKEND_DEPS := $(RAYLIB_A)
KRYON_NATIVE_BACKEND_LIBS := $(RAYLIB_A)
KRYON_NATIVE_BACKEND_CFLAGS := -DKRYON_BACKEND_RAYLIB=1 $(RAY_CFLAGS)
KRYON_NATIVE_BACKEND_LDLIBS := $(RAY_LDLIBS)
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
WEB_HOST_JS := src/web_host.js scripts/telegram_host.js
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

include mk/package-freebsd.mk

.PHONY: web-canvas web-canvas-smoke-test web-compare-test web-side-by-side-test all native kryon-host install install-user uninstall stage package-freebsd deb package-deb deb-check rpm package-rpm rpm-check snap package-snap snap-cache-clean flatpak package-flatpak podman-check validate-desktop run run-fresh screenshot test ci dist appimage click click-verify vendor-prebuilds vendor-prebuilds-native vendor-prebuilds-web vendor-prebuilds-windows font-subsets font-bundle-check clean clean-linux clean-native clean-vendor-builds windows-setup windows-setup-check android-avd android-audio-e2e android-check-keystore android-copy-assets android-copy-debug-apks android-copy-release-apks android-copy-fdroid-apk android-copy-bundle android-smoke android-local-properties android-debug android-release android-bundle android-install android-install-release android-clean android-rebuild validate-meditation-audio package-unpackaged-assets windows-runtime-assets-check windows windows64 web web-tools-check web-smoke-test web-smoke-test-firefox web-smoke-test-librewolf site site-release-assets-check chrome-web-store chrome-web-store-test firefox-addons firefox-addons-lint firefox-addons-source-zip verify-firefox-addons sync-web-icons
.PHONY: zi-check
.PHONY: clean-text-api-check package-check secret-check secret-check-history hooks-install
.NOTPARALLEL: all native test visual-test ci zi-check dist windows windows64 android-release android-bundle click deb package-deb rpm package-rpm snap package-snap flatpak package-flatpak

all: native

# Tests take the whole toolchain directory, so every tool rebuilds together;
# mixing a new zi2zir with an old ziran fails on the ZIR version.
ZIRAN_TOOLS := $(addprefix $(ZIRAN_BUILD_DIR)/bin/,zi2c zi2zir zi2zx zi2go ziran)

$(ZI2C_BIN) $(ZIRAN_BUILD_DIR)/libziran.a &: $(ZIRAN_SOURCES) ziran.lock
	$(MAKE) -C $(ZIRAN_DIR) BUILD_DIR=$(ZIRAN_BUILD_DIR) $(ZIRAN_TOOLS) $(ZIRAN_BUILD_DIR)/libziran.a

$(ZIRAN_BIN): $(ZI2C_BIN)

zi-check: $(ZI_CHECK_STAMP) | build-laws

$(ZI_CHECK_STAMP): Makefile scripts/check-zi-sources.py $(ZI2C_BIN) \
	$(ZI_SRCS) $(DAOCHI_CLIENT_MODULES) $(wildcard build/packages/entity/src/*.zi) $(ZIRAN_STD_MODULES) \
	$(KRYON_UI_ZI) $(KRYON_KSS_ZI) $(GAME2D_MODULES) | build-laws
	@ZI_CHECK_DEFINES="$(ZI_NATIVE_DEFINES)" python3 scripts/check-zi-sources.py $(ZI2ZIR_BIN) $(KRYON_DIR)/src/ui $(ZIRAN_DIR)/std $(KSS_DIR)/src
	@mkdir -p $(dir $@)
	@touch $@

.PHONY: kryon-library-check
kryon-library-check: $(KRYON_LIBRARY_BUILD_DIR)/libkryon.a

$(KRYON_LIBRARY_BUILD_DIR)/libkryon.a: $(KRYON_UI_ZI) $(KRYON_DIR)/src/ui/modules.txt $(KRYON_DIR)/Makefile $(ZI2C_BIN)
	$(MAKE) -C $(KRYON_DIR) BUILD_DIR=$(KRYON_LIBRARY_BUILD_DIR) \
		ZIRAN_DIR=$(abspath $(ZIRAN_DIR)) ZIRAN_BUILD_DIR=$(ZIRAN_BUILD_DIR) \
		$(KRYON_LIBRARY_BUILD_DIR)/libkryon.a

native: $(TARGET)

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
		--module-path $(KRYON_DIR)/src/ui --module-path kryon=$(KRYON_DIR)/src/ui --module-path kryon=$(KRYON_DIR)/src/backend \
		-o $(dir $@) $(KRYON_KSS_ZI)
	touch $@

$(KRYON_KSS_C) $(KRYON_KSS_H): $(KRYON_KSS_STAMP)
	@test -f $@

$(KRY_GEN_STAMP): Makefile ziran.lock $(ZI2C_BIN) $(ZI_SRCS) $(KRYON_ZI_MODULES) $(GAME2D_MODULES) $(DAOCHI_CLIENT_MODULES) $(wildcard build/packages/entity/src/*.zi) $(ZIRAN_STD_MODULES) $(SYNC_RETRY_SOURCE) | build-laws zi-check
	# Imports can change emitted paths; never retain an obsolete header/code pair.
	rm -rf $(KRY_GEN_DIR)
	mkdir -p $(KRY_GEN_DIR)
	sh scripts/run-ziran.sh $(ZI2C_BIN) --no-main --prune-stale --root . \
		$(foreach define,$(ZI_NATIVE_DEFINES),--define $(define)) \
		--module-path src --module-path $(KRYON_DIR)/src/ui \
		--module-path $(KSS_DIR)/src \
		--module-path $(KRYON_DIR)/src/backend \
		--module-path $(GAME2D_DIR)/src \
		--module-path $(ZIRAN_DIR)/std \
		--module-path $(DAOCHI_CLIENT_DIR) $(ZI_PACKAGE_PATHS) \
		-o $(KRY_GEN_DIR) $(ZI_SRCS)
	touch $@

$(KRY_GEN_SRCS) $(KRY_GEN_HDRS) $(KRY_GEN_GAME_C): $(KRY_GEN_STAMP)

vendor-prebuilds: vendor-prebuilds-native vendor-prebuilds-web vendor-prebuilds-windows

vendor-prebuilds-native: $(KRYON_NATIVE_BACKEND_DEPS) $(SQLITE_AMALGAMATION_C) $(SQLITE_AMALGAMATION_H) $(LIBOQS_A) $(CURL_PROTOCOL_CHECK)

vendor-prebuilds-web: web-tools-check $(SQLITE_AMALGAMATION_C) $(SQLITE_AMALGAMATION_H) $(WEB_LIBOQS_A)

vendor-prebuilds-windows: $(WIN64_RAYLIB_A) $(WIN64_CURL_A) $(WIN64_LIBOQS_A) $(SQLITE_AMALGAMATION_C) $(SQLITE_AMALGAMATION_H)

run: $(TARGET)
	@root="$${XDG_DATA_HOME:-$$HOME/.local/share}/inbe-debug"; \
	APP_DATA_ROOT="$$root" ./$(TARGET)

run-fresh: $(TARGET)
	@root=$$(mktemp -d /tmp/$(APP_NAME)-fresh.XXXXXX); \
	echo "APP_DATA_ROOT=$$root"; \
	APP_FORCE_DARK_MODE=1 APP_DATA_ROOT="$$root" ./$(TARGET)

$(sort $(BUILD_OBJ_DIR) $(NATIVE_OBJ_DIR) $(NATIVE_BIN_DIR) $(NATIVE_DIST_DIR) $(LINUX_BIN_DIR) $(LINUX_DIST_DIR) $(LINUX_APPIMAGE_BUILD_DIR) $(DEB_BUILD_DIR) $(DEB_DIST_DIR) $(RPM_BUILD_DIR) $(RPM_DIST_DIR) $(SNAP_BUILD_DIR) $(SNAP_DIST_DIR) $(FLATPAK_BUILD_DIR) $(FLATPAK_DIST_DIR) $(CLICK_BIN_DIR) $(CLICK_BUILD_DIR) $(CLICK_DIST_DIR) $(WINDOWS_DIST_DIR) $(ANDROID_BUILD_DIR) $(TEST_BIN_DIR) $(WEB_OBJ_DIR) $(WEB_DIST_DIR) $(CHROME_WEB_STORE_DIR) $(FIREFOX_ADDONS_DIR)):
	mkdir -p $@

FORCE:

.PHONY: theme-catalog-bundle-check
theme-catalog-bundle-check:
	@cmp themes/catalog_light.kss $(KRYON_DIR)/themes/catalog_light.kss
	@cmp themes/catalog_dark.kss $(KRYON_DIR)/themes/catalog_dark.kss

$(EMBEDDED_ASSETS_C): Makefile $(EMBEDDED_ASSET_FILES) scripts/embed-app-assets.py src/app/assets_host.h | $(BUILD_OBJ_DIR) theme-catalog-bundle-check
	python3 scripts/embed-app-assets.py $@ $(EMBEDDED_ASSET_FILES)

$(KRYON_ICON_ASSETS_C) $(KRYON_ICON_NAMES_C) $(KRYON_ICON_TYPES_H): $(KRYON_ICON_FILES) $(KRYON_DIR)/scripts/embed-icon-sheets.py  | $(BUILD_OBJ_DIR)
	cd $(KRYON_DIR) && python3 scripts/embed-icon-sheets.py "$(KRYON_ICON_DIR)" \
		"$(abspath $(KRYON_ICON_ASSETS_C))" \
		--types-output "$(abspath $(KRYON_ICON_TYPES_H))" \
		--names-output "$(abspath $(KRYON_ICON_NAMES_C))"

$(SQLITE_AMALGAMATION_C) $(SQLITE_AMALGAMATION_H): $(SQLITE_DIR)/configure $(SQLITE_DIR)/manifest | $(BUILD_OBJ_DIR)
	mkdir -p $(SQLITE_BUILD_DIR)
	cd $(SQLITE_BUILD_DIR) && $(abspath $(SQLITE_DIR))/configure
	$(MAKE) -C $(SQLITE_BUILD_DIR) sqlite3.c sqlite3.h

$(TARGET): $(ZIRAN_BUILD_DIR)/libziran.a Makefile $(SRC) $(KRYON_LIBRARY_BUILD_DIR)/libkryon.a $(SQLITE_SRC) $(SQLITE_AMALGAMATION_H) $(FONT_FILES) $(EMBEDDED_ASSETS_C) $(KRYON_NATIVE_BACKEND_DEPS) $(LIBOQS_A) $(CURL_PROTOCOL_CHECK) | $(NATIVE_BIN_DIR)
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
		$(KRYON_LIBRARY_BUILD_DIR)/libkryon.a $(ZIRAN_BUILD_DIR)/libziran.a \
		$(KRYON_NATIVE_BACKEND_LIBS) \
		$(LIBOQS_A) \
		$(KRYON_NATIVE_BACKEND_LDLIBS) \
		$(RUNTIME_ASSET_LDLIBS) \
		$(NATIVE_SYSTEM_LDLIBS) \
		$(LDFLAGS)
	$(if $(filter linux,$(NATIVE_PLATFORM)),python3 scripts/check-package-size.py $@,)

$(KRYON_HOST_TARGET): $(ZIRAN_BUILD_DIR)/libziran.a Makefile $(KRYON_HOST_SRC) $(SQLITE_SRC) $(SQLITE_AMALGAMATION_H) $(FONT_FILES) $(EMBEDDED_ASSETS_C) | $(BUILD_DIR)
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
		-DSUPPORT_FILEFORMAT_MP3=1 \
		-o $@ \
		$(KRYON_HOST_SRC) $(ZIRAN_BUILD_DIR)/libziran.a \
		$(SQLITE_SRC) \
		$(NATIVE_SYSTEM_LDLIBS) \
		-Wl,-Bsymbolic \
		-Wl,--allow-shlib-undefined \
		$(LDFLAGS)

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
# A fresh tree (a container or snap build) has not fetched the packages yet,
# and make reads this whole file before it fetches them and reads it again.
# Check the build environment on that second read, against real sources.
ifeq ($(PACKAGES_READY),1)
ifneq ($(strip $(NEEDS_NATIVE_ENV)),)
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
ifeq ($(strip $(KRYON_CURL_LDLIBS)),)
$(error libcurl metadata is missing. Install libcurl pkg-config metadata or set KRYON_CURL_CFLAGS/KRYON_CURL_LDLIBS explicitly)
endif
ifneq ($(shell v='$(KRYON_CURL_VERSION_HEX)'; if [ "$$v" = 075600 ] || [ "$$v" \> 075600 ]; then echo yes; fi),yes)
$(error libcurl >= 7.86.0 is required for websocket sync; found LIBCURL_VERSION_NUM=$(KRYON_CURL_VERSION_NUM))
endif
endif
endif

include mk/laws.mk
include mk/apps.mk
include mk/windows.mk
include mk/web.mk
include mk/android.mk
include mk/packaging.mk
include mk/site.mk
include mk/release.mk
include mk/tools.mk

# Validate before producing release packages, including direct artifact targets.
$(APPIMAGE_TARGET) $(DEB_TARGET) $(RPM_TARGET) $(SNAP_TARGET) $(FLATPAK_TARGET) $(CLICK_TARGET) $(CHROME_WEB_STORE_ZIP) $(FIREFOX_ADDONS_ZIP): | version-check
android-release android-bundle android-copy-release-apks android-copy-fdroid-apk android-copy-bundle windows-setup site: version-check

# Actual artifacts are gated too, including direct and incremental builds.
$(TARGET) $(KRYON_HOST_TARGET) $(WIN64_TARGET) $(WEB_JS_TARGET) $(WEB_CANVAS_TARGET): $(SYNC_RETRY_SOURCE) | build-laws

BUNDLE_RUNTIME_INPUTS := $(wildcard $(ZIRAN_DIR)/cmd/zir/*.[ch]) $(ZIRAN_DIR)/Makefile scripts/build-bundle-runtime.py
WEB_BUNDLE_RUNTIME := $(abspath $(BUILD_DIR)/bundle-runtime/web/libziran.a)
WINDOWS_BUNDLE_RUNTIME := $(abspath $(BUILD_DIR)/bundle-runtime/windows/libziran.a)
CLICK_BUNDLE_RUNTIME := $(abspath $(BUILD_DIR)/bundle-runtime/click/libziran.a)
$(WEB_BUNDLE_RUNTIME): $(BUNDLE_RUNTIME_INPUTS)
	python3 scripts/build-bundle-runtime.py --source $(ZIRAN_DIR) --output $(dir $@) --cc '$(WEB_CC)' --ar '$(WEB_AR)' --objcopy true --flags='-O2' --wasm
$(WINDOWS_BUNDLE_RUNTIME): $(BUNDLE_RUNTIME_INPUTS)
	python3 scripts/build-bundle-runtime.py --source $(ZIRAN_DIR) --output $(dir $@) --cc '$(WIN64_CC)' --ar '$(WIN64_AR)' --objcopy x86_64-w64-mingw32-objcopy
$(CLICK_BUNDLE_RUNTIME): $(BUNDLE_RUNTIME_INPUTS)
	python3 scripts/build-bundle-runtime.py --source $(ZIRAN_DIR) --output $(dir $@) --cc '$(AARCH64_CC)' --ar '$(AARCH64_AR)' --objcopy aarch64-linux-gnu-objcopy
$(WIN64_TARGET): $(WINDOWS_BUNDLE_RUNTIME)
$(WEB_JS_TARGET) $(WEB_CANVAS_TARGET): $(WEB_BUNDLE_RUNTIME)
$(CLICK_BIN): $(CLICK_BUNDLE_RUNTIME)

# Build fragments affect the artifacts even when Makefile itself is unchanged.
BUILD_MAKEFILES := $(filter-out mk/tests-%.mk,$(MAKEFILE_LIST)) mk/native-objects.mk
$(TARGET) $(KRYON_HOST_TARGET) $(KRY_GEN_STAMP) $(WINDOWS_GEN_STAMP) $(WEB_GEN_STAMP) $(WIN64_TARGET) $(WEB_JS_TARGET) $(WEB_TARGET) $(WEB_CANVAS_TARGET) $(INBE_BUNDLE) $(INBE_FULL_BUNDLE) $(APP_BUNDLES): $(BUILD_MAKEFILES)

# UI prerequisites are expanded only after all artifact paths are defined.
include mk/tests-lumi.mk
include mk/tests-checks.mk
include mk/tests-storage.mk
include mk/tests-practices.mk
include mk/tests-platform.mk
include mk/tests-app.mk
include mk/tests-android.mk
include mk/tests-web.mk
include mk/tests-apps.mk
include mk/tests-ui.mk
include mk/tests-suite.mk
