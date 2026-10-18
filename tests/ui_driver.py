"""Drive Inner Breeze in UI tests through Kryon's test driver.

Start the app with ``driver.environment()`` added to its environment: the app
then reads commands from a private directory after each frame and answers with
its committed widget tree. Widgets are found by label, role, key or focus id
instead of by reading screenshots, and presses, typing and keys go through
the app's own input path, so a slow machine cannot drop them.

    driver = UiDriver(output / "driver")
    app = subprocess.Popen([binary], env={**env, **driver.environment()})
    driver.wait(label="Settings")
    driver.press(label="Settings")
    driver.press(role="text_field", index=0)
    driver.type("Morning walk")
    driver.key("enter")
    assert driver.find(contains="Morning walk")

Every wait has a timeout and reports what the app showed when it expired.
"""

import json
import os
from pathlib import Path
import time


KEYS = {
    "escape": 256, "enter": 257, "tab": 258, "backspace": 259, "insert": 260,
    "delete": 261, "right": 262, "left": 263, "down": 264, "up": 265,
    "page_up": 266, "page_down": 267, "home": 268, "end": 269, "space": 32,
    "left_shift": 340, "left_control": 341,
}


class UiDriverError(AssertionError):
    pass


def escape(value):
    return (str(value).replace("\\", "\\\\").replace("\t", "\\t")
            .replace("\n", "\\n"))


class UiDriver:
    def __init__(self, directory, process=None, log=None):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.process = process
        self.log = Path(log) if log else None
        self.serial = 0
        self.last = {}
        self.reset()

    def environment(self):
        return {"KRYON_TEST_DRIVER": str(self.directory)}

    def attach(self, process, log=None):
        """Follow a newly started app, so a crash fails at once."""
        self.process = process
        if log is not None:
            self.log = Path(log)
        self.reset()

    def reset(self):
        for name in ("command", "command.tmp", "reply", "reply.tmp"):
            try:
                (self.directory / name).unlink()
            except FileNotFoundError:
                pass

    def _failure(self, message):
        detail = message
        if self.process is not None and self.process.poll() is not None:
            detail += f" (the app exited with {self.process.returncode})"
        if self.log is not None and self.log.exists():
            detail += "\n" + self.log.read_text(errors="replace")[-4000:]
        labels = [f'{node["label"]} ({node["kind"]})' for node in self.last.get("nodes", [])
                  if node.get("label") and node.get("visible")]
        if labels:
            detail += "\nVisible labels: " + ", ".join(labels[:80])
        return UiDriverError(detail)

    def send(self, verb, timeout=15, **fields):
        """Send one command and return the app's reply."""
        self.serial += 1
        parts = [str(self.serial), verb]
        for name, value in fields.items():
            if value is None:
                continue
            if isinstance(value, bool):
                value = "1" if value else "0"
            parts.append(f"{name}={escape(value)}")
        reply_path = self.directory / "reply"
        try:
            reply_path.unlink()
        except FileNotFoundError:
            pass
        temporary = self.directory / "command.tmp"
        temporary.write_text("\t".join(parts) + "\n", encoding="utf-8")
        os.replace(temporary, self.directory / "command")
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.process is not None and self.process.poll() is not None:
                raise self._failure(f"{verb}: the app stopped")
            try:
                text = reply_path.read_text(encoding="utf-8")
            except FileNotFoundError:
                time.sleep(0.01)
                continue
            reply = json.loads(text)
            reply_path.unlink()
            if reply.get("serial") != self.serial:
                continue
            if verb == "tree":
                self.last = reply
            return reply
        raise self._failure(f"{verb}: no reply within {timeout} s")

    def tree(self):
        return self.send("tree")["nodes"]

    def find(self, **selector):
        """Every widget matching the selector, in tree order."""
        return self.send("find", **selector)["nodes"]

    def labels(self, visible=True):
        return [node["label"] for node in self.tree()
                if node["label"] and (node["visible"] or not visible)]

    def text(self, visible=True):
        """All labels as one text, for checks on what a screen says."""
        return "\n".join(self.labels(visible))

    def wait(self, timeout=20, visible=True, **selector):
        """The first visible widget matching the selector, once it shows."""
        deadline = time.monotonic() + timeout
        selector["visible"] = visible or None
        while True:
            nodes = self.find(**selector)
            if nodes:
                return nodes[0]
            if time.monotonic() >= deadline:
                self.tree()
                raise self._failure(f"no widget matches {selector} within {timeout} s")
            time.sleep(0.05)

    def wait_gone(self, timeout=20, visible=True, **selector):
        deadline = time.monotonic() + timeout
        while self.find(visible=visible or None, **selector):
            if time.monotonic() >= deadline:
                self.tree()
                raise self._failure(f"{selector} still shows after {timeout} s")
            time.sleep(0.05)

    def wait_idle(self, frames=3, timeout=5, required=False):
        """Wait until the tree stays the same for some frames.

        Screens with a running animation never settle, so by default this
        returns after the timeout either way.
        """
        deadline = time.monotonic() + timeout
        while True:
            reply = self.send("status")
            if reply["stable_frames"] >= frames:
                return True
            if time.monotonic() >= deadline:
                if required:
                    self.tree()
                    raise self._failure(f"the screen did not settle within {timeout} s")
                return False
            time.sleep(0.03)

    def press(self, timeout=20, settle=True, **selector):
        """Press the selector's first visible match with the app's pointer."""
        selector.setdefault("visible", True)
        self.wait(timeout=timeout, **selector)
        if settle:
            self.wait_idle(frames=2, timeout=2)
        reply = self.send("press", **selector)
        if not reply["ok"]:
            self.tree()
            raise self._failure(f"press {selector}: {reply['error']}")
        return reply

    def type(self, text, timeout=20):
        reply = self.send("type", timeout=timeout, text=text)
        if not reply["ok"]:
            self.tree()
            raise self._failure(f"type {text!r}: {reply['error']}")
        return reply

    def key(self, name, control=False, shift=False):
        code = name if isinstance(name, int) else KEYS.get(name)
        if code is None:
            code = ord(name.upper()) if len(name) == 1 else None
        if code is None:
            raise ValueError(f"unknown key {name!r}")
        reply = self.send("key", code=code, control=control or None,
                          shift=shift or None)
        if not reply["ok"]:
            raise self._failure(f"key {name}: {reply['error']}")
        return reply

    def pointer(self, x, y, down=False, wheel=None, wheel_x=None):
        """Hold the app's pointer at x, y for the following frames.

        wheel turns the wheel up (positive) or down; wheel_x is a sideways
        wheel, positive to the right, as a touchpad swipe sends it.
        """
        return self.send("pointer", x=round(x, 1), y=round(y, 1), down=down,
                         wheel=wheel, wheel_x=wheel_x)

    def release_pointer(self):
        return self.send("pointer", real=True)

    def drag(self, start, end, steps=8):
        """Press at start, move to end over some frames, and release there."""
        (x0, y0), (x1, y1) = start, end
        self.pointer(x0, y0)
        self.pointer(x0, y0, down=True)
        for step in range(1, steps + 1):
            self.pointer(x0 + (x1 - x0) * step / steps,
                         y0 + (y1 - y0) * step / steps, down=True)
        self.pointer(x1, y1, down=False)
        self.release_pointer()

    @staticmethod
    def center(node):
        return (node["visible_x"] + node["visible_width"] / 2,
                node["visible_y"] + node["visible_height"] / 2)
