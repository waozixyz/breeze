package xyz.waozi.inbe;

import android.content.pm.PackageManager;
import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.graphics.drawable.Drawable;
import java.io.File;
import java.io.FileOutputStream;
import java.lang.reflect.Method;
import java.util.ArrayList;
import java.util.List;
import org.unifiedpush.android.connector.UnifiedPush;

final class UnifiedPushBridge {
    private UnifiedPushBridge() {}

    static String[] getDistributors(MainActivity activity) {
        List<String> distributors = UnifiedPush.getDistributors(activity);
        return distributors.toArray(new String[0]);
    }

    static String[] getDistributorLabels(MainActivity activity) {
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

    static void configureWith(MainActivity activity, String pkg) {
        if (UnifiedPush.getDistributors(activity).contains(pkg)) UnifiedPush.saveDistributor(activity, pkg);
    }
}
