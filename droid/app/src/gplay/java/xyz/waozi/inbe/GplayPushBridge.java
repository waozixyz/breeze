package xyz.waozi.inbe;

import android.widget.Toast;
import com.google.firebase.messaging.FirebaseMessaging;

final class GplayPushBridge {
    private static String lastToken;

    private GplayPushBridge() {}

    static boolean isRegistered(MainActivity activity) {
        return lastToken != null && !lastToken.isEmpty();
    }

    static String[] getDistributors(MainActivity activity) {
        return new String[] {"fcm"};
    }

    static String[] getDistributorLabels(MainActivity activity) {
        return new String[] {"Google notifications"};
    }

    static String[] getDistributorIcons(MainActivity activity) {
        return new String[] {""};
    }

    static void disable(MainActivity activity) {
        lastToken = null;
        try {
            FirebaseMessaging.getInstance().deleteToken();
        } catch (IllegalStateException ignored) {
        }
    }

    static void configureWith(MainActivity activity, String pkg) {
        configure(activity);
    }

    static void configure(final MainActivity activity) {
        try {
            FirebaseMessaging.getInstance().getToken()
                    .addOnSuccessListener(token -> {
                        lastToken = token;
                        Toast.makeText(activity, "Google notifications enabled", Toast.LENGTH_SHORT).show();
                    })
                    .addOnFailureListener(error ->
                        Toast.makeText(activity, "Google notifications unavailable", Toast.LENGTH_LONG).show());
        } catch (IllegalStateException e) {
            Toast.makeText(activity, "Google notifications unavailable", Toast.LENGTH_LONG).show();
        }
    }
}
