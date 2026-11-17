package xyz.waozi.inbe;

import android.test.InstrumentationTestCase;
import android.content.Intent;
import android.os.Build;
import android.os.SystemClock;
import android.view.KeyEvent;
import android.view.MotionEvent;
import android.view.inputmethod.BaseInputConnection;
import android.view.inputmethod.EditorInfo;
import android.view.inputmethod.InputConnection;
import java.nio.charset.StandardCharsets;
import java.lang.reflect.Field;

public class TextInputViewTest extends InstrumentationTestCase {
    private static byte[] bytes(String value) {
        return value.getBytes(StandardCharsets.UTF_8);
    }

    private static final class Changes implements TextInputView.Listener {
        String value;
        long revision;
        int cursor;
        int anchor;
        int count;
        @Override public void changed(long target, long revision, byte[] value, int cursor, int anchor) {
            this.value = new String(value, StandardCharsets.UTF_8);
            this.revision = revision;
            this.cursor = cursor;
            this.anchor = anchor;
            count++;
        }
        @Override public void enter() {}
    }

    /** The runner seeds Diary in its private 480x960 Android emulator. */
    public void testImeDeleteKeysInNativeActivity() throws Exception {
        assertTrue("This test owns a private emulator only",
            Build.HARDWARE.equals("ranchu") || Build.HARDWARE.equals("goldfish"));
        Intent launch = new Intent(getInstrumentation().getTargetContext(), MainActivity.class);
        launch.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        MainActivity activity = (MainActivity)getInstrumentation().startActivitySync(launch);
        SystemClock.sleep(3000);
        long now = SystemClock.uptimeMillis();
        MotionEvent down = MotionEvent.obtain(now, now, MotionEvent.ACTION_DOWN, 250, 250, 0);
        getInstrumentation().sendPointerSync(down);
        down.recycle();
        MotionEvent up = MotionEvent.obtain(now, SystemClock.uptimeMillis(), MotionEvent.ACTION_UP, 250, 250, 0);
        getInstrumentation().sendPointerSync(up);
        up.recycle();
        SystemClock.sleep(1000);
        Field input = MainActivity.class.getDeclaredField("textInputView");
        input.setAccessible(true);
        TextInputView editor = (TextInputView)input.get(activity);
        Field target = TextInputView.class.getDeclaredField("target");
        target.setAccessible(true);
        assertTrue("Diary must own the native editor", target.getLong(editor) > 0);
        assertTrue(editor.hasFocus());
        awaitSeededEntry(editor);
        InputConnection[] connection = new InputConnection[1];
        getInstrumentation().runOnMainSync(() -> {
            connection[0] = editor.onCreateInputConnection(new EditorInfo());
            // The emulator's own keyboard may compose the word at the caret;
            // commitText replaces that region instead of the selection.
            connection[0].finishComposingText();
            connection[0].setSelection(0, editor.length());
            connection[0].commitText("alpha 水😀 omega", 1);
        });
        awaitText(editor, "alpha 水😀 omega");
        getInstrumentation().runOnMainSync(() -> {
            connection[0].sendKeyEvent(new KeyEvent(KeyEvent.ACTION_DOWN, KeyEvent.KEYCODE_DEL));
            connection[0].sendKeyEvent(new KeyEvent(KeyEvent.ACTION_UP, KeyEvent.KEYCODE_DEL));
        });
        awaitText(editor, "alpha 水😀 omeg");
        getInstrumentation().runOnMainSync(() -> {
            connection[0].setSelection(6, 9);
            connection[0].sendKeyEvent(new KeyEvent(KeyEvent.ACTION_DOWN, KeyEvent.KEYCODE_DEL));
            connection[0].sendKeyEvent(new KeyEvent(KeyEvent.ACTION_UP, KeyEvent.KEYCODE_DEL));
        });
        awaitText(editor, "alpha  omeg");
        assertEquals(6, editor.getSelectionStart());
        assertEquals(6, editor.getSelectionEnd());
    }

    /** Kryon publishes the focused Diary entry before the IME replaces it. */
    private void awaitSeededEntry(TextInputView editor) {
        long deadline = SystemClock.uptimeMillis() + 7000;
        int[] length = { 0 };
        do {
            getInstrumentation().runOnMainSync(() -> length[0] = editor.length());
            if (length[0] > 0) {
                return;
            }
            SystemClock.sleep(100);
        } while (SystemClock.uptimeMillis() < deadline);
        fail("Diary did not publish its seeded entry to the native editor");
    }

    private void awaitText(TextInputView editor, String expected) throws Exception {
        Field revision = TextInputView.class.getDeclaredField("revision");
        revision.setAccessible(true);
        Field acknowledged = TextInputView.class.getDeclaredField("acknowledgedRevision");
        acknowledged.setAccessible(true);
        long deadline = SystemClock.uptimeMillis() + 7000;
        String[] value = { "" };
        do {
            getInstrumentation().runOnMainSync(() -> value[0] = editor.getText().toString());
            if (value[0].equals(expected) && acknowledged.getLong(editor) >= revision.getLong(editor)) {
                return;
            }
            SystemClock.sleep(100);
        } while (SystemClock.uptimeMillis() < deadline);
        assertEquals(expected, value[0]);
        assertEquals("Native widget must acknowledge the edit", revision.getLong(editor),
            acknowledged.getLong(editor));
    }

    public void testSwipeCompositionCorrectionsAndUnicode() {
        getInstrumentation().runOnMainSync(() -> {
            Changes changes = new Changes();
            TextInputView view = new TextInputView(getInstrumentation().getTargetContext(), changes);
            view.update(1, 0, bytes("prefix "), 7, 7, false, false, true);
            InputConnection connection = view.onCreateInputConnection(new EditorInfo());
            assertNotNull(connection);
            connection.beginBatchEdit();
            assertTrue(connection.setComposingText("hel", 1));
            assertTrue(connection.setComposingText("hello", 1));
            connection.endBatchEdit();
            assertEquals("prefix hello", changes.value);
            assertEquals(12, changes.cursor);
            long acknowledged = changes.revision;
            view.update(1, acknowledged, bytes(changes.value), 12, 12, false, false, true);
            assertTrue(BaseInputConnection.getComposingSpanStart(view.getText()) >= 0);
            assertTrue(connection.commitText("hello ", 1));
            assertEquals("prefix hello ", changes.value);
            assertTrue(connection.commitText("水😀", 1));
            assertEquals("prefix hello 水😀", changes.value);
            assertEquals(20, changes.cursor);
            assertTrue(connection.deleteSurroundingTextInCodePoints(1, 0));
            assertEquals("prefix hello 水", changes.value);
            assertEquals(16, changes.cursor);
            assertTrue(connection.setSelection(0, 6));
            assertTrue(connection.commitText("start", 1));
            assertEquals("start hello 水", changes.value);
            assertEquals(5, changes.cursor);
            assertTrue(connection.commitText("\n", 1));
            assertEquals("start\n hello 水", changes.value);
        });
    }

    public void testStaleAcknowledgementAndOldConnectionCannotReplaceNewField() {
        getInstrumentation().runOnMainSync(() -> {
            Changes changes = new Changes();
            TextInputView view = new TextInputView(getInstrumentation().getTargetContext(), changes);
            view.update(10, 0, bytes(""), 0, 0, false, false, true);
            InputConnection old = view.onCreateInputConnection(new EditorInfo());
            assertTrue(old.commitText("fresh", 1));
            view.update(10, 0, bytes("stale"), 5, 5, false, false, true);
            assertEquals("fresh", view.getText().toString());
            view.update(11, 0, bytes("saved"), 5, 5, false, false, true);
            assertFalse(old.commitText("late", 1));
            assertEquals("saved", view.getText().toString());
            InputConnection current = view.onCreateInputConnection(new EditorInfo());
            assertTrue(current.commitText(" draft", 1));
            assertEquals("saved draft", changes.value);
            view.deactivate();
            assertFalse(current.commitText("after blur", 1));
        });
    }
}
