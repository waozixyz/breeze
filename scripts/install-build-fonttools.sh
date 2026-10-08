#!/bin/sh
# Isolated package builders need fontTools for the required shipped-font gate.
set -eu

destination=${1:?Usage: install-build-fonttools.sh destination}
python3 - "$destination" <<'PY'
import hashlib
import io
from pathlib import Path
import sys
import urllib.request
import zipfile

url = "https://files.pythonhosted.org/packages/c7/93/0dd45cd283c32dea1545151d8c3637b4b8c53cdb3a625aeb2885b184d74d/fonttools-4.60.1-py3-none-any.whl"
expected = "906306ac7afe2156fcf0042173d6ebbb05416af70f6b370967b47f8f00103bbb"
with urllib.request.urlopen(url, timeout=60) as response:
    wheel = response.read()
if hashlib.sha256(wheel).hexdigest() != expected:
    raise SystemExit("fontTools build dependency checksum mismatch")
destination = Path(sys.argv[1])
destination.mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(io.BytesIO(wheel)) as archive:
    archive.extractall(destination)
PY
