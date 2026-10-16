package xyz.waozi.inbe;

import android.graphics.Rect;
import android.os.Build;
import android.view.ActionMode;
import android.view.Menu;
import android.view.MenuItem;
import android.view.View;

/** Presents Kryon's text commands using Android's localized selection toolbar. */
final class TextSelectionMenu {
    private final View view;
    private ActionMode mode;
    private long shownToken;
    private int flags;
    private final Rect content = new Rect();
    private volatile long resultToken;
    private volatile int result;

    TextSelectionMenu(View view) {
        this.view = view;
    }

    synchronized int take(long token) {
        return resultToken == token ? result : 0;
    }

    private synchronized void finish(long token, int command) {
        resultToken = token;
        result = command;
    }

    void show(long token, float x, float y, int flags) {
        if (flags == 0) {
            if (shownToken == token && mode != null) {
                mode.finish();
            }
            return;
        }
        if (shownToken == token && resultToken == token && result != 0) {
            return;
        }
        if (shownToken != token && mode != null) {
            mode.finish();
        }
        shownToken = token;
        boolean changed = this.flags != flags;
        this.flags = flags;
        content.set(Math.round(x), Math.round(y), Math.round(x) + 1, Math.round(y) + 1);
        if (mode != null) {
            if (changed) {
                mode.invalidate();
            }
            if (Build.VERSION.SDK_INT >= 23) {
                mode.invalidateContentRect();
            }
            return;
        }
        ActionMode.Callback callback;
        if (Build.VERSION.SDK_INT >= 23) {
            callback = new ActionMode.Callback2() {
                @Override public boolean onCreateActionMode(ActionMode mode, Menu menu) {
                    return populate(menu);
                }
                @Override public boolean onPrepareActionMode(ActionMode mode, Menu menu) {
                    return populate(menu);
                }
                @Override public boolean onActionItemClicked(ActionMode mode, MenuItem item) {
                    return choose(mode, token, item.getItemId());
                }
                @Override public void onDestroyActionMode(ActionMode ended) {
                    dismissed(ended, token);
                }
                @Override public void onGetContentRect(ActionMode mode, View view, Rect out) {
                    out.set(content);
                }
            };
            mode = view.startActionMode(callback, ActionMode.TYPE_FLOATING);
        } else {
            callback = new ActionMode.Callback() {
                @Override public boolean onCreateActionMode(ActionMode mode, Menu menu) {
                    return populate(menu);
                }
                @Override public boolean onPrepareActionMode(ActionMode mode, Menu menu) {
                    return populate(menu);
                }
                @Override public boolean onActionItemClicked(ActionMode mode, MenuItem item) {
                    return choose(mode, token, item.getItemId());
                }
                @Override public void onDestroyActionMode(ActionMode ended) {
                    dismissed(ended, token);
                }
            };
            mode = view.startActionMode(callback);
        }
        if (mode == null) {
            finish(token, -1);
        }
    }

    private boolean populate(Menu menu) {
        menu.clear();
        add(menu, 1, 1, android.R.string.cut);
        add(menu, 2, 2, android.R.string.copy);
        add(menu, 4, 3, android.R.string.paste);
        add(menu, 8, 4, android.R.string.selectAll);
        return menu.size() > 0;
    }

    private void add(Menu menu, int flag, int command, int title) {
        if ((flags & flag) != 0) {
            menu.add(Menu.NONE, command, command, title).setShowAsAction(MenuItem.SHOW_AS_ACTION_IF_ROOM);
        }
    }

    private boolean choose(ActionMode mode, long token, int command) {
        if (shownToken != token || command < 1 || command > 4 || (flags & (1 << (command - 1))) == 0) {
            return false;
        }
        finish(token, command);
        mode.finish();
        return true;
    }

    private void dismissed(ActionMode ended, long token) {
        if (mode == ended) {
            mode = null;
        }
        if (shownToken == token && take(token) == 0) {
            finish(token, -1);
        }
    }
}
