"""Run the complete visual gate against unchanged release artifacts."""

import argparse
from concurrent.futures import ALL_COMPLETED, FIRST_COMPLETED, ThreadPoolExecutor, wait
import contextlib
import fcntl
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import threading
import time


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "build/visual-test"
DISPLAY_KEYS = ("DISPLAY", "WAYLAND_DISPLAY", "XAUTHORITY", "GDK_DISPLAY",
                "DBUS_SESSION_BUS_ADDRESS", "SESSION_MANAGER")
# Timing measurements need the runner to themselves; other suites own
# separate displays, profiles and evidence directories.
EXCLUSIVE_TARGETS = {"tab-switch-performance-test"}


def default_jobs():
    """Leave one processor for the shared build and display work, using at most four."""
    processors = len(os.sched_getaffinity(0))
    return max(2, min(4, processors - 1))


def artifacts(binary):
    paths = [binary, ROOT / "ziran.lock", ROOT / "build/inbe.zx",
             ROOT / "build/inbe-full.zx", *sorted((ROOT / "build/cells").glob("*.zx")),
             *sorted((ROOT / "build/node-apps").glob("*.zx"))]
    return {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in paths}


def source_hash():
    paths = subprocess.check_output([
        "git", "ls-files", "-z", "--cached", "--others", "--exclude-standard", "--",
        "src", "apps", "assets/styles", "locales", "tests", "scripts", ".github",
        "Makefile", "mk", "ziran.toml", "ziran.lock",
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
    parser.add_argument("--jobs", type=int, default=int(os.environ.get("VISUAL_TEST_JOBS", default_jobs())))
    arguments = parser.parse_args()
    if arguments.jobs < 1:
        parser.error("--jobs must be positive")
    assert len(set(arguments.targets)) == len(arguments.targets), "Duplicate visual suites"
    assert "visual-test" not in arguments.targets, "Visual gate cannot invoke itself"
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with (OUTPUT / "lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        run(arguments)


def run_suites(targets, jobs, execute, complete, cancel=lambda: None):
    """Bound concurrent UI processes and leave timing suites uncontended.

    Timing suites run alone after every other suite, so waiting for them
    never idles the other workers in the middle of the gate.
    """
    with ThreadPoolExecutor(max_workers=jobs) as pool:
        pending = set()

        def collect(all_pending=False):
            if not pending:
                return
            finished, _ = wait(pending, return_when=ALL_COMPLETED if all_pending else FIRST_COMPLETED)
            for future in finished:
                pending.remove(future)
                complete(future.result())

        try:
            for target in targets:
                if target in EXCLUSIVE_TARGETS:
                    continue
                pending.add(pool.submit(execute, target))
                if len(pending) >= jobs:
                    collect()
            collect(all_pending=True)
            for target in targets:
                if target in EXCLUSIVE_TARGETS:
                    complete(execute(target))
        except BaseException:
            cancel()
            for future in pending:
                future.cancel()
            raise


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
        "jobs": arguments.jobs,
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
    completed = {}
    children = set()
    children_lock = threading.Lock()
    cancelled = threading.Event()
    # The parent make has prepared these artifacts once. Child makes may
    # compile their own fixtures but cannot rebuild shared release outputs.
    prepared = ["--old-file=" + path for path in receipt["artifacts"] if path != "ziran.lock"]

    def terminate(process):
        with contextlib.suppress(ProcessLookupError):
            os.killpg(process.pid, signal.SIGTERM)
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            with contextlib.suppress(ProcessLookupError):
                os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=5)

    def execute(target):
        print(f"Visual gate: {target}", flush=True)
        started = time.monotonic()
        log_path = OUTPUT / (target + ".log")
        timed_out = False
        status = -1
        with log_path.open("w") as log:
            with children_lock:
                if cancelled.is_set():
                    raise RuntimeError("Visual gate was interrupted")
                process = subprocess.Popen(["make", "--no-print-directory", *prepared, target], cwd=ROOT,
                                           env=environment, stdout=log, stderr=subprocess.STDOUT,
                                           start_new_session=True)
                children.add(process)
            try:
                try:
                    status = process.wait(timeout=900)
                except subprocess.TimeoutExpired:
                    timed_out = True
                    terminate(process)
                    status = process.returncode
            finally:
                with children_lock:
                    children.discard(process)
        return {"suite": target, "status": "passed" if status == 0 else "failed",
                "exit_code": status, "timed_out": timed_out,
                "seconds": round(time.monotonic() - started, 2),
                "log": str(log_path.relative_to(ROOT))}

    def complete(check):
        completed[check["suite"]] = check
        checks[:] = [completed[target] for target in arguments.targets if target in completed]
        save()
        print(f"Visual gate: {check['suite']} {check['status']}", flush=True)
        if check["status"] != "passed":
            print("\n".join((ROOT / check["log"]).read_text().splitlines()[-20:]), flush=True)

    def cancel():
        cancelled.set()
        with children_lock:
            active = list(children)
        for process in active:
            terminate(process)

    try:
        run_suites(arguments.targets, arguments.jobs, execute, complete, cancel)
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
