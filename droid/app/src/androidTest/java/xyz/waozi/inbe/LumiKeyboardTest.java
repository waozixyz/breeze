package xyz.waozi.inbe;

import android.content.Intent;
import android.os.SystemClock;
import android.test.InstrumentationTestCase;
import android.view.MotionEvent;
import android.view.KeyEvent;
import android.view.WindowInsets;
import android.view.inputmethod.EditorInfo;
import android.view.inputmethod.InputConnection;
import android.view.inputmethod.InputMethodManager;
import java.lang.reflect.Field;

/** Runs only in the disposable 390x844 Lumi profile prepared by the harness. */
public class LumiKeyboardTest extends InstrumentationTestCase {
    private void awaitKeyboard(MainActivity activity, boolean visible) {
        boolean[] actual = { !visible };
        long deadline = SystemClock.uptimeMillis() + 7000;
        while (actual[0] != visible && SystemClock.uptimeMillis() < deadline) {
            getInstrumentation().runOnMainSync(() -> {
                WindowInsets insets = activity.getWindow().getDecorView().getRootWindowInsets();
                actual[0] = insets != null && insets.isVisible(WindowInsets.Type.ime());
            });
            SystemClock.sleep(100);
        }
        assertEquals("Keyboard visibility", visible, actual[0]);
    }

    private void tap(int x, int y) {
        long now = SystemClock.uptimeMillis();
        MotionEvent down = MotionEvent.obtain(now, now, MotionEvent.ACTION_DOWN, x, y, 0);
        getInstrumentation().sendPointerSync(down);
        down.recycle();
        SystemClock.sleep(100);
        MotionEvent up = MotionEvent.obtain(now, SystemClock.uptimeMillis(), MotionEvent.ACTION_UP, x, y, 0);
        getInstrumentation().sendPointerSync(up);
        up.recycle();
        SystemClock.sleep(500);
    }

    public void testFirstFocusSwipeTextReachesNativeLumi() throws Exception {
        Intent launch = new Intent(getInstrumentation().getTargetContext(), MainActivity.class);
        launch.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        MainActivity activity = (MainActivity)getInstrumentation().startActivitySync(launch);
        SystemClock.sleep(4000);
        tap(80, 715);
        Field inputField = MainActivity.class.getDeclaredField("textInputView");
        inputField.setAccessible(true);
        TextInputView input = (TextInputView)inputField.get(activity);
        Field target = TextInputView.class.getDeclaredField("target");
        target.setAccessible(true);
        assertTrue("Native Lumi field did not acquire the IME", target.getLong(input) > 0);
        getInstrumentation().runOnMainSync(() -> {
            assertTrue(input.hasFocus());
            InputMethodManager manager = (InputMethodManager)activity.getSystemService(MainActivity.INPUT_METHOD_SERVICE);
            assertTrue(manager.isActive(input));
            InputConnection connection = input.onCreateInputConnection(new EditorInfo());
            assertNotNull(connection);
            connection.beginBatchEdit();
            assertTrue(connection.setComposingText("hel", 1));
            assertTrue(connection.setComposingText("hello", 1));
            assertTrue(connection.commitText("hello 水😀", 1));
            connection.endBatchEdit();
        });
        Field revision = TextInputView.class.getDeclaredField("revision");
        revision.setAccessible(true);
        long sent = revision.getLong(input);
        Field acknowledged = TextInputView.class.getDeclaredField("acknowledgedRevision");
        acknowledged.setAccessible(true);
        long deadline = SystemClock.uptimeMillis() + 7000;
        while (acknowledged.getLong(input) < sent && SystemClock.uptimeMillis() < deadline) {
            SystemClock.sleep(100);
        }
        assertEquals("Native widget did not acknowledge the IME edit", sent, acknowledged.getLong(input));
        getInstrumentation().runOnMainSync(() -> assertEquals("hello 水😀", input.getText().toString()));
        awaitKeyboard(activity, true);
        getInstrumentation().sendKeyDownUpSync(KeyEvent.KEYCODE_BACK);
        awaitKeyboard(activity, false);
        tap(80, 715);
        awaitKeyboard(activity, true);
        getInstrumentation().runOnMainSync(() -> {
            assertTrue("Lumi did not regain the editor", input.hasFocus());
            assertEquals("Dismissal changed the draft", "hello 水😀", input.getText().toString());
        });
        assertFalse(activity.isFinishing());
    }
}
