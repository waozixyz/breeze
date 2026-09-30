<p align="center">
  <img src="assets/app/readme-banner.png" alt="Inner Breeze" width="100%">
</p>

<p align="center">
  <a href="https://play.google.com/store/apps/details?id=xyz.waozi.inbe">
    <img src="assets/app/badge-google-play.png" alt="Get it on Google Play" height="56">
  </a>
  <a href="https://f-droid.org/packages/xyz.waozi.inbe/">
    <img src="assets/app/badge-f-droid.png" alt="Get it on F-Droid" height="56">
  </a>
</p>

# Inner Breeze

Inner Breeze is a free, open-source practice app for breathing, meditation, and
habit tracking. It works offline, stores data locally in SQLite, and can
optionally sync user-owned data through a Daochi-compatible sync server.

## Features

- Guided practice sessions with visual and audio cues
- Mind, Yoga, and Fitness organization for different practice routines
- Customizable breathing sessions, meditation timers, and habit counters
- Habit tracking with session history and linked practice counts
- Local import and export support
- Theme customization with light and dark variants
- Repeat the last completed practice using its current settings

## Build

The build checks Inbe's laws with the Ziran compiler (`ziran check`); no
separate proof tool is needed. The build host needs Python 3 and the platform's
native build dependencies. See [build laws](docs/build-laws-plan.md) for the
checked behavior.

Initialize the submodules once:

```bash
git submodule update --init --recursive
```

Build and run the desktop app:

```bash
make native
make run
```

Run the terminal backend:

```bash
make tui
```

Build Android artifacts:

```bash
make android-debug
PASSWORD=your-keystore-password make android-release
PASSWORD=your-keystore-password make android-bundle
```

Build the web app:

```bash
make web
make site
```

Run the test suite:

```bash
make test
```

To test sync and recovery against an isolated local server:

```bash
make sync-server-test DAOCHI_BIN=/absolute/path/to/daochi
```

This uses disposable client databases and a loopback server; see
[web and sync test coverage](WEB_RENDERER_TESTS.md) for details.

Native binaries are written to `build/bin/<platform>/`. Release artifacts are
written under `build/dist/`.

Dependencies, including Kryon and the Ziran toolchain, are pinned in
`ziran.lock`. `make` fetches them into the Ziran package cache and links them
under `build/packages/`; `sh scripts/packages.sh` does the same by hand.
Builders that supply the sources themselves need no network: put Git checkouts
containing the locked commits (including Kryon's `raylib` submodule) in
`$ZIRAN_PACKAGE_SOURCES`, or declare them as F-Droid srclibs, which are found
in `../srclib` automatically.

To debug Inbe against the root Kryon checkout, map it in an ignored
`ziran.local.toml`:

```toml
[overrides]
kryon = "../../kryonlabs/kryon"
```

Use this only for local debugging. Permanent Kryon fixes should be committed in
the root Kryon repository and then brought into Inbe with `ziran update kryon`.

## Project Layout

- `src/` - app code
- `assets/` - images, fonts, and sounds
- `locales/` - translations
- `droid/` - Android project
- `site/` - website
- `ziran.toml`, `ziran.lock` - pinned Ziran toolchain and dependencies

## Support

Monero:

```text
48ms5LfFrPJ2LUvqP9Mm5BhDSnZnqu14jB8XpAukw3jDBKxRAxYvq3k4fEwXY7kCY3LrtycMUayJZR1YJuyvJHCDCcyw6pA
```

Bitcoin:

```text
bc1qxzcetg50f6epgddc09n82xqn3zswlmk44235y5
```

Lightning:

```text
waozi@cake.cash
```

## License

BSD 3-Clause. See [LICENSE](LICENSE).
