PREFIX ?= /usr/local
DESTDIR ?=
APP_NAME ?= app
APP_TITLE ?= $(APP_NAME)
APP_ID ?= $(APP_NAME)
APP_DESKTOP_ID ?= $(APP_ID)
APP_ICON_NAME ?= $(APP_DESKTOP_ID)
APP_VERSION ?= 0
APP_COMMENT ?= $(APP_TITLE)
APP_DESC ?= $(APP_COMMENT)
APP_CATEGORIES ?= Utility;
APP_MAINTAINER ?= Waozi <waozi@waozi.xyz>
APP_WWW ?= https://waozi.xyz/
APP_ORIGIN ?= local/$(APP_NAME)
APP_LICENSE ?=
APP_DESKTOP ?=
APP_METAINFO ?=
APP_ICON ?=
APP_ICON_SIZE ?= 512x512
FREEBSD_PKG_DEPS ?=

FREEBSD_PKG_STAGE_DIR ?= $(BUILD_DIR)/pkg/freebsd/root
FREEBSD_PKG_WORK_DIR ?= $(BUILD_DIR)/pkg/freebsd
FREEBSD_PKG_DIST_DIR ?= $(BUILD_DIST_DIR)/freebsd
FREEBSD_PKG_ARCH ?= $(shell uname -m 2>/dev/null | sed 's/^amd64$$/x86_64/')
FREEBSD_PKG_ABI ?= $(shell pkg config ABI 2>/dev/null)
FREEBSD_PKG_FILE ?= $(FREEBSD_PKG_DIST_DIR)/$(APP_NAME)-$(APP_VERSION)-freebsd-$(FREEBSD_PKG_ARCH).pkg
FREEBSD_PKG_MANIFEST ?= $(FREEBSD_PKG_WORK_DIR)/+MANIFEST
FREEBSD_PKG_PLIST ?= $(FREEBSD_PKG_WORK_DIR)/plist

.PHONY: install install-user uninstall stage package-freebsd freebsd-pkg-check validate-desktop

install: $(TARGET)
	@$(MAKE) stage DESTDIR=

install-user: $(TARGET)
	@$(MAKE) stage PREFIX="$(HOME)/.local" DESTDIR=

uninstall:
	rm -f "$(DESTDIR)$(PREFIX)/bin/$(APP_NAME)"
	rm -f "$(DESTDIR)$(PREFIX)/share/applications/$(APP_DESKTOP_ID).desktop"
	rm -f "$(DESTDIR)$(PREFIX)/share/applications/$(APP_NAME).desktop"
	rm -f "$(DESTDIR)$(PREFIX)/share/icons/hicolor/$(APP_ICON_SIZE)/apps/$(APP_ICON_NAME).png"
	rm -f "$(DESTDIR)$(PREFIX)/share/icons/hicolor/$(APP_ICON_SIZE)/apps/$(APP_NAME).png"
	rm -f "$(DESTDIR)$(PREFIX)/share/metainfo/$(APP_ID).metainfo.xml"

stage: $(TARGET)
	@set -eu; \
	bin_dir="$(DESTDIR)$(PREFIX)/bin"; \
	app_dir="$(DESTDIR)$(PREFIX)/share/applications"; \
	icon_dir="$(DESTDIR)$(PREFIX)/share/icons/hicolor/$(APP_ICON_SIZE)/apps"; \
	meta_dir="$(DESTDIR)$(PREFIX)/share/metainfo"; \
	mkdir -p "$$bin_dir"; \
	cp "$(TARGET)" "$$bin_dir/$(APP_NAME)"; \
	chmod 755 "$$bin_dir/$(APP_NAME)"; \
	if [ -n "$(strip $(APP_DESKTOP))" ]; then \
		mkdir -p "$$app_dir"; \
		sed -e 's/^Icon=.*/Icon=$(APP_ICON_NAME)/' \
			"$(APP_DESKTOP)" > "$$app_dir/$(APP_DESKTOP_ID).desktop"; \
	fi; \
	if [ -n "$(strip $(APP_ICON))" ]; then \
		mkdir -p "$$icon_dir"; \
		cp "$(APP_ICON)" "$$icon_dir/$(APP_ICON_NAME).png"; \
	fi; \
	if [ -n "$(strip $(APP_METAINFO))" ]; then \
		mkdir -p "$$meta_dir"; \
		sed -e 's/<release version="[^"]*"/<release version="$(APP_VERSION)"/' \
			-e 's#<launchable type="desktop-id">[^<]*</launchable>#<launchable type="desktop-id">$(APP_DESKTOP_ID).desktop</launchable>#' \
			"$(APP_METAINFO)" > "$$meta_dir/$(APP_ID).metainfo.xml"; \
	fi; \
	echo "Staged $(APP_NAME) under $(DESTDIR)$(PREFIX)"

validate-desktop:
	@if [ -n "$(strip $(APP_DESKTOP))" ] && command -v desktop-file-validate >/dev/null 2>&1; then \
		desktop-file-validate "$(APP_DESKTOP)"; \
	else \
		echo "desktop-file-validate not available; skipping"; \
	fi

freebsd-pkg-check:
	@if [ "$$(uname -s)" != "FreeBSD" ]; then \
		echo "package-freebsd must run on FreeBSD"; \
		exit 1; \
	fi
	@command -v pkg >/dev/null 2>&1 || { echo "pkg is required"; exit 1; }

package-freebsd: freebsd-pkg-check validate-desktop
	@set -eu; \
	rm -rf "$(FREEBSD_PKG_STAGE_DIR)" "$(FREEBSD_PKG_WORK_DIR)/manifest.deps"; \
	mkdir -p "$(FREEBSD_PKG_STAGE_DIR)" "$(FREEBSD_PKG_WORK_DIR)" "$(FREEBSD_PKG_DIST_DIR)"; \
	$(MAKE) stage DESTDIR="$(abspath $(FREEBSD_PKG_STAGE_DIR))" PREFIX="$(PREFIX)"; \
	find "$(abspath $(FREEBSD_PKG_STAGE_DIR))$(PREFIX)" -type f | sed "s#^$(abspath $(FREEBSD_PKG_STAGE_DIR))$(PREFIX)/##" | sort > "$(FREEBSD_PKG_PLIST)"; \
	{ \
		printf 'name: "%s"\n' "$(APP_NAME)"; \
		printf 'version: "%s"\n' "$(APP_VERSION)"; \
		printf 'origin: "%s"\n' "$(APP_ORIGIN)"; \
		printf 'comment: "%s"\n' "$(APP_COMMENT)"; \
		printf 'desc: "%s"\n' "$(APP_DESC)"; \
		printf 'maintainer: "%s"\n' "$(APP_MAINTAINER)"; \
		printf 'www: "%s"\n' "$(APP_WWW)"; \
		printf 'prefix: "%s"\n' "$(PREFIX)"; \
		printf 'categories: [ '; \
		first=1; \
		for category in $$(printf '%s\n' "$(APP_CATEGORIES)" | tr ';' ' '); do \
			if [ "$$first" -eq 0 ]; then printf ', '; fi; \
			printf '"%s"' "$$category"; \
			first=0; \
		done; \
		printf ' ]\n'; \
		if [ -n "$(strip $(FREEBSD_PKG_ABI))" ]; then printf 'abi: "%s"\n' "$(FREEBSD_PKG_ABI)"; fi; \
		if [ -n "$(strip $(APP_LICENSE))" ]; then printf 'licenselogic: "single"\nlicenses: [ "%s" ]\n' "$(APP_LICENSE)"; fi; \
		printf 'deps: {\n'; \
		for dep in $(FREEBSD_PKG_DEPS); do \
			dep_name=$${dep%%:*}; \
			dep_origin=$${dep#*:}; \
			if [ "$$dep_origin" = "$$dep" ]; then dep_origin="ports/$$dep_name"; fi; \
			printf '  "%s": { origin: "%s", version: "*" }\n' "$$dep_name" "$$dep_origin"; \
		done; \
		printf '}\n'; \
	} > "$(FREEBSD_PKG_MANIFEST)"; \
	rm -f "$(FREEBSD_PKG_FILE)"; \
	pkg create -M "$(FREEBSD_PKG_MANIFEST)" -r "$(FREEBSD_PKG_STAGE_DIR)" -p "$(FREEBSD_PKG_PLIST)" -o "$(FREEBSD_PKG_DIST_DIR)"; \
	created=$$(find "$(FREEBSD_PKG_DIST_DIR)" -maxdepth 1 -type f -name '$(APP_NAME)-$(APP_VERSION)*.pkg' | head -n 1); \
	if [ -z "$$created" ]; then echo "pkg create did not produce a package"; exit 1; fi; \
	if [ "$$created" != "$(FREEBSD_PKG_FILE)" ]; then mv "$$created" "$(FREEBSD_PKG_FILE)"; fi; \
	echo "Created $(FREEBSD_PKG_FILE)"
