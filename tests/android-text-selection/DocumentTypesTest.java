import static org.junit.Assert.*;

import android.content.Intent;
import android.webkit.MimeTypeMap;
import java.util.Arrays;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.kryonlabs.platform.DocumentTypes;
import org.robolectric.RobolectricTestRunner;
import org.robolectric.annotation.Config;

@RunWith(RobolectricTestRunner.class)
@Config(sdk = {28, 36}, manifest = Config.NONE)
public class DocumentTypesTest {
    @Test public void recoveryFiltersKeepKeysAndRelatedBackupsSelectable() {
        Intent picker = new Intent(Intent.ACTION_OPEN_DOCUMENT);
        DocumentTypes.apply(picker,
                "application/pgp-keys,application/octet-stream,application/json,text/plain");
        assertEquals("*/*", picker.getType());
        String[] types = picker.getStringArrayExtra(Intent.EXTRA_MIME_TYPES);
        assertArrayEquals(new String[] {"application/pgp-keys", "application/octet-stream",
                "application/json", "text/plain"}, types);
        String keyMime = MimeTypeMap.getSingleton().getMimeTypeFromExtension("key");
        assertTrue(Arrays.asList(types).contains(keyMime == null ? "application/octet-stream" : keyMime));
        assertFalse(Arrays.asList(types).contains("*/*"));
        assertFalse(Arrays.asList(types).contains("image/*"));
    }

    @Test public void singleTypesAndUnrestrictedImportsRetainTheirMeaning() {
        Intent picker = new Intent(Intent.ACTION_OPEN_DOCUMENT);
        DocumentTypes.apply(picker, "image/*,application/json");
        assertArrayEquals(new String[] {"image/*", "application/json"},
                picker.getStringArrayExtra(Intent.EXTRA_MIME_TYPES));
        DocumentTypes.apply(picker, " image/*, ,image/* ");
        assertEquals("image/*", picker.getType());
        assertFalse(picker.hasExtra(Intent.EXTRA_MIME_TYPES));
        DocumentTypes.apply(picker, null);
        assertEquals("*/*", picker.getType());
        assertFalse(picker.hasExtra(Intent.EXTRA_MIME_TYPES));
        DocumentTypes.apply(picker, " , ");
        assertEquals("*/*", picker.getType());
    }
}
