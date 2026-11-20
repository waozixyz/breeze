# Test harnesses on Ziran 0.6 — open work

`make -k test` on a clean export of master still fails 54 targets. CI stops
each shard at its first failure, so most of these never show there. The
Browser Add-ons job also stops at the web build.

- Module-path builds cannot reach Kryon's export names (`kryon/text_area`,
  `kryon/text_field`, `kryon/title_bar`) or resolve an `#if` enum member
  imported through them: accessibility, account-activity,
  android-geometry-probe, android-text-input-zi, app-chrome-zi, app-clock,
  audio-runtime, dpi-state-zi, entity-photos, language-selection-zi,
  lists-sharing, lumi-connection, lumi-delegate-scope,
  lumi-feedback-delivery, lumi-telegram-input, main-platform-zi,
  media-store, notification-lifecycle, raylib-text-input-zi,
  settings-telegram-ui, settings-ui-zi, storage-sync-zi, sync-account-zi,
  sync-connection, telegram-account-flow, telegram-account-ui and
  theme-catalog-zi. Build them in project mode like
  `tests/storage_sync_zi_test.sh`, or from the export map `ziran pkg list`
  prints. Project mode also needs qualified test imports (`kryon/tree`) and a
  C link that provides Kryon's raster host (`ImageWidth`, `ImageHeight`,
  `RasterLine`).
- C link tests name generated headers or files that are now package-prefixed
  (`p<hash>_typeface_source.h`) or header-only: fonts-zi, metrics-zi,
  legacy-session-zi, database-upgrade-zi, daochi-client-zi, daochi-native-zi,
  lumi-narration, node-app-loading and voice-audio-play.
- media-compression: its test host imports `kryon/raylib_image_decode`, which
  Kryon does not export.
- The web build generates C for Linux, but Kryon defines its canvas events
  only for `OS == .WEB`. With `--target-os web`, Breeze's own window runtime
  (`practice_probe.zi`) does not resolve. Port the web build to the web target.
- Practice media: astral-projection and patterns-session read
  `astral_projection/drafts/bruce-practices.json`, which the pinned practices
  package lacks. practice-narration-keys and practice-narration-snapshot find
  Sun Salutation recordings missing or older than their text.
- embedded-image-assets-check and test-references-check reject a resource
  bundle format; audio-meter-zi imports `raylib_trace`; and update-transport-zi,
  node-app-snapshot, app-click-block-zi, visual-runner, settings-mutation-zi,
  small-app-bundling, device-preferences-zi, ziran-behavior-tests,
  android-text-selection (Gradle) and fdroid-build (ThinLTO output differs
  between checkout locations) each need a look at their own failure.

## Commits waiting for the practice-app tests

Three preserved local commits fix these behaviors. They are
d9f2f0fe (Lumi's mascot mirror), 03c72e43 (no line break at the end of
translated text) and 8308de19 (coins and break timers in theme colors). No
branch holds them, only `refs/keep/breeze-lumi-locale-theme`. They sit on
83752098. On 2026-11-18 their combined patch applied cleanly to a private
index on current master (`17a0cfd9`), and the working files match that result.
The private index and recovery patch are under ignored
`backup/lumi-locale-theme/`; the main shared index is untouched.

Local `lumi-mascot-test`, `style-apply-zi-test`, the clean Text/Button API
checks and the generated app-codec check passed. Locale parser source and
saved IR passed C, Go and portable-bundle execution. Fresh `make apps-test`
exposed the native indexed locale cache still keeping trailing blank lines;
the missing-capability message immediately before it is an intentional negative
test, not the failure. `src/app/locale.zi` now applies the same trimming rule.
The packaged harness then passed all module/integration checks, including all
ten locales and shop behavior, while reusing the freshly built bundles.

The current-tree native test-driver build passed. Private UI verification is
still pending: Lumi/Appearance tests stop waiting for `_HARMONY_APP_STATE`,
which the desktop-port lane is fixing. The shop diagnostic showed that label
and key selectors both find its visible Purchase statistics button. The test
sent the unsupported `kind` field; the driver rejects it as an unknown field.
The test now uses the documented `role` selector for interactions. The full
rerun passed at 390×844, 900×720 and 390×844 with 200% scaling, including
purchase totals and reward activity. Its tree-kind geometry checks remain.
No source has been committed, pushed or installed. Do not bypass failed build
laws. Pending command IDs and integration state are recorded under ignored
`backup/lumi-locale-theme/checkpoint.json`.

## USB Moto performance follow-up

The parent's authenticated handoff relays the owner's request to benchmark
the Moto fully and pursue a 5× improvement through Kryon or Ziran. Land and
install the already verified fix sets first. The USB development phone is
connected on Omega as `ZE2223BQZT`, reports `armeabi-v7a`, and currently has
debug Breeze 2.1.63 (version code 200). Update in place; preserve its profile.

Measure current-tree startup and native presented-frame median/p95 for each
screen and practice before optimizing. Reuse SurfaceFlinger timing from
`scripts/phone-check.py`; Android gfxinfo measures a different rendering path
and remains separate evidence. `scripts/benchmark-moto.py` adds per-run
receipts, periodic CPU/memory/battery-temperature samples and explicit
sampling-overrun detection. Receipts live under ignored
`backup/moto-performance/`. Syntax/help and all 16 phone gate/timing regression
tests passed. The installed-build practice-list baseline completed: 185
presented frames, 69.26 ms median, 69.5 ms p95 and 15.6 fps. PSS was
366,278 KiB median; battery temperature was 31 °C. Three cold activity starts
took 763, 751 and 504 ms (native first paint is not measured by those times).
This is an installed-build baseline, not verification of the updated sources.
A first `make phone-check-gate-test` attempt stopped at a concurrent
toolchain manifest/lock update before running the tests. The queued rerun
uses the same test's direct Python entry, without changing dependency pins.

The ten-minute installed-build Wim Hof baseline completed without a PID change:
34,072 presented frames over 599.06 seconds, 56.9 fps, 17.32 ms median and
17.4 ms p95 frame intervals, and 0.37% late frames. PSS was 319,948 KiB median
and 327,700 KiB maximum. CPU usage was 111.11% of one core median; battery
temperature rose from 31 to at most 33 °C. A phone capture confirmed Round 1
running at the start; these aggregate timings include subsequent practice
phases and do not prove every phase or audio behavior. CPU ticks use the
kernel's `AT_CLKTCK` value (100 ticks/second), because Android 9 lacks
`getconf`. Receipts retain installed APK hashes. CPU thermal sysfs is denied
to adb, so battery temperature is the available thermal measurement.

Include a ten-minute practice run, assets/audio/reminders/input and crash
checks. Profile real hotspots before changing Kryon/Ziran, retain identical
workload/settings for before/after measurements, and report any remaining
gap to 5×. The measured desktop glTF speedup does not establish Moto speed.

### Current integration gate

Kryon's primitive-local vertex compaction is committed and pushed upstream.
Its CPU glTF updates improved approximately 10–14× for the two desktop avatar
fixtures with matching surface and rendered pixel hashes. Full-preview timing
attempts collected only the woman avatar; model switching failed, so there is
no complete both-avatar full-preview comparison.

The root manifest/lock now select that Kryon revision and Ziran's published
streaming asset-hash update. Breeze explicitly pins its AVIF build dependency
to Kryon's version to disambiguate two transitive versions. Package resolution
then passed, but the native source gate exceeded Ziran's old 1,024-module
loader cap while checking all 513 application roots with their imports.

The upstream loader already allocates its module arrays dynamically. Its fix
removes the arbitrary cap and checks integer/addressable-storage bounds at
append. The retained regression passes a 1,101-module source/saved graph,
duplicate input and identical portable results. The full current compiler
suite passed 263/271 tests; eight failures in concurrent optimizer work remain,
and bootstrap validation has not run. The loader fix and Breeze integration
remain uncommitted pending meaningful integrated local validation. No updated
Breeze binary or APK has been installed.

The compiler lane fixed a missing assembly dependency and its optimizer-focused
suite now passes; its complete compiler/bootstrap gate is running. Breeze has
an ignored local Ziran override to the canonical upstream checkout, and its
native test-driver rebuild is queued. Final integration must return to the
published toolchain pin and pass with that graph before committing.

The native ARMv7 VRM benchmark and both woman/man runs completed successfully
on the Moto's PowerVR Rogue GE8320. They exercise a moving frame, expressions,
spring joints, both skinning modes and 600×800 GPU render/readback, with 12
warmup and 120 measured frames per mode. Raw samples and binary/model hashes
are retained under Kryon's ignored `backup/figure-preview-lag/`. Aggregate
report validation passed, including complete sequences and nonempty frames.

| Avatar / skinning | Springs median ms | Skin median ms | Render median ms | Total median / p95 ms |
| --- | --- | --- | --- | --- |
| Woman / linear | 0.1850 | 13.7849 | 49.6782 | 63.6353 / 74.2820 |
| Woman / DQ | 0.2630 | 27.6589 | 52.5224 | 80.5852 / 84.4890 |
| Man / linear | 0.3166 | 27.4683 | 61.5099 | 88.8307 / 95.4020 |
| Man / DQ | 0.3130 | 37.9562 | 58.3315 | 96.6450 / 100.7812 |

Rendering includes readback; these offscreen results are not application
presented frame times. No mobile before/after speedup is established by these
current-source runs. The existing GPU readback owner received these results;
its source hunks remain separate from this task.

The first local-compiler native rebuild passed the loader cap but failed on
distinct Kryon Session identities: root Kryon is current, while shared Apps,
Css, plot, Entity and Game2D retain the older dependency. Upstream aligned
repins have been routed to the coordinator. An ignored canonical Kryon
override merges transitive source identities and eliminated those type
conflicts. That next native diagnostic build then failed on cyclic compile-time
imports: the compiler tries to resolve enum imports for platform-only
`#defined` conditions in Lumi Telegram, the Lumi screen and application setup.
The exact failure was routed to the existing compiler/language owners; there
is no application workaround or green native gate yet.

The desktop lane's ARMv7 APK build failed before Gradle because the newly
generated shared Apps controller differs from the reviewed native digest.
The trust check remains enforced. The final published dependency graph needs
a reviewed, locally tested controller artifact and matching digest before a
new packaging gate. No updated APK was produced by that command.

Its separate old-installed native first-paint baseline completed three process
launches at 9,966, 9,157 and 7,142 ms (median 9,157 ms), measured from PID-scoped
native startup logs rather than Android activity timing. No `.zxn` cache files
were observed in that baseline; this does not establish cache reuse. Its
receipt is `backup/moto-performance/native-startup-before.json`. The phone
reservation is released. Preserve this baseline; measure the updated install
after a valid APK is ready. The startup-prelude contract test passed both normal
and test-driver variants; the SDL software-window bridge regression still
needs its fixture type errors fixed by its owning desktop lane.


### Conditional-import compiler repair and controller integration follow-up

- Parent handoffs d40848ee58df3913cd8cbb0927e2987a2fe3 and 943bf9213a2be86e9c64ec297660ec3801fe preserve all Moto baselines, assign controller artifact review/digest integration here, and keep final dependency alignment with canonical coordinator 682fa05a6e2b77ba2be829b6cab60096eaed. No baseline repeat, digest bypass, incomplete commit or duplicate ARMv7/full compiler gate.
- Canonical Ziran `cmd/zir/zir_parse_condition.c` now tries an already self-contained condition before loading file-scope enum imports. Layout queries retain the resolved-type route. This addresses ordinary cyclic imports containing platform `#defined` conditions. No peer optimizer/guard/loader diagnostic hunks changed.
- `tests/module_root_capacity_cases.zi` now retains present/absent flag cycles, imported enum/layout conditions, source/saved bundle and run parity, and ambiguous enum rejection. First focused receipt cae3993728742f2d2b51d05822c4998c78e6 failed because the new fixture omitted required using semicolons; corrected. Replacement focused receipt 10ce8b9f13dfde41f5e1fd4bf2105b936743 is pending. No successful regression verdict yet.
- Wasm owner 73941c6db7eff04aebae72bc1acc42f0e321 acknowledged no conflicting frontend edits; Android owner 30d987ed276b1d718927dda7899e2c0db303 retains the sole integrated full suite/bootstrap gate.
- Figure worker reports bcf70c122718a723ed186f2fc7d73b04e00f scoped sole/reload/retarget/slipper/30Hz floor/silhouette/practice gates passed; app-bundles still fails reviewed Apps-controller digest. No figure root/preview pin integrated here yet.
- Controller trust review must use a freshly rebuilt actual final graph, preserve both runtime SHA-256 validation and the package digest guard, and validate positive UI behavior plus wrong-digest/tamper rejection. Current intermediate apps.zx is not accepted as a new trust anchor. Desktop lane notified of single anchor ownership; it retains its desktop getter, startup cache, bridge and decoder edits.


### Resumed focused-regression result and missing build wrapper

- Exact focused receipt `10ce8b9f13dfde41f5e1fd4bf2105b936743` ended 2 before tests at the transient shared check registry capacity (declared 50, 51 entries). Current peer table is already 51; no registry edit here.
- Parent reports shared gate `99679865b0c4e3cfdb43cb3a3f7d8ef0827a` 270/274 and bootstrap PASS; current focused log rejected the new single-line compile-time branches. Corrected all new #if fixture branches to supported multiline syntax, retaining ordinary cycles, both flag branches, source/saved bundle/run parity, imported enum/layout and ambiguity rejection. Not a green compiler regression verdict yet.
- Replacement command `139f840d00d8bfac811ee95fbd0771803035` ended 127: `build-queue` not found. Login-shell lookup also failed. No current wrapper found in supported harness/library paths; only an inactive saved snapshot exists, which was not executed or restored here. No test/build bypass and no pending replacement command.
- Harmony tooling fault report `179af0f63ffa80ff37d99739face7d9d493f` resolved to existing owner `codex-projects-model-set-the-ai-model-for-claude-code-c` (24fba99f811c667d33f718ae86ccfebd36ec). Compiler owner `codex-ziran-wasm-widget-speed-3` notified with `6638a0d035a4d865d3ad2bd77314f7973d0f`. Owning parent informed of the actual blocker.
- This task is not using Moto and has no pending ADB commands. Existing Android UI regression task `codex-breeze-lumi-developer-bridge` (721e979b7ba1cf6dcead687ad8a76d278265) was told to coordinate its phone use and later return installed APK identity; no Java/Android renderer edits from this task.
- Follow-up: bounded Harmony owner output identifies intentional queue removal in another lane. Requested active-worker instruction and managed execution-route correction (8be286d380b942b00cd948e08d20304f2fd5), not restoration of the removed scheduler. This task still carries the explicit developer build-queue requirement. No supported replacement build has run; parent notified aaa18c736111f00a02f8ac0837fde325e1a8. Final dependency alignment report ab0c38477d08afa59c0022463cc707e563c4 remains queued/off with canonical coordinator682, not verified completion.

### Current integration checkpoint, 2026-11-19

- Fresh scoped instructions now require plain managed `desktop_run` commands. The two old queued commands were cancelled before their payloads ran (final 143); they must not be replayed. Peer tasks retaining an explicit queue contract keep their routing; shared output writers remain serialized.
- Ziran compiler consolidation is complete and pushed upstream at `2cafe84dc88031b951f9c1788aa2689e22aa6f5e`. Its owner reports 273 retained local tests, matching bootstrap and installed tool identities. This task's module-capacity and compile-condition regressions were included. No compiler gate remains here.
- `build/packages/ziran` now selects the canonical compiler (SHA-256 `4860081bb9e8c7f489581e2125408244202de03ecfe727c85ba73192499b003a`), and Kryon selects its canonical checkout. The package stamp now depends on the ignored local override file, so changing that selection invalidates stale links. No cache sources were edited.
- The desktop bridge fixture now compares byte text correctly. Its state/action/feature request test passes with the canonical compiler. The inactive desktop lane's product changes remain intact.
- The old Apps controller anchor was deliberately retained until actual reproduction and runtime validation. The `678e29...` and `198a615...` payloads are superseded by `9b60d9d9f71ef7ab9cd2fe372636f14ed72ad7a96920d663e966d72059a1ba6e` (1,962,558 bytes). This final local payload reproduces identically at stable and test output paths and passes the real identity, wrong-digest and one-byte-tamper cases (`77440815587a050d3684bc53471c4eb0f693`). The selected launcher stayed unchanged while its compiler backends were rebuilt; the review now records each backend and runtime archive hash separately. Current and superseded graph provenance is saved in ignored `backup/lumi-locale-theme/controller-review.json`.
- The actual current payload opens through the real Apps identity handshake; a wrong digest and a one-byte change are rejected (`45d00bd41c1459141b62c6240b55bfa1a4b5`). The source trust anchor is now updated, with runtime and packaging guards preserved. The source-anchor test passes without an environment override, together with Lumi mascot, style link and Cairo bridge tests (`ee70c96470ba55073e81708634fcc913b3c2`). A separate real packaging attempt rejects changed bytes with the expected digest error (`84e94a4e41d987e3ef69cf4dd84788248825`).
- The controller target now also depends on its selected compiler and local override metadata. No release, version bump, tag or CI wait was requested.
- Diary finished and pushed its locally verified changes, then released all shared outputs. This task's supervised native/app/UI/install sequence (`25e69816775bb2cff96935e607b3eff32501`) passed the current controller source-anchor test without an override, real package preparation, native build and full `apps-test`. It stopped at `apps-artifact-test`: the test expected an obsolete direct C field-count assignment, while the compiler now emits an address and indirect assignment. The reader is corrected, with syntax and whitespace validation passed; its actual artifact rerun and the UI/install steps remain pending. No installer ran in that sequence.
- Shared outputs are now released to the existing Android task for its unified ARMv7 candidate and restored reproducing-folder Moto startup regression. A peer legacy queue briefly overlapped `apps-test` because it did not serialize against a plain managed command; that peer terminated its exact queued process before Android compilation and acknowledged the explicit release protocol. Do not submit shared native/app writers until the Android task releases them. No new Moto baseline measurements are needed.
- Kryon AndroidProcess now gates private-folder driver preparation on the compiled test-driver define. All eight normal/driver × absent/leftover-folder × source/saved-IR cases passed (`38463c6b7d15eea9d0c51d867312e98c1c07`), and canonical Kryon `make push-check` passed (`617f6f9d7aff25d1d9bdbf50742ff4e942d1`). The focused host regression and real-device evidence are distinct: the latter is still pending before the coherent upstream commit. Other lanes' source and changelog edits remain intact.
- Remaining: complete native UI/package gates, install and verify the standard native binary without restarting the owner app, validate the startup fix on Moto, finish official dependency pin alignment and the requested full Moto app/performance verification. No 5× full-app result is established.
- Independent locale portability rerun passed source/saved C, Go and ZX (`d2ef8abc674e00e21a16789413c40db0e032`). The corrected artifact reader's first read-only rerun (`bd116298a3d5453f0a70f1b6c21787aa92e2`) encountered an absent `build/apps/lumi.zx` during Android's package regeneration; it did not verify the correction and made no shared output changes. Artifact/UI readers now wait for a stable package window or Android's full release. The existing Android job is `14a4a98ee4fb6af75eddfeebc8c0c2d1fad7`; do not replay it.

### Later verification in the same checkpoint

- Android granted a stable read-only fixture window. The actual artifact gate passed (`e61baaa7dfc193f4bf695f0a328829ee9fb5`): all six embedded app packages match their independent outputs, and the generated Lists encoder retains 31 fields. Native SHA-256 is `fb05479a6941e1e354cc1890d9f949dd8dee3efbecc4d917a6d39c6c8a873913`; full bundle is `477eaf21ae77fe13cfdb55fb1a4178d1f5fbc11df1de02e185c09fc6735ead5a`. This supersedes the pending artifact-reader result above. The test-driver native binary is not yet installed.
- Appearance passed its real editor, live validation, scopes, save/restart, reset and Lumi handoff (`f55ea6bde806d97ff1ac14aef2b3315a4524`). Habits passed full purchase totals, per-reward frequency and complete activity at phone, desktop and 200% zoom (`6bfa33071dd0e8c957dcb3d2a4d6f12db50d`, Habits stage 0). Waits now follow the committed selector update; no shop product behavior was changed for this fixture correction.
- Lumi's reported theme settings require an asynchronous wait after the chat exchange is saved. That correction passes. Its older paid Tai Chi offer expectation is superseded by the shipped free basics; the fixture now tests starting the preview. Practice fixtures also must end their own active sessions before closing the process, or the intentional unfinished-practice recovery prompt blocks their next launch. The first revised run reached this prompt at uppercase Meditation; teardown and preview verification are being completed.
- Controller drift after the review was traced to canonical Kryon HEAD advancing from `e2212c43` to `a77c82bf`, which changes local override package identity. All four compiler tool hashes and root input hashes still match the review. Android explicitly consumes the retained, reviewed `build/apps-test/controller/apps.zx` through `APPS_BUNDLE`, with unchanged guards and before/after digest validation; the mismatching default object is preserved. Final official graph reproduction/review remains necessary.
- Android's guarded ARMv7 candidate built successfully (`17f8aa068c82891c5f3fe3c66d8612d8b9ce`). Its retained-folder Moto test (`922a158d5f857a2c20d2a06ee576c93fb8e2`) started NativeActivity and rendered full navigation/geometry with the original test-driver directory restored. This verifies the startup guard on device. The initial overall roundtrip test failed because it expected another opening page; explicit navigation is being checked separately. ARM64 and shared-output release remain with the same Android task; do not replay either operation or change the graph during its current build.

### Native renderer and Android runtime follow-up

- Android released shared app/controller/native build output custody. Its ARM64 Pixel candidate built, installed, matched the device APK readback and rendered Lumi/Practices without Main loader errors. Moto's ARMv7 retained-folder startup guard is proven, but explicitly opening Practices fails to load Main's native image even with an empty native cache. This is a separate runtime failure, not test-driver activation or cache reuse. Parent/runtime coordination has the evidence; the requested full Moto after-benchmark remains pending. Do not repeat the retained baselines.
- Sun Salutation froze the native UI even with narration disabled. An owned private-display app backtrace and triangle breakpoint isolated Cairo's BEST image-mesh sampling on an actual 6×1 figure mask. Thirty-two copies of the captured triangle took 0.564553 s with BEST versus 0.001037 s with GOOD. This is a Cairo microbenchmark, not a fivefold full-app Moto result. The upstream mesh sampler now uses GOOD, matching ordinary image sampling.
- The new source/saved-IR mesh regression times out against the old sampler and passes after the change; existing sampling/mirror pixel tests pass. Kryon `make push-check` passed (`dbaa0855c67b29c36b8672afd256e205cd7f`). The AndroidProcess regression also passed again with the current shared tools (`7eb681f87be71971ecf1b635c93505b99da6`).
- Actual test-driver native rebuild passed (`f95357737797d5323796658e6e8ccd2a7312`); SHA-256 is `c6f92e2e83c4659258f347171a882bffc22dcae37d839757c4ef060055aec386`. Recorded compiler/controller inputs remained unchanged throughout that build (`build/lumi-ui-test/mesh-build-inputs.json`). The complete Lumi UI stage passed (`a524fcc262205a5723288d62ff81b077cbe6`, Lumi stage 0), including Sun start/ten frames/exit, recovery-safe practice teardown and selecting Tai Chi's free basics from its course chooser. Habits is being rerun through its private-display wrapper; the first direct Python invocation correctly refused an absent private-display marker before launching an app.
- The first new Kryon push-check attempt was invalid: exporting our private `GIT_INDEX_FILE` into make made package-cache Git validation see the wrong index. The source cache was preserved and clean; no package or Ziran repair was needed. Scope the private index to individual Git commands only.

### Current graph integration verification

- Kryon's complete AndroidProcess guard and Cairo mesh fix passed its local regressions and push-check, then was committed and pushed as `d2e537cc9491a869f690ab32210e79fea0bc47ef` (`32c2ab00b9174ecff27e6ea2de5430fcd876`). CI has not been checked. The pre-pin Habits shop suite passed all three sizes with required committed-layout waits (`c45af2a93400314053f89534dec92b1f817a`).
- Breeze now selects published Ziran `3a59682d869617e27b1fec5ff5990ee4e1a13cd1`, Kryon `d2e537cc9491a869f690ab32210e79fea0bc47ef`, and the direct AVIF ref already declared by its manifest. The lock was regenerated with the package tool; package sources, clean Text/Button API and translated-locale local gates passed (`1bc24f2565d34e2a766634daf2d1abef74da`). Shared compiler binaries still include another lane's unpublished native/inline candidates; this is current-tree validation, not validation of an isolated published compiler.
- The development Apps controller reproduces at two independent output paths as `fb56b2f0d65eaf86cfefa775a7732dfb5c1b0b80c7f834b7b2d28f475479da64` (`9417ccf066cc709df7307d3de1187cfbee26`, `a47c02a8998891ecf7935ddc0790d010bcec`). Apps source remains the unchanged reviewed `b95d19334ab4338d3611ec9d44db62b50694e464`. The source trust anchor was updated only after this comparison; wrong-digest and tampered-byte guards remain intact.
- Native, Apps behavior, controller trust, and final artifact local tests passed (`39b7bdfeed8580e4014156b1e6af011e56be`). All six independently built app bundles and the generated 31-field Lists encoder match the final native artifact. Native SHA-256 is `a78e740ac1a79b497e989af0319b6abb01ca39b0922a42eb4184652d8b58fce5`. Every recorded compiler/controller input remained unchanged after the build. Current-graph Lumi/Habits/Appearance UI verification is command `3107a62ef5b94cf3091b975f1b6367bbeed9`; its final result and standard installation remain pending.
- The official locked controller attempt is still refused (`00aecaebf1c27ffd07cb51dc756a0f2153a1`): Apps declares Kryon `8d5d2e752a219674f993473c8410847ba42fad48`, while the selected root lock needs the new renderer/Android fix. The routing audit identifies the existing cross-coordinator Apps/CSS/Entity/Game2D integration task. That exact worker is unavailable; no feedback was queued to it. Its coordinator has the conflict. Canonical Apps currently contains a substantial existing draft; this task has not edited or committed it. This publication dependency does not prevent a current-tree local installation.

- Current-graph Lumi passed in `3107a62ef5b94cf3091b975f1b6367bbeed9`; that combined command stopped at Habits, so it did not run Appearance. Appearance then passed independently (`723bc5ebf02ba0f8b7ef5779ce60bdba927c`). The 200% Habits miss is now isolated: the fixture's earned “One habit, seven times” notification overlays the Icon button and correctly owns the hit. Before/after committed trees and the returned hit identify that notification (`e0fe14bc3d07ca3f244adda74b8f858572f3`), disproving a stale geometry or compiler explanation. The fixture now waits for its earned notification to disappear before testing the underlying picker; no product input behavior changed. A full three-size rerun is pending.

### Installed native checkpoint

- The notification-aware Habits shop test passed all three sizes (`36c606f11ecb400ba48a33d588ecce519f80`), following current-graph Lumi and Appearance passes above. No product click handling was changed.
- Standard desktop build with `KRYON_TEST_DRIVER` unset and `make -j2 install-user` passed (`7292140a1ad5b460aebe852ead0d4a404814`). `/home/wao/.local/bin/breeze` exactly matches the stable build output, SHA-256 `37032d841ce9330ff0da7716e4b91f474ba9181700d308462cd12c6677bd976e`. The final installed artifact again passed all six embedded/independent bundle comparisons and the 31-field Lists codec check. The installed standard app rendered Home and exited within 30 seconds on a private display (`d486ea109bda1a4b48713de7dd3369a98692`). The owner's running app was not restarted.
- Shared compiler `libziran.a` changed after this binary's link and installation, during the active compiler lane's Regalloc work. The installed static binary and recorded component identities remain fixed. Detailed installation provenance is in ignored `backup/lumi-locale-theme/native-install-receipt.json`. This is a current-working-tree installation, including peer unpublished compiler candidates, not a release.
- Breeze changes remain uncommitted and unpushed pending the official dependency graph/controller integration and remaining Android verification. No version, tag or release was created. Kryon's earlier upstream fix is pushed, with CI not checked. The active x86 compiler worker confirms it is not implementing the ARM32 runtime failure; its parent retains routing custody and a current ARM32 implementer remains unknown. No new Ziran runtime edits or Moto baseline reruns were made here.


### ARM32 loader implementation continuation

- Parent handoff `d85cd3500b09dc9a70c790d1bece483da6a8` retains this task's write-and-implement scope for the minimal canonical Ziran ARM32 loader repair. Before a new Android build, confirm the latest APK/runtime/source identity and Moto/build custody with the existing developer-bridge task `721e979b7ba1cf6dcead687ad8a76d278265`. Its identity request `7e45e25d0403893280a54a7725ddde5612e4` is still pending; routing report `9cfeaf8c8d1d0587caf0b1247c4389406300` went to its owning parent. Neither receipt proves delivery or a handoff.
- Fresh read-only Moto identity (`f7f86d46356061e735e986e6b2696a2cb267`, `bbb7b26301c1358d27e3be454ddd8f153663`) proves the installed debug APK is the retained baseline `e6fcbd9acc8742c020db032143d20fc91f64c3d59e75c827a344230dd2e4391f`, not a current-toolchain candidate. The retained stable ARMv7 output is that same baseline. Bounded normal output/backup inventories (`07202a4f2100d9acca3f9827723b23dc61d8`, `f3c736b072ac009065d71de145556aaf94f4`) did not find the earlier guard candidate. Do not attribute its old failure to current `3a59682d` without a matching new runtime/artifact record. No phone install, launch, cache mutation or new Android build occurred in this continuation.
- A bounded active runtime-owner check found the current x86 worker, which explicitly excludes ARM/loader sources. Its output coordination feedback `eecf1cc091e01b423b882a1fa2c0e38da9e8` confirms its compiler/library window finished before this task's host edit, with 273 local tests and bootstrap reported green. Its frozen artifacts remain its own evidence; future integrated builds need fresh identities.
- Added failure-stage and relocation diagnostics only in canonical `ziranlang/ziran/cmd/zir/zir_host_native.c`. Local `cc -fsyntax-only` and `git diff --check` passed (`96074c95b9d6654b34d1845e609665b63a21`). No canonical output rebuild, cache identity change, engine fallback or guard relaxation was made. This instrumentation is not the repair and has not been installed on the Moto.
- The ARM32 BL reach of about 32 MiB and the loader's relocation-sized veneer reservation are a hypothesis to test against the actual failing image. No range repair has been chosen or claimed. Remaining: confirm current candidate identity/custody, reproduce with exact runtime and empty cache, implement the minimal proven repair with retained regression, verify Main/Practices/tab roundtrip on the Moto, then full integrated app/performance and official dependency graph verification before a coherent Breeze commit/push.
