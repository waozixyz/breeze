package xyz.waozi.inbe;

import android.Manifest;
import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.os.Build;
import org.kryonlabs.notifications.push.PushCallbacks;

/** Display only accepted, enabled account messages, including cold background delivery. */
final class PushNotificationDisplay {
    private static final String CHANNEL_ID = "inbe.push";
    private static final int NOTIFICATION_ID = 0x7042;

    private PushNotificationDisplay() {}

    // Call under PushBridge's lock so revocation also removes an already
    // visible former-account body before another account can be published.
    static void cancel(Context context) {
        NotificationManager manager = (NotificationManager) context.getSystemService(Context.NOTIFICATION_SERVICE);
        if (manager != null) manager.cancel(NOTIFICATION_ID);
    }

    static void show(Context context, int provider, String wire, String title, String body) {
        if (body == null || body.trim().isEmpty() || body.length() > 4096 ||
                (title != null && title.length() > 256) || !PushBridge.canDisplay(context) ||
                !PushCallbacks.accepts(context, provider, wire)) return;
        if (Build.VERSION.SDK_INT >= 33 && context.checkSelfPermission(
                Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) return;
        NotificationManager manager = (NotificationManager) context.getSystemService(Context.NOTIFICATION_SERVICE);
        if (manager == null || (Build.VERSION.SDK_INT >= 24 && !manager.areNotificationsEnabled())) return;
        if (Build.VERSION.SDK_INT >= 26) {
            manager.createNotificationChannel(new NotificationChannel(CHANNEL_ID,
                    context.getString(R.string.notification_channel_push), NotificationManager.IMPORTANCE_DEFAULT));
            NotificationChannel channel = manager.getNotificationChannel(CHANNEL_ID);
            if (channel == null || channel.getImportance() == NotificationManager.IMPORTANCE_NONE) return;
        }
        Intent launch = context.getPackageManager().getLaunchIntentForPackage(context.getPackageName());
        if (launch == null) return;
        PendingIntent intent = PendingIntent.getActivity(context, 0, launch,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
        Notification.Builder builder = Build.VERSION.SDK_INT >= 26
                ? new Notification.Builder(context, CHANNEL_ID) : new Notification.Builder(context);
        Notification notification = builder.setSmallIcon(context.getApplicationInfo().icon)
                .setContentTitle(title == null || title.trim().isEmpty() ? "Inner Breeze" : title)
                .setContentText(body).setStyle(new Notification.BigTextStyle().bigText(body))
                .setAutoCancel(true).setContentIntent(intent).build();
        // Serialize posting with disable/account replacement so a former scope
        // cannot pass a stale decision while it is being revoked.
        synchronized (PushBridge.class) {
            if (PushBridge.canDisplay(context) && PushCallbacks.accepts(context, provider, wire)) {
                try { manager.notify(NOTIFICATION_ID, notification); }
                catch (SecurityException permissionRevoked) { /* OS permission changed during dispatch. */ }
            }
        }
    }
}
