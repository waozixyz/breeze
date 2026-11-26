#!/usr/bin/env python3
"""Unit test CrashReporter.java without needing an Android device or SDK."""
import os
from pathlib import Path
import subprocess
import tempfile

STUBS = {
    "android/app/ApplicationExitInfo.java": """\
package android.app;
import java.io.InputStream;
public class ApplicationExitInfo {
    public int getReason() { return 0; }
    public int getStatus() { return 0; }
    public long getTimestamp() { return 0L; }
    public String getDescription() { return ""; }
    public InputStream getTraceInputStream() { return null; }
}
""",
    "android/app/ActivityManager.java": """\
package android.app;
import java.util.Collections;
import java.util.List;
public class ActivityManager {
    public List<ApplicationExitInfo> getHistoricalProcessExitReasons(String pkg, int pid, int maxNum) {
        return Collections.emptyList();
    }
}
""",
    "android/content/SharedPreferences.java": """\
package android.content;
public interface SharedPreferences {
    long getLong(String key, long defValue);
    Editor edit();
    interface Editor {
        Editor putLong(String key, long value);
        void apply();
    }
}
""",
    "android/content/Context.java": """\
package android.content;
import java.io.File;
public abstract class Context {
    public static final String ACTIVITY_SERVICE = "activity";
    public static final int MODE_PRIVATE = 0;
    public abstract Context getApplicationContext();
    public abstract File getFilesDir();
    public abstract String getPackageName();
    public abstract Object getSystemService(String name);
    public abstract SharedPreferences getSharedPreferences(String name, int mode);
}
""",
    "android/os/Build.java": """\
package android.os;
public class Build {
    public static String MANUFACTURER = "TestMaker";
    public static String MODEL = "TestModel";
    public static class VERSION {
        public static int SDK_INT = 33;
        public static String RELEASE = "13";
    }
    public static class VERSION_CODES {
        public static final int R = 30;
    }
}
""",
    "android/util/Log.java": """\
package android.util;
public final class Log {
    public static int w(String tag, String msg, Throwable tr) { return 0; }
}
""",
}

root = Path(__file__).resolve().parents[1]
environment = dict(os.environ)
for name in ("DISPLAY", "WAYLAND_DISPLAY", "XAUTHORITY", "GDK_DISPLAY"):
    environment.pop(name, None)

with tempfile.TemporaryDirectory(prefix="inbe-android-crash-") as directory:
    work = Path(directory)
    stub_dir = work / "stubs"
    classes_dir = work / "classes"
    data_dir = work / "data"
    classes_dir.mkdir()
    data_dir.mkdir()
    stub_files = []
    for rel_path, source in STUBS.items():
        path = stub_dir / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source, encoding="utf-8")
        stub_files.append(str(path))
    subprocess.run(
        [
            "javac",
            "-d",
            str(classes_dir),
            *stub_files,
            str(root / "droid/app/src/main/java/xyz/waozi/inbe/CrashReporter.java"),
            str(root / "tests/AndroidCrashReporterTest.java"),
        ],
        check=True,
        env=environment,
    )
    subprocess.run(
        [
            "java",
            "-cp",
            str(classes_dir),
            "xyz.waozi.inbe.AndroidCrashReporterTest",
            str(data_dir),
        ],
        check=True,
        env=environment,
        timeout=20,
    )
