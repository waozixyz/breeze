#!/usr/bin/env python3
"""Exercise the owned Android bridge as Zi and verify its ABI against the NDK."""
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
BIN = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "build/ziran-toolchain/bin"
UI = Path(os.environ.get("KRYON_UI", str(ROOT / "build/packages/kryon/src/ui")))
WORK = ROOT / "build/android-jni-zi-test"
GEN = WORK / "generated"
# Stale generated files from an earlier layout would be compiled again.
shutil.rmtree(GEN, ignore_errors=True)
GEN.mkdir(parents=True, exist_ok=True)
MODULES = [
    "activity_jni", "android_mutex", "android_health_host",
    "android_wakelock_host", "android_share", "android_import_host",
    "android_push_host", "android_push_types", "android_device",
    "android_runtime_assets_host", "android_insets", "android_network",
]
SOURCES = [ROOT / f"src/platform/android/{name}.zi" for name in MODULES]
SOURCES.append(ROOT / "src/platform/uri_host.zi")
subprocess.run([
    "sh", str(ROOT / "scripts/run-ziran.sh"), str(BIN / "zi2c"), "--no-main", "--root", str(ROOT),
    "--module-path", str(ROOT / "build/packages/ziran/std"),
    "--module-path", str(ROOT / "build/packages/daochi-client"),
    "--module-path", str(UI), "--define", "ANDROID_BUILD",
    "-o", str(GEN), str(ROOT / "tests/android_jni_behavior.zi"),
    *map(str, SOURCES), str(ROOT / "build/packages/ziran/std/c_string.zi"),
], check=True)
files = sorted(GEN.rglob("*.c"))
includes = ["-I" + str(ROOT / "build/packages/ziran/include"), "-I" + str(GEN)]
includes += ["-I" + str(path) for path in sorted({p.parent for p in GEN.rglob("*.h")})]
subprocess.run([
    os.environ.get("CC", "cc"), "-std=c11", "-Wall", "-Wextra", "-Werror",
    "-Wno-unused-function", "-ffunction-sections", "-fdata-sections",
    "-Wl,--gc-sections", "-pthread", *includes, *map(str, files),
    "-o", str(WORK / "test"),
], check=True)
environment = dict(os.environ)
for name in ("DISPLAY", "WAYLAND_DISPLAY", "XAUTHORITY", "GDK_DISPLAY"):
    environment.pop(name, None)
subprocess.run([str(WORK / "test")], env=environment, check=True)

ndk_base = Path(os.environ.get("ANDROID_HOME", str(Path.home() / "Android/Sdk"))) / "ndk"
ndks = sorted(ndk_base.glob("*/toolchains/llvm/prebuilt/linux-x86_64"))
if ndks:
    toolchain = ndks[-1]
    ndk = toolchain.parents[3]
    header = (ROOT / "src/platform/android/activity_jni.zi").read_text()
    names = re.findall(r"^    (\w+): Jni\w+Fn$", header, re.MULTILINE)
    assertions = [
        '#include <stddef.h>', '#include <pthread.h>', '#define JNI_OnLoad NdkJniOnLoad', '#include <jni.h>', '#undef JNI_OnLoad',
        '#include <android/native_activity.h>', '#include <android_native_app_glue.h>',
        '#include "activity_jni.h"', '#include "android_insets.h"', '#include "android_mutex.h"',
        '_Static_assert(sizeof(AndroidMutex) >= sizeof(pthread_mutex_t), "mutex storage");',
        '_Static_assert(_Alignof(AndroidMutex) >= _Alignof(pthread_mutex_t), "mutex alignment");',
        '_Static_assert(offsetof(NativeActivity, internal_data_path) == offsetof(ANativeActivity, internalDataPath), "internal storage path");',
        '_Static_assert(offsetof(NativeActivity, external_data_path) == offsetof(ANativeActivity, externalDataPath), "external storage path");',
        '_Static_assert(offsetof(NativeActivity, sdk_version) == offsetof(ANativeActivity, sdkVersion), "SDK version");',
        '_Static_assert(offsetof(NativeActivity, instance) == offsetof(ANativeActivity, instance), "native instance");',
        '_Static_assert(offsetof(NativeActivity, asset_manager) == offsetof(ANativeActivity, assetManager), "asset manager");',
        '_Static_assert(sizeof(JniValue) == sizeof(jvalue), "JNI value size");',
        '_Static_assert(_Alignof(JniValue) == _Alignof(jvalue), "JNI value alignment");',
        '_Static_assert(sizeof(NativeMethod) == sizeof(JNINativeMethod), "JNI method size");',
        '_Static_assert(offsetof(NativeAndroidApp, activity) == offsetof(struct android_app, activity), "app activity");',
        '_Static_assert(offsetof(NativeActivity, activity) == offsetof(ANativeActivity, clazz), "native activity");',
    ]
    for name in names:
        table = "JniVmFunctions" if name in {"AttachCurrentThread", "DetachCurrentThread", "GetEnv"} else "JniFunctions"
        native = "JNIInvokeInterface" if table == "JniVmFunctions" else "JNINativeInterface"
        assertions.append(f'_Static_assert(offsetof({table}, {name}) == offsetof(struct {native}, {name}), "{name}");')
    for target in ("aarch64-linux-android24", "armv7a-linux-androideabi24", "i686-linux-android24", "x86_64-linux-android24"):
        command = [str(toolchain / "bin/clang"), "--target=" + target,
                   "-std=c11", "-fsyntax-only", *includes,
                   "-I" + str(ndk / "sources/android/native_app_glue")]
        subprocess.run([*command, "-x", "c", "-"], input="\n".join(assertions), text=True, check=True)
        for source in files:
            subprocess.run([*command, str(source)], check=True)
else:
    print("Android NDK unavailable; native JNI behavior passed, cross ABI checks skipped")
print("Android Zi JNI behavior and available NDK ABI checks passed")
