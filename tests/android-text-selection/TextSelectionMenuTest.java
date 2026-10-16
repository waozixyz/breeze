package xyz.waozi.inbe;

import static org.junit.Assert.*;

import android.content.Context;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.graphics.Rect;
import android.net.Uri;
import android.view.ActionMode;
import android.view.Menu;
import android.view.MenuInflater;
import android.view.View;
import android.view.inputmethod.EditorInfo;
import android.view.inputmethod.InputConnection;
import android.widget.PopupMenu;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.robolectric.RobolectricTestRunner;
import org.robolectric.RuntimeEnvironment;
import org.robolectric.annotation.Config;
import java.nio.charset.StandardCharsets;

@RunWith(RobolectricTestRunner.class)
@Config(sdk = {34, 36}, manifest = Config.NONE)
public class TextSelectionMenuTest {
    private static final class Mode extends ActionMode {
        final Callback callback;
        final Menu menu;
        final View view;
        boolean finished;

        Mode(View view, Callback callback) {
            this.view = view;
            this.callback = callback;
            menu = new PopupMenu(view.getContext(), view).getMenu();
            assertTrue(callback.onCreateActionMode(this, menu));
        }
        @Override public void setTitle(CharSequence title) {}
        @Override public void setTitle(int title) {}
        @Override public void setSubtitle(CharSequence subtitle) {}
        @Override public void setSubtitle(int subtitle) {}
        @Override public void setCustomView(View view) {}
        @Override public void invalidate() { callback.onPrepareActionMode(this, menu); }
        @Override public void finish() {
            if (!finished) {
                finished = true;
                callback.onDestroyActionMode(this);
            }
        }
        @Override public Menu getMenu() { return menu; }
        @Override public MenuInflater getMenuInflater() { return new MenuInflater(view.getContext()); }
        @Override public CharSequence getTitle() { return ""; }
        @Override public CharSequence getSubtitle() { return ""; }
        @Override public View getCustomView() { return null; }
    }

    private static final class ToolbarView extends View {
        Mode last;
        int count;
        int type;
        ToolbarView(Context context) { super(context); }
        @Override public ActionMode startActionMode(ActionMode.Callback callback, int type) {
            this.type = type;
            count++;
            last = new Mode(this, callback);
            return last;
        }
    }

    @Test public void floatingToolbarUsesPlatformLabelsAndPreservesChosenCommand() {
        ToolbarView view = new ToolbarView(RuntimeEnvironment.getApplication());
        TextSelectionMenu menu = new TextSelectionMenu(view);
        menu.show(1, 120, 240, 15);
        assertEquals(ActionMode.TYPE_FLOATING, view.type);
        assertEquals(4, view.last.menu.size());
        assertEquals(view.getContext().getString(android.R.string.copy), view.last.menu.findItem(2).getTitle());
        Rect content = new Rect();
        ((ActionMode.Callback2)view.last.callback).onGetContentRect(view.last, view, content);
        assertEquals(new Rect(120, 240, 121, 241), content);
        assertTrue(view.last.callback.onActionItemClicked(view.last, view.last.menu.findItem(2)));
        assertEquals(2, menu.take(1));
        menu.show(1, 120, 240, 15);
        assertEquals(1, view.count);
    }

    @Test public void chatToolbarHasOnlyCopyAndSelectAllAndRejectsStaleActions() {
        ToolbarView view = new ToolbarView(RuntimeEnvironment.getApplication());
        TextSelectionMenu menu = new TextSelectionMenu(view);
        menu.show(1, 10, 20, 15);
        Mode old = view.last;
        menu.show(2, 20, 30, 10);
        assertTrue(old.finished);
        assertEquals(2, view.last.menu.size());
        assertNull(view.last.menu.findItem(1));
        assertNull(view.last.menu.findItem(3));
        assertFalse(old.callback.onActionItemClicked(old, old.menu.findItem(2)));
        assertEquals(0, menu.take(2));
        assertTrue(view.last.callback.onActionItemClicked(view.last, view.last.menu.findItem(4)));
        assertEquals(4, menu.take(2));
    }

    @Test public void dismissalDoesNotReopenUntilAnotherSelectionRequestsIt() {
        ToolbarView view = new ToolbarView(RuntimeEnvironment.getApplication());
        TextSelectionMenu menu = new TextSelectionMenu(view);
        menu.show(1, 10, 20, 10);
        view.last.finish();
        assertEquals(-1, menu.take(1));
        menu.show(1, 10, 20, 10);
        assertEquals(1, view.count);
        menu.show(2, 20, 30, 4);
        assertEquals(2, view.count);
        assertEquals(1, view.last.menu.size());
        assertTrue(view.last.callback.onActionItemClicked(view.last, view.last.menu.findItem(3)));
        assertEquals(3, menu.take(2));
    }

    @Test public void editingStillSupportsCompositionUnicodeAndStaleAcknowledgements() {
        final String[] latest = {""};
        final long[] revision = {0};
        TextInputView editor = new TextInputView(RuntimeEnvironment.getApplication(), new TextInputView.Listener() {
            @Override public void changed(long target, long next, byte[] text, int cursor, int anchor) {
                latest[0] = new String(text, StandardCharsets.UTF_8);
                revision[0] = next;
            }
            @Override public void enter() {}
        });
        editor.update(1, 0, "hello ".getBytes(StandardCharsets.UTF_8), 6, 6, false, false, true);
        InputConnection connection = editor.onCreateInputConnection(new EditorInfo());
        assertNotNull(connection);
        assertTrue(connection.setComposingText("calm", 1));
        assertTrue(connection.commitText("水😀", 1));
        assertEquals("hello 水😀", latest[0]);
        editor.update(1, 0, "old".getBytes(StandardCharsets.UTF_8), 3, 3, false, false, true);
        assertEquals("hello 水😀", editor.getText().toString());
        assertTrue(connection.setSelection(0, 5));
        assertTrue(connection.commitText("fresh", 1));
        assertEquals("fresh 水😀", latest[0]);
        editor.update(2, 0, "saved".getBytes(StandardCharsets.UTF_8), 5, 5, false, false, true);
        assertFalse(connection.commitText("late", 1));
        assertEquals("saved", editor.getText().toString());
        assertTrue(revision[0] > 0);
    }

    @Test public void systemClipboardPreservesUnicodeAndIgnoresNonTextClips() {
        Context context = RuntimeEnvironment.getApplication();
        byte[] text = "Diary\n水😀 é".getBytes(StandardCharsets.UTF_8);
        assertTrue(TextClipboard.write(context, text));
        assertArrayEquals(text, TextClipboard.read(context));
        ClipboardManager clipboard = (ClipboardManager)context.getSystemService(Context.CLIPBOARD_SERVICE);
        assertEquals("Diary\n水😀 é", clipboard.getPrimaryClip().getItemAt(0).getText().toString());
        clipboard.setPrimaryClip(ClipData.newRawUri("image", Uri.parse("content://example/image")));
        assertArrayEquals(new byte[0], TextClipboard.read(context));
        assertTrue(TextClipboard.write(context, new byte[0]));
        assertArrayEquals(new byte[0], TextClipboard.read(context));
        assertFalse(TextClipboard.write(context, null));
    }
}
