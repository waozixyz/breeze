package xyz.waozi.inbe;

import android.content.Intent;
import android.content.pm.PackageManager;
import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.graphics.drawable.Drawable;
import android.net.Uri;
import android.widget.Toast;
import java.io.File;
import java.io.FileOutputStream;
import java.lang.reflect.Method;
import java.util.ArrayList;
import java.util.List;
import org.unifiedpush.android.connector.UnifiedPush;

final class PushBridge {
    private PushBridge() {}

    static boolean isRegistered(MainActivity activity) {
        if (BuildConfig.GPLAY) {
            Object value = callGplay("isRegistered", new Class<?>[] {MainActivity.class}, activity);
            if (value instanceof Boolean) {
                return (Boolean) value;
            }
        }
        return PushServiceImpl.getEndpoint(activity) != null;
    }

    static String[] getDistributors(MainActivity activity) {
        if (BuildConfig.GPLAY) {
            Object value = callGplay("getDistributors", new Class<?>[] {MainActivity.class}, activity);
            if (value instanceof String[]) {
                return (String[]) value;
            }
        }
        List<String> distributors = UnifiedPush.getDistributors(activity);
        return distributors.toArray(new String[0]);
    }

    static String[] getDistributorLabels(MainActivity activity) {
        if (BuildConfig.GPLAY) {
            Object value = callGplay("getDistributorLabels", new Class<?>[] {MainActivity.class}, activity);
            if (value instanceof String[]) {
                return (String[]) value;
            }
        }
        PackageManager pm = activity.getPackageManager();
        List<String> labels = new ArrayList<>();
        for (String pkg : UnifiedPush.getDistributors(activity)) {
            try {
                labels.add(pm.getApplicationLabel(pm.getApplicationInfo(pkg, 0)).toString());
            } catch (PackageManager.NameNotFoundException e) {
                labels.add(pkg);
            }
        }
        return labels.toArray(new String[0]);
    }

    static String[] getDistributorIcons(MainActivity activity) {
        if (BuildConfig.GPLAY) {
            Object value = callGplay("getDistributorIcons", new Class<?>[] {MainActivity.class}, activity);
            if (value instanceof String[]) {
                return (String[]) value;
            }
        }
        PackageManager pm = activity.getPackageManager();
        File dir = new File(activity.getCacheDir(), "push-icons");
        if (!dir.exists()) {
            dir.mkdirs();
        }
        List<String> paths = new ArrayList<>();
        List<String> distributors = UnifiedPush.getDistributors(activity);
        for (int i = 0; i < distributors.size(); i++) {
            File out = new File(dir, "icon_" + i + ".png");
            try {
                Drawable drawable = pm.getApplicationIcon(distributors.get(i));
                Bitmap bmp = Bitmap.createBitmap(96, 96, Bitmap.Config.ARGB_8888);
                Canvas canvas = new Canvas(bmp);
                drawable.setBounds(0, 0, 96, 96);
                drawable.draw(canvas);
                FileOutputStream fos = new FileOutputStream(out);
                bmp.compress(Bitmap.CompressFormat.PNG, 100, fos);
                fos.close();
                paths.add(out.getAbsolutePath());
            } catch (Exception e) {
                paths.add("");
            }
        }
        return paths.toArray(new String[0]);
    }

    static void configureWith(final MainActivity activity, final String pkg) {
        if (BuildConfig.GPLAY && callGplay("configureWith",
                new Class<?>[] {MainActivity.class, String.class}, activity, pkg) != null) {
            return;
        }
        activity.runOnUiThread(new Runnable() {
            @Override
            public void run() {
                UnifiedPush.saveDistributor(activity, pkg);
                UnifiedPush.register(activity, "inbe", "Inner Breeze", null);
                Toast.makeText(activity, activity.getString(R.string.push_registering, pkg), Toast.LENGTH_SHORT).show();
            }
        });
    }

    static void configure(final MainActivity activity) {
        if (BuildConfig.GPLAY && callGplay("configure",
                new Class<?>[] {MainActivity.class}, activity) != null) {
            return;
        }
        activity.runOnUiThread(new Runnable() {
            @Override
            public void run() {
                if (!UnifiedPush.getDistributors(activity).isEmpty()) {
                    return;
                }
                Toast.makeText(activity, activity.getString(R.string.push_install_distributor), Toast.LENGTH_LONG).show();
                try {
                    activity.startActivity(new Intent(Intent.ACTION_VIEW, Uri.parse(
                            "https://f-droid.org/en/packages/org.unifiedpush.distributor.sunup/")));
                } catch (Exception ignored) {
                }
            }
        });
    }

    // "None" in the picker: unregister and forget the distributor, so push
    // notifications stay off until one is chosen again.
    static void disable(final MainActivity activity) {
        if (BuildConfig.GPLAY && callGplay("disable",
                new Class<?>[] {MainActivity.class}, activity) != null) {
            return;
        }
        activity.runOnUiThread(new Runnable() {
            @Override
            public void run() {
                UnifiedPush.unregister(activity, "inbe");
                UnifiedPush.removeDistributor(activity);
                PushServiceImpl.forgetEndpoint(activity);
            }
        });
    }

    private static Object callGplay(String name, Class<?>[] parameterTypes, Object... args) {
        try {
            Method method = Class.forName("xyz.waozi.inbe.GplayPushBridge").getDeclaredMethod(name, parameterTypes);
            method.setAccessible(true);
            Object value = method.invoke(null, args);
            return value != null ? value : Boolean.TRUE;
        } catch (ClassNotFoundException e) {
            return null;
        } catch (Exception e) {
            return null;
        }
    }
}
