/* Expected storage names for tests/storage_paths_test.c. These are written
 * independently of src/storage/storage_layout.zi so the test catches drift. */
#ifndef STORAGE_LAYOUT_H
#define STORAGE_LAYOUT_H

#define STORAGE_DIR_NAME "inbe"
#define STORAGE_DB_NAME "inbe.db"
#define STORAGE_DB_NAME_LEGACY "breathing.db"
#define STORAGE_DIR_ARCHIVE_SUFFIX ".before-breathing-migration-"
#define STORAGE_EXPORT_ENTRY_DB "inbe-data/inbe.db"
#define STORAGE_EXPORT_ENTRY_META "inbe-data/metadata.json"
#define STORAGE_EXPORT_META_FORMAT "inbe-data-sqlite"
#define STORAGE_EXPORT_PREFIX "inbe"
#define STORAGE_IMPORT_ENTRY_COUNT 2
static const char *const storage_import_entries[STORAGE_IMPORT_ENTRY_COUNT] = {
    "inbe-data/inbe.db",
    "breathing-data/breathing.db"
};
#define STORAGE_WEB_HOME "/home/inbe"
#define STORAGE_WEB_HOME_LEGACY "/home/breathing"
#define STORAGE_IMPORT_DB_TMP "import-inbe.db"
#define STORAGE_IMPORT_DB_INSPECT "import-inspect-inbe.db"
#define STORAGE_EXPORT_DB_TMP "export-inbe.db"
#define STORAGE_EXPORT_FILENAME_FMT "inbe-%lld.zip"
#define STORAGE_EXPORT_FILENAME_FALLBACK "inbe.zip"
#define STORAGE_EXPORT_SESSIONS_CSV "inbe-sessions.csv"
#define STORAGE_WEB_EXPORT_TMP "/tmp/inbe-web-export.zip"

#define STORAGE_EXPECT_DIR_ANDROID "inbe"
#define STORAGE_EXPECT_DIR_WEB "inbe"
#define STORAGE_EXPECT_DIR_WINDOWS "inbe"
#define STORAGE_EXPECT_DIR_POSIX "inbe"
#define STORAGE_DIR_LEGACY_ANDROID "breathing"
#define STORAGE_DIR_LEGACY_WEB "breathing"
#define STORAGE_DIR_LEGACY_WINDOWS "BreathSession"
#define STORAGE_DIR_LEGACY_POSIX "breathing"
#if defined(__EMSCRIPTEN__) || defined(PLATFORM_WEB)
#define STORAGE_EXPECT_DIR_HERE STORAGE_EXPECT_DIR_WEB
#elif defined(ANDROID_BUILD)
#define STORAGE_EXPECT_DIR_HERE STORAGE_EXPECT_DIR_ANDROID
#elif defined(_WIN32)
#define STORAGE_EXPECT_DIR_HERE STORAGE_EXPECT_DIR_WINDOWS
#else
#define STORAGE_EXPECT_DIR_HERE STORAGE_EXPECT_DIR_POSIX
#endif
#endif
