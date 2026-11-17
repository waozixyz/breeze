package xyz.waozi.inbe;

import static org.junit.Assert.*;

import android.app.Activity;
import android.os.Looper;
import android.view.KeyEvent;
import android.view.inputmethod.EditorInfo;
import android.view.inputmethod.InputConnection;
import java.nio.charset.StandardCharsets;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.robolectric.Robolectric;
import org.robolectric.RobolectricTestRunner;
import org.robolectric.Shadows;
import org.robolectric.annotation.Config;
import org.robolectric.annotation.GraphicsMode;

@RunWith(RobolectricTestRunner.class)
@Config(sdk = {31, 32, 34, 36}, manifest = Config.NONE)
@GraphicsMode(GraphicsMode.Mode.NATIVE)
public class TextInputEditingTest {
    private static final class Changes implements TextInputView.Listener {
        String value = "";
        long revision;
        int cursor;
        int anchor;
        int count;
        int enters;

        @Override public void changed(long target, long revision, byte[] value, int cursor, int anchor) {
            this.value = new String(value, StandardCharsets.UTF_8);
            this.revision = revision;
            this.cursor = cursor;
            this.anchor = anchor;
            count++;
        }
        @Override public void enter() {
            enters++;
        }
    }

    private static byte[] bytes(String value) {
        return value.getBytes(StandardCharsets.UTF_8);
    }

    private static void key(InputConnection connection, int code) {
        connection.sendKeyEvent(new KeyEvent(KeyEvent.ACTION_DOWN, code));
        connection.sendKeyEvent(new KeyEvent(KeyEvent.ACTION_UP, code));
        Shadows.shadowOf(Looper.getMainLooper()).idle();
    }

    @Test public void imeDeleteKeysRemoveTextAndSelections() {
        try (var activity = Robolectric.buildActivity(Activity.class).setup().visible()) {
            Changes changes = new Changes();
            TextInputView editor = new TextInputView(activity.get(), changes);
            activity.get().setContentView(editor);
            editor.update(1, 0, bytes(""), 0, 0, false, false, true);
            assertTrue(editor.requestFocus());
            InputConnection connection = editor.onCreateInputConnection(new EditorInfo());
            assertNotNull(connection);
            assertTrue(connection.commitText("alpha 水😀 omega", 1));
            int before = changes.count;
            key(connection, KeyEvent.KEYCODE_DEL);
            assertEquals("alpha 水😀 omeg", changes.value);
            assertEquals(before + 1, changes.count);
            editor.update(1, changes.revision, bytes(changes.value), changes.cursor, changes.anchor,
                false, false, true);
            assertTrue(connection.setSelection(6, 9));
            key(connection, KeyEvent.KEYCODE_DEL);
            assertEquals("alpha  omeg", changes.value);
            assertEquals(6, changes.cursor);
            assertEquals(6, changes.anchor);
            key(connection, KeyEvent.KEYCODE_FORWARD_DEL);
            assertEquals("alpha omeg", changes.value);
            assertTrue(connection.setSelection(0, editor.length()));
            key(connection, KeyEvent.KEYCODE_DEL);
            assertEquals("", changes.value);
            assertEquals(0, changes.cursor);
            assertEquals(0, changes.anchor);
            editor.update(2, 0, bytes("next"), 4, 4, false, false, true);
            key(connection, KeyEvent.KEYCODE_DEL);
            assertEquals("next", editor.getText().toString());
        }
    }

    @Test public void imeEnterKeySubmitsSingleLineAndBreaksMultiline() {
        try (var activity = Robolectric.buildActivity(Activity.class).setup().visible()) {
            Changes changes = new Changes();
            TextInputView editor = new TextInputView(activity.get(), changes);
            activity.get().setContentView(editor);
            editor.update(1, 0, bytes("name"), 4, 4, false, false, false);
            assertTrue(editor.requestFocus());
            InputConnection connection = editor.onCreateInputConnection(new EditorInfo());
            assertNotNull(connection);
            key(connection, KeyEvent.KEYCODE_ENTER);
            assertEquals(1, changes.enters);
            assertEquals("name", editor.getText().toString());
            editor.update(2, 0, bytes("line"), 4, 4, false, false, true);
            connection = editor.onCreateInputConnection(new EditorInfo());
            assertNotNull(connection);
            key(connection, KeyEvent.KEYCODE_ENTER);
            assertEquals(1, changes.enters);
            assertEquals("line\n", changes.value);
            assertEquals(5, changes.cursor);
        }
    }

    @Test public void imeSurroundingDeleteAndCorrectionsKeepUnicodeAndCursor() {
        Changes changes = new Changes();
        TextInputView editor = new TextInputView(org.robolectric.RuntimeEnvironment.getApplication(), changes);
        editor.update(1, 0, bytes(""), 0, 0, false, false, true);
        InputConnection connection = editor.onCreateInputConnection(new EditorInfo());
        assertNotNull(connection);
        assertTrue(connection.commitText("hello 水😀", 1));
        assertTrue(connection.deleteSurroundingTextInCodePoints(1, 0));
        assertEquals("hello 水", changes.value);
        assertEquals(9, changes.cursor);
        assertTrue(connection.deleteSurroundingText(1, 0));
        assertEquals("hello ", changes.value);
        assertTrue(connection.setSelection(0, 5));
        assertTrue(connection.setComposingText("calm", 1));
        assertTrue(connection.commitText("calmer", 1));
        assertEquals("calmer ", changes.value);
        assertEquals(6, changes.cursor);
        assertEquals(6, changes.anchor);
    }
}
