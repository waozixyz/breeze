package xyz.waozi.inbe;

import com.google.firebase.messaging.RemoteMessage;
import org.kryonlabs.notifications.push.SharedFcmService;

public class FcmPushService extends SharedFcmService {
    @Override protected void onPushMessage(RemoteMessage message) {
        // Only data messages with Kryon's current scope/generation reach here.
        PushNotificationDisplay.show(this, 2, message.getData().get("kryon_instance"),
                message.getData().get("title"), message.getData().get("body"));
    }
}
