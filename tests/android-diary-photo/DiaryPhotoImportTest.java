package xyz.waozi.inbe;

import static org.junit.Assert.*;

import android.content.Intent;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.Color;
import android.media.ExifInterface;
import android.net.Uri;
import android.provider.MediaStore;
import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Files;
import java.util.Random;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;
import org.junit.runner.RunWith;
import org.robolectric.RobolectricTestRunner;
import org.robolectric.RuntimeEnvironment;
import org.robolectric.annotation.Config;
import org.robolectric.annotation.GraphicsMode;

@RunWith(RobolectricTestRunner.class)
@Config(sdk = 34, manifest = Config.NONE)
@GraphicsMode(GraphicsMode.Mode.NATIVE)
public class DiaryPhotoImportTest {
    @Rule public TemporaryFolder temporary = new TemporaryFolder();

    private File image(int width, int height, boolean noise, Bitmap.CompressFormat format) throws IOException {
        File file = temporary.newFile();
        Bitmap bitmap = Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888);
        bitmap.eraseColor(Color.argb(128, 20, 100, 180));
        if (noise) {
            Random random = new Random(42);
            int[] row = new int[width];
            for (int y = 0; y < height; y++) {
                for (int x = 0; x < width; x++) {
                    row[x] = random.nextInt() | 0xff000000;
                }
                bitmap.setPixels(row, 0, width, 0, y, width, 1);
            }
        }
        try (FileOutputStream output = new FileOutputStream(file)) {
            assertTrue(bitmap.compress(format, 95, output));
        } finally {
            bitmap.recycle();
        }
        return file;
    }

    private File copy(File source, File directory) throws IOException {
        return DiaryPhotoImport.copy(RuntimeEnvironment.getApplication().getContentResolver(),
                Uri.fromFile(source), directory);
    }

    @Test public void android14UsesPermissionFreeSingleImagePicker() {
        Intent intent = DiaryPhotoImport.pickerIntent();
        assertEquals(MediaStore.ACTION_PICK_IMAGES, intent.getAction());
        assertEquals("image/*", intent.getType());
        assertFalse(intent.getBooleanExtra(Intent.EXTRA_ALLOW_MULTIPLE, false));
    }

    @Test @Config(sdk = 28) public void olderAndroidUsesOpenDocument() {
        Intent intent = DiaryPhotoImport.pickerIntent();
        assertEquals(Intent.ACTION_OPEN_DOCUMENT, intent.getAction());
        assertTrue(intent.hasCategory(Intent.CATEGORY_OPENABLE));
    }

    @Test public void largeNoisyImageFitsBothLimitsAndOriginalStaysUntouched() throws Exception {
        File source = image(3200, 2400, true, Bitmap.CompressFormat.PNG);
        byte[] original = Files.readAllBytes(source.toPath());
        File directory = temporary.newFolder();
        File result = copy(source, directory);
        assertTrue(result.length() > 0);
        assertTrue(result.length() <= DiaryPhotoImport.MAX_BYTES);
        assertTrue(result.length() < source.length() / 10);
        byte[] encoded = Files.readAllBytes(result.toPath());
        assertEquals(255, encoded[0] & 255);
        assertEquals(216, encoded[1] & 255);
        Bitmap bitmap = BitmapFactory.decodeFile(result.getAbsolutePath());
        assertNotNull(bitmap);
        assertTrue(bitmap.getWidth() <= DiaryPhotoImport.MAX_EDGE);
        assertEquals(4.0 / 3.0, (double) bitmap.getWidth() / bitmap.getHeight(), 0.01);
        bitmap.recycle();
        assertArrayEquals(original, Files.readAllBytes(source.toPath()));
        assertArrayEquals(new String[]{result.getName()}, directory.list());
    }

    @Test @Config(sdk = {27, 34})
    public void smallTransparentImageKeepsSizeAndAlphaAndAllowsAnotherAttachment() throws Exception {
        File source = image(120, 80, false, Bitmap.CompressFormat.PNG);
        File directory = temporary.newFolder();
        File first = copy(source, directory);
        File second = copy(source, directory);
        assertNotEquals(first, second);
        byte[] encoded = Files.readAllBytes(first.toPath());
        assertEquals(137, encoded[0] & 255);
        assertEquals('P', encoded[1]);
        Bitmap bitmap = BitmapFactory.decodeFile(first.getAbsolutePath());
        assertEquals(120, bitmap.getWidth());
        assertEquals(80, bitmap.getHeight());
        assertEquals(128, Color.alpha(bitmap.getPixel(40, 40)), 1);
        bitmap.recycle();
        assertEquals(2, directory.list().length);
    }

    @Test @Config(sdk = {27, 34})
    public void rotatedJpegIsUprightAndDropsLocationMetadata() throws Exception {
        File source = image(240, 120, false, Bitmap.CompressFormat.JPEG);
        ExifInterface exif = new ExifInterface(source.getAbsolutePath());
        exif.setAttribute(ExifInterface.TAG_ORIENTATION, "6");
        exif.setAttribute(ExifInterface.TAG_GPS_LATITUDE, "25/1,18/1,0/1");
        exif.setAttribute(ExifInterface.TAG_GPS_LATITUDE_REF, "S");
        exif.saveAttributes();
        File result = copy(source, temporary.newFolder());
        Bitmap bitmap = BitmapFactory.decodeFile(result.getAbsolutePath());
        assertEquals(120, bitmap.getWidth());
        assertEquals(240, bitmap.getHeight());
        bitmap.recycle();
        ExifInterface outputExif = new ExifInterface(result.getAbsolutePath());
        assertNull(outputExif.getAttribute(ExifInterface.TAG_GPS_LATITUDE));
    }

    @Test public void invalidPhotoLeavesNoCacheFiles() throws Exception {
        File source = temporary.newFile();
        Files.write(source.toPath(), new byte[]{1, 2, 3, 4});
        File directory = temporary.newFolder();
        try {
            copy(source, directory);
            fail("Invalid image was accepted");
        } catch (IOException expected) {
            assertEquals(0, directory.list().length);
            assertTrue(source.isFile());
        }
    }

    @Test public void sourceCopyStopsAtLimit() throws Exception {
        File destination = temporary.newFile();
        InputStream oversized = new InputStream() {
            @Override public int read() { return 0; }
            @Override public int read(byte[] bytes, int offset, int length) { return length; }
        };
        try (FileOutputStream output = new FileOutputStream(destination)) {
            try {
                DiaryPhotoImport.copySource(oversized, output);
                fail("Oversized input was accepted");
            } catch (IOException expected) {
                assertEquals(DiaryPhotoImport.MAX_SOURCE_BYTES, destination.length());
            }
        }
    }
}
