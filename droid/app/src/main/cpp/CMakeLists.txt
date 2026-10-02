cmake_minimum_required(VERSION 3.22)
project(App C)

find_program(CCACHE_PROGRAM ccache)
if(CCACHE_PROGRAM AND EXISTS "${CCACHE_PROGRAM}")
    set(CMAKE_C_COMPILER_LAUNCHER "${CCACHE_PROGRAM}")
else()
    set(CMAKE_C_COMPILER_LAUNCHER "")
    set(CMAKE_C_COMPILER_LAUNCHER "" CACHE STRING "" FORCE)
endif()

get_filename_component(REPO_ROOT "${CMAKE_CURRENT_LIST_DIR}/../../../../.." ABSOLUTE)
set(SRC_DIR "${REPO_ROOT}/src")
if(NOT EXISTS "${REPO_ROOT}/build/packages/.complete")
    message(FATAL_ERROR "Run sh scripts/packages.sh to fetch the dependencies pinned in ziran.lock")
endif()
set(MONOCYPHER_DIR "${REPO_ROOT}/build/packages/monocypher/src")
if(NOT DEFINED KRYON_DIR)
    set(KRYON_DIR "${REPO_ROOT}/build/packages/kryon")
endif()
get_filename_component(KRYON_DIR "${KRYON_DIR}" ABSOLUTE BASE_DIR "${REPO_ROOT}")
set(RAYLIB_DIR "${REPO_ROOT}/build/packages/raylib/src")
set(SQLITE_DIR "${REPO_ROOT}/build/packages/sqlite")
set(SQLITE_BUILD_DIR "${CMAKE_BINARY_DIR}/sqlite")
set(SQLITE_AMALGAMATION_C "${SQLITE_BUILD_DIR}/sqlite3.c")
set(SQLITE_AMALGAMATION_H "${SQLITE_BUILD_DIR}/sqlite3.h")
include("${KRYON_DIR}/cmake/KryonAndroid.cmake")
set(OQS_BUILD_ONLY_LIB ON CACHE BOOL "" FORCE)
set(OQS_USE_OPENSSL OFF CACHE BOOL "" FORCE)
set(OQS_MINIMAL_BUILD "SIG_ml_dsa_44" CACHE STRING "" FORCE)
set(OQS_DIST_BUILD OFF CACHE BOOL "" FORCE)
set(OQS_OPT_TARGET generic CACHE STRING "" FORCE)
foreach(oqs_x86_feature
        ADX AES AVX AVX2 AVX512 AVX512BW AVX512DQ AVX512F
        BMI1 BMI2 FMA PCLMULQDQ POPCNT SSE SSE2 SSE3 VPCLMULQDQ)
    set(OQS_USE_${oqs_x86_feature}_INSTRUCTIONS OFF CACHE BOOL "" FORCE)
endforeach()
add_subdirectory("${REPO_ROOT}/build/packages/liboqs" "${CMAKE_BINARY_DIR}/liboqs")
if(NOT TARGET oqs)
    message(FATAL_ERROR "Android builds require liboqs for sync account crypto")
endif()
set(ZIRAN_DIR "${REPO_ROOT}/build/packages/ziran")
set(ZIRAN_BUILD_DIR "${REPO_ROOT}/build/ziran-toolchain")
set(ZI2C_BIN "${ZIRAN_BUILD_DIR}/bin/zi2c")
set(ZI2ZIR_BIN "${ZIRAN_BUILD_DIR}/bin/zi2zir")
file(GLOB ZIRAN_SOURCES CONFIGURE_DEPENDS
    "${ZIRAN_DIR}/cmd/zir/*.c" "${ZIRAN_DIR}/cmd/zir/*.h"
    "${ZIRAN_DIR}/cmd/zir-c/*.c" "${ZIRAN_DIR}/cmd/zir-c/*.h"
    "${ZIRAN_DIR}/cmd/zir-ir/*.c" "${ZIRAN_DIR}/cmd/zir-ir/*.h")
find_program(HOST_MAKE NAMES make gmake REQUIRED)
find_program(HOST_PYTHON NAMES python3 REQUIRED)
find_program(HOST_CC NAMES cc gcc REQUIRED NO_CMAKE_FIND_ROOT_PATH)
set(ZIRAN_BIN "${ZIRAN_BUILD_DIR}/bin/ziran")
add_custom_target(app_build_laws
    COMMAND "${HOST_PYTHON}" "${REPO_ROOT}/scripts/check-version.py"
    COMMAND "${ZIRAN_BIN}" check --root "${SRC_DIR}" "${SRC_DIR}/app/sync_retry_laws.zi"
    COMMAND "${ZIRAN_BIN}" check --root "${SRC_DIR}" "${SRC_DIR}/app/practice_lifecycle_laws.zi"
    COMMAND "${ZIRAN_BIN}" check --root "${SRC_DIR}" "${SRC_DIR}/app/sync_recovery_policy_laws.zi"
    COMMAND "${ZIRAN_BIN}" check --root "${SRC_DIR}" "${SRC_DIR}/storage/habit_merge_laws.zi"
    COMMAND "${ZIRAN_BIN}" check --root "${SRC_DIR}" "${SRC_DIR}/storage/sync_restore_laws.zi"
    COMMAND "${ZIRAN_BIN}" check --root "${SRC_DIR}" "${SRC_DIR}/app/modal_rules_laws.zi"
    COMMAND "${ZIRAN_BIN}" check --root "${SRC_DIR}" "${SRC_DIR}/storage/storage_layout_laws.zi"
    COMMAND "${ZIRAN_BIN}" check --root "${SRC_DIR}" --module-path "${KRYON_DIR}/src/ui" --module-path "${ZIRAN_DIR}/std" "${SRC_DIR}/guide_laws.zi"
    DEPENDS "${ZI2C_BIN}"
    WORKING_DIRECTORY "${REPO_ROOT}"
    COMMENT "Checking release consistency and proving app laws"
    VERBATIM
)
add_custom_command(
    OUTPUT "${ZI2C_BIN}"
    BYPRODUCTS "${ZI2ZIR_BIN}"
    COMMAND "${HOST_MAKE}" -j1 -C "${ZIRAN_DIR}"
        "CC=${HOST_CC}" "HOST_CC=${HOST_CC}"
        "BUILD_DIR=${ZIRAN_BUILD_DIR}" all
    DEPENDS ${ZIRAN_SOURCES} "${ZIRAN_DIR}/Makefile"
    VERBATIM
)
set(APP_ZIRAN_GEN_DIR "${CMAKE_BINARY_DIR}/ziran/generated")
set(APP_ZIRAN_MANIFEST "${CMAKE_BINARY_DIR}/ziran/generated-sources.cmake")
file(GLOB_RECURSE APP_ZIRAN_SOURCES CONFIGURE_DEPENDS "${SRC_DIR}/*.zi")
file(GLOB_RECURSE APP_LIBRARY_ZIRAN_SOURCES CONFIGURE_DEPENDS
    "${KRYON_DIR}/src/ui/*.zi" "${KRYON_DIR}/src/backend/*.zi"
    "${REPO_ROOT}/build/packages/kss/src/*.zi" "${REPO_ROOT}/build/packages/oqs/src/*.zi" "${REPO_ROOT}/build/packages/game2d/src/*.zi"
    "${ZIRAN_DIR}/std/*.zi" "${REPO_ROOT}/build/packages/daochi-client/*.zi")
set(APP_ZIRAN_DEFINES --define ANDROID_BUILD)
set(APP_ZIRAN_CHECK_DEFINES "ANDROID_BUILD")
if(ANDROID_ABI STREQUAL "arm64-v8a")
    set(APP_ZIRAN_ARCH __aarch64__)
elseif(ANDROID_ABI STREQUAL "armeabi-v7a")
    set(APP_ZIRAN_ARCH __arm__)
elseif(ANDROID_ABI STREQUAL "x86_64")
    set(APP_ZIRAN_ARCH __x86_64__)
elseif(ANDROID_ABI STREQUAL "x86")
    set(APP_ZIRAN_ARCH __i386__)
else()
    message(FATAL_ERROR "Unsupported Android ABI: ${ANDROID_ABI}")
endif()
list(APPEND APP_ZIRAN_DEFINES --define ${APP_ZIRAN_ARCH})
string(APPEND APP_ZIRAN_CHECK_DEFINES " ${APP_ZIRAN_ARCH}")

# CMake needs the complete emitted import graph before it creates build rules.
# Run the same required law gates before this initial source generation.
execute_process(COMMAND "${HOST_MAKE}" -j1 -C "${ZIRAN_DIR}"
    "CC=${HOST_CC}" "HOST_CC=${HOST_CC}"
    "BUILD_DIR=${ZIRAN_BUILD_DIR}" all COMMAND_ERROR_IS_FATAL ANY)
execute_process(COMMAND "${HOST_PYTHON}" "${REPO_ROOT}/scripts/check-version.py"
    WORKING_DIRECTORY "${REPO_ROOT}" COMMAND_ERROR_IS_FATAL ANY)
execute_process(COMMAND "${ZIRAN_BIN}" check --root "${SRC_DIR}"
    "${SRC_DIR}/app/sync_retry_laws.zi"
    WORKING_DIRECTORY "${REPO_ROOT}" COMMAND_ERROR_IS_FATAL ANY)
execute_process(COMMAND "${ZIRAN_BIN}" check --root "${SRC_DIR}"
    "${SRC_DIR}/app/practice_lifecycle_laws.zi"
    WORKING_DIRECTORY "${REPO_ROOT}" COMMAND_ERROR_IS_FATAL ANY)
execute_process(COMMAND "${ZIRAN_BIN}" check --root "${SRC_DIR}"
    "${SRC_DIR}/app/sync_recovery_policy_laws.zi"
    WORKING_DIRECTORY "${REPO_ROOT}" COMMAND_ERROR_IS_FATAL ANY)
execute_process(COMMAND "${ZIRAN_BIN}" check --root "${SRC_DIR}"
    "${SRC_DIR}/storage/habit_merge_laws.zi"
    WORKING_DIRECTORY "${REPO_ROOT}" COMMAND_ERROR_IS_FATAL ANY)
execute_process(COMMAND "${ZIRAN_BIN}" check --root "${SRC_DIR}"
    "${SRC_DIR}/storage/sync_restore_laws.zi"
    WORKING_DIRECTORY "${REPO_ROOT}" COMMAND_ERROR_IS_FATAL ANY)
execute_process(COMMAND "${ZIRAN_BIN}" check --root "${SRC_DIR}"
    "${SRC_DIR}/app/modal_rules_laws.zi"
    WORKING_DIRECTORY "${REPO_ROOT}" COMMAND_ERROR_IS_FATAL ANY)
execute_process(COMMAND "${ZIRAN_BIN}" check --root "${SRC_DIR}"
    "${SRC_DIR}/storage/storage_layout_laws.zi"
    WORKING_DIRECTORY "${REPO_ROOT}" COMMAND_ERROR_IS_FATAL ANY)
execute_process(COMMAND "${ZIRAN_BIN}" check --root "${SRC_DIR}"
    --module-path "${KRYON_DIR}/src/ui" --module-path "${ZIRAN_DIR}/std"
    "${SRC_DIR}/guide_laws.zi"
    WORKING_DIRECTORY "${REPO_ROOT}" COMMAND_ERROR_IS_FATAL ANY)
set(APP_GENERATE_ZIRAN_COMMAND "${HOST_PYTHON}"
    "${REPO_ROOT}/scripts/generate-android-sources.py"
    --compiler "${ZI2C_BIN}" --root "${REPO_ROOT}" --kryon "${KRYON_DIR}"
    --output "${APP_ZIRAN_GEN_DIR}" --manifest "${APP_ZIRAN_MANIFEST}"
    ${APP_ZIRAN_DEFINES})
set(APP_ZIRAN_STAMP "${CMAKE_BINARY_DIR}/ziran/generated.stamp")
set(APP_ZIRAN_INPUTS_FILE "${CMAKE_BINARY_DIR}/ziran/generation-inputs.txt")
set(APP_ZIRAN_INPUTS "${APP_GENERATE_ZIRAN_COMMAND};${APP_ZIRAN_SOURCES};${APP_LIBRARY_ZIRAN_SOURCES}")
set(APP_ZIRAN_GENERATE TRUE)
if(EXISTS "${APP_ZIRAN_MANIFEST}" AND EXISTS "${APP_ZIRAN_STAMP}" AND
        EXISTS "${APP_ZIRAN_INPUTS_FILE}")
    file(READ "${APP_ZIRAN_INPUTS_FILE}" APP_ZIRAN_OLD_INPUTS)
    if(APP_ZIRAN_OLD_INPUTS STREQUAL APP_ZIRAN_INPUTS)
        set(APP_ZIRAN_GENERATE FALSE)
        include("${APP_ZIRAN_MANIFEST}")
        foreach(input ${APP_ZIRAN_SOURCES} ${APP_LIBRARY_ZIRAN_SOURCES}
                "${ZI2C_BIN}" "${REPO_ROOT}/scripts/generate-android-sources.py")
            if("${input}" IS_NEWER_THAN "${APP_ZIRAN_STAMP}")
                set(APP_ZIRAN_GENERATE TRUE)
            endif()
        endforeach()
        foreach(output ${APP_ZIRAN_GENERATED_SOURCES} ${APP_ZIRAN_GENERATED_HEADERS})
            if(NOT EXISTS "${output}")
                set(APP_ZIRAN_GENERATE TRUE)
            endif()
        endforeach()
    endif()
endif()
if(APP_ZIRAN_GENERATE)
    execute_process(COMMAND ${APP_GENERATE_ZIRAN_COMMAND}
        WORKING_DIRECTORY "${REPO_ROOT}" COMMAND_ERROR_IS_FATAL ANY)
    file(WRITE "${APP_ZIRAN_INPUTS_FILE}" "${APP_ZIRAN_INPUTS}")
    file(TOUCH "${APP_ZIRAN_STAMP}")
endif()
include("${APP_ZIRAN_MANIFEST}")
add_custom_command(
    OUTPUT "${APP_ZIRAN_STAMP}"
    BYPRODUCTS ${APP_ZIRAN_GENERATED_SOURCES} ${APP_ZIRAN_GENERATED_HEADERS}
    COMMAND ${APP_GENERATE_ZIRAN_COMMAND}
    COMMAND ${CMAKE_COMMAND} -E touch "${APP_ZIRAN_STAMP}"
    DEPENDS ${APP_ZIRAN_SOURCES} ${APP_LIBRARY_ZIRAN_SOURCES} "${ZI2C_BIN}"
        "${REPO_ROOT}/scripts/generate-android-sources.py"
        "${REPO_ROOT}/scripts/run-ziran.sh"
    WORKING_DIRECTORY "${REPO_ROOT}" VERBATIM)
add_custom_target(app_ziran_generated DEPENDS "${APP_ZIRAN_STAMP}")
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS
    ${APP_ZIRAN_SOURCES} ${APP_LIBRARY_ZIRAN_SOURCES}
    "${REPO_ROOT}/scripts/generate-android-sources.py")
set_source_files_properties(${APP_ZIRAN_GENERATED_SOURCES}
    ${APP_ZIRAN_GENERATED_HEADERS} PROPERTIES GENERATED TRUE)
add_custom_target(app_clean_runtime_api
    COMMAND "${HOST_PYTHON}" "${REPO_ROOT}/scripts/check-clean-text-api.py" "${SRC_DIR}"
    WORKING_DIRECTORY "${REPO_ROOT}" VERBATIM)
add_custom_target(app_zi_check
    COMMAND ${CMAKE_COMMAND} -E env "ZI_CHECK_DEFINES=${APP_ZIRAN_CHECK_DEFINES}"
        "${HOST_PYTHON}" "${REPO_ROOT}/scripts/check-zi-sources.py" "${ZI2ZIR_BIN}"
    DEPENDS "${ZI2C_BIN}" WORKING_DIRECTORY "${REPO_ROOT}" VERBATIM)
add_dependencies(app_zi_check app_build_laws)
add_dependencies(app_ziran_generated app_build_laws app_clean_runtime_api app_zi_check)

file(GLOB APP_LOCALE_ASSETS RELATIVE "${REPO_ROOT}" CONFIGURE_DEPENDS "${REPO_ROOT}/locales/*.txt")
file(GLOB APP_SOUND_ASSETS RELATIVE "${REPO_ROOT}" CONFIGURE_DEPENDS "${REPO_ROOT}/assets/sounds/*.ogg")
file(GLOB APP_SOCIAL_ASSETS RELATIVE "${REPO_ROOT}" CONFIGURE_DEPENDS "${REPO_ROOT}/assets/social/*.png")
# banner.png is the web/store copy of banner-light.png; the app loads only
# the themed pair.
file(GLOB APP_PRACTICE_BANNER_ASSETS RELATIVE "${REPO_ROOT}" CONFIGURE_DEPENDS
    "${REPO_ROOT}/assets/practices/*/banner-light.png"
    "${REPO_ROOT}/assets/practices/*/banner-dark.png")
file(GLOB APP_SUN_SALUTATION_FRAMES RELATIVE "${REPO_ROOT}" CONFIGURE_DEPENDS
    "${REPO_ROOT}/assets/practices/sunsalutation/girl/*.png")
file(GLOB APP_STYLE_ASSETS RELATIVE "${REPO_ROOT}"
    "${REPO_ROOT}/build/packages/kss/styles/*.kss" "${REPO_ROOT}/assets/styles/*.kss"
    "${REPO_ROOT}/themes/catalog_*.kss")
foreach(mode light dark)
    file(SHA256 "${REPO_ROOT}/themes/catalog_${mode}.kss" APP_CATALOG_HASH)
    file(SHA256 "${KRYON_DIR}/themes/catalog_${mode}.kss" KRYON_CATALOG_HASH)
    if(NOT APP_CATALOG_HASH STREQUAL KRYON_CATALOG_HASH)
        message(FATAL_ERROR "Packaged ${mode} theme catalog differs from Kryon")
    endif()
endforeach()
set(APP_EMBEDDED_INPUTS
    ${APP_STYLE_ASSETS}
    ${APP_LOCALE_ASSETS}
    assets/app/icon.png
    assets/app/icon-sky-cradle.png
    assets/app/icon-ink-and-air.png
    assets/easteregg/art.png
    assets/easteregg/waozi.png
    assets/practices/whm/1.png
    assets/practices/whm/2.png
    assets/practices/meditation/1.png
    assets/pet/egg1.png
    build/packages/kryon/icons/ui.png
    build/packages/kryon/icons/pfp.png
    ${APP_PRACTICE_BANNER_ASSETS}
    ${APP_SOCIAL_ASSETS}
    ${APP_SUN_SALUTATION_FRAMES}
    assets/fonts/subset/NotoSans-App-Regular.ttf
    assets/fonts/subset/NotoSansSC-App-Regular.otf
    assets/fonts/subset/NotoSansJP-App-Regular.otf
    assets/fonts/subset/NotoSansKR-App-Regular.otf
    assets/fonts/subset/NotoSansTC-App-Regular.otf
    ${APP_SOUND_ASSETS}
)
set(APP_EMBEDDED_DEPS)
foreach(asset ${APP_EMBEDDED_INPUTS})
    list(APPEND APP_EMBEDDED_DEPS "${REPO_ROOT}/${asset}")
endforeach()
set(APP_EMBEDDED_ASSETS_C "${CMAKE_BINARY_DIR}/app_embedded_assets.c")

add_custom_command(
    OUTPUT "${APP_EMBEDDED_ASSETS_C}"
    COMMAND "${HOST_PYTHON}" "${REPO_ROOT}/scripts/embed-app-assets.py"
        "${APP_EMBEDDED_ASSETS_C}" ${APP_EMBEDDED_INPUTS}
    DEPENDS "${REPO_ROOT}/scripts/embed-app-assets.py" ${APP_EMBEDDED_DEPS}
    WORKING_DIRECTORY "${REPO_ROOT}"
    VERBATIM
)

add_custom_command(
    OUTPUT "${SQLITE_AMALGAMATION_C}" "${SQLITE_AMALGAMATION_H}"
    COMMAND ${CMAKE_COMMAND} -E make_directory "${SQLITE_BUILD_DIR}"
    COMMAND sh -c "cd '${SQLITE_BUILD_DIR}' && '${SQLITE_DIR}/configure'"
    COMMAND make -C "${SQLITE_BUILD_DIR}" sqlite3.c sqlite3.h
    DEPENDS "${SQLITE_DIR}/configure" "${SQLITE_DIR}/manifest"
    VERBATIM
)

kryon_android_raylib("${RAYLIB_DIR}")

add_library(main SHARED
    "${MONOCYPHER_DIR}/monocypher.c"
    "${MONOCYPHER_DIR}/optional/monocypher-ed25519.c"
    "${SQLITE_AMALGAMATION_C}"
    "${APP_EMBEDDED_ASSETS_C}"
    ${APP_ZIRAN_GENERATED_SOURCES}
)
kryon_android_app(main)
add_dependencies(main app_ziran_generated app_clean_runtime_api app_build_laws app_zi_check)

target_include_directories(main PRIVATE
    "${ZIRAN_DIR}/include"
    "${MONOCYPHER_DIR}"
    "${MONOCYPHER_DIR}/optional"
    "${SRC_DIR}/app"
    "${SQLITE_BUILD_DIR}"
)
# Generated module names such as math.h must not shadow libc's <math.h>
# in SQLite and other native dependencies. Zi imports use quoted includes.
foreach(directory ${APP_ZIRAN_INCLUDE_DIRS})
    target_compile_options(main PRIVATE "-iquote${directory}")
endforeach()

target_compile_definitions(main PRIVATE
    UTF8PROC_STATIC
    MG_TLS=MG_TLS_BUILTIN
    MG_ENABLE_EPOLL=0
    MG_ENABLE_POLL=1
    MG_ENABLE_POSIX_FS=0
    SUPPORT_MODULE_RAUDIO=1
    SUPPORT_FILEFORMAT_OGG=1
    UI_EMBEDDED_ONLY=1
    HAS_LIBOQS=1
    KRYON_WITH_SYNC=1
    KRYON_WITH_PHYSICS=0
)

# The VM locates this exported entry before native methods are registered.
foreach(source ${APP_ZIRAN_GENERATED_SOURCES})
    get_filename_component(source_name "${source}" NAME)
    if(source_name STREQUAL "android_insets.c")
        set_source_files_properties("${source}"
            PROPERTIES COMPILE_OPTIONS "-fvisibility=default")
    elseif(source_name STREQUAL "main.c")
        # Raylib invokes this shared-library entry itself; its Zi argv is
        # byte pointers, so hosted C's spelling rule for main does not apply.
        set_source_files_properties("${source}"
            PROPERTIES COMPILE_OPTIONS "-ffreestanding")
    endif()
endforeach()

target_link_libraries(main oqs z)
