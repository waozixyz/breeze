package xyz.waozi.inbe;

import android.content.Context;
import android.text.Editable;
import android.text.InputType;
import android.text.TextWatcher;
import android.view.KeyEvent;
import android.view.View;
import android.view.inputmethod.EditorInfo;
import android.view.inputmethod.InputConnection;
import android.view.inputmethod.InputConnectionWrapper;
import android.view.inputmethod.InputMethodManager;
import android.view.inputmethod.TextAttribute;
import android.widget.EditText;
import java.nio.charset.StandardCharsets;

/** The IME's editor. Kryon renders and validates the actual focused field. */
final class TextInputView extends EditText {
    interface Listener {
        void changed(long target, long revision, byte[] value, int cursor, int anchor);
        void enter();
    }

    private final Listener listener;
    private long target;
    private long revision;
    private long acknowledgedRevision;
    private boolean restoring;
    private int batchDepth;
    private boolean dirty;
    private boolean secure;
    private boolean multiline;

    TextInputView(Context context, Listener listener) {
        super(context);
        this.listener = listener;
        setFocusableInTouchMode(true);
        setBackground(null);
        setPadding(0, 0, 0, 0);
        setAlpha(0);
        setCursorVisible(false);
        setImportantForAccessibility(View.IMPORTANT_FOR_ACCESSIBILITY_NO);
        setImeOptions(EditorInfo.IME_FLAG_NO_EXTRACT_UI | EditorInfo.IME_FLAG_NO_FULLSCREEN);
        addTextChangedListener(new TextWatcher() {
            @Override public void beforeTextChanged(CharSequence text, int start, int count, int after) {}
            @Override public void onTextChanged(CharSequence text, int start, int before, int count) {}
            @Override public void afterTextChanged(Editable text) { publish(); }
        });
        setOnEditorActionListener((view, action, event) -> {
            if (!multiline && action != EditorInfo.IME_NULL) {
                listener.enter();
                return true;
            }
            return false;
        });
    }

    private static int byteOffset(String value, int characterOffset) {
        int offset = Math.max(0, Math.min(characterOffset, value.length()));
        if (offset > 0 && offset < value.length() && Character.isLowSurrogate(value.charAt(offset))) {
            offset--;
        }
        return value.substring(0, offset).getBytes(StandardCharsets.UTF_8).length;
    }

    private static int characterOffset(String value, int byteOffset) {
        int bytes = 0;
        int offset = 0;
        while (offset < value.length() && bytes < byteOffset) {
            int point = value.codePointAt(offset);
            int width = point < 128 ? 1 : point < 2048 ? 2 : point < 65536 ? 3 : 4;
            if (bytes + width > byteOffset) {
                break;
            }
            bytes += width;
            offset += Character.charCount(point);
        }
        return offset;
    }

    private void publish() {
        if (restoring || target == 0 || listener == null) {
            return;
        }
        if (batchDepth > 0) {
            dirty = true;
            return;
        }
        String value = getText().toString();
        revision++;
        listener.changed(target, revision, value.getBytes(StandardCharsets.UTF_8),
            byteOffset(value, getSelectionEnd()), byteOffset(value, getSelectionStart()));
        dirty = false;
    }

    @Override protected void onSelectionChanged(int start, int end) {
        super.onSelectionChanged(start, end);
        publish();
    }

    void update(long target, long acknowledged, byte[] bytes, int cursor, int anchor,
                boolean secure, boolean multiline) {
        boolean changedTarget = this.target != target;
        if (!changedTarget && acknowledged < revision) {
            return;
        }
        String value = new String(bytes, StandardCharsets.UTF_8);
        boolean changedType = this.secure != secure || this.multiline != multiline;
        restoring = true;
        try {
            this.target = target;
            this.revision = acknowledged;
            this.acknowledgedRevision = acknowledged;
            if (changedTarget) {
                batchDepth = 0;
            }
            if (changedType || changedTarget) {
                int type = InputType.TYPE_CLASS_TEXT;
                if (secure) {
                    type |= InputType.TYPE_TEXT_VARIATION_PASSWORD;
                } else {
                    type |= InputType.TYPE_TEXT_FLAG_AUTO_CORRECT | InputType.TYPE_TEXT_FLAG_CAP_SENTENCES;
                }
                if (multiline) {
                    type |= InputType.TYPE_TEXT_FLAG_MULTI_LINE;
                }
                setInputType(type);
                setImeOptions(EditorInfo.IME_FLAG_NO_EXTRACT_UI | EditorInfo.IME_FLAG_NO_FULLSCREEN
                    | (secure ? EditorInfo.IME_FLAG_NO_PERSONALIZED_LEARNING : 0)
                    | (multiline ? EditorInfo.IME_ACTION_NONE : EditorInfo.IME_ACTION_DONE));
                this.secure = secure;
                this.multiline = multiline;
            }
            // Preserve composing spans when acknowledging the same text.
            if (!getText().toString().equals(value) || changedTarget) {
                setText(value);
            }
            int start = characterOffset(value, anchor);
            int end = characterOffset(value, cursor);
            if (getSelectionStart() != start || getSelectionEnd() != end) {
                setSelection(start, end);
            }
            dirty = false;
        } finally {
            restoring = false;
        }
        if (changedTarget || changedType) {
            InputMethodManager manager = (InputMethodManager)getContext().getSystemService(Context.INPUT_METHOD_SERVICE);
            if (manager != null && hasFocus()) {
                manager.restartInput(this);
            }
        }
    }

    void deactivate() {
        target = 0;
        dirty = false;
        clearFocus();
    }

    @Override public InputConnection onCreateInputConnection(EditorInfo info) {
        InputConnection connection = super.onCreateInputConnection(info);
        if (connection == null) {
            return null;
        }
        final long connectionTarget = target;
        return new InputConnectionWrapper(connection, false) {
            private boolean current() {
                return target != 0 && target == connectionTarget;
            }

            @Override public boolean beginBatchEdit() {
                if (!current()) {
                    return false;
                }
                batchDepth++;
                return super.beginBatchEdit();
            }

            @Override public boolean endBatchEdit() {
                if (!current()) {
                    return false;
                }
                boolean result = super.endBatchEdit();
                if (batchDepth > 0) {
                    batchDepth--;
                }
                if (batchDepth == 0 && dirty) {
                    publish();
                }
                return result;
            }

            @Override public boolean sendKeyEvent(KeyEvent event) {
                // EditText owns text keys; Activity must not also queue them.
                return current() && super.sendKeyEvent(event);
            }

            @Override public boolean commitText(CharSequence text, int cursor) {
                return current() && super.commitText(text, cursor);
            }

            @Override public boolean commitText(CharSequence text, int cursor, TextAttribute attributes) {
                return commitText(text, cursor);
            }

            @Override public boolean setComposingText(CharSequence text, int cursor) {
                return current() && super.setComposingText(text, cursor);
            }

            @Override public boolean setComposingText(CharSequence text, int cursor, TextAttribute attributes) {
                return setComposingText(text, cursor);
            }

            @Override public boolean setComposingRegion(int start, int end) {
                return current() && super.setComposingRegion(start, end);
            }

            @Override public boolean setComposingRegion(int start, int end, TextAttribute attributes) {
                return setComposingRegion(start, end);
            }

            @Override public boolean finishComposingText() {
                return current() && super.finishComposingText();
            }

            @Override public boolean setSelection(int start, int end) {
                return current() && super.setSelection(start, end);
            }

            @Override public boolean deleteSurroundingText(int before, int after) {
                return current() && super.deleteSurroundingText(before, after);
            }

            @Override public boolean deleteSurroundingTextInCodePoints(int before, int after) {
                return current() && super.deleteSurroundingTextInCodePoints(before, after);
            }

            @Override public boolean performEditorAction(int action) {
                return current() && super.performEditorAction(action);
            }

            @Override public boolean replaceText(int start, int end, CharSequence text,
                                                 int cursor, TextAttribute attributes) {
                if (!current()) {
                    return false;
                }
                beginBatchEdit();
                try {
                    finishComposingText();
                    setSelection(start, end);
                    return commitText(text, cursor);
                } finally {
                    endBatchEdit();
                }
            }
        };
    }
}
