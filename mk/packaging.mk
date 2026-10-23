# Linux and Ubuntu Touch packages: AppImage, deb, rpm, snap, flatpak and click.

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

$(CLICK_LIBOQS_A): $(LIBOQS_DIR)/CMakeLists.txt mk/sync.mk Makefile
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
		-DOQS_MINIMAL_BUILD="$(KRYON_LIBOQS_MINIMAL_BUILD)"
	$(CMAKE) --build $(CLICK_LIBOQS_BUILD_DIR) --target oqs

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
		$(APP_SRCS) $(GENERATED_NATIVE_C) $(EMBEDDED_ASSETS_C) $(CLICK_BUNDLE_RUNTIME) \
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
	cp $(CLICK_BIN_INPUT) $(CLICK_ROOT)/usr/bin/$(APP_EXECUTABLE)
	cp $(CLICK_RUNNER) $(CLICK_ROOT)/run-$(APP_NAME).sh
	chmod +x $(CLICK_ROOT)/run-$(APP_NAME).sh $(CLICK_ROOT)/usr/bin/$(APP_EXECUTABLE)
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
	cp $(TARGET) $(LINUX_APPDIR)/usr/bin/$(APP_EXECUTABLE)
	patchelf --set-interpreter $(APPIMAGE_INTERPRETER) $(LINUX_APPDIR)/usr/bin/$(APP_EXECUTABLE)
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
		--executable $(abspath $(LINUX_APPDIR)/usr/bin/$(APP_EXECUTABLE)) \
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
	cp $(DEB_BIN_INPUT) $(DEB_ROOT)/usr/bin/$(APP_EXECUTABLE)
	chmod 755 $(DEB_ROOT)/usr/bin/$(APP_EXECUTABLE)
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
		printf '%s\n' 'cp "$(abspath $(RPM_BIN_INPUT))" %{buildroot}/usr/bin/$(APP_EXECUTABLE)'; \
		printf '%s\n' 'chmod 755 %{buildroot}/usr/bin/$(APP_EXECUTABLE)'; \
		printf '%s\n' 'sed -e '\''s/^Icon=.*/Icon=$(APP_ICON_NAME)/'\'' "$(abspath $(LINUX_APPIMAGE_DESKTOP))" > %{buildroot}/usr/share/applications/$(APP_DESKTOP_ID).desktop'; \
		printf '%s\n' 'cp "$(abspath $(LINUX_APPIMAGE_ICON))" %{buildroot}/usr/share/icons/hicolor/512x512/apps/$(APP_ICON_NAME).png'; \
		printf '%s\n' 'sed -e '\''s/<release version="[^"]*"/<release version="$(APP_VERSION)"/'\'' -e '\''s#<launchable type="desktop-id">[^<]*</launchable>#<launchable type="desktop-id">$(APP_DESKTOP_ID).desktop</launchable>#'\'' "$(abspath $(LINUX_APPIMAGE_APPDATA))" > %{buildroot}/usr/share/metainfo/$(ANDROID_APP_ID).metainfo.xml'; \
		printf '%s\n' ''; \
		printf '%s\n' '%files'; \
		printf '%s\n' '/usr/bin/$(APP_EXECUTABLE)'; \
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

$(FLATPAK_TARGET): Makefile $(FLATPAK_MANIFEST) scripts/install-build-fonttools.sh | $(FLATPAK_BUILD_DIR) $(FLATPAK_DIST_DIR) podman-check
	rm -f $(FLATPAK_DIST_DIR)/*.flatpak
	$(PODMAN) run $(PODMAN_RUN_PLATFORM) $(PODMAN_RUN_NETWORK) --rm --privileged \
		-v "$(abspath .):/work" \
		-w /work \
		$(FLATPAK_IMAGE) \
		sh -lc 'set -eu; sh scripts/install-build-node.sh /tmp/inbe-build-node; export PATH=/tmp/inbe-build-node/bin:$$PATH; sh scripts/install-build-fonttools.sh /tmp/inbe-build-fonttools; export PYTHONPATH=/tmp/inbe-build-fonttools; rm -rf .flatpak-builder $(FLATPAK_BUILD_DIR)/repo $(FLATPAK_BUILD_DIR)/build-dir; flatpak-builder --disable-rofiles-fuse --force-clean --repo=$(FLATPAK_BUILD_DIR)/repo $(FLATPAK_BUILD_DIR)/build-dir $(FLATPAK_MANIFEST) || { rm -rf $(FLATPAK_BUILD_DIR)/repo $(FLATPAK_BUILD_DIR)/build-dir vendor-builds/linux build/bin/linux; make vendor-prebuilds-native; make native; flatpak build-init $(FLATPAK_BUILD_DIR)/build-dir $(APP_ID) org.gnome.Sdk org.gnome.Platform 46; install -D -m755 "$$(find build/bin/linux -maxdepth 1 -type f -name '\''$(APP_EXECUTABLE)-linux-*'\'' | head -n 1)" $(FLATPAK_BUILD_DIR)/build-dir/files/bin/$(APP_EXECUTABLE); install -D -m644 packaging/linux/appimage/inbe.desktop $(FLATPAK_BUILD_DIR)/build-dir/files/share/applications/$(APP_ID).desktop; sed -i '\''s/^Icon=.*/Icon=$(APP_ID)/'\'' $(FLATPAK_BUILD_DIR)/build-dir/files/share/applications/$(APP_ID).desktop; install -D -m644 packaging/linux/appimage/inbe.png $(FLATPAK_BUILD_DIR)/build-dir/files/share/icons/hicolor/512x512/apps/$(APP_ID).png; install -D -m644 packaging/linux/appimage/inbe.appdata.xml $(FLATPAK_BUILD_DIR)/build-dir/files/share/metainfo/$(APP_ID).metainfo.xml; flatpak build-finish --share=ipc --share=network --socket=fallback-x11 --socket=wayland --socket=pulseaudio --device=dri --filesystem=home $(FLATPAK_BUILD_DIR)/build-dir; flatpak build-export $(FLATPAK_BUILD_DIR)/repo $(FLATPAK_BUILD_DIR)/build-dir; }; flatpak build-bundle $(FLATPAK_BUILD_DIR)/repo $(FLATPAK_TARGET) $(APP_ID)'
	test -f $@

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
