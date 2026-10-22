# Contributing to Inner Breeze

Report a bug through Lumi's feedback card in the app or
[GitHub Issues](https://github.com/waozixyz/inbe/issues). Include the app version,
platform, steps to reproduce, what you expected, and what happened. Keep account
keys, private conversations and personal practice data out of public reports.
For a security issue, use [Security](SECURITY.md).

## Development

Build with `make native cells`. Dependencies and the Ziran toolchain are pinned
in `ziran.lock`; see [build guide](docs/building.md) for other platforms. Read
[AGENTS.md](AGENTS.md) for repository conventions and
[app packages](docs/cells.md) for module ownership.

Keep a change focused. Put app UI in its owning package, reusable Kryon changes
in Kryon, and compiler changes in Ziran. Preserve existing data and upgrade
paths. Translate changed app strings in every supported locale.

Run the tests that exercise the changed behavior and `git diff --check`.
For UI changes, run `make clean-text-api-check button-api-check` and the relevant
private-display UI tests. `make test` and `make visual-test` are the CI gates.
Android adapter tests need Java 17 and Android SDK platform 36; set
`ANDROID_SDK_ROOT` to your SDK directory.
Visual tests create disposable profiles and private displays; they must never
use your desktop or personal profile. See [verification](docs/cells.md#verification)
for the additional exact-source phone and release checks.

In a pull request, explain the user-visible change and list the checks you ran,
including any platform you could not verify. A build or a commit does not
publish a release.
