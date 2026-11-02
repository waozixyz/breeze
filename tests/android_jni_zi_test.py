#!/usr/bin/env python3
"""Exercise the owned Android bridge as Zi and verify its ABI against the NDK."""
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
BIN = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "build/ziran-toolchain/bin"
UI = Path(os.environ.get("KRYON_UI", str(ROOT / "build/packages/kryon/src/ui")))
WORK = ROOT / "build/android-jni-zi-test"
GEN = WORK / "generated"
BACKEND = Path(os.environ.get("KRYON_BACKEND", str(ROOT / "build/packages/kryon/src/backend")))
MODULES = [
    "android_mutex", "android_health_host",
    "android_wakelock_host",
    "android_push_host", "android_push_types", "android_activity",
    "android_insets", "android_startup",
]
SOURCES = [ROOT / f"src/platform/android/{name}.zi" for name in MODULES]


def generate(output, architecture=None):
    shutil.rmtree(output, ignore_errors=True)
    output.mkdir(parents=True, exist_ok=True)
    arguments = [
        "sh", str(ROOT / "scripts/run-ziran.sh"), str(BIN / "zi2c"), "--no-main", "--root", str(ROOT),
        "--module-path", str(ROOT / "build/packages/ziran/std"),
        "--module-path", str(ROOT / "build/packages/daochi-client"),
        "--module-path", str(UI), "--module-path", str(BACKEND),
        # Named package imports such as entity/account_handoff.
        *subprocess.check_output(["sh", str(ROOT / "scripts/package-paths.sh"), str(ROOT / "build/packages")],
                                 text=True).split(),
        "--define", "ANDROID_BUILD", "--define", "KRYON_ANDROID_HOST",
        "-o", str(output), str(ROOT / "tests/android_jni_behavior.zi"),
        *map(str, SOURCES), str(ROOT / "build/packages/ziran/std/c_string.zi"),
    ]
    if architecture:
        index = arguments.index("-o")
        arguments[index:index] = ["--define", architecture]
    subprocess.run(arguments, check=True)


def generated_includes(output):
    return ["-I" + str(ROOT / "build/packages/ziran/include"), "-I" + str(output)] + [
        "-I" + str(path) for path in sorted({p.parent for p in output.rglob("*.h")})]


# The host run needs its own architecture too: Android-only std code, such as
# file_linux's renameat2 system call number, is chosen per architecture.
HOST_ARCHITECTURE = {"x86_64": "__x86_64__", "amd64": "__x86_64__", "aarch64": "__aarch64__",
                     "arm64": "__aarch64__"}[platform.machine().lower()]
generate(GEN, HOST_ARCHITECTURE)
files =sorted(GEN.rglob("*.c"))
includes = generated_includes(GEN)
subprocess.run([
    os.environ.get("CC", "cc"), "-std=c11", "-Wall", "-Wextra", "-Werror",
    "-Wno-unused-function", "-ffunction-sections", "-fdata-sections",
    "-Wl,--gc-sections", "-Wl,--wrap=write", "-pthread", *includes, *map(str, files),
    # Entity's account handoff links its locked Monocypher and liboqs.
    str(ROOT / "build/packages/monocypher/src/monocypher.c"), os.environ["LIBOQS_A"],
    "-o", str(WORK / "test"),
], check=True)
environment = dict(os.environ)
for name in ("DISPLAY", "WAYLAND_DISPLAY", "XAUTHORITY", "GDK_DISPLAY",
             "DBUS_SESSION_BUS_ADDRESS", "SESSION_MANAGER"):
    environment.pop(name, None)
subprocess.run([str(WORK / "test")], env=environment, check=True)

ndk_base = Path(os.environ.get("ANDROID_HOME", str(Path.home() / "Android/Sdk"))) / "ndk"
ndks = sorted(ndk_base.glob("*/toolchains/llvm/prebuilt/linux-x86_64"))
if ndks:
    toolchain = ndks[-1]
    ndk = toolchain.parents[3]
    # Kryon's tests/ziran_android_jni_test.sh checks android_jni's JNI tables
    # and NativeActivity/android_app layouts; these are Inner Breeze's own.
    assertions = [
        '#include <stddef.h>', '#include <pthread.h>', '#define JNI_OnLoad NdkJniOnLoad', '#include <jni.h>', '#undef JNI_OnLoad',
        '#include <android/native_activity.h>', '#include <android_native_app_glue.h>',
        '#include "android_jni.h"', '#include "android_insets.h"', '#include "android_mutex.h"', '#include "android_startup.h"',
        '_Static_assert(sizeof(AndroidPollSource) == sizeof(struct android_poll_source), "poll source size");',
        '_Static_assert(offsetof(AndroidPollSource, process) == offsetof(struct android_poll_source, process), "poll source process");',
        '_Static_assert(sizeof(AndroidMutex) >= sizeof(pthread_mutex_t), "mutex storage");',
        '_Static_assert(_Alignof(AndroidMutex) >= _Alignof(pthread_mutex_t), "mutex alignment");',
        '_Static_assert(sizeof(NativeMethod) == sizeof(JNINativeMethod), "JNI method size");',
    ]
    for target, architecture in (("aarch64-linux-android24", "__aarch64__"),
                                 ("armv7a-linux-androideabi24", "__arm__"),
                                 ("i686-linux-android24", "__i386__"),
                                 ("x86_64-linux-android24", "__x86_64__")):
        abi_output = WORK / architecture / "generated"
        generate(abi_output, architecture)
        command = [str(toolchain / "bin/clang"), "--target=" + target,
                   "-std=c11", "-fsyntax-only", *generated_includes(abi_output),
                   "-I" + str(ndk / "sources/android/native_app_glue")]
        subprocess.run([*command, "-x", "c", "-"], input="\n".join(assertions), text=True, check=True)
        for source in sorted(abi_output.rglob("*.c")):
            subprocess.run([*command, str(source)], check=True)
else:
    print("Android NDK unavailable; native JNI behavior passed, cross ABI checks skipped")
print("Android Zi JNI behavior and available NDK ABI checks passed")
