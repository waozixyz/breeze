import static org.junit.Assert.*;

import android.app.Activity;
import android.content.ComponentName;
import android.content.Intent;
import android.content.pm.ShortcutManager;
import android.graphics.Bitmap;
import java.io.File;
import java.io.FileOutputStream;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.robolectric.Robolectric;
import org.robolectric.RobolectricTestRunner;
import org.robolectric.annotation.Config;
import org.robolectric.Shadows;
import xyz.waozi.inbe.AppShortcuts;

@RunWith(RobolectricTestRunner.class)
@Config(sdk = {28, 36}, manifest = Config.NONE)
public class AppShortcutsTest {
    private AppShortcuts shortcuts(Activity activity) {
        return new AppShortcuts(activity);
    }

    @Test public void constructionDoesNotRequireAnAttachedActivity() {
        AppShortcuts shortcuts = new AppShortcuts(new Activity());
        shortcuts.accept(new Intent(AppShortcuts.ACTION_OPEN_APP)
                .putExtra(AppShortcuts.EXTRA_APP, "diary"));
        assertEquals("diary", shortcuts.take());
    }

    @Test public void launchIntentsAreConsumedOnceAndValidateAppNames() {
        Activity activity = Robolectric.buildActivity(Activity.class).setup().get();
        AppShortcuts shortcuts = shortcuts(activity);
        shortcuts.accept(new Intent(AppShortcuts.ACTION_OPEN_APP)
                .putExtra(AppShortcuts.EXTRA_APP, "diary"));
        assertEquals("diary", shortcuts.take());
        assertNull(shortcuts.take());
        shortcuts.accept(new Intent(AppShortcuts.ACTION_OPEN_APP)
                .putExtra(AppShortcuts.EXTRA_APP, "../../anything"));
        assertNull(shortcuts.take());
        shortcuts.accept(new Intent(Intent.ACTION_MAIN).addCategory(Intent.CATEGORY_LAUNCHER));
        assertEquals("inbe", shortcuts.take());
        shortcuts.accept(new Intent("unrelated").putExtra(AppShortcuts.EXTRA_APP, "habits"));
        assertNull(shortcuts.take());
    }

    @Test public void pinUsesStableAppIdentityAndDoesNotDuplicateExistingPin() throws Exception {
        Activity activity = Robolectric.buildActivity(Activity.class).setup().get();
        ShortcutManager manager = activity.getSystemService(ShortcutManager.class);
        Shadows.shadowOf(manager).setIsRequestPinShortcutSupported(true);
        AppShortcuts shortcuts = shortcuts(activity);
        File icon = new File(activity.getCacheDir(), "launcher.png");
        Bitmap bitmap = Bitmap.createBitmap(128, 128, Bitmap.Config.ARGB_8888);
        try (FileOutputStream output = new FileOutputStream(icon)) {
            assertTrue(bitmap.compress(Bitmap.CompressFormat.PNG, 100, output));
        }
        assertTrue(shortcuts.supported());
        assertEquals(1, shortcuts.pin("diary", "日記", icon.getAbsolutePath()));
        assertEquals(1, manager.getPinnedShortcuts().size());
        assertEquals("inbe.app.diary", manager.getPinnedShortcuts().get(0).getId());
        Intent intent = manager.getPinnedShortcuts().get(0).getIntent();
        assertEquals(AppShortcuts.ACTION_OPEN_APP, intent.getAction());
        assertEquals("diary", intent.getStringExtra(AppShortcuts.EXTRA_APP));
        assertEquals("inbe-app://launch/diary", intent.getDataString());
        assertEquals(new ComponentName(activity, Activity.class), intent.getComponent());
        assertEquals(2, shortcuts.pin("diary", "Diary", icon.getAbsolutePath()));
        assertEquals(1, manager.getPinnedShortcuts().size());
        assertEquals("Diary", manager.getPinnedShortcuts().get(0).getShortLabel());
        assertEquals(0, shortcuts.pin("../diary", "Diary", icon.getAbsolutePath()));
        assertEquals(0, shortcuts.pin("lists", "Lists", "/missing.png"));
        Shadows.shadowOf(manager).setIsRequestPinShortcutSupported(false);
        assertFalse(shortcuts.supported());
        assertEquals(0, shortcuts.pin("lists", "Lists", icon.getAbsolutePath()));
    }
}
