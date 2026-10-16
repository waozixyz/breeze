package xyz.waozi.inbe;

import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.Context;
import java.nio.charset.StandardCharsets;

/** Android clipboard transport; text commands and selection remain in Kryon. */
final class TextClipboard {
    static byte[] read(Context context) {
        ClipboardManager manager = (ClipboardManager)context.getSystemService(Context.CLIPBOARD_SERVICE);
        if (manager == null) {
            return null;
        }
        ClipData clip = manager.getPrimaryClip();
        if (clip == null || clip.getItemCount() == 0) {
            return new byte[0];
        }
        CharSequence text = clip.getItemAt(0).getText();
        return text == null ? new byte[0] : text.toString().getBytes(StandardCharsets.UTF_8);
    }

    static boolean write(Context context, byte[] bytes) {
        ClipboardManager manager = (ClipboardManager)context.getSystemService(Context.CLIPBOARD_SERVICE);
        if (manager == null || bytes == null) {
            return false;
        }
        manager.setPrimaryClip(ClipData.newPlainText(context.getApplicationInfo().loadLabel(
            context.getPackageManager()), new String(bytes, StandardCharsets.UTF_8)));
        return true;
    }
}
