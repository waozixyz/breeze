#!/usr/bin/env python3
"""Measure the USB Moto's debug Breeze app without replacing its profile.

Run through managed desktop_run. Navigate first, or select --app/--practice.
SurfaceFlinger measures native presented frames; gfxinfo is saved separately
because Android's HWUI timings do not measure the native renderer.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import re
import statistics
import struct
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = "xyz.waozi.inbe.debug"
SERIAL = "ZE2223BQZT"
OUTPUT = ROOT / "backup/moto-performance"
spec = importlib.util.spec_from_file_location("phone_check", ROOT / "scripts/phone-check.py")
phone_check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(phone_check)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("label", help="Stable receipt name, such as baseline-whm")
    parser.add_argument("--seconds", type=int, default=30)
    parser.add_argument("--startup-runs", type=int, default=0,
                        help="Cold process launches; preserves app data")
    route = parser.add_mutually_exclusive_group()
    route.add_argument("--app")
    route.add_argument("--practice", type=int)
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z0-9_-]+", args.label):
        parser.error("label must contain only lowercase letters, digits, _ or -")
    if not 5 <= args.seconds <= 1800 or not 0 <= args.startup_runs <= 10:
        parser.error("seconds must be 5..1800 and startup-runs 0..10")
    if args.app and not re.fullmatch(r"[a-z0-9_-]+", args.app):
        parser.error("invalid app name")
    if args.practice is not None and args.practice < 0:
        parser.error("practice must be nonnegative")
    phone = phone_check.Phone("local", SERIAL)
    assert phone.adb("get-state").decode().strip() == "device", "Moto is not ready"
    assert phone.shell("getprop", "ro.product.model").strip() == "moto e6 play"
    assert phone.shell("getprop", "ro.product.cpu.abi").strip() == "armeabi-v7a"
    # Refuse a production package or an install which cannot expose its own stats.
    phone.shell("run-as", PACKAGE, "id")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    prefix = OUTPUT / args.label
    receipt_path = prefix.with_suffix(".json")
    if receipt_path.exists():
        parser.error("receipt already exists; inspect it before choosing a new run label")
    result = {"complete": False, "serial": SERIAL, "package": PACKAGE,
              "label": args.label, "requested_seconds": args.seconds,
              "started_at": time.time(), "startup": [], "telemetry": []}

    def save():
        pending = receipt_path.with_suffix(".json.pending")
        pending.write_text(json.dumps(result, indent=2) + "\n")
        pending.replace(receipt_path)

    save()
    try:
        identity = phone.shell("dumpsys", "package", PACKAGE)
        result["installed"] = [line.strip() for line in identity.splitlines()
                               if "versionCode=" in line or "versionName=" in line]
        apk_paths = phone.shell("pm", "path", PACKAGE).splitlines()
        result["installed_apks"] = []
        for line in apk_paths:
            assert line.startswith("package:"), "Unexpected APK path response"
            apk_path = line.removeprefix("package:")
            digest = phone.shell("sha256sum", apk_path).split()[0]
            assert re.fullmatch(r"[0-9a-f]{64}", digest), "Invalid APK identity"
            result["installed_apks"].append({"path": apk_path, "sha256": digest})
        if args.startup_runs:
            assert not phone.pid(PACKAGE), "App is already running; preserve the existing session"
        for _ in range(args.startup_runs):
            phone.shell("am", "force-stop", PACKAGE)
            started = time.monotonic()
            launch = phone.shell("am", "start", "-W", "-n",
                                 PACKAGE + "/" + phone_check.ACTIVITY)
            assert "Status: ok" in launch, launch
            result["startup"].append({
                "adb_wall_ms": round((time.monotonic() - started) * 1000, 2),
                "activity_times_ms": dict((key, int(value)) for key, value in
                                          re.findall(r"^(ThisTime|TotalTime|WaitTime): (\d+)",
                                                     launch, re.MULTILINE)),
                "note": "Activity timings; native first-paint timing is separate",
            })
            save()
            time.sleep(3)
        if args.app:
            phone.start(PACKAGE, "-a", "xyz.waozi.inbe.action.OPEN_APP",
                        "--es", "app_name", args.app, "-d", "inbe-app://launch/" + args.app)
        elif args.practice is not None:
            phone.start(PACKAGE, "-a", phone_check.START_PRACTICE,
                        "--ei", "practice_id", str(args.practice))
        elif not phone.pid(PACKAGE):
            phone.start(PACKAGE)
        time.sleep(3)
        phone.focused(PACKAGE)
        pid = phone.pid(PACKAGE)
        assert pid.isdecimal(), "Expected one debug app process"
        result["pid"] = int(pid)
        try:
            result["cpu_ticks_per_second"] = int(phone.shell("getconf", "CLK_TCK").strip())
            result["cpu_tick_source"] = "getconf CLK_TCK"
        except (subprocess.SubprocessError, ValueError):
            # Android 9 lacks getconf; AT_CLKTCK is the kernel's clock rate.
            # This phone was verified above as little-endian ARMv7.
            auxiliary = phone.adb("exec-out", "run-as", PACKAGE, "cat", "/proc/" + pid + "/auxv")
            result["cpu_ticks_per_second"] = next(
                (value for tag, value in struct.iter_unpack("<II", auxiliary) if tag == 17), None)
            result["cpu_tick_source"] = "kernel AT_CLKTCK"
        assert result["cpu_ticks_per_second"], "CPU clock rate is unavailable"
        result["thermal_limitations"] = "CPU thermal sysfs is denied to adb on this phone; battery temperature is recorded"
        started = time.monotonic()
        next_sample = 0.0

        def observe():
            nonlocal next_sample
            elapsed = time.monotonic() - started
            if elapsed < next_sample:
                return
            next_sample = elapsed + 5
            assert phone.pid(PACKAGE) == pid, "Debug app exited or restarted"
            sample = {"seconds": round(elapsed, 2)}
            for key, command in (
                ("process_stat", ("run-as", PACKAGE, "cat", "/proc/" + pid + "/stat")),
                ("memory", ("dumpsys", "meminfo", pid)),
                ("battery", ("dumpsys", "battery")),
            ):
                try:
                    text = phone.shell(*command)
                    if key == "process_stat":
                        fields = text.rsplit(")", 1)[1].split()
                        sample["cpu_ticks"] = int(fields[11]) + int(fields[12])
                        sample["rss_pages"] = int(fields[21])
                    elif key == "memory":
                        match = re.search(r"TOTAL PSS:\s*(\d+)|^\s*TOTAL\s+(\d+)",
                                          text, re.MULTILINE)
                        sample["pss_kib"] = int(next(value for value in match.groups() if value)) if match else None
                    else:
                        match = re.search(r"^\s*temperature:\s*(\d+)", text, re.MULTILINE)
                        sample["battery_celsius"] = int(match[1]) / 10 if match else None
                except (subprocess.SubprocessError, ValueError, IndexError) as error:
                    sample[key + "_unavailable"] = type(error).__name__
            result["telemetry"].append(sample)
            save()

        result["presentation"] = phone_check.frame_timing(phone, PACKAGE, args.seconds, observe)
        assert not result["presentation"]["buffer_overrun_possible"], "Sampling was too slow for SurfaceFlinger's frame buffer"
        assert phone.pid(PACKAGE) == pid, "Debug app exited or restarted"
        phone.focused(PACKAGE)
        prefix.with_suffix(".gfxinfo.txt").write_text(phone.shell("dumpsys", "gfxinfo", PACKAGE, "framestats"))
        for key in ("pss_kib", "battery_celsius"):
            values = [sample[key] for sample in result["telemetry"] if sample.get(key) is not None]
            result[key] = {"median": statistics.median(values), "max": max(values)} if values else None
        ticks_per_second = result["cpu_ticks_per_second"]
        if ticks_per_second:
            samples = [sample for sample in result["telemetry"] if "cpu_ticks" in sample]
            cpu = [(right["cpu_ticks"] - left["cpu_ticks"]) * 100 /
                   (ticks_per_second * (right["seconds"] - left["seconds"]))
                   for left, right in zip(samples, samples[1:])
                   if right["seconds"] > left["seconds"]]
            result["cpu_percent_one_core"] = {"median": statistics.median(cpu), "max": max(cpu)} if cpu else None
        result["complete"] = True
        result["finished_at"] = time.time()
        result["limitations"] = ["No assertion of route correctness or audio/reminder behavior",
                                  "Idle-screen frame intervals include intentional frame throttling",
                                  "Telemetry collection adds device work; compare identical settings"]
    except Exception as error:
        result["failure"] = str(error)
        raise
    finally:
        save()
    print(json.dumps({"receipt": str(receipt_path), "presentation": result["presentation"],
                      "pss_kib": result["pss_kib"], "battery_celsius": result["battery_celsius"]}))


if __name__ == "__main__":
    main()
