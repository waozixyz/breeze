# Account activity and Telegram reopening

The Lumi bot's link belongs to the numeric Telegram account and remains in
Daochi's database across Telegram clients and node restarts. It does not belong
to a Telegram Desktop window or a Mini App launch.

On reopening the Mini App, Inbe verifies fresh Telegram identity, validates the
saved owner's signed delegate grant, and obtains a fresh key-bound session
automatically. A temporary sync outage or offline reopening keeps the saved
delegate. Offline reopening denies access until a fresh online launch verifies
the identity; it does not delete the protected account. Changed
identity, revocation, or an expired grant still prevents access. The owner's
private key is never sent to the bot or stored in the delegate capsule.

Telegram SecureStorage is device-local. A new Mini App device still needs its
own initial authorization. A native app joins the same account by importing the
same account key. The current Mini App grant covers Lumi history and shared
activity; it does not grant access to owner-only Diary, Lists, or Habits data.

The running device publishes encrypted activity every two seconds through the
existing v6 private Lumi collection. The shared record identifies the practice,
its originating device, session, phase, counters, elapsed or remaining time,
pause state, and last update. Phase and round boundaries publish immediately.
Other signed-in devices show it on the Practice
page and provide a shortcut from other pages. The Telegram Mini App opens the
live activity view and can return to Lumi.

Pause and resume requests target the exact session, originating device, and
state revision. The running device acknowledges them in its next activity
record. Replayed, expired, and superseded requests are ignored. Observers do not
advance the practice or save another result. A finished session publishes an
inactive record. A session without updates for twenty seconds shows its last
known state and disables remote controls.

Sync transport continues during practice while changes to its screen and
settings remain deferred. Android's existing background practice timer also
pumps activity and sync while background play is enabled. Background suspension,
an offline device, or concurrent offline starts cannot provide uninterrupted
live synchronization. This is a live view and remote pause/resume, not a transfer
of practice execution to another device.

Validation: `make account-activity-test telegram-account-flow-test
sync-safety-test android-timer-zi-test android-lifecycle-zi-test`;
`make build-laws proof-test sync-recovery-test version-test`; and the
two-client `sync-server-test` scenario, which exchanges the encrypted session,
pause request, acknowledgement, and completion through a real Daochi server.
`make account-activity-ui-test` checks the desktop and narrow-screen live view,
remote control acknowledgement, stale controls, and completion on a private
Xvfb display. Harmony's application state also exposes the account activity
and enables its remote pause/resume controls only while the session is fresh.
