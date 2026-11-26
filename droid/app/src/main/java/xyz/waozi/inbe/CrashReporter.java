package xyz.waozi.inbe;

import android.app.ActivityManager;
import android.app.ApplicationExitInfo;
import android.content.Context;
import android.content.SharedPreferences;
import android.os.Build;
import android.util.Log;
import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.PrintWriter;
import java.io.StringWriter;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.concurrent.atomic.AtomicBoolean;

/**
 * Captures unexpected Android crash diagnostics to a pending file on disk so
 * the next launch can ask the user for explicit confirmation before queueing
 * an error report to the developer.
 */
final class CrashReporter {
    private static final String TAG = "InbeCrash";
    static final String PENDING_FILE_NAME = "crash-report.pending.json";
    private static final String PREFS_NAME = "inbe_crash_reporter";
    private static final String KEY_LAST_EXIT_TIMESTAMP = "last_exit_timestamp";
    private static final int SCHEMA_VERSION = 1;
    private static final int MAX_BREADCRUMBS = 16;
    private static final int MAX_BREADCRUMB_CHARS = 96;
    private static final int MAX_SUMMARY_CHARS = 140;
    private static final int MAX_STACK_CHARS = 6144;
    private static final int MAX_TRACE_BYTES = 4096;

    // Android 11+ ApplicationExitInfo crash reason constants (numeric values
    // match android.app.ApplicationExitInfo so unit tests can exercise them).
    static final int REASON_CRASH = 4;
    static final int REASON_CRASH_NATIVE = 5;
    static final int REASON_ANR = 6;

    private static final Object BREADCRUMB_LOCK = new Object();
    private static final String[] breadcrumbs = new String[MAX_BREADCRUMBS];
    private static int breadcrumbHead;
    private static int breadcrumbCount;

    private static final AtomicBoolean handling = new AtomicBoolean(false);
    private static boolean installed;

    private CrashReporter() {
    }

    static synchronized void install(Context context, String versionName, int versionCode) {
        if (context == null) {
            return;
        }
        Context appContext = context.getApplicationContext();
        File filesDir = appContext.getFilesDir();
        String packageName = appContext.getPackageName();
        String safeVersion = versionName == null ? "" : versionName;
        if (!installed) {
            Thread.UncaughtExceptionHandler previous = Thread.getDefaultUncaughtExceptionHandler();
            Thread.setDefaultUncaughtExceptionHandler((thread, throwable) ->
                handleUncaughtException(
                    thread,
                    throwable,
                    filesDir,
                    safeVersion,
                    versionCode,
                    packageName,
                    systemDescription(),
                    deviceDescription(),
                    System.currentTimeMillis() / 1000L,
                    previous
                )
            );
            installed = true;
        }
        collectProcessExitCrash(appContext, safeVersion, versionCode);
    }

    static void recordBreadcrumb(String event) {
        if (event == null) {
            return;
        }
        String cleaned = sanitizeSingleLine(event, MAX_BREADCRUMB_CHARS);
        if (cleaned.isEmpty()) {
            return;
        }
        String entry = "[" + (System.currentTimeMillis() / 1000L) + "] " + cleaned;
        synchronized (BREADCRUMB_LOCK) {
            int slot = (breadcrumbHead + breadcrumbCount) % MAX_BREADCRUMBS;
            if (breadcrumbCount == MAX_BREADCRUMBS) {
                breadcrumbHead = (breadcrumbHead + 1) % MAX_BREADCRUMBS;
            } else {
                breadcrumbCount++;
            }
            breadcrumbs[slot] = entry;
        }
    }

    static void clearBreadcrumbs() {
        synchronized (BREADCRUMB_LOCK) {
            for (int i = 0; i < MAX_BREADCRUMBS; i++) {
                breadcrumbs[i] = null;
            }
            breadcrumbHead = 0;
            breadcrumbCount = 0;
        }
    }

    static String snapshotBreadcrumbs() {
        StringBuilder out = new StringBuilder();
        synchronized (BREADCRUMB_LOCK) {
            for (int i = 0; i < breadcrumbCount; i++) {
                String entry = breadcrumbs[(breadcrumbHead + i) % MAX_BREADCRUMBS];
                if (entry == null || entry.isEmpty()) {
                    continue;
                }
                if (out.length() > 0) {
                    out.append('\n');
                }
                out.append(entry);
            }
        }
        return out.toString();
    }

    static void handleUncaughtException(
        Thread thread,
        Throwable throwable,
        File filesDir,
        String versionName,
        int versionCode,
        String packageName,
        String system,
        String device,
        long timestampSec,
        Thread.UncaughtExceptionHandler previous
    ) {
        boolean owns = handling.compareAndSet(false, true);
        try {
            if (owns && filesDir != null && throwable != null) {
                String json = formatJavaCrashJson(
                    thread,
                    throwable,
                    versionName,
                    versionCode,
                    packageName,
                    system,
                    device,
                    timestampSec,
                    snapshotBreadcrumbs()
                );
                writePendingFile(filesDir, json);
            }
        } catch (Throwable ignored) {
            // Never interfere with default crash termination.
        } finally {
            if (owns) {
                handling.set(false);
            }
            if (previous != null) {
                previous.uncaughtException(thread, throwable);
            }
        }
    }

    static String formatJavaCrashJson(
        Thread thread,
        Throwable throwable,
        String versionName,
        int versionCode,
        String packageName,
        String system,
        String device,
        long timestampSec,
        String recentBreadcrumbs
    ) {
        String className = throwable == null ? "Throwable" : throwable.getClass().getSimpleName();
        if (className == null || className.isEmpty()) {
            className = throwable.getClass().getName();
        }
        String rawMessage = throwable == null ? null : throwable.getMessage();
        String summary = buildSummary(className, rawMessage);
        String threadName = thread == null ? "unknown" : sanitizeSingleLine(thread.getName(), 64);
        String stack = formatStackTrace(throwable, MAX_STACK_CHARS);

        return buildReportJson(
            "android_java_exception",
            timestampSec,
            summary,
            threadName,
            versionName,
            versionCode,
            packageName,
            system,
            device,
            recentBreadcrumbs,
            stack
        );
    }

    static boolean isCrashExitReason(int reason) {
        return reason == REASON_CRASH || reason == REASON_CRASH_NATIVE || reason == REASON_ANR;
    }

    static String exitReasonKind(int reason) {
        if (reason == REASON_CRASH_NATIVE) {
            return "android_native_crash";
        }
        if (reason == REASON_ANR) {
            return "android_anr";
        }
        return "android_java_crash";
    }

    static String exitReasonLabel(int reason) {
        if (reason == REASON_CRASH_NATIVE) {
            return "Native crash";
        }
        if (reason == REASON_ANR) {
            return "Application Not Responding";
        }
        return "Application crash";
    }

    static long recordProcessExitIfNew(
        File filesDir,
        int reason,
        int status,
        long timestampMs,
        String description,
        String traceText,
        long lastRecordedTimestampMs,
        String versionName,
        int versionCode,
        String packageName,
        String system,
        String device
    ) {
        if (filesDir == null || !isCrashExitReason(reason) || timestampMs <= lastRecordedTimestampMs) {
            return lastRecordedTimestampMs;
        }
        File pending = new File(filesDir, PENDING_FILE_NAME);
        if (pending.isFile() && pending.length() > 0) {
            // A richer report from our uncaught exception or native signal
            // handler is already waiting for the user's decision.
            return timestampMs;
        }
        String label = exitReasonLabel(reason);
        String summaryText = label + " (status=" + status + ")";
        String cleanDesc = sanitizeSingleLine(description, 240);
        if (!cleanDesc.isEmpty()) {
            summaryText = buildSummary(label, cleanDesc);
        }
        StringBuilder details = new StringBuilder();
        details.append("reason=").append(label).append(" (").append(reason).append(")\n");
        details.append("status=").append(status).append('\n');
        if (!cleanDesc.isEmpty()) {
            details.append("description=").append(cleanDesc).append('\n');
        }
        if (traceText != null && !traceText.isEmpty()) {
            String trimmedTrace = sanitizeMultiline(traceText, MAX_TRACE_BYTES);
            if (!trimmedTrace.isEmpty()) {
                details.append("\n").append(trimmedTrace);
            }
        }
        String json = buildReportJson(
            exitReasonKind(reason),
            timestampMs / 1000L,
            summaryText,
            "",
            versionName,
            versionCode,
            packageName,
            system,
            device,
            "",
            details.toString()
        );
        if (writePendingFile(filesDir, json)) {
            return timestampMs;
        }
        return lastRecordedTimestampMs;
    }

    private static void collectProcessExitCrash(Context context, String versionName, int versionCode) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.R) {
            return;
        }
        try {
            ActivityManager manager = (ActivityManager)context.getSystemService(Context.ACTIVITY_SERVICE);
            if (manager == null) {
                return;
            }
            List<ApplicationExitInfo> exits = manager.getHistoricalProcessExitReasons(context.getPackageName(), 0, 5);
            if (exits == null || exits.isEmpty()) {
                return;
            }
            SharedPreferences prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE);
            long lastRecorded = prefs.getLong(KEY_LAST_EXIT_TIMESTAMP, 0L);
            for (ApplicationExitInfo info : exits) {
                if (info == null || !isCrashExitReason(info.getReason())) {
                    continue;
                }
                long timestamp = info.getTimestamp();
                if (timestamp <= lastRecorded) {
                    break;
                }
                String trace = readBoundedTrace(info);
                long updated = recordProcessExitIfNew(
                    context.getFilesDir(),
                    info.getReason(),
                    info.getStatus(),
                    timestamp,
                    info.getDescription(),
                    trace,
                    lastRecorded,
                    versionName,
                    versionCode,
                    context.getPackageName(),
                    systemDescription(),
                    deviceDescription()
                );
                if (updated > lastRecorded) {
                    prefs.edit().putLong(KEY_LAST_EXIT_TIMESTAMP, updated).apply();
                }
                break;
            }
        } catch (Throwable error) {
            Log.w(TAG, "Could not inspect historical process exits", error);
        }
    }

    private static String readBoundedTrace(ApplicationExitInfo info) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.R || info == null) {
            return "";
        }
        try (InputStream stream = info.getTraceInputStream()) {
            if (stream == null) {
                return "";
            }
            ByteArrayOutputStream out = new ByteArrayOutputStream();
            byte[] chunk = new byte[1024];
            int remaining = MAX_TRACE_BYTES;
            while (remaining > 0) {
                int read = stream.read(chunk, 0, Math.min(chunk.length, remaining));
                if (read <= 0) {
                    break;
                }
                out.write(chunk, 0, read);
                remaining -= read;
            }
            return new String(out.toByteArray(), StandardCharsets.UTF_8);
        } catch (Throwable ignored) {
            return "";
        }
    }

    static boolean writePendingFile(File filesDir, String json) {
        if (filesDir == null || json == null || json.isEmpty()) {
            return false;
        }
        if (!filesDir.exists() && !filesDir.mkdirs()) {
            return false;
        }
        byte[] bytes = json.getBytes(StandardCharsets.UTF_8);
        File target = new File(filesDir, PENDING_FILE_NAME);
        File temporary = new File(filesDir, PENDING_FILE_NAME + ".tmp");
        try (FileOutputStream output = new FileOutputStream(temporary)) {
            output.write(bytes);
            output.getFD().sync();
        } catch (IOException error) {
            temporary.delete();
            return writeDirectFallback(target, bytes);
        }
        if (temporary.renameTo(target)) {
            return true;
        }
        temporary.delete();
        return writeDirectFallback(target, bytes);
    }

    private static boolean writeDirectFallback(File target, byte[] bytes) {
        try (FileOutputStream output = new FileOutputStream(target)) {
            output.write(bytes);
            output.getFD().sync();
            return true;
        } catch (IOException ignored) {
            return false;
        }
    }

    private static String buildReportJson(
        String kind,
        long timestampSec,
        String summary,
        String threadName,
        String versionName,
        int versionCode,
        String packageName,
        String system,
        String device,
        String recentBreadcrumbs,
        String details
    ) {
        StringBuilder out = new StringBuilder(1024);
        out.append("{\"schema\":").append(SCHEMA_VERSION);
        out.append(",\"kind\":");
        appendJsonString(out, kind);
        out.append(",\"timestamp\":").append(Math.max(0L, timestampSec));
        out.append(",\"summary\":");
        appendJsonString(out, sanitizeSingleLine(summary, MAX_SUMMARY_CHARS));
        if (threadName != null && !threadName.isEmpty()) {
            out.append(",\"thread\":");
            appendJsonString(out, sanitizeSingleLine(threadName, 64));
        }
        out.append(",\"version\":");
        appendJsonString(out, sanitizeSingleLine(versionName, 32));
        out.append(",\"version_code\":").append(Math.max(0, versionCode));
        out.append(",\"platform\":\"android\"");
        out.append(",\"system\":");
        appendJsonString(out, sanitizeSingleLine(system, 120));
        out.append(",\"device\":");
        appendJsonString(out, sanitizeSingleLine(device, 150));
        out.append(",\"package\":");
        appendJsonString(out, sanitizeSingleLine(packageName, 90));
        if (recentBreadcrumbs != null && !recentBreadcrumbs.isEmpty()) {
            out.append(",\"breadcrumbs\":");
            appendJsonString(out, sanitizeMultiline(recentBreadcrumbs, 1800));
        }
        if (details != null && !details.isEmpty()) {
            out.append(",\"details\":");
            appendJsonString(out, sanitizeMultiline(details, MAX_STACK_CHARS));
        }
        out.append('}');
        return out.toString();
    }

    private static String buildSummary(String prefix, String detail) {
        String cleanPrefix = sanitizeSingleLine(prefix, 80);
        String cleanDetail = sanitizeSingleLine(detail, MAX_SUMMARY_CHARS);
        if (cleanPrefix.isEmpty()) {
            return cleanDetail.isEmpty() ? "Unexpected crash" : cleanDetail;
        }
        if (cleanDetail.isEmpty()) {
            return cleanPrefix;
        }
        String combined = cleanPrefix + ": " + cleanDetail;
        return truncate(combined, MAX_SUMMARY_CHARS);
    }

    private static String formatStackTrace(Throwable throwable, int maxChars) {
        if (throwable == null) {
            return "";
        }
        StringWriter writer = new StringWriter();
        PrintWriter printer = new PrintWriter(writer);
        throwable.printStackTrace(printer);
        printer.flush();
        return sanitizeMultiline(writer.toString(), maxChars);
    }

    private static String systemDescription() {
        String release = Build.VERSION.RELEASE == null ? "" : Build.VERSION.RELEASE;
        return "Android " + release + " (SDK " + Build.VERSION.SDK_INT + ")";
    }

    private static String deviceDescription() {
        String maker = Build.MANUFACTURER == null ? "" : Build.MANUFACTURER.trim();
        String model = Build.MODEL == null ? "" : Build.MODEL.trim();
        if (maker.isEmpty()) {
            return model;
        }
        if (model.isEmpty()) {
            return maker;
        }
        if (model.toLowerCase(java.util.Locale.US).startsWith(maker.toLowerCase(java.util.Locale.US))) {
            return model;
        }
        return maker + " " + model;
    }

    private static String sanitizeSingleLine(String text, int maxChars) {
        if (text == null || text.isEmpty() || maxChars <= 0) {
            return "";
        }
        StringBuilder out = new StringBuilder(Math.min(text.length(), maxChars));
        boolean lastSpace = false;
        for (int i = 0; i < text.length() && out.length() < maxChars; i++) {
            char ch = text.charAt(i);
            if (ch < 32 || ch == 127) {
                if (!lastSpace && out.length() > 0) {
                    out.append(' ');
                    lastSpace = true;
                }
                continue;
            }
            out.append(ch);
            lastSpace = (ch == ' ');
        }
        return truncate(out.toString().trim(), maxChars);
    }

    private static String sanitizeMultiline(String text, int maxChars) {
        if (text == null || text.isEmpty() || maxChars <= 0) {
            return "";
        }
        StringBuilder out = new StringBuilder(Math.min(text.length(), maxChars));
        for (int i = 0; i < text.length() && out.length() < maxChars; i++) {
            char ch = text.charAt(i);
            if (ch == '\r') {
                continue;
            }
            if (ch == '\n' || ch == '\t' || (ch >= 32 && ch != 127)) {
                out.append(ch);
            }
        }
        return truncate(out.toString().trim(), maxChars);
    }

    // The native reader has fixed UTF-8 byte buffers, not UTF-16 character
    // buffers. Keep localized diagnostics within those limits without splitting
    // a surrogate pair or a UTF-8 sequence.
    private static String truncate(String text, int maxChars) {
        if (text == null || maxChars <= 0) {
            return "";
        }
        int end = 0;
        int bytes = 0;
        while (end < text.length()) {
            int point = text.codePointAt(end);
            int width = point <= 0x7f ? 1 : point <= 0x7ff ? 2 : point <= 0xffff ? 3 : 4;
            if (bytes + width > maxChars) {
                break;
            }
            bytes += width;
            end += Character.charCount(point);
        }
        return text.substring(0, end);
    }

    static void appendJsonString(StringBuilder out, String value) {
        out.append('"');
        if (value != null) {
            for (int i = 0; i < value.length(); i++) {
                char ch = value.charAt(i);
                switch (ch) {
                    case '"':
                        out.append("\\\"");
                        break;
                    case '\\':
                        out.append("\\\\");
                        break;
                    case '\b':
                        out.append("\\b");
                        break;
                    case '\f':
                        out.append("\\f");
                        break;
                    case '\n':
                        out.append("\\n");
                        break;
                    case '\r':
                        out.append("\\r");
                        break;
                    case '\t':
                        out.append("\\t");
                        break;
                    default:
                        if (ch < 32) {
                            out.append(String.format(java.util.Locale.US, "\\u%04x", (int)ch));
                        } else {
                            out.append(ch);
                        }
                        break;
                }
            }
        }
        out.append('"');
    }
}
