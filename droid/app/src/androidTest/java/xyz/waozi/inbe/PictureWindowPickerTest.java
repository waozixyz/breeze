package xyz.waozi.inbe;

import android.content.Intent;
import android.provider.MediaStore;
import android.test.InstrumentationTestCase;

// A running practice floated into picture-in-picture when the app opened its
// own photo picker; on Android 12 the picker then closed into an empty task
// and reopening the app crashed (owner's Pixel, 2026-11-16). Screens the app
// opens in its own task must hold the floating window; other apps opened in
// their own tasks may still let the practice float.
public class PictureWindowPickerTest extends InstrumentationTestCase {
    public void testPickersAndOwnScreensHoldTheFloatingWindow() {
        Intent document = new Intent(Intent.ACTION_OPEN_DOCUMENT);
        document.addCategory(Intent.CATEGORY_OPENABLE);
        document.setType("image/*");
        assertTrue(MainActivity.opensInThisTask(document));

        Intent photos = new Intent(MediaStore.ACTION_PICK_IMAGES);
        photos.setType("image/*");
        assertTrue(MainActivity.opensInThisTask(photos));

        Intent share = Intent.createChooser(new Intent(Intent.ACTION_SEND), null);
        assertTrue(MainActivity.opensInThisTask(share));
    }

    public void testOtherAppsInTheirOwnTasksMayFloat() {
        Intent browser = new Intent(Intent.ACTION_VIEW);
        browser.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        assertFalse(MainActivity.opensInThisTask(browser));

        Intent document = new Intent(Intent.ACTION_VIEW);
        document.addFlags(Intent.FLAG_ACTIVITY_NEW_DOCUMENT);
        assertFalse(MainActivity.opensInThisTask(document));

        assertFalse(MainActivity.opensInThisTask(null));
    }
}
