package xyz.waozi.inbe;

import android.app.Activity;
import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageInfo;
import android.content.pm.PackageInstaller;
import android.content.pm.PackageManager;
import android.content.pm.Signature;
import android.os.Build;
import android.util.Log;
import org.json.JSONObject;
import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.Arrays;
import java.util.HashSet;
import java.util.Locale;
import java.util.Set;

/** APKs installed straight from the GitHub release update themselves: once a
 * day the release feed is read in the background and a newer APK for this
 * device is downloaded and verified. The next start offers it through
 * Android's own installer. Store builds (Google Play, F-Droid) leave this
 * off with BuildConfig.SELF_UPDATE and keep updating through their store. */
final class AppUpdate {
    private static final String TAG = "InbeUpdate";
    private static final long CHECK_INTERVAL_MS = 24L * 60 * 60 * 1000;
    private static final long OFFER_INTERVAL_MS = 24L * 60 * 60 * 1000;
    private static final long FEED_LIMIT = 65536;
    private static final long APK_LIMIT = 256L * 1024 * 1024;
    private static final Object LOCK = new Object();

    private AppUpdate() {}

    static SharedPreferences preferences(Context context) {
        return context.getSharedPreferences("app-updates", Context.MODE_PRIVATE);
    }

    /** Offers a verified update from an earlier start, or checks for one. A
     * start that opens a practice is never interrupted. */
    static void onStart(Activity activity, boolean practice) {
        if (!BuildConfig.SELF_UPDATE || BuildConfig.UPDATE_FEED.isEmpty()) {
            return;
        }
        Context context = activity.getApplicationContext();
        SharedPreferences preferences = preferences(context);
        long now = System.currentTimeMillis();
        File ready = readyUpdate(context);
        if (ready != null) {
            if (!practice && now - preferences.getLong("offered_at", 0) >= OFFER_INTERVAL_MS) {
                preferences.edit().putLong("offered_at", now).apply();
                new Thread(() -> install(context, ready), "inbe-update-install").start();
            }
            return;
        }
        if (now - preferences.getLong("checked_at", 0) < CHECK_INTERVAL_MS) {
            return;
        }
        preferences.edit().putLong("checked_at", now).apply();
        new Thread(() -> {
            try {
                check(context);
            } catch (Exception error) {
                Log.w(TAG, "Update check failed", error);
            }
        }, "inbe-update-check").start();
    }

    /** Release versions are numeric x.y.z; a missing part counts as zero. */
    static boolean newer(String candidate, String installed) {
        String[] left = candidate.split("\\.");
        String[] right = installed.split("\\.");
        for (int index = 0; index < Math.max(left.length, right.length); index++) {
            long a = index < left.length ? parsePart(left[index]) : 0;
            long b = index < right.length ? parsePart(right[index]) : 0;
            if (a < 0 || b < 0) {
                return false;
            }
            if (a != b) {
                return a > b;
            }
        }
        return false;
    }

    private static long parsePart(String part) {
        if (part.isEmpty() || part.length() > 9 || !part.matches("[0-9]+")) {
            return -1;
        }
        return Long.parseLong(part);
    }

    /** The APK built for this device's preferred ABI, else the universal one. */
    static JSONObject channel(JSONObject channels, String[] abis) {
        for (String abi : abis) {
            JSONObject entry = channels.optJSONObject("android-" + abi);
            if (entry != null) {
                return entry;
            }
        }
        return channels.optJSONObject("android");
    }

    private static void check(Context context) throws Exception {
        JSONObject feed = new JSONObject(new String(fetch(BuildConfig.UPDATE_FEED, FEED_LIMIT, null),
                StandardCharsets.UTF_8));
        String version = feed.getString("version");
        PackageInfo installed = context.getPackageManager().getPackageInfo(context.getPackageName(), 0);
        if (installed.versionName == null || !newer(version, installed.versionName)) {
            return;
        }
        JSONObject entry = channel(feed.getJSONObject("channels"), Build.SUPPORTED_ABIS);
        if (entry == null) {
            return;
        }
        String hash = entry.getString("sha256");
        long size = entry.getLong("size");
        String url = entry.getString("url");
        if (!hash.matches("[0-9a-f]{64}") || size <= 0 || size > APK_LIMIT ||
                !(url.startsWith("https://") || (BuildConfig.DEBUG && url.startsWith("http://")))) {
            throw new IOException("Invalid release feed entry");
        }
        File directory = directory(context);
        if (size > directory.getUsableSpace()) {
            throw new IOException("Not enough space for the update");
        }
        File apk = new File(directory, hash + ".apk");
        File part = new File(directory, hash + ".part");
        synchronized (LOCK) {
            try (OutputStream output = new FileOutputStream(part)) {
                fetch(url, size, output);
            }
            if (part.length() != size || !hash.equals(sha256(part))) {
                part.delete();
                throw new IOException("The downloaded APK differs from the release feed");
            }
            long code;
            try {
                code = verify(context, part);
            } catch (Exception error) {
                part.delete();
                throw error;
            }
            if (!part.renameTo(apk)) {
                part.delete();
                throw new IOException("Could not keep the verified update");
            }
            clearOthers(directory, apk);
            preferences(context).edit().putString("ready_hash", hash).putLong("ready_code", code)
                    .putString("ready_version", version).remove("offered_at").apply();
        }
        Log.i(TAG, "Update " + version + " is verified and will be offered on the next start");
    }

    /** Returns the verified APK from an earlier check while it is still newer. */
    private static File readyUpdate(Context context) {
        SharedPreferences preferences = preferences(context);
        String hash = preferences.getString("ready_hash", "");
        if (hash.isEmpty()) {
            return null;
        }
        try {
            File apk = new File(directory(context), hash + ".apk");
            long code = verify(context, apk);
            if (code == preferences.getLong("ready_code", -1) && hash.equals(sha256(apk))) {
                return apk;
            }
        } catch (Exception error) {
            Log.i(TAG, "The kept update is no longer usable", error);
        }
        forget(context);
        return null;
    }

    static void forget(Context context) {
        preferences(context).edit().remove("ready_hash").remove("ready_code").remove("ready_version")
                .remove("offered_at").apply();
        try {
            clearOthers(directory(context), null);
        } catch (IOException ignored) {
        }
    }

    /** The APK must be this app, newer than it and signed by the same key. */
    private static long verify(Context context, File apk) throws Exception {
        if (!apk.isFile()) {
            throw new IOException("No update file");
        }
        PackageManager manager = context.getPackageManager();
        int flags = Build.VERSION.SDK_INT >= 28
                ? PackageManager.GET_SIGNING_CERTIFICATES : PackageManager.GET_SIGNATURES;
        PackageInfo current = manager.getPackageInfo(context.getPackageName(), flags);
        PackageInfo candidate = manager.getPackageArchiveInfo(apk.getAbsolutePath(), flags);
        if (candidate == null || !context.getPackageName().equals(candidate.packageName)) {
            throw new IOException("The update is not this app");
        }
        long code = versionCode(candidate);
        if (code <= versionCode(current)) {
            throw new IOException("The update is not newer than this app");
        }
        Set<String> expected = signers(current);
        Set<String> actual = signers(candidate);
        // Android refuses an update signed by another key in any case; older
        // versions may not report an archive's signers, newer ones must match.
        if (expected.isEmpty() || (!actual.isEmpty() && !expected.equals(actual)) ||
                (Build.VERSION.SDK_INT >= 28 && actual.isEmpty())) {
            throw new IOException("The update is signed by another key");
        }
        return code;
    }

    @SuppressWarnings("deprecation")
    private static long versionCode(PackageInfo info) {
        return Build.VERSION.SDK_INT >= 28 ? info.getLongVersionCode() : info.versionCode;
    }

    @SuppressWarnings("deprecation")
    private static Set<String> signers(PackageInfo info) throws Exception {
        Signature[] signatures;
        if (Build.VERSION.SDK_INT >= 28) {
            signatures = info.signingInfo == null ? null : info.signingInfo.getApkContentsSigners();
        } else {
            signatures = info.signatures;
        }
        Set<String> values = new HashSet<>();
        if (signatures != null) {
            for (Signature signature : signatures) {
                values.add(hex(MessageDigest.getInstance("SHA-256").digest(signature.toByteArray())));
            }
        }
        return values;
    }

    private static void install(Context context, File apk) {
        synchronized (LOCK) {
            PackageInstaller installer = context.getPackageManager().getPackageInstaller();
            int session = -1;
            try {
                if (!installer.getMySessions().isEmpty()) {
                    return;
                }
                PackageInstaller.SessionParams parameters = new PackageInstaller.SessionParams(
                        PackageInstaller.SessionParams.MODE_FULL_INSTALL);
                parameters.setAppPackageName(context.getPackageName());
                parameters.setSize(apk.length());
                session = installer.createSession(parameters);
                try (PackageInstaller.Session open = installer.openSession(session)) {
                    try (InputStream input = new FileInputStream(apk);
                         OutputStream output = open.openWrite("base.apk", 0, apk.length())) {
                        copy(input, output, apk.length());
                        open.fsync(output);
                    }
                    Intent callback = new Intent(context, AppUpdateReceiver.class)
                            .setAction(context.getPackageName() + ".APP_UPDATE_RESULT");
                    int flags = PendingIntent.FLAG_UPDATE_CURRENT;
                    if (Build.VERSION.SDK_INT >= 31) {
                        flags |= PendingIntent.FLAG_MUTABLE;
                    }
                    PendingIntent reply = PendingIntent.getBroadcast(context, session, callback, flags);
                    open.commit(reply.getIntentSender());
                    session = -1;
                }
            } catch (Exception error) {
                Log.w(TAG, "Could not start the update installation", error);
            } finally {
                if (session >= 0) {
                    installer.abandonSession(session);
                }
            }
        }
    }

    private static byte[] fetch(String address, long limit, OutputStream sink) throws IOException {
        HttpURLConnection connection = (HttpURLConnection)new URL(address).openConnection();
        connection.setConnectTimeout(15000);
        connection.setReadTimeout(30000);
        connection.setInstanceFollowRedirects(true);
        connection.setRequestProperty("User-Agent", "Inner-Breeze/" + BuildConfig.VERSION_NAME);
        try {
            int code = connection.getResponseCode();
            if (code != 200) {
                throw new IOException("Update download answered " + code);
            }
            try (InputStream input = connection.getInputStream()) {
                if (sink != null) {
                    copy(input, sink, limit);
                    return null;
                }
                ByteArrayOutputStream buffer = new ByteArrayOutputStream();
                copy(input, buffer, limit);
                return buffer.toByteArray();
            }
        } finally {
            connection.disconnect();
        }
    }

    private static void copy(InputStream input, OutputStream output, long limit) throws IOException {
        byte[] buffer = new byte[65536];
        long total = 0;
        int count;
        while ((count = input.read(buffer)) != -1) {
            total += count;
            if (total > limit) {
                throw new IOException("Update download exceeds its size");
            }
            output.write(buffer, 0, count);
        }
    }

    private static String sha256(File file) throws Exception {
        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        byte[] buffer = new byte[65536];
        try (InputStream input = new FileInputStream(file)) {
            int count;
            while ((count = input.read(buffer)) != -1) {
                digest.update(buffer, 0, count);
            }
        }
        return hex(digest.digest());
    }

    private static String hex(byte[] bytes) {
        StringBuilder text = new StringBuilder();
        for (byte value : bytes) {
            text.append(String.format(Locale.ROOT, "%02x", value & 255));
        }
        return text.toString();
    }

    private static File directory(Context context) throws IOException {
        File directory = new File(context.getFilesDir(), "app-updates");
        if (!directory.isDirectory() && !directory.mkdirs()) {
            throw new IOException("Update storage unavailable");
        }
        return directory;
    }

    private static void clearOthers(File directory, File keep) {
        File[] files = directory.listFiles();
        if (files == null) {
            return;
        }
        for (File file : files) {
            if (keep == null || !file.equals(keep)) {
                file.delete();
            }
        }
    }
}
