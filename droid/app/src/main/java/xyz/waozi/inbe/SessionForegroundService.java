package xyz.waozi.inbe;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.content.pm.ServiceInfo;
import android.os.Build;
import android.os.IBinder;
import android.os.PowerManager;
import android.service.notification.StatusBarNotification;
import android.util.Log;

public class SessionForegroundService extends Service {
    public static final String ACTION_START = "xyz.waozi.inbe.action.START_SESSION_FOREGROUND";
    public static final String ACTION_STOP = "xyz.waozi.inbe.action.STOP_SESSION_FOREGROUND";
    private static final String TAG = "SessionService";
    private static final String CHANNEL_ID = "active_session";
    private static final int NOTIFICATION_ID = 3001;
    private static String currentStatusText = "";
    private static volatile SessionForegroundService activeService = null;

    private PowerManager.WakeLock wakeLock = null;
    private volatile boolean foregroundActive = false;

    @Override
    public void onCreate() {
        super.onCreate();
        activeService = this;
        ensureNotificationChannel(this);
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        String action = intent != null ? intent.getAction() : ACTION_START;

        if (ACTION_STOP.equals(action)) {
            stopSession();
            return START_NOT_STICKY;
        }
        startSession();
        return START_NOT_STICKY;
    }

    @Override
    public void onDestroy() {
        releaseWakeLock();
        clearForeground();
        if (activeService == this) {
            activeService = null;
        }
        super.onDestroy();
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }

    private void startSession() {
        // The session keeps running even when notifications are disabled:
        // Android still runs the foreground service and only hides its card.
        if (!canShowIndicator(this)) {
            Log.w(TAG, "Session notification hidden; continuing in the background");
        }
        currentStatusText = "";
        Notification notification = buildNotification();
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            startForeground(
                NOTIFICATION_ID,
                notification,
                ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PLAYBACK
            );
        } else {
            startForeground(NOTIFICATION_ID, notification);
        }
        foregroundActive = true;
        acquireWakeLock();
        Log.d(TAG, "Session foreground service started");
    }

    private void stopSession() {
        currentStatusText = "";
        releaseWakeLock();
        clearForeground();
        stopSelf();
        Log.d(TAG, "Session foreground service stopped");
    }

    public static void updateStatus(String statusText) {
        currentStatusText = statusText != null ? statusText : "";

        SessionForegroundService service = activeService;
        if (service == null) {
            return;
        }
        if (!service.foregroundActive) {
            return;
        }

        NotificationManager manager =
            (NotificationManager)service.getSystemService(Context.NOTIFICATION_SERVICE);
        if (manager != null) {
            manager.notify(NOTIFICATION_ID, service.buildNotification());
        }
    }

    static boolean hasVisibleIndicator(Context context) {
        SessionForegroundService service = activeService;
        if (service == null || !service.foregroundActive) {
            return false;
        }

        NotificationManager manager = notificationManagerWithVisibleChannel(context);
        if (manager == null) {
            return false;
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            try {
                for (StatusBarNotification notification : manager.getActiveNotifications()) {
                    if (notification.getId() == NOTIFICATION_ID) {
                        return true;
                    }
                }
            } catch (RuntimeException error) {
                Log.w(TAG, "Could not confirm session indicator", error);
            }
            return false;
        }
        // Older Android releases cannot confirm that the posted indicator is
        // visible, so they cannot authorize background session execution.
        return false;
    }

    static boolean canShowIndicator(Context context) {
        ensureNotificationChannel(context);
        return notificationManagerWithVisibleChannel(context) != null;
    }

    private static NotificationManager notificationManagerWithVisibleChannel(Context context) {
        NotificationManager manager =
            (NotificationManager)context.getSystemService(Context.NOTIFICATION_SERVICE);
        if (manager == null) {
            return null;
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N && !manager.areNotificationsEnabled()) {
            return null;
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationChannel channel = manager.getNotificationChannel(CHANNEL_ID);
            if (channel == null || channel.getImportance() == NotificationManager.IMPORTANCE_NONE) {
                return null;
            }
        }
        return manager;
    }

    private void stopForegroundCompat() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {
            stopForeground(STOP_FOREGROUND_REMOVE);
        } else {
            stopForeground(true);
        }
    }

    private void clearForeground() {
        foregroundActive = false;
        stopForegroundCompat();
        cancelNotification();
    }

    private void cancelNotification() {
        NotificationManager manager =
            (NotificationManager)getSystemService(Context.NOTIFICATION_SERVICE);
        if (manager != null) {
            manager.cancel(NOTIFICATION_ID);
        }
    }

    private void acquireWakeLock() {
        if (wakeLock != null && wakeLock.isHeld()) {
            return;
        }

        PowerManager pm = (PowerManager)getSystemService(Context.POWER_SERVICE);
        if (pm == null) {
            Log.e(TAG, "PowerManager unavailable; cannot acquire wakelock");
            return;
        }

        wakeLock = pm.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "inbe:active_session");
        wakeLock.setReferenceCounted(false);
        wakeLock.acquire();
        Log.d(TAG, "Session wakelock acquired");
    }

    private void releaseWakeLock() {
        if (wakeLock != null && wakeLock.isHeld()) {
            wakeLock.release();
            Log.d(TAG, "Session wakelock released");
        }
        wakeLock = null;
    }

    private Notification buildNotification() {
        Intent launchIntent = new Intent(this, MainActivity.class);
        launchIntent.setFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP | Intent.FLAG_ACTIVITY_CLEAR_TOP);
        int pendingFlags = PendingIntent.FLAG_UPDATE_CURRENT;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            pendingFlags |= PendingIntent.FLAG_IMMUTABLE;
        }
        PendingIntent pendingIntent = PendingIntent.getActivity(this, 0, launchIntent, pendingFlags);

        Notification.Builder builder = Build.VERSION.SDK_INT >= Build.VERSION_CODES.O
            ? new Notification.Builder(this, CHANNEL_ID)
            : new Notification.Builder(this);

        CharSequence title = getApplicationInfo().loadLabel(getPackageManager());
        builder.setSmallIcon(android.R.drawable.ic_media_play)
            .setContentTitle(title)
            .setContentText(currentStatusText)
            .setContentIntent(pendingIntent)
            .setOngoing(true)
            .setOnlyAlertOnce(true)
            .setShowWhen(false);

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
            builder.setCategory(Notification.CATEGORY_TRANSPORT)
                .setVisibility(Notification.VISIBILITY_PUBLIC);
        }

        return builder.build();
    }

    private static void ensureNotificationChannel(Context context) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) {
            return;
        }

        NotificationManager manager =
            (NotificationManager)context.getSystemService(Context.NOTIFICATION_SERVICE);
        if (manager == null) {
            return;
        }

        NotificationChannel channel = new NotificationChannel(
            CHANNEL_ID,
            context.getApplicationInfo().loadLabel(context.getPackageManager()),
            NotificationManager.IMPORTANCE_LOW
        );
        manager.createNotificationChannel(channel);
    }
}
