# Inbe consistency review

This review continues the 21 October Inbe session. It records the requested fixes and the remaining implementation differences; it does not propose new product controls.

## Changes in this continuation

- Lists prepares shared edits from the complete account-scoped saved document in `src/cells/lists_command.zi`. The screen's bounded item buffer is a view, not a replacement document. Local sharing reads all saved items from SQLite; shared edits read the complete confirmed cache.
- The Share dialog uses the list's owner and accepted/pending invitations. It copies strings that must survive another host read. Daochi supplies the same collaborator states to authorized members and the owner.
- Undo restores a private item's existing row, retaining its ID, comment, completion and order. Shared undo retains the item ID, comment and completion in the next revision.
- Games inside Arcade use the existing nested Back path. Host navigation hides during a game and the return bar remains available, including when Arcade is pinned.
- Library uses the existing Kryon horizontal swipe decision for chapter turns. Vertical movement remains chapter scrolling. Reading hides host navigation and uses a paper background. The current catalog contains one book; no additional books have been selected or added.
- The shop keeps Activity below Add reward and reserves room for the scrollbar. Narrow reward cards and activity rows keep names readable instead of squeezing them between controls. Its regression scene includes more activity than fits on a screen and a soda symbol.

## Remaining differences worth deciding separately

- Lists loads at most 32 list headers and 256 items for rendering. Complete saved documents are used for writes, so this limit must never remove hidden items. Displaying larger collections needs a separate product decision about paging or loading more rows.
- Lists still uses the legacy cell message interface; Diary uses the shared app context. A migration should preserve the existing identity, on-disk upgrade paths and account isolation rather than introducing a second implementation.
- Library's warm reading colours are local to its reading page. Other apps retain their selected palettes. A general reading appearance setting has not been requested.
- Habits and Practices still have compiled host screens alongside their portable package views. Moving an entire screen into a package is separate from these fixes; reusable widgets belong in Kryon.

## Verification

Behavior tests cover complete-document edits beyond the screen capacity and restoring deleted item data. UI checks exercise Lists sharing, the shop's final activity row at phone and desktop sizes and 200% zoom, Library swipes and Back, and returning from Chess to Arcade. Release status and exact check results are recorded in `backup/session-completion/`; this file does not claim a build or publication has completed.
