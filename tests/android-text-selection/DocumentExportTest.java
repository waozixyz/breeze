import static org.junit.Assert.*;

import android.app.Activity;
import android.content.Intent;
import android.net.Uri;
import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.IOException;
import java.io.OutputStream;
import java.nio.file.Files;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.robolectric.Robolectric;
import org.robolectric.RobolectricTestRunner;
import org.robolectric.Shadows;
import org.robolectric.annotation.Config;
import xyz.waozi.inbe.DocumentExport;

@RunWith(RobolectricTestRunner.class)
@Config(sdk = {28, 36}, manifest = Config.NONE)
public class DocumentExportTest {
    private final Uri destination = Uri.parse("content://documents/document/backup");

    @Test public void requestsSystemSaveWithAnExplicitFilename() {
        Intent picker = DocumentExport.picker("account.key", "application/octet-stream");
        assertEquals(Intent.ACTION_CREATE_DOCUMENT, picker.getAction());
        assertTrue(picker.hasCategory(Intent.CATEGORY_OPENABLE));
        assertEquals("account.key", picker.getStringExtra(Intent.EXTRA_TITLE));
        assertEquals("application/octet-stream", picker.getType());
        assertThrows(IllegalArgumentException.class, () -> DocumentExport.picker("../account.key", "*/*"));
    }

    @Test public void writesTheSelectedUriAndRemovesPrivateStaging() throws Exception {
        Activity activity = Robolectric.buildActivity(Activity.class).setup().get();
        DocumentExport export = new DocumentExport();
        File staged = new File(export.selected(activity.getCacheDir(), destination));
        byte[] fixture = "synthetic recovery fixture".getBytes("UTF-8");
        Files.write(staged.toPath(), fixture);
        ByteArrayOutputStream received = new ByteArrayOutputStream();
        Shadows.shadowOf(activity.getContentResolver()).registerOutputStream(destination, received);
        assertFalse(export.commit(activity.getContentResolver(), "/another/file"));
        assertTrue(export.commit(activity.getContentResolver(), staged.getAbsolutePath()));
        assertArrayEquals(fixture, received.toByteArray());
        assertFalse(staged.exists());
        assertFalse(export.commit(activity.getContentResolver(), staged.getAbsolutePath()));
    }

    @Test public void cancellationAndProviderFailureNeverReportSuccess() throws Exception {
        Activity activity = Robolectric.buildActivity(Activity.class).setup().get();
        DocumentExport export = new DocumentExport();
        File cancelled = new File(export.selected(activity.getCacheDir(), destination));
        export.clear();
        assertFalse(cancelled.exists());
        assertFalse(export.commit(activity.getContentResolver(), cancelled.getAbsolutePath()));
        File staged = new File(export.selected(activity.getCacheDir(), destination));
        Files.write(staged.toPath(), new byte[] {1, 2, 3});
        Shadows.shadowOf(activity.getContentResolver()).registerOutputStream(destination,
                new OutputStream() {
                    @Override public void write(int value) throws IOException {
                        throw new IOException("Provider refused the write");
                    }
                });
        assertFalse(export.commit(activity.getContentResolver(), staged.getAbsolutePath()));
        assertFalse(staged.exists());
    }
}
