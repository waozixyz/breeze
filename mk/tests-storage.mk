# Storage, sync, account, crypto and Telegram delegation tests.

.PHONY: sync-retry-zi-test
sync-retry-zi-test: build-laws $(ZI2C_BIN)
	@sh tests/sync_retry_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

# Exercise the packaged Ziran crypto API against the exact archive used by
# Inbe, including ML-KEM round trips, tampering and short-buffer rejection.
.PHONY: liboqs-crypto-test
liboqs-crypto-test: $(ZIRAN_BIN) $(LIBOQS_A)
	@rm -rf $(BUILD_DIR)/liboqs-crypto-test/generated
	@mkdir -p $(BUILD_DIR)/liboqs-crypto-test/generated
	@$(ZIRAN_BIN) build --target=c --root $(OQS_DIR)/src \
		--module-path $(OQS_DIR)/tests --module-path $(ZIRAN_DIR)/std \
		--entry oqs_test:main -o $(BUILD_DIR)/liboqs-crypto-test/generated \
		$(OQS_DIR)/tests/oqs_test.zi
	@$(CC) -std=c99 -O2 -I$(ZIRAN_DIR)/include \
		-I$(BUILD_DIR)/liboqs-crypto-test/generated \
		$(BUILD_DIR)/liboqs-crypto-test/generated/*.c $(LIBOQS_A) \
		-lm -lpthread -o $(BUILD_DIR)/liboqs-crypto-test/test
	@env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u DBUS_SESSION_BUS_ADDRESS \
		$(BUILD_DIR)/liboqs-crypto-test/test
	@echo "Inbe liboqs: ML-DSA-44 and ML-KEM-768 checks passed"

.PHONY: sync-account-zi-test
sync-account-zi-test: $(ZI2C_BIN) $(SQLITE_SRC) $(LIBOQS_A)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/sync_account_zi_test.sh $(ZIRAN_BUILD_DIR)/bin/ziran $(LIBOQS_A)

.PHONY: storage-import-zi-test
storage-import-zi-test: $(ZI2C_BIN) $(SQLITE_SRC) $(LIBOQS_A)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/storage_import_zi_test.sh $(ZIRAN_BUILD_DIR)/bin/ziran $(LIBOQS_A)

.PHONY: storage-habits-zi-test
storage-habits-zi-test: $(ZI2C_BIN) $(SQLITE_SRC) $(LIBOQS_A)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/storage_habits_zi_test.sh $(ZIRAN_BUILD_DIR)/bin/ziran $(LIBOQS_A)

.PHONY: achievements-test achievement-catalog-test
achievements-test: build-laws $(ZI2C_BIN) $(ZIRAN_BUILD_DIR)/libziran.a $(SQLITE_SRC) $(LIBOQS_A)
	@env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u DBUS_SESSION_BUS_ADDRESS \
		sh tests/achievements_zi_test.sh $(ZIRAN_BUILD_DIR)/bin/ziran $(LIBOQS_A)

achievement-catalog-test:
	python3 tests/achievement_catalogs_test.py

.PHONY: storage-settings-threads-zi-test
storage-settings-threads-zi-test: $(ZI2C_BIN) $(SQLITE_SRC) $(LIBOQS_A)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/storage_settings_threads_zi_test.sh $(ZIRAN_BUILD_DIR)/bin/ziran $(LIBOQS_A)

.PHONY: storage-sync-zi-test
storage-sync-zi-test: $(ZI2C_BIN) $(SQLITE_SRC) $(LIBOQS_A)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/storage_sync_zi_test.sh $(ZIRAN_BUILD_DIR)/bin/ziran $(LIBOQS_A)

.PHONY: sync-url-zi-test
sync-url-zi-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/sync_url_zi_test.sh $(ZIRAN_BUILD_DIR)/bin/ziran

.PHONY: sync-review-zi-test
sync-review-zi-test: $(ZI2C_BIN) $(SQLITE_SRC) | build-laws
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/sync_review_zi_test.sh $(ZIRAN_BUILD_DIR)/bin/ziran

# The real merge SQL must satisfy the laws stated for its model.
.PHONY: habit-merge-sql-test sync-restore-sql-test
habit-merge-sql-test:
	python3 tests/habit_merge_sql_test.py

sync-restore-sql-test:
	python3 tests/sync_restore_sql_test.py

.PHONY: sync-server-test
sync-server-test: $(ZI2C_BIN) $(SQLITE_SRC) $(LIBOQS_A)
	@sh tests/sync_server_zi_test.sh $(ZIRAN_BUILD_DIR)/bin/ziran $(LIBOQS_A)
	node scripts/sync-server-test.mjs

.PHONY: schema-zi-test
schema-zi-test: $(ZI2C_BIN) $(SQLITE_SRC)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/schema_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

.PHONY: root-upgrade-zi-test
root-upgrade-zi-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/root_upgrade_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

.PHONY: database-upgrade-zi-test
database-upgrade-zi-test: $(ZI2C_BIN) $(SQLITE_SRC)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/database_upgrade_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

.PHONY: legacy-session-zi-test
legacy-session-zi-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/legacy_session_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

.PHONY: archive-file-linux-zi-test
archive-file-linux-zi-test: $(ZI2C_BIN) $(SQLITE_SRC) | build-laws
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/archive_file_linux_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

.PHONY: export-filename-test
export-filename-test: $(ZI2C_BIN) | build-laws
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/export_filename_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

.PHONY: storage-state-zi-test
storage-state-zi-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/storage_state_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

.PHONY: storage-sql-zi-test
storage-sql-zi-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY $(ZI2ZIR_BIN) --check-only --root src \
		src/storage/sync_sql.zi src/storage/export_sql.zi \
		src/storage/habit_sync_sql.zi
	@env -u DISPLAY -u WAYLAND_DISPLAY python3 tests/storage_sql_behavior_test.py

.PHONY: storage-json-builder-zi-test
storage-json-builder-zi-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/storage_json_builder_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

.PHONY: storage-thread-buffer-zi-test
storage-thread-buffer-zi-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/storage_thread_buffer_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

.PHONY: sqlite-text-zi-test
sqlite-text-zi-test: $(ZI2C_BIN) $(SQLITE_SRC) $(SQLITE_AMALGAMATION_H)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/sqlite_text_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

.PHONY: sql-transaction-zi-test
sql-transaction-zi-test: $(ZI2C_BIN) $(SQLITE_SRC) $(SQLITE_AMALGAMATION_H)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/sql_transaction_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

.PHONY: storage-paths-zi-test
storage-paths-zi-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/storage_paths_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

.PHONY: daochi-client-zi-test
daochi-client-zi-test: $(ZI2C_BIN) $(LIBOQS_A)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		ZI2C_BIN=$(abspath $(ZI2C_BIN)) ZIRAN_DIR=$(abspath $(ZIRAN_DIR)) \
		ZIRAN_BIN=$(abspath $(ZIRAN_BIN)) OQS_DIR=$(abspath build/packages/oqs) \
		LIBOQS_A=$(abspath $(LIBOQS_A)) \
		sh build/packages/daochi-client/tests/run.sh

.PHONY: daochi-native-zi-test device-link-zi-test
daochi-native-zi-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u DBUS_SESSION_BUS_ADDRESS \
		python3 tests/daochi_native_zi_test.py $(ZI2C_BIN)

device-link-zi-test: $(ZIRAN_BIN) $(LIBOQS_A)
	@env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u DBUS_SESSION_BUS_ADDRESS \
		python3 tests/device_link_zi_test.py $(ZIRAN_BIN) $(abspath $(LIBOQS_A))

.PHONY: sync-safety-test
sync-safety-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/sync_safety_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

.PHONY: account-activity-test
account-activity-test: $(ZIRAN_BIN) $(LIBOQS_A) $(SQLITE_SRC) $(SQLITE_AMALGAMATION_H)
	@sh tests/account_activity_zi_test.sh $(ZIRAN_BIN) $(LIBOQS_A)

.PHONY: sync-status-policy-test
sync-status-policy-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/sync_status_policy_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

.PHONY: social-action-queue-test
social-action-queue-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/social_action_queue_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

.PHONY: sync-worker-host-test
sync-worker-host-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/sync_worker_host_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

.PHONY: sync-status-test
sync-status-test: $(ZI2C_BIN)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/sync_status_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

.PHONY: sync-recovery-test
sync-recovery-test: build-laws $(ZI2C_BIN) $(SQLITE_SRC) $(SQLITE_AMALGAMATION_H)
	@env -u DISPLAY -u WAYLAND_DISPLAY \
		sh tests/sync_recovery_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

.PHONY: sync-connection-test
sync-connection-test: $(ZIRAN_BIN) $(LIBOQS_A) $(SQLITE_SRC) $(SQLITE_AMALGAMATION_H)
	@sh tests/sync_connection_zi_test.sh $(ZIRAN_BIN) $(LIBOQS_A)

.PHONY: sync-record-fields-test
sync-record-fields-test:
	python3 tests/sync_record_fields_test.py

.PHONY: app-preferences-sync-test
app-preferences-sync-test:
	python3 tests/app_preferences_sync_test.py

.PHONY: device-key-test
device-key-test: $(ZI2C_BIN)
	python3 tests/device_key_zi_test.py $(ZI2C_BIN)

.PHONY: telegram-authorization-test telegram-bridge-test telegram-host-test telegram-entry-protocol-test telegram-account-flow-test telegram-account-ui-test settings-telegram-ui-test lumi-authorization-test delegate-account-test storage-delegate-test lumi-delegate-scope-test

telegram-bridge-test:
	@sh tests/telegram_bridge_test.sh

telegram-host-test:
	@sh tests/telegram_host_test.sh

telegram-entry-protocol-test: $(ZIRAN_BIN) $(LIBOQS_A) $(SQLITE_SRC) $(SQLITE_AMALGAMATION_H)
	@sh tests/telegram_entry_protocol_zi_test.sh $(ZIRAN_BIN) $(LIBOQS_A)

telegram-account-flow-test: $(ZIRAN_BIN) $(LIBOQS_A) $(SQLITE_SRC) $(SQLITE_AMALGAMATION_H)
	@sh tests/telegram_account_flow_zi_test.sh $(ZIRAN_BIN) $(LIBOQS_A)

telegram-account-ui-test: $(ZIRAN_BIN)
	@sh tests/telegram_account_ui_zi_test.sh $(ZIRAN_BUILD_DIR)/bin

settings-telegram-ui-test: $(ZIRAN_BIN) $(LIBOQS_A)
	@sh tests/settings_telegram_ui_zi_test.sh $(ZIRAN_BUILD_DIR)/bin $(LIBOQS_A)

lumi-authorization-test: $(ZIRAN_BIN) $(LIBOQS_A) $(SQLITE_SRC) $(SQLITE_AMALGAMATION_H)
	@sh tests/lumi_authorization_zi_test.sh $(ZIRAN_BIN) $(LIBOQS_A)

delegate-account-test: $(ZIRAN_BIN) $(LIBOQS_A) $(SQLITE_SRC) $(SQLITE_AMALGAMATION_H)
	@sh tests/delegate_account_zi_test.sh $(ZIRAN_BIN) $(LIBOQS_A)

storage-delegate-test: $(ZIRAN_BIN) $(LIBOQS_A) $(SQLITE_SRC) $(SQLITE_AMALGAMATION_H)
	@sh tests/storage_delegate_zi_test.sh $(ZIRAN_BIN) $(LIBOQS_A)

lumi-delegate-scope-test: $(ZIRAN_BIN) $(LIBOQS_A) $(SQLITE_SRC) $(SQLITE_AMALGAMATION_H)
	@sh tests/lumi_delegate_scope_zi_test.sh $(ZIRAN_BIN) $(LIBOQS_A)

telegram-authorization-test: telegram-bridge-test telegram-host-test telegram-entry-protocol-test telegram-account-flow-test telegram-account-ui-test settings-telegram-ui-test lumi-authorization-test delegate-account-test storage-delegate-test lumi-delegate-scope-test

.PHONY: dew-test
dew-test: $(ZIRAN_BIN) $(LIBOQS_A) $(SQLITE_SRC) $(SQLITE_AMALGAMATION_H) | build-laws
	@sh tests/dew_test.sh $(ZIRAN_BIN) $(LIBOQS_A)

.PHONY: lists-sharing-test
lists-sharing-test: $(ZIRAN_BIN) $(LIBOQS_A) $(SQLITE_SRC) $(SQLITE_AMALGAMATION_H) | build-laws
	@sh tests/lists_sharing_test.sh $(ZIRAN_BIN) $(LIBOQS_A)
