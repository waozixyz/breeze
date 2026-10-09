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


def scenario(commit=False, fail=False, unreviewed=False):
    calls = []
    def preflight(*args):
        if unreviewed:
            raise AssertionError("unreviewed")
    harness = SimpleNamespace(store_preflight=preflight)
    def request(method, url, **kwargs):
        calls.append((method, url))
        if method == "POST" and url.endswith("/edits"):
            return b'{"id":"test-edit"}'
        if fail and url.endswith(":validate"):
            raise SystemExit("simulated HTTP error")
        return b"{}"
    env = dict(PLAY_PACKAGE_NAME="xyz.waozi.inbe", PLAY_SERVICE_ACCOUNT_JSON="unused.json", PLAY_COMMIT="1" if commit else "0", PLAY_LISTING_TEXT="0")
    with patch.dict(os.environ, env, clear=True), patch.object(sys, "argv", ["upload"]), patch.object(publisher, "load_env_file"), patch.object(publisher, "service_account_token", return_value="unused") as token, patch.object(publisher, "http_request", side_effect=request), patch.object(publisher, "list_images", return_value=[]), patch.object(publisher.pathlib.Path, "read_text", return_value='{"files":[]}'), patch.object(publisher.importlib.util, "module_from_spec", return_value=harness), patch.object(publisher.importlib.util, "spec_from_file_location", return_value=SimpleNamespace(loader=SimpleNamespace(exec_module=lambda module: None))):
        try:
            publisher.main()
        except (AssertionError, SystemExit):
            assert fail or unreviewed
        if unreviewed:
            assert not calls and not token.called, "unreviewed input reached authentication/network"
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
print("PASS Play transaction gates: preflight, validate-only, validate-before-commit and failed-edit cleanup")
