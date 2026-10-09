"""No network: failed edits are discarded, validation precedes commit."""
import importlib.util
import os
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("publisher", ROOT / "scripts/upload-play-screenshots.py")
publisher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(publisher)


def scenario(commit=False, fail=False, unreviewed=False, video_url=None, video_only=False):
    calls = []
    bodies = []
    preflights = []
    def preflight(*args):
        preflights.append(args)
        if unreviewed:
            raise AssertionError("unreviewed")
    harness = SimpleNamespace(store_preflight=preflight)
    def request(method, url, **kwargs):
        calls.append((method, url))
        bodies.append(kwargs.get("body"))
        if method == "POST" and url.endswith("/edits"):
            return b'{"id":"test-edit"}'
        if fail and url.endswith(":validate"):
            raise SystemExit("simulated HTTP error")
        return b"{}"
    env = dict(PLAY_PACKAGE_NAME="xyz.waozi.inbe", PLAY_SERVICE_ACCOUNT_JSON="unused.json", PLAY_COMMIT="1" if commit else "0", PLAY_LISTING_TEXT="0")
    argv = ["upload"]
    if video_url:
        argv.extend(["--video-url", video_url])
    if video_only:
        argv.append("--video-only")
    with patch.dict(os.environ, env, clear=True), patch.object(sys, "argv", argv), patch.object(publisher, "load_env_file"), patch.object(publisher, "service_account_token", return_value="unused") as token, patch.object(publisher, "http_request", side_effect=request), patch.object(publisher, "list_images", return_value=[]) as images, patch.object(publisher.pathlib.Path, "read_text", return_value='{"files":[]}') as reads, patch.object(publisher.importlib.util, "module_from_spec", return_value=harness), patch.object(publisher.importlib.util, "spec_from_file_location", return_value=SimpleNamespace(loader=SimpleNamespace(exec_module=lambda module: None))):
        try:
            publisher.main()
        except (AssertionError, SystemExit):
            assert fail or unreviewed
        if unreviewed:
            assert not calls and not token.called, "unreviewed input reached authentication/network"
        if video_only:
            assert not preflights and not images.called and not reads.called
        elif not unreviewed:
            assert len(preflights) == 2, "screenshot publishing lost its before/after gates"
        if video_url and not unreviewed:
            index = next(i for i, (method, url) in enumerate(calls) if method == "PATCH" and url.endswith("/listings/en-US"))
            assert bodies[index] == b'{"video": "https://www.youtube.com/watch?v=abcdefghijk"}'
    if fail:
        assert calls[-1] == ("DELETE", publisher.api_url("xyz.waozi.inbe", "/edits/test-edit")), "failed edit survived SystemExit"
        assert not any(url.endswith(":commit") for _, url in calls)
    elif commit:
        validate = next(i for i, (_, url) in enumerate(calls) if url.endswith(":validate"))
        committed = next(i for i, (_, url) in enumerate(calls) if url.endswith(":commit"))
        assert validate < committed
    elif not unreviewed:
        assert calls[-1][0] == "DELETE" and not any(url.endswith(":commit") for _, url in calls)


scenario()
scenario(commit=True)
scenario(commit=True, fail=True)
scenario(unreviewed=True)
scenario(commit=True, video_url="https://youtu.be/abcdefghijk")
scenario(commit=True, video_url="https://www.youtube.com/watch?v=abcdefghijk", video_only=True)
scenario(commit=True, fail=True, video_url="https://youtu.be/abcdefghijk", video_only=True)
for url in ("http://www.youtube.com/watch?v=abcdefghijk", "https://youtube.com.evil.test/watch?v=abcdefghijk", "https://www.youtube.com/watch?v=bad", "https://www.youtube.com/watch?v=abcdefghijk&v=lmnopqrstuv"):
    with patch.dict(os.environ, {}, clear=True), patch.object(sys, "argv", ["upload", "--video-only", "--video-url", url]), patch.object(publisher, "load_env_file"), patch.object(publisher, "service_account_token") as token:
        try:
            publisher.main()
        except ValueError:
            pass
        else:
            raise AssertionError("invalid YouTube URL accepted")
        assert not token.called, "invalid URL reached authentication"
print("PASS Play transaction gates: screenshot review, video-only isolation, URL validation, validate-before-commit and failed-edit cleanup")
