package xyz.waozi.inbe;

import android.test.InstrumentationTestCase;
import org.json.JSONObject;

public class AppUpdateTest extends InstrumentationTestCase {
    public void testOnlyNewerNumericReleasesUpdate() {
        assertTrue(AppUpdate.newer("2.1.29", "2.1.28"));
        assertTrue(AppUpdate.newer("2.2.0", "2.1.99"));
        assertTrue(AppUpdate.newer("10.0.0", "9.9.9"));
        assertTrue(AppUpdate.newer("2.1.28.1", "2.1.28"));
        assertFalse(AppUpdate.newer("2.1.28", "2.1.28"));
        assertFalse(AppUpdate.newer("2.1.27", "2.1.28"));
        assertFalse(AppUpdate.newer("2.1.x", "2.1.28"));
        assertFalse(AppUpdate.newer("2.1.29-beta", "2.1.28"));
        assertFalse(AppUpdate.newer("", "2.1.28"));
    }

    public void testPicksThePreferredAbiThenTheUniversalApk() throws Exception {
        JSONObject channels = new JSONObject("{\"android\":{\"url\":\"u\"},"
                + "\"android-arm64-v8a\":{\"url\":\"a64\"},\"android-armeabi-v7a\":{\"url\":\"a32\"},"
                + "\"appimage-amd64\":{\"url\":\"linux\"}}");
        assertEquals("a64", AppUpdate.channel(channels, new String[] {"arm64-v8a", "armeabi-v7a"}).getString("url"));
        assertEquals("a32", AppUpdate.channel(channels, new String[] {"armeabi-v7a", "armeabi"}).getString("url"));
        assertEquals("u", AppUpdate.channel(channels, new String[] {"x86_64"}).getString("url"));
        assertNull(AppUpdate.channel(new JSONObject("{\"appimage-amd64\":{}}"), new String[] {"x86_64"}));
    }
}
