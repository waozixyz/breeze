package xyz.waozi.inbe;

import java.io.File;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.concurrent.atomic.AtomicReference;

public final class AndroidCrashReporterTest {
    private static void require(boolean condition, String message) {
        if (!condition) {
            throw new AssertionError(message);
        }
    }

    private static String readUtf8(File file) throws Exception {
        return new String(Files.readAllBytes(file.toPath()), StandardCharsets.UTF_8);
    }

    private static void testBreadcrumbsRingBuffer() {
        CrashReporter.clearBreadcrumbs();
        for (int i = 0; i < 20; i++) {
            CrashReporter.recordBreadcrumb("event-\n" + i + "\twith-control");
        }
        String snapshot = CrashReporter.snapshotBreadcrumbs();
        String[] lines = snapshot.split("\n");
        require(lines.length == 16, "ring buffer keeps at most 16 breadcrumbs");
        require(!snapshot.contains("event- 0 "), "oldest breadcrumb evicted");
        require(!snapshot.contains("event- 3 "), "first four breadcrumbs evicted");
        require(lines[0].contains("event- 4 with-control"), "fifth breadcrumb is now oldest");
        require(lines[15].contains("event- 19 with-control"), "latest breadcrumb preserved");
        CrashReporter.clearBreadcrumbs();
        require(CrashReporter.snapshotBreadcrumbs().isEmpty(), "clear empties breadcrumbs");
    }

    private static void testUncaughtExceptionWritesPendingAndChainsPrevious(File workDir) throws Exception {
        File dir = new File(workDir, "uncaught");
        CrashReporter.clearBreadcrumbs();
        CrashReporter.recordBreadcrumb("enterPictureWindow:onUserLeaveHint");
        CrashReporter.recordBreadcrumb("onPictureInPictureModeChanged:visible=false,stopped=false");

        AtomicReference<Throwable> chained = new AtomicReference<>();
        Thread.UncaughtExceptionHandler previous = (t, e) -> chained.set(e);
        IllegalStateException error = new IllegalStateException("PiP \"expand\" failed\nwith\\slash");
        Thread worker = new Thread(() -> {}, "pip-main");

        CrashReporter.handleUncaughtException(
            worker,
            error,
            dir,
            "2.1.63",
            200,
            "xyz.waozi.inbe.debug",
            "Android 13 (SDK 33)",
            "Motorola moto e6 play",
            1795000000L,
            previous
        );

        require(chained.get() == error, "previous uncaught exception handler must still run");
        File pending = new File(dir, CrashReporter.PENDING_FILE_NAME);
        require(pending.isFile() && pending.length() > 0, "pending crash file created");
        String json = readUtf8(pending);
        require(json.contains("\"schema\":1"), "schema version present");
        require(json.contains("\"kind\":\"android_java_exception\""), "java exception kind present");
        require(json.contains("\"timestamp\":1795000000"), "timestamp present");
        require(json.contains("\"summary\":\"IllegalStateException: PiP \\\"expand\\\" failed with\\\\slash\""),
            "summary sanitized and JSON-escaped");
        require(json.contains("\"thread\":\"pip-main\""), "thread name recorded");
        require(json.contains("\"version\":\"2.1.63\""), "version recorded");
        require(json.contains("\"version_code\":200"), "version code recorded");
        require(json.contains("\"platform\":\"android\""), "android platform recorded");
        require(json.contains("enterPictureWindow:onUserLeaveHint"), "PiP breadcrumb recorded");
        require(json.contains("onPictureInPictureModeChanged:visible=false,stopped=false"), "PiP return breadcrumb recorded");
        require(json.contains("IllegalStateException"), "stack trace recorded in details");
    }

    private static void testProcessExitReasonsAndDedup(File workDir) throws Exception {
        File dir = new File(workDir, "exit-info");
        // Non-crash reason (e.g. REASON_EXIT_SELF = 1) must not write anything.
        long ts = CrashReporter.recordProcessExitIfNew(
            dir, 1, 0, 1795000100000L, "normal exit", "", 0L,
            "2.1.63", 200, "xyz.waozi.inbe", "Android 13 (SDK 33)", "Moto"
        );
        require(ts == 0L, "non-crash exit reason ignored");
        File pending = new File(dir, CrashReporter.PENDING_FILE_NAME);
        require(!pending.exists(), "non-crash exit creates no pending file");

        // Native crash reason writes a pending report and advances timestamp.
        ts = CrashReporter.recordProcessExitIfNew(
            dir, CrashReporter.REASON_CRASH_NATIVE, 11, 1795000200000L,
            "SIGSEGV in libmain.so", "backtrace:\n  #00 pc 00001234 libmain.so",
            0L, "2.1.63", 200, "xyz.waozi.inbe", "Android 13 (SDK 33)", "Moto"
        );
        require(ts == 1795000200000L, "native crash exit timestamp recorded");
        require(pending.isFile(), "native crash exit writes pending file");
        String json = readUtf8(pending);
        require(json.contains("\"kind\":\"android_native_crash\""), "native crash kind");
        require(json.contains("Native crash: SIGSEGV in libmain.so"), "native crash summary");
        require(json.contains("backtrace:\\n  #00 pc 00001234 libmain.so"), "native trace captured");

        // Duplicate timestamp does not re-write or fail.
        require(pending.delete(), "remove first pending report");
        long sameTs = CrashReporter.recordProcessExitIfNew(
            dir, CrashReporter.REASON_CRASH_NATIVE, 11, 1795000200000L,
            "SIGSEGV in libmain.so", "", ts,
            "2.1.63", 200, "xyz.waozi.inbe", "Android 13 (SDK 33)", "Moto"
        );
        require(sameTs == ts, "already-recorded exit timestamp unchanged");
        require(!pending.exists(), "already-recorded exit does not re-create pending file");

        // Existing richer pending report is never overwritten by historical exit info.
        String richer = "{\"schema\":1,\"kind\":\"android_java_exception\",\"summary\":\"Richer\"}";
        require(CrashReporter.writePendingFile(dir, richer), "write richer report");
        long newerTs = CrashReporter.recordProcessExitIfNew(
            dir, CrashReporter.REASON_ANR, 0, 1795000300000L,
            "Input dispatching timed out", "anr trace", ts,
            "2.1.63", 200, "xyz.waozi.inbe", "Android 13 (SDK 33)", "Moto"
        );
        require(newerTs == 1795000300000L, "timestamp advances past superseded exit");
        require(readUtf8(pending).equals(richer), "existing richer pending report preserved");
    }

    private static void testLocalizedSummaryByteLimit() {
        String message = new String(new char[140]).replace("\0", "界");
        String json = CrashReporter.formatJavaCrashJson(
            Thread.currentThread(), new IllegalStateException(message),
            "2.1.63", 200, "xyz.waozi.inbe", "Android", "Moto", 1L, ""
        );
        int start = json.indexOf("\"summary\":\"") + "\"summary\":\"".length();
        String summary = json.substring(start, json.indexOf('"', start));
        require(summary.getBytes(StandardCharsets.UTF_8).length <= 140,
            "localized summary fits native UTF-8 buffer");
        require(!summary.contains("\ufffd"), "localized summary keeps whole code points");
    }

    public static void main(String[] args) throws Exception {
        File workDir = new File(args[0]);
        testLocalizedSummaryByteLimit();
        testBreadcrumbsRingBuffer();
        testUncaughtExceptionWritesPendingAndChainsPrevious(workDir);
        testProcessExitReasonsAndDedup(workDir);
        System.out.println("Android CrashReporter tests passed");
    }
}
