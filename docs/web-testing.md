# Web Renderer Tests

Inbe ships the Kryon Canvas2D renderer. `web-canvas` is an alias for `web`.

| Target | Renderer | Purpose |
|---|---|---|
| `make web` | Kryon Canvas2D | Shipping Emscripten/WASM build with liboqs sync support; WebGL is not required. |
| `make web-canvas` | Kryon Canvas2D | Alias for the shipping web build. |
| `make web-compare-test` | Kryon Canvas2D | Builds the web target and runs its smoke suite. |
| `make web-side-by-side-test` | Kryon Canvas2D | Builds, tests, and serves a preview page. |

The shared smoke test is `scripts/web-smoke-test.mjs`:

- `WEB_SMOKE_RENDERER=canvas` requires a live Canvas2D context and nonblank pixels.
- It requires the app runtime-ready hook, a cycling render loop, IDBFS idle/flush behavior, and app settings persistence.
- It verifies sync-key import, practice startup, and habit navigation without reloading.
- The Chromium path also completes a one-minute meditation through pause and
  background elapsed time, saves its mood, and verifies the saved check-in after reload.

Server integration:

- Run `make sync-server-test DAOCHI_BIN=/absolute/path/to/daochi` with a built
  Daochi server. The runner starts a disposable loopback server and two isolated
  client databases, and retains test data and logs in a printed temporary directory.
- It checks offline recovery, a lost upload response, retry without duplicates,
  conflicting mood edits, backup restoration, and synced deletion. It uses Inbe's
  native storage and sync code; browser transport remains covered by the web smoke suite.

For a manual preview, run:

```bash
make web-side-by-side-test
```

The script prints a local preview URL. Use
`scripts/web-side-by-side-test.sh --no-serve` for build-and-smoke validation
without starting the preview server.
