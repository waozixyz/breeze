package xyz.waozi.inbe;

import android.app.Activity;
import android.content.ComponentName;
import android.content.Intent;
import android.content.pm.ShortcutInfo;
import android.content.pm.ShortcutManager;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.drawable.Icon;
import android.net.Uri;
import android.os.Build;
import android.util.Log;
import java.util.Collections;
import java.io.File;

/** OS launch entries only; app selection stays on the native frame thread. */
public final class AppShortcuts {
    public static final String ACTION_OPEN_APP = "xyz.waozi.inbe.action.OPEN_APP";
    public static final String EXTRA_APP = "app_name";
    private final Activity activity;
    private String pendingApp;

    public AppShortcuts(Activity activity) {
        this.activity = activity;
    }

    static boolean validName(String name) {
        return name != null && name.matches("[a-z0-9_-]{1,24}");
    }

    public boolean supported() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) {
            return false;
        }
        try {
            ShortcutManager manager = activity.getSystemService(ShortcutManager.class);
            return manager != null && manager.isRequestPinShortcutSupported();
        } catch (IllegalStateException | SecurityException error) {
            return false;
        }
    }

    Intent intent(String name) {
        return new Intent(ACTION_OPEN_APP)
                .setComponent(new ComponentName(activity, activity.getClass()))
                .setData(new Uri.Builder().scheme("inbe-app").authority("launch")
                        .appendPath(name).build())
                .putExtra(EXTRA_APP, name)
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP);
    }

    /** 1 = confirmation requested, 2 = already pinned, 0 = unavailable/failed. */
    public int pin(String name, String label, String iconPath) {
        if (!validName(name) || label == null || label.trim().isEmpty() || !supported()) {
            return 0;
        }
        if (iconPath == null || !new File(iconPath).isFile()) {
            return 0;
        }
        Bitmap bitmap = BitmapFactory.decodeFile(iconPath);
        if (bitmap == null) {
            return 0;
        }
        try {
            ShortcutManager manager = activity.getSystemService(ShortcutManager.class);
            String id = "inbe.app." + name;
            ShortcutInfo shortcut = new ShortcutInfo.Builder(activity, id)
                    .setShortLabel(label)
                    .setLongLabel(label)
                    .setIcon(Icon.createWithBitmap(bitmap))
                    .setIntent(intent(name))
                    .build();
            for (ShortcutInfo existing : manager.getPinnedShortcuts()) {
                if (id.equals(existing.getId())) {
                    return manager.updateShortcuts(Collections.singletonList(shortcut)) ? 2 : 0;
                }
            }
            return manager.requestPinShortcut(shortcut, null) ? 1 : 0;
        } catch (IllegalArgumentException | IllegalStateException | SecurityException error) {
            Log.w("AppShortcuts", "Launcher pin request failed", error);
            return 0;
        } finally {
            bitmap.recycle();
        }
    }

    public synchronized void accept(Intent intent) {
        if (intent == null) {
            return;
        }
        if (ACTION_OPEN_APP.equals(intent.getAction())) {
            String name = intent.getStringExtra(EXTRA_APP);
            if (validName(name)) {
                pendingApp = name;
            }
        } else if (Intent.ACTION_MAIN.equals(intent.getAction()) &&
                intent.hasCategory(Intent.CATEGORY_LAUNCHER)) {
            pendingApp = "inbe";
        }
    }

    public synchronized String take() {
        String name = pendingApp;
        pendingApp = null;
        return name;
    }
}
