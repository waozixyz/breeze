"""Run the complete visual gate against unchanged release artifacts."""

import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "build/visual-test"
DISPLAY_KEYS = ("DISPLAY", "WAYLAND_DISPLAY", "XAUTHORITY", "GDK_DISPLAY",
                "DBUS_SESSION_BUS_ADDRESS", "SESSION_MANAGER")


def artifacts(binary):
    paths = [binary, ROOT / "ziran.lock", ROOT / "build/inbe.zib",
             ROOT / "build/inbe-full.zib", *sorted((ROOT / "build/cells").glob("*.zib"))]
    return {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in paths}


def source_hash():
    paths = subprocess.check_output([
        "git", "ls-files", "-z", "--cached", "--others", "--exclude-standard", "--",
        "src", "apps", "assets/styles", "locales", "tests", "scripts", ".github",
        "Makefile", "ziran.toml", "ziran.lock",
    ], cwd=ROOT).split(b"\0")
    digest = hashlib.sha256()
    for name in sorted(set(paths) - {b""}):
        path = ROOT / os.fsdecode(name)
        digest.update(name + b"\0")
        digest.update(path.read_bytes())
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("binary", type=Path)
    parser.add_argument("targets", nargs="+")
    arguments = parser.parse_args()
    assert len(set(arguments.targets)) == len(arguments.targets), "Duplicate visual suites"
    assert "visual-test" not in arguments.targets, "Visual gate cannot invoke itself"
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with (OUTPUT / "lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        run(arguments)


def run(arguments):
    environment = {key: value for key, value in os.environ.items() if key not in DISPLAY_KEYS}
    environment["YUE_DESKTOP_RECOVERY"] = "0"
    checks = []
    receipt = {
        "status": "running",
        "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT,
                                                   text=True).strip(),
        "version": subprocess.check_output(["python3", "scripts/check-version.py", "--print-version"],
                                             cwd=ROOT, text=True).strip(),
        "expected_suites": arguments.targets,
        "source_sha256": source_hash(),
        "artifacts": artifacts(arguments.binary.resolve()),
        "checks": checks,
    }
    result_path = OUTPUT / "results.json"

    def save():
        temporary = result_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(receipt, indent=2) + "\n")
        temporary.replace(result_path)

    save()
    try:
        for target in arguments.targets:
            print(f"Visual gate: {target}", flush=True)
            started = time.monotonic()
            log_path = OUTPUT / (target + ".log")
            timed_out = False
            with log_path.open("w") as log:
                process = subprocess.Popen(["make", "--no-print-directory", target], cwd=ROOT,
                                           env=environment, stdout=log, stderr=subprocess.STDOUT,
                                           start_new_session=True)
                try:
                    status = process.wait(timeout=900)
                except subprocess.TimeoutExpired:
                    timed_out = True
                    os.killpg(process.pid, signal.SIGTERM)
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        os.killpg(process.pid, signal.SIGKILL)
                        process.wait(timeout=5)
                    status = process.returncode
            checks.append({"suite": target, "status": "passed" if status == 0 else "failed",
                           "exit_code": status, "timed_out": timed_out,
                           "seconds": round(time.monotonic() - started, 2),
                           "log": str(log_path.relative_to(ROOT))})
            save()
            print(f"Visual gate: {target} {checks[-1]['status']}", flush=True)
            if status != 0:
                print("\n".join(log_path.read_text().splitlines()[-20:]), flush=True)
        assert artifacts(arguments.binary.resolve()) == receipt["artifacts"], \
            "Release artifacts changed while the visual gate was running"
        assert source_hash() == receipt["source_sha256"], \
            "Source or tests changed while the visual gate was running"
        failed = [check["suite"] for check in checks if check["status"] != "passed"]
        assert not failed, "Visual suites failed: " + ", ".join(failed)
        assert [check["suite"] for check in checks] == arguments.targets, "Incomplete visual gate"
        receipt["status"] = "passed"
    except BaseException as error:
        receipt["status"] = "failed"
        receipt["error"] = str(error)
        raise
    finally:
        save()
    print(f"Visual gate: all {len(checks)} suites passed on unchanged release artifacts", flush=True)


if __name__ == "__main__":
    main()
