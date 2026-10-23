# Android build: Gradle APKs and bundles, their copies, install and emulator.

android-copy-assets:
	$(MAKE) $(FONT_FILES)
	$(MAKE) cells
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
	$(ANDROID_GRADLE_ENV) $(GRADLE) -p droid assembleDebug $(if $(ANDROID_ABI),-Papp.onlyAbi="$(ANDROID_ABI)") $(if $(ANDROID_VERIFY_INSTANCE),-Papp.verificationInstance=true) $(ANDROID_GRADLE_ARGS)
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
			python3 scripts/check-package-size.py "$$apk" || exit $$?; \
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
	for abi in arm64-v8a armeabi-v7a x86 x86_64; do \
		for apk in droid/app/build/outputs/apk/release/app-$$abi-release*.apk; do \
			if [ -f "$$apk" ]; then \
				cp "$$apk" "$(ANDROID_BUILD_DIR)/$(APP_NAME)-$(APP_VERSION)-$$abi.apk"; \
			fi; \
		done; \
	done; \
	gplay_universal="$$(find droid/app/build/outputs/apk -path '*/gplay/*' -name "app-universal-gplay*.apk" | head -n 1)"; \
	if [ -z "$$gplay_universal" ] || [ ! -f "$$gplay_universal" ]; then \
		echo "No gplay universal release APK was produced"; \
		exit 1; \
	fi; \
	cp "$$gplay_universal" "$(ANDROID_BUILD_DIR)/$(APP_NAME)-$(APP_VERSION)-gplay.apk"

# F-Droid rebuilds this universal APK with -PfDroidBuild and copies its
# signature, so run after a signed assembleRelease -PfDroidBuild=true.
android-copy-fdroid-apk: | $(ANDROID_BUILD_DIR)
	@fdroid_universal="$$(find droid/app/build/outputs/apk -path '*/release/*' -name "app-universal-release*.apk" | head -n 1)"; \
	if [ -z "$$fdroid_universal" ] || [ ! -f "$$fdroid_universal" ]; then \
		echo "No universal F-Droid APK was produced"; \
		exit 1; \
	fi; \
	cp "$$fdroid_universal" "$(ANDROID_BUILD_DIR)/$(APP_NAME)-$(APP_VERSION)-fdroid.apk"

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
# The app downloads practices by the exact hashes this build lists, and a
# toolchain change gives every pack a new hash. With the publisher key here,
# the missing packs go to the node before the phone asks for them.
	@if [ -f backup/package-publisher/2026-10/publisher.pem ]; then \
		python3 scripts/upload-practice-packs.py || \
		echo "WARNING: this build's practice packs are not all on the node; downloads fail until scripts/upload-practice-packs.py succeeds" >&2; \
	fi
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

android-clean:
	$(GRADLE) -p droid clean $(ANDROID_GRADLE_ARGS)
	rm -rf $(ANDROID_BUILD_DIR)

android-rebuild:
	$(MAKE) android-clean
	$(MAKE) android-debug
