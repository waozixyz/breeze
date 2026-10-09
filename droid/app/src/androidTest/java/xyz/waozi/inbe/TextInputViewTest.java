package xyz.waozi.inbe;

import android.test.InstrumentationTestCase;
import android.view.inputmethod.BaseInputConnection;
import android.view.inputmethod.EditorInfo;
import android.view.inputmethod.InputConnection;
import java.nio.charset.StandardCharsets;

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

    public void testSwipeCompositionCorrectionsAndUnicode() {
        getInstrumentation().runOnMainSync(() -> {
            Changes changes = new Changes();
            TextInputView view = new TextInputView(getInstrumentation().getTargetContext(), changes);
            view.update(1, 0, bytes("prefix "), 7, 7, false, true);
            InputConnection connection = view.onCreateInputConnection(new EditorInfo());
            assertNotNull(connection);
            connection.beginBatchEdit();
            assertTrue(connection.setComposingText("hel", 1));
            assertTrue(connection.setComposingText("hello", 1));
            connection.endBatchEdit();
            assertEquals("prefix hello", changes.value);
            assertEquals(12, changes.cursor);
            long acknowledged = changes.revision;
            view.update(1, acknowledged, bytes(changes.value), 12, 12, false, true);
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
            view.update(10, 0, bytes(""), 0, 0, false, true);
            InputConnection old = view.onCreateInputConnection(new EditorInfo());
            assertTrue(old.commitText("fresh", 1));
            view.update(10, 0, bytes("stale"), 5, 5, false, true);
            assertEquals("fresh", view.getText().toString());
            view.update(11, 0, bytes("saved"), 5, 5, false, true);
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
