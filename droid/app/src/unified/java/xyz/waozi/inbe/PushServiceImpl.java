package xyz.waozi.inbe;

import java.nio.charset.StandardCharsets;
import org.kryonlabs.notifications.push.SharedPushService;
import org.unifiedpush.android.connector.data.PushMessage;

public class PushServiceImpl extends SharedPushService {
    @Override protected void onPushMessage(PushMessage message, String instance) {
        byte[] content = message.getContent();
        if (content == null || content.length == 0 || content.length > 8192) return;
        // Retain the existing plain title/newline/body payload convention.
        String text = new String(content, StandardCharsets.UTF_8);
        int newline = text.indexOf('\n');
        String title = newline < 0 ? "Inner Breeze" : text.substring(0, newline);
        String body = newline < 0 ? text : text.substring(newline + 1);
        PushNotificationDisplay.show(this, 1, instance, title, body);
    }
}
