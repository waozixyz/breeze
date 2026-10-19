# Windows build: cross-compiled libraries, the executable, its zip and installer.

# Windows raylib, cross-compiled with MinGW. Kryon's shared make fragments
# used to provide this rule; Inbe builds it now, like the native library.
define WINDOWS_RAYLIB_RULE
$(1): $(RAYLIB_SOURCES) $(RAYLIB_DIR)/Makefile
	@test -f $(RAYLIB_DIR)/raylib.h || { echo "Fetch the raylib package: sh scripts/packages.sh" >&2; exit 1; }
	rm -rf $(2)/source
	mkdir -p $(2)/source
	cp -R $(RAYLIB_DIR)/. $(2)/source/
	find $(2)/source -type f \( -name '*.o' -o -name '*.a' \) -delete
	$(MAKE) -j4 -C $(2)/source \
		OS=Windows_NT RAYLIB_SRC_PATH=. RAYLIB_RELEASE_PATH=.. \
		PLATFORM=PLATFORM_DESKTOP_RGFW GRAPHICS=GRAPHICS_API_OPENGL_11 \
		RAYLIB_LIBTYPE=STATIC RAYLIB_MODULE_AUDIO=TRUE \
		RAYLIB_MODULE_MODELS=TRUE \
		CC="$(3)" AR="$(4)" RANLIB="$(5)" \
		CUSTOM_CFLAGS="$(APP_RAYLIB_CONFIG) -O2 -ffunction-sections -fdata-sections"
	@test -f $$@
endef
$(eval $(call WINDOWS_RAYLIB_RULE,$(WIN64_RAYLIB_A),$(WIN64_RAYLIB_BUILD_DIR),$(WIN64_CC),$(WIN64_AR),$(WIN64_RANLIB)))

$(WINDOWS_GEN_STAMP): Makefile ziran.lock $(ZI2C_BIN) $(ZI_SRCS) $(KRYON_ZI_MODULES) $(GAME2D_MODULES) $(DAOCHI_CLIENT_MODULES) $(wildcard build/packages/self/src/*.zi) $(ZIRAN_STD_MODULES) $(SYNC_RETRY_SOURCE) | build-laws zi-check
	rm -rf $(WINDOWS_GEN_DIR)
	mkdir -p $(WINDOWS_GEN_DIR)
	sh scripts/run-ziran.sh $(ZI2C_BIN) --no-main --root . \
		--define PLATFORM_DESKTOP --define _WIN32 \
		--define DESKTOP_TRAY_ENABLED \
		--module-path src --module-path $(KRYON_DIR)/src/ui \
		--module-path $(KSS_DIR)/src \
		--module-path $(KRYON_DIR)/src/backend \
		--module-path $(GAME2D_DIR)/src \
		--module-path $(ZIRAN_DIR)/std \
		--module-path build/packages/daochi-client $(ZI_PACKAGE_PATHS) \
		-o $(WINDOWS_GEN_DIR) $(ZI_SRCS)
	touch $@
	find $(WINDOWS_GEN_DIR) -type f \( -name '*.c' -o -name '*.h' \) -exec touch -r $@ {} +

$(WINDOWS_GEN_SRCS) $(WINDOWS_GEN_GAME_C): $(WINDOWS_GEN_STAMP)
	@test -f $@

$(WINDOWS_BIN_DIR)/$(WIN64_ARCH):
	mkdir -p $@

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

$(WIN64_LIBOQS_A): $(LIBOQS_DIR)/CMakeLists.txt mk/sync.mk Makefile
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
		-DOQS_MINIMAL_BUILD="$(KRYON_LIBOQS_MINIMAL_BUILD)"
	$(CMAKE) --build $(WIN64_LIBOQS_BUILD_DIR) --target oqs

$(WIN64_RESOURCE): windows/$(APP_NAME).rc windows/$(APP_NAME).ico
	mkdir -p $(dir $@)
	$(WIN64_WINDRES) -Iwindows -O coff $< $@

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
		$(WINDOWS_SRC) $(GENERATED_WINDOWS_C) $(WINDOWS_BUNDLE_RUNTIME) \
		$(SQLITE_SRC) \
		$(WIN64_RAYLIB_A) \
		$(WIN64_CURL_A) \
		$(WIN64_LIBOQS_A) \
		$(WIN64_RESOURCE) $(WINDOWS_LDLIBS) \
		$(WIN64_THREAD_LDFLAGS) \
		$(WINDOWS_LDFLAGS)
	$(WIN64_STRIP) $@

windows-runtime-assets-check:
	@:

windows64: windows-runtime-assets-check $(WIN64_TARGET)

# Windows ships for x86_64 only. 32-bit Windows needs stdcall Win32 calls,
# which Ziran's C output does not emit.
windows:
	$(MAKE) windows64
	mkdir -p $(WINDOWS_DIST_DIR)
	rm -f $(WINDOWS_DIST_DIR)/$(APP_NAME)-windows-*.zip
	rm -f $(WINDOWS_DIST)
	cd $(WINDOWS_BIN_DIR) && zip -9 -j $(abspath $(WINDOWS_DIST)) \
		$(WIN64_ARCH)/$(WIN64_BINARY_NAME)

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
		-DOUT=$(abspath $(WINDOWS_SETUP)) $(WINDOWS_SETUP_SCRIPT)
	test -f $(WINDOWS_SETUP)
