package xyz.waozi.inbe;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.Context;
import android.content.SharedPreferences;
import android.os.Build;
import android.util.Log;
import org.unifiedpush.android.connector.FailedReason;
import org.unifiedpush.android.connector.PushService;
import org.unifiedpush.android.connector.data.PublicKeySet;
import org.unifiedpush.android.connector.data.PushEndpoint;
import org.unifiedpush.android.connector.data.PushMessage;

public class PushServiceImpl extends PushService {
    private static final String TAG = "PUSH";
    private static final String PREFS = "push";
    private static final String PREF_ENDPOINT = "endpoint";
    private static final String PREF_AUTH = "auth";
    private static final String PREF_P256DH = "p256dh";
    private static final String CHANNEL_ID = "inbe.push";
    private static final int NOTIFICATION_ID = 0x7042;

    @Override
    public void onMessage(PushMessage message, String instance) {
        if (!NotificationPresence.canPostPush(this)) {
            Log.d(TAG, "Ignoring push without a visible app or session indicator");
            return;
        }
        String text = new String(message.getContent());
        String title = "Inner Breeze";
        String body = text;
        int nl = text.indexOf('\n');
        if (nl >= 0) {
            title = text.substring(0, nl);
            body = text.substring(nl + 1);
        }
        showNotification(title, body);
    }

    @Override
    public void onNewEndpoint(PushEndpoint endpoint, String instance) {
        Log.d(TAG, "new endpoint (temporary=" + endpoint.getTemporary() + ")");
        SharedPreferences.Editor e = prefs().edit().putString(PREF_ENDPOINT, endpoint.getUrl());
        PublicKeySet keys = endpoint.getPubKeySet();
        if (keys != null) {
            e.putString(PREF_AUTH, keys.getAuth()).putString(PREF_P256DH, keys.getPubKey());
        } else {
            e.remove(PREF_AUTH).remove(PREF_P256DH);
        }
        e.apply();
    }

    @Override
    public void onRegistrationFailed(FailedReason reason, String instance) {
        Log.w(TAG, "registration failed: " + reason);
        prefs().edit().remove(PREF_ENDPOINT).apply();
    }

    @Override
    public void onUnregistered(String instance) {
        prefs().edit().remove(PREF_ENDPOINT).apply();
    }

    public static String getEndpoint(Context context) {
        return context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getString(PREF_ENDPOINT, null);
    }

    // Push turned off: no endpoint until a distributor is chosen again.
    public static void forgetEndpoint(Context context) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit()
                .remove(PREF_ENDPOINT).remove(PREF_AUTH).remove(PREF_P256DH).apply();
    }

    private SharedPreferences prefs() {
        return getSharedPreferences(PREFS, Context.MODE_PRIVATE);
    }

    private void showNotification(String title, String body) {
        NotificationManager nm = (NotificationManager) getSystemService(NOTIFICATION_SERVICE);
        if (nm == null) return;
        if (Build.VERSION.SDK_INT >= 26 && nm.getNotificationChannel(CHANNEL_ID) == null) {
            nm.createNotificationChannel(new NotificationChannel(CHANNEL_ID, "Push messages", NotificationManager.IMPORTANCE_DEFAULT));
        }
        PendingIntent pi = PendingIntent.getActivity(this, 0,
                getPackageManager().getLaunchIntentForPackage(getPackageName()),
                PendingIntent.FLAG_IMMUTABLE);
        Notification.Builder b = Build.VERSION.SDK_INT >= 26
                ? new Notification.Builder(this, CHANNEL_ID)
                : new Notification.Builder(this);
        b.setSmallIcon(getApplicationInfo().icon)
                .setContentTitle(title)
                .setContentText(body)
                .setAutoCancel(true)
                .setContentIntent(pi);
        if (!NotificationPresence.canPostPush(this)) {
            return;
        }
        nm.notify(NOTIFICATION_ID, b.build());
    }
}
