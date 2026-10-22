# Building Inner Breeze


The build checks Inbe's laws with the Ziran compiler (`ziran check`); no
separate proof tool is needed. The build host needs Python 3 and the platform's
native build dependencies. See [build laws](build-laws-plan.md) for the
checked behavior.

Build commands fetch the dependencies pinned in `ziran.lock`.

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

[Custom appearance](appearance.md) describes live KSS editing, per-app
customizations, reset, and Lumi's appearance tools.

```bash
make test
make visual-test
```

CI and releases require the visual gate. It uses disposable profiles and
private Xvfb displays to check glyph pixels, every zoom from 50% to 250%,
selected navigation and app cards in all 13 palettes and both color modes,
enlarged Appearance labels, shipped locales, and page interactions. It keeps
screenshots and logs under `build/`; CI uploads them even when a check fails.
Every visual suite runs even if an earlier suite fails. The complete result,
including hashes of the tested binary and bundles, is in
`build/visual-test/results.json`; changing an artifact during the gate fails it.
Its system tools are listed in `.github/apt/test-packages.txt`.

Store captures cover Apps, Lumi, Practices, Habits, Lists, Diary, Appearance,
and supporting pages in phone, 7-inch tablet, 10-inch tablet, and Chromebook
layouts. Capture runs use disposable profiles on private Xvfb displays and
check viewport sizes, nonblank rendering, and expected screen text. They do
not copy images into the store listing until visual review is recorded:

```bash
make native cells PACKAGE_FLAGS=--locked
make screenshot
# Inspect build/screenshots/review-*.jpg and the full-size PNGs.
make screenshot-review REVIEWER="your name"
make screenshot-export
make play-preflight
python3 scripts/upload-play-screenshots.py
```

The scene list in `scripts/screenshot-scenes.json` selects eight store images
per phone/tablet type while retaining all 64 captures for review. Changing
source, scene definitions, Kryon, binaries, bundles, or screenshot bytes
invalidates publishing preflight. A historical capture can still be visually
reviewed and used for a review video; Play requires a fresh capture of the
current locked build. Local Kryon preview builds cannot pass Play preflight.
Preflight checks every dependency against its locked commit and runs a fresh
source check, so reused incremental preview outputs cannot hide missing imports.
Keep credentials in the ignored `.env.play` using `.env.play.example`.
The uploader defaults to validating and discarding its remote edit. After
review, `PLAY_COMMIT=1 python3 scripts/upload-play-screenshots.py` validates
and commits the listing; a failed edit is discarded. This updates listing
assets only. App releases follow the numeric changelog, `update_version.sh`,
and the existing release workflow, which builds and publishes the signed
Google Play AAB and owns release tags. A local build or commit is not a Play
deployment.

`make lumi-promo` renders a narrated portrait review MP4 from the exact
reviewed phone captures and the generated artwork in `design/lumi-promo/`.
Lumi uses eight generated wing-flapping frames, flies to each screen and settles
facing the app while a narrator explains it. Lumi turns with the flight direction
and flips inward after arriving on the right. Wings flap continuously using
distinct poses; each app screen stays in a fixed position without sliding in.
The audio contains speech only, without music or sound effects. Scene timings
expand to fit the complete spoken lines.
`make lumi-narration` generates the stored narrator clips through OpenRouter
using a locally configured `OPENROUTER_API_KEY`; unchanged clips are reused.
The voice, script and provider options are in `design/lumi-promo/narration.json`.
The chat example runs real local theme actions; the surrounding forest and
glow are marketing effects. Inspect `build/lumi-promo/storyboard.jpg` and
`build/lumi-promo/inner-breeze-lumi-review.mp4` before using it publicly.
Google Play's preview video field takes a YouTube URL, so the MP4 needs an
approved public or unlisted YouTube upload with embedding enabled before it can
be added to the listing. Pass `--video-url https://www.youtube.com/watch?v=VIDEO_ID`
to the listing uploader, or configure `PLAY_VIDEO_URL`. To update only the
video, use `PLAY_COMMIT=1 python3 scripts/upload-play-screenshots.py --video-only --video-url URL`.
The [Inner Breeze trailer](https://www.youtube.com/watch?v=GTly6Fu5zPk),
"A Day with Lumi", is public on YouTube and configured in every Google Play
listing language.
`design/promo-film/` holds the trailer's sources: `film.json` (clips, voice
times, app-screen inserts), `narrate.py` (Lumi's voice), `score.py` (music),
`mix.py`, `keyframes.py` and `compose.py`, which renders the cut with the real
app screens into `build/promo-video/`. `mix.py --short` and
`compose.py --short` render the 36-second vertical short from `short.json`,
the portrait keyframes in `keyframes-vertical/` and sections of the same score.
Screenshot publishing still requires the complete current
capture, visual review, export and locked build preflight.

To test sync and recovery against an isolated local server:

```bash
make sync-server-test DAOCHI_BIN=/absolute/path/to/daochi
```

This uses disposable client databases and a loopback server; see
[web and sync test coverage](WEB_RENDERER_TESTS.md) for details.

The Apps picker, independent ZIB packages, update settings, account choices and
publisher setup are described in [app packages](cells.md).

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
