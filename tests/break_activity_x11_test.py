"""Type into another owned window on the private Xvfb display, sampling Breeze."""
import os
import pathlib
import select
import subprocess
import sys
import time


def main():
    display = os.environ["DISPLAY"]
    number = display.removeprefix(":").split(".")[0]
    # xvfb-run owns this server; also verify its live executable before input.
    lock = pathlib.Path(f"/tmp/.X{number}-lock")
    pid = int(lock.read_text().strip())
    assert pathlib.Path(f"/proc/{pid}/exe").resolve().name == "Xvfb", display
    assert number != "0", "refusing the real desktop display"
    title = f"Breeze typing test {os.getpid()}"
    other = subprocess.Popen(["xmessage", "-title", title, "Private typing target"])
    probe = subprocess.Popen([sys.argv[1]], stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE, text=True, bufsize=1)
    typing = None

    def sample():
        probe.stdin.write("\n")
        probe.stdin.flush()
        assert select.select([probe.stdout], [], [], 5)[0], "probe timed out"
        values = tuple(map(int, probe.stdout.readline().split()))
        assert len(values) == 4 and values[0] >= 0, values
        return values

    try:
        window = subprocess.check_output(
            ["xdotool", "search", "--sync", "--onlyvisible", "--name", title],
            text=True, timeout=10).splitlines()[0]
        subprocess.run(["xdotool", "windowfocus", "--sync", window], check=True)
        time.sleep(1.6)
        idle = sample()
        assert idle[1] == 0 and idle[2] > 0 and idle[3] > 0, idle
        typing = subprocess.Popen(["xdotool", "type", "--delay", "35",
                                   "continuous keyboard activity " * 6])
        # Allow the shared OS sampler's 500 ms cache to refresh.
        time.sleep(0.65)
        samples = 0
        while typing.poll() is None:
            values = sample()
            assert values[1:] == (1, 0, 0), values
            samples += 1
            time.sleep(0.15)
        assert typing.wait() == 0 and samples >= 15, samples
        time.sleep(1.6)
        stopped = sample()
        assert stopped[1] == 0 and stopped[2] > 0 and stopped[3] > 0, stopped
        print(f"Private Xvfb typing: {samples} active samples; both rest meters stayed at 0; idle resumed after typing stopped")
    finally:
        for process in (typing, probe, other):
            if process is not None and process.poll() is None:
                process.terminate()
                process.wait(timeout=5)


if __name__ == "__main__":
    main()
