"""Concurrency must retain every suite, failures and immutable artifacts."""
import argparse
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import threading
import time
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("visual_gate", ROOT / "tests/visual_test.py")
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


class VisualRunnerTest(unittest.TestCase):
    def test_parallel_suites_keep_failures_and_run_timing_alone(self):
        lock = threading.Lock()
        first_pair = threading.Barrier(2)
        active = set()
        peak = 0
        completed = []
        targets = ["first", "failure", "tab-switch-performance-test", "last", "after"]

        def execute(target):
            nonlocal peak
            with lock:
                if target in gate.EXCLUSIVE_TARGETS:
                    self.assertFalse(active)
                else:
                    self.assertFalse(active & gate.EXCLUSIVE_TARGETS)
                active.add(target)
                peak = max(peak, len(active))
            if target in targets[:2]:
                first_pair.wait(timeout=3)
            time.sleep(.03)
            with lock:
                active.remove(target)
            return {"suite": target, "status": "failed" if target == "failure" else "passed"}

        gate.run_suites(targets, 2, execute, completed.append)
        self.assertEqual(peak, 2)
        self.assertEqual({check["suite"] for check in completed}, set(targets))
        self.assertEqual(len(completed), len(targets))
        self.assertEqual([check for check in completed if check["status"] == "failed"],
                         [{"suite": "failure", "status": "failed"}])
        self.assertEqual(completed[-1]["suite"], "tab-switch-performance-test")

    def test_default_jobs_use_spare_processors_within_bounds(self):
        for processors, jobs in ((1, 2), (2, 2), (4, 3), (5, 4), (32, 4)):
            with mock.patch.object(gate.os, "sched_getaffinity", return_value=set(range(processors))):
                self.assertEqual(gate.default_jobs(), jobs)

    def test_interrupted_scheduling_cancels_its_children(self):
        cancelled = []

        def execute(target):
            raise RuntimeError("owned child failed to start")

        with self.assertRaisesRegex(RuntimeError, "failed to start"):
            gate.run_suites(["broken", "later"], 1, execute, lambda _: None,
                            lambda: cancelled.append(True))
        self.assertEqual(cancelled, [True])

    def test_real_children_scrub_displays_and_keep_shared_artifacts(self):
        with tempfile.TemporaryDirectory(prefix="inbe-visual-runner-") as temporary:
            root = Path(temporary)
            output = root / "build/visual-test"
            output.mkdir(parents=True)
            binary = root / "build/app"
            paths = [binary, root / "ziran.lock", root / "build/inbe.zib", root / "build/inbe-full.zib"]
            for path in paths:
                path.write_text("immutable\n")
            child = root / "child.py"
            child.write_text(
                "import json,os,sys\nfrom pathlib import Path\n"
                "Path(sys.argv[-1]+'.json').write_text(json.dumps({k:os.environ.get(k) "
                "for k in ('DISPLAY','WAYLAND_DISPLAY','XAUTHORITY','DBUS_SESSION_BUS_ADDRESS',"
                "'SESSION_MANAGER','GDK_DISPLAY','YUE_DESKTOP_RECOVERY')}))\n"
                "sys.exit(2 if sys.argv[-1]=='failure' else 0)\n")
            actual_popen = subprocess.Popen

            def popen(command, **kwargs):
                self.assertTrue(all("--old-file=" + str(path.relative_to(root)) in command
                                    for path in paths if path.name != "ziran.lock"))
                return actual_popen([os.sys.executable, str(child), command[-1]], **kwargs)

            arguments = argparse.Namespace(binary=binary, targets=["failure", "later"], jobs=2)
            with mock.patch.object(gate, "ROOT", root), mock.patch.object(gate, "OUTPUT", output), \
                    mock.patch.object(gate, "source_hash", return_value="same-source"), \
                    mock.patch.object(gate.subprocess, "check_output", side_effect=["source\n", "2.1.42\n"]), \
                    mock.patch.object(gate.subprocess, "Popen", side_effect=popen), \
                    mock.patch.dict(os.environ, {key: "foreign-display" for key in gate.DISPLAY_KEYS}), \
                    contextlib.redirect_stdout(io.StringIO()):
                with self.assertRaisesRegex(AssertionError, "Visual suites failed: failure"):
                    gate.run(arguments)
            receipt = json.loads((output / "results.json").read_text())
            self.assertEqual(receipt["status"], "failed")
            self.assertEqual([check["suite"] for check in receipt["checks"]], arguments.targets)
            self.assertEqual([check["exit_code"] for check in receipt["checks"]], [2, 0])
            for target in arguments.targets:
                environment = json.loads((root / (target + ".json")).read_text())
                self.assertTrue(all(environment[key] is None for key in gate.DISPLAY_KEYS))
                self.assertEqual(environment["YUE_DESKTOP_RECOVERY"], "0")
            for path in paths:
                self.assertEqual(path.read_text(), "immutable\n")


if __name__ == "__main__":
    unittest.main()
