package xyz.waozi.inbe;

import android.accessibilityservice.AccessibilityServiceInfo;
import android.content.Intent;
import android.graphics.Rect;
import android.os.Build;
import android.os.ParcelFileDescriptor;
import android.os.SystemClock;
import android.test.InstrumentationTestCase;
import android.view.KeyEvent;
import android.view.InputDevice;
import android.view.MotionEvent;
import android.view.WindowInsets;
import android.view.accessibility.AccessibilityNodeInfo;
import android.view.accessibility.AccessibilityWindowInfo;
import android.view.inputmethod.EditorInfo;
import android.view.inputmethod.InputConnection;
import java.lang.reflect.Field;
import java.io.ByteArrayOutputStream;
import java.io.InputStream;

/** Physical Pixel check: never sends a message and restores the original draft. */
public class PixelLumiKeyboardTest extends InstrumentationTestCase {
    private void pointer(int action, long start, float x, float y) {
        AccessibilityNodeInfo root = getInstrumentation().getUiAutomation().getRootInActiveWindow();
        assertNotNull("No foreground window for keyboard check", root);
        String owner = String.valueOf(root.getPackageName());
        root.recycle();
        assertTrue("Another app took the foreground; stopping input",
            owner.equals("xyz.waozi.inbe.debug") || owner.equals("com.google.android.inputmethod.latin"));
        MotionEvent event = MotionEvent.obtain(start, SystemClock.uptimeMillis(), action, x, y, 0);
        event.setSource(InputDevice.SOURCE_TOUCHSCREEN);
        try {
            assertTrue("Keyboard touch was rejected", getInstrumentation().getUiAutomation().injectInputEvent(event, true));
        } finally {
            event.recycle();
        }
    }

    private void glide(Rect first, Rect second) throws Exception {
        AccessibilityNodeInfo root = getInstrumentation().getUiAutomation().getRootInActiveWindow();
        assertNotNull("No foreground window for Gboard check", root);
        String owner = String.valueOf(root.getPackageName());
        root.recycle();
        assertTrue("Another app took the foreground; stopping input",
            owner.equals("xyz.waozi.inbe.debug") || owner.equals("com.google.android.inputmethod.latin"));
        String command = "input touchscreen swipe " + first.centerX() + " " + first.centerY() +
            " " + second.centerX() + " " + second.centerY() + " 400";
        ParcelFileDescriptor pipe = getInstrumentation().getUiAutomation().executeShellCommand(command);
        ByteArrayOutputStream output = new ByteArrayOutputStream();
        try (InputStream stream = new ParcelFileDescriptor.AutoCloseInputStream(pipe)) {
            byte[] buffer = new byte[1024];
            int count;
            while ((count = stream.read(buffer)) != -1) {
                output.write(buffer, 0, count);
            }
        }
        assertEquals("Shell keyboard gesture failed", "", output.toString("UTF-8").trim());
    }

    private void focus(MainActivity activity) {
        int[] location = new int[2];
        getInstrumentation().runOnMainSync(() -> {
            WindowInsets insets = activity.getWindow().getDecorView().getRootWindowInsets();
            int bottom = insets.getInsets(WindowInsets.Type.navigationBars()).bottom;
            float density = activity.getResources().getDisplayMetrics().density;
            location[0] = activity.getWindow().getDecorView().getWidth() / 5;
            location[1] = activity.getWindow().getDecorView().getHeight() - bottom - Math.round(92 * density);
        });
        long start = SystemClock.uptimeMillis();
        pointer(MotionEvent.ACTION_DOWN, start, location[0], location[1]);
        SystemClock.sleep(250);
        pointer(MotionEvent.ACTION_UP, start, location[0], location[1]);
        SystemClock.sleep(1500);
    }

    private void openLumi(MainActivity activity) {
        int[] point = new int[2];
        getInstrumentation().runOnMainSync(() -> {
            WindowInsets insets = activity.getWindow().getDecorView().getRootWindowInsets();
            int bottom = insets.getInsets(WindowInsets.Type.navigationBars()).bottom;
            float density = activity.getResources().getDisplayMetrics().density;
            point[0] = activity.getWindow().getDecorView().getWidth() / 12;
            point[1] = activity.getWindow().getDecorView().getHeight() - bottom - Math.round(14 * density);
        });
        long start = SystemClock.uptimeMillis();
        pointer(MotionEvent.ACTION_DOWN, start, point[0], point[1]);
        SystemClock.sleep(250);
        pointer(MotionEvent.ACTION_UP, start, point[0], point[1]);
        SystemClock.sleep(1500);
    }

    private Rect findKey(AccessibilityNodeInfo node, String letter) {
        if (node == null) return null;
        CharSequence text = node.getText();
        CharSequence description = node.getContentDescription();
        if ((text != null && letter.equalsIgnoreCase(text.toString())) ||
            (description != null && letter.equalsIgnoreCase(description.toString()))) {
            Rect bounds = new Rect();
            node.getBoundsInScreen(bounds);
            if (!bounds.isEmpty()) return bounds;
        }
        for (int index = 0; index < node.getChildCount(); index++) {
            AccessibilityNodeInfo child = node.getChild(index);
            Rect result = findKey(child, letter);
            if (child != null) child.recycle();
            if (result != null) return result;
        }
        return null;
    }

    private Rect key(String letter) {
        for (AccessibilityWindowInfo window : getInstrumentation().getUiAutomation().getWindows()) {
            if (window.getType() != AccessibilityWindowInfo.TYPE_INPUT_METHOD) continue;
            AccessibilityNodeInfo root = window.getRoot();
            if (root == null) continue;
            Rect result = null;
            if ("com.google.android.inputmethod.latin".contentEquals(root.getPackageName())) {
                result = findKey(root, letter);
            }
            root.recycle();
            if (result != null) return result;
        }
        return null;
    }

    private void acknowledged(TextInputView input) throws Exception {
        Field sent = TextInputView.class.getDeclaredField("revision");
        Field accepted = TextInputView.class.getDeclaredField("acknowledgedRevision");
        sent.setAccessible(true);
        accepted.setAccessible(true);
        long deadline = SystemClock.uptimeMillis() + 7000;
        while (accepted.getLong(input) < sent.getLong(input) && SystemClock.uptimeMillis() < deadline) {
            SystemClock.sleep(100);
        }
        assertEquals("Native Lumi did not apply the keyboard edit", sent.getLong(input), accepted.getLong(input));
    }

    public void testGboardSwipeAndReopeningOnPixel() throws Exception {
        assertEquals("This check is only for the authorized Pixel", "Pixel 3a", Build.MODEL);
        AccessibilityServiceInfo service = getInstrumentation().getUiAutomation().getServiceInfo();
        service.flags |= AccessibilityServiceInfo.FLAG_RETRIEVE_INTERACTIVE_WINDOWS;
        getInstrumentation().getUiAutomation().setServiceInfo(service);
        Intent launch = new Intent(getInstrumentation().getTargetContext(), MainActivity.class);
        launch.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        MainActivity activity = (MainActivity)getInstrumentation().startActivitySync(launch);
        Field ready = MainActivity.class.getDeclaredField("firstFrameReady");
        ready.setAccessible(true);
        long deadline = SystemClock.uptimeMillis() + 15000;
        while (!ready.getBoolean(activity) && SystemClock.uptimeMillis() < deadline) {
            SystemClock.sleep(100);
        }
        assertTrue("Native first frame did not finish", ready.getBoolean(activity));
        openLumi(activity);
        focus(activity);
        Field field = MainActivity.class.getDeclaredField("textInputView");
        field.setAccessible(true);
        TextInputView input = (TextInputView)field.get(activity);
        String[] original = new String[1];
        InputConnection[] connection = new InputConnection[1];
        boolean[] focused = new boolean[1];
        getInstrumentation().runOnMainSync(() -> {
            focused[0] = input.hasFocus();
            original[0] = input.getText().toString();
            connection[0] = input.onCreateInputConnection(new EditorInfo());
        });
        assertTrue("Lumi did not focus its editor", focused[0]);
        assertNotNull(connection[0]);
        getInstrumentation().runOnMainSync(() -> {
            connection[0].setSelection(0, input.length());
            connection[0].commitText("", 1);
        });
        try {
            acknowledged(input);
            Rect first = key("w");
            Rect second = key("e");
            assertNotNull("Gboard W key unavailable", first);
            assertNotNull("Gboard E key unavailable", second);
            glide(first, second);
            SystemClock.sleep(1500);
            boolean[] typed = new boolean[1];
            getInstrumentation().runOnMainSync(() -> typed[0] = input.length() > 0);
            assertTrue("Gboard glide did not produce text", typed[0]);
            acknowledged(input);
            getInstrumentation().sendKeyDownUpSync(KeyEvent.KEYCODE_BACK);
            SystemClock.sleep(1000);
            focus(activity);
            assertNotNull("Keyboard did not reopen", key("w"));
            assertFalse("Activity closed during keyboard use", activity.isFinishing());
        } finally {
            getInstrumentation().runOnMainSync(() -> {
                InputConnection current = input.onCreateInputConnection(new EditorInfo());
                current.setSelection(0, input.length());
                current.commitText(original[0], 1);
            });
            acknowledged(input);
        }
    }
}
