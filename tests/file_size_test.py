"""Files over 1 MB enter Git only when .github/large-files.txt lists them."""
import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("check_file_size", ROOT / "scripts/check-file-size.py")
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)

LARGE = b"\0" * (guard.LIMIT + 1)


class FileSizeTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="inbe-file-size-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.git("init", "-q")
        self.git("config", "user.email", "test@example.invalid")
        self.git("config", "user.name", "Test")
        self.stage({"README.md": b"small\n", guard.ALLOWLIST: b"# shipped\nassets/*.mp4\n"})
        self.git("commit", "-q", "-m", "start")
        self.base = self.git("rev-parse", "HEAD").strip()

    def git(self, *argv):
        return subprocess.run(["git", "-C", str(self.root), *argv], check=True, capture_output=True,
                              text=True).stdout

    def stage(self, files):
        for name, data in files.items():
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            self.git("add", name)

    def oversized(self, mode="staged", since=""):
        return [path for path, _ in guard.oversized(self.root, mode, since)]

    def test_small_and_listed_files_pass(self):
        self.stage({"src/main.zi": b"x" * guard.LIMIT, "assets/practice.mp4": LARGE})
        self.assertEqual(self.oversized(), [])

    def test_large_unlisted_files_are_refused(self):
        self.stage({"design/render.png": LARGE, "assets/practice.png": LARGE})
        self.assertEqual(self.oversized(), ["assets/practice.png", "design/render.png"])

    def test_listing_the_file_in_the_same_commit(self):
        self.stage({"assets/banner.png": LARGE,
                    guard.ALLOWLIST: b"assets/*.mp4\nassets/banner.png\n"})
        self.assertEqual(self.oversized(), [])

    def test_an_unstaged_allowlist_does_not_count(self):
        self.stage({"assets/banner.png": LARGE})
        (self.root / guard.ALLOWLIST).write_text("assets/banner.png\n")
        self.assertEqual(self.oversized(), ["assets/banner.png"])

    def test_changed_files_since_a_commit(self):
        self.stage({"design/render.png": LARGE, "assets/practice.mp4": LARGE})
        self.git("commit", "-q", "-m", "media")
        self.assertEqual(self.oversized("since", self.base), ["design/render.png"])
        self.stage({"docs/notes.md": b"later\n"})
        self.git("commit", "-q", "-m", "docs")
        self.assertEqual(self.oversized("since", "HEAD~1"), [])

    def test_changing_an_existing_large_file(self):
        self.stage({"design/render.png": LARGE})
        self.git("commit", "-q", "--no-verify", "-m", "old render")
        self.stage({"design/render.png": LARGE + b"\1"})
        self.assertEqual(self.oversized(), ["design/render.png"])
        self.assertEqual(self.oversized("tracked"), ["design/render.png"])

    def test_deleting_a_large_file_passes(self):
        self.stage({"design/render.png": LARGE})
        self.git("commit", "-q", "--no-verify", "-m", "old render")
        self.git("rm", "-q", "design/render.png")
        self.assertEqual(self.oversized(), [])


if __name__ == "__main__":
    unittest.main()
