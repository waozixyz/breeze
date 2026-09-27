#!/usr/bin/env python3
"""Run the Android platform HTTP effects against local HTTP and TLS servers."""
import os
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
environment = dict(os.environ)
for name in ("DISPLAY", "WAYLAND_DISPLAY", "XAUTHORITY", "GDK_DISPLAY"):
    environment.pop(name, None)
with tempfile.TemporaryDirectory(prefix="inbe-android-http-") as directory:
    work = Path(directory)
    keys = work / "server.p12"
    subprocess.run([
        "keytool", "-genkeypair", "-alias", "server", "-keyalg", "RSA",
        "-keysize", "2048", "-validity", "1", "-dname", "CN=localhost",
        "-ext", "SAN=dns:localhost", "-storetype", "PKCS12", "-keystore", str(keys),
        "-storepass", "password", "-keypass", "password", "-noprompt",
    ], check=True, env=environment, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run([
        "javac", "-d", str(work),
        str(root / "droid/app/src/main/java/xyz/waozi/inbe/HttpTransport.java"),
        str(root / "tests/AndroidHttpTransportTest.java"),
    ], check=True, env=environment)
    subprocess.run([
        "java", "-cp", str(work), "xyz.waozi.inbe.AndroidHttpTransportTest", str(keys),
    ], check=True, env=environment, timeout=20)
