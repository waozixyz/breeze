# Release routine: every artifact (dist), the phone check and the release commit.

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

# Check an exact APK on the development Moto and record the release receipt:
# make phone-check APK=path/to/inbe.apk
.PHONY: phone-check
phone-check:
	@test -n "$(APK)" || { echo "Set APK=path/to/inbe.apk"; exit 1; }
	python3 scripts/phone-check.py "$(APK)" --record

# The release routine (docs/cells.md, "Verification"): run CI's checks here, then
# check on the development Moto and make the one release commit. Never pushes.
# make release [APK=path/to/inbe.apk]
.PHONY: release-ready release
release-ready:
	sh scripts/release-ready.sh

release:
	python3 scripts/release.py $(if $(REVISION),--revision "$(REVISION)",) $(if $(APK),--apk "$(APK)",) $(if $(BUILD_RECEIPT),--build-receipt "$(BUILD_RECEIPT)",)
