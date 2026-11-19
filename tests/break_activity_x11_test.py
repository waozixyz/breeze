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
        assert len(values) == 6 and values[0] >= 0, values
        return values

    def wait_for(predicate, timeout):
        deadline = time.monotonic() + timeout
        while True:
            values = sample()
            if predicate(values):
                return values
            assert time.monotonic() < deadline, values
            time.sleep(0.1)

    def start_typing():
        return subprocess.Popen(["xdotool", "type", "--delay", "45",
                                 "continuous keyboard activity " * 3])

    try:
        window = subprocess.check_output(
            ["xdotool", "search", "--sync", "--onlyvisible", "--name", title],
            text=True, timeout=10).splitlines()[0]
        subprocess.run(["xdotool", "windowfocus", "--sync", window], check=True)
        subprocess.run(["xdotool", "key", "space"], check=True)
        typing = start_typing()
        working = wait_for(lambda values: values[1] == 1 and values[2] >= 2, 5)
        assert working[2] == working[3] and working[4:] == (0, 0), working
        while typing.poll() is None:
            time.sleep(0.1)
            sample()
        assert typing.wait() == 0

        short = wait_for(lambda values: values[0] >= 1500, 3)
        assert short[0] < 4000 and short[1] == 0, short
        assert short[2] >= working[2] and short[2] == short[3] and short[4:] == (0, 0), short
        typing = start_typing()
        returned = wait_for(lambda values: values[1] == 1 and values[2] > short[2], 4)
        assert returned[2] == returned[3] and returned[4:] == (0, 0), returned
        while typing.poll() is None:
            time.sleep(0.1)
            sample()
        assert typing.wait() == 0

        micro = wait_for(lambda values: values[4] == 1, 7)
        assert micro[0] >= 4000 and micro[1] == 0, micro
        assert micro[2] == 0 and micro[3] >= returned[3] and micro[5] == 0, micro
        rest = wait_for(lambda values: values[5] == 1, 4)
        assert rest[0] >= 6000 and rest[1:] == (0, 0, 0, 1, 1), rest
        continued = wait_for(lambda values: values[0] >= 7000, 3)
        assert continued[1:] == rest[1:], continued

        typing = start_typing()
        restarted = wait_for(lambda values: values[1] == 1 and values[2] >= 1, 5)
        assert restarted[2] == restarted[3] and restarted[4:] == (1, 1), restarted
        print("Private Xvfb: typing elsewhere accrued work, short idle preserved it, each full rest reset once, and typing resumed work")
    finally:
        for process in (typing, probe, other):
            if process is not None and process.poll() is None:
                process.terminate()
                process.wait(timeout=5)


if __name__ == "__main__":
    main()
