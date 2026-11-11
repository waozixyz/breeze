# Six-practice implementation and local validation

Physical Alpha app checkpoint (2026-11-10): all 44 free Tai Chi items preserve
canonical motion, timing and markers. All 20 voice profiles contain exactly 184
free Opus cues, matching source bytes; complete Ogg pages, checksums, end markers
and positive durations passed. All 3,680 actual staged clips decode through
FFmpeg. The retained preview is 26,847,373 bytes (26,826,395 bytes of audio).
The ignored receipt is `backup/tai-chi-preview/validation.json`; this measures
preview staging, not the complete app package or executable.

Fresh Alpha source tests passed translated locales, all 823 used locale keys and
placeholders, settings storage/import keys and the clean Text/Button APIs. The
broader locale inventory gate also passes after the Radio owner removed the two
obsolete keys from all ten locales and the stale French exception. The successful
Alpha result was independently read from command `b31864503f3a34c5d1493b7e859379c56bcb`.
About source has the inline app/version,
Core first, no package heading and no appearance style chooser. GUI verification
is still pending. Radio's test now uses the app build's scoped package exports.

The existing preview and package-asset tests now enforce full 20-voice coverage,
exact free motion/audio ownership and generated AVIF launcher/Back assets.
Complete native build, laws, fresh compiled package inventory/size and private GUI
verification await the stable compiler handoff. No feature commit, push or install.

App code and all ten supported text catalogues are implemented. Earlier native
and private-display local test results are recorded below. Everything remains
uncommitted; complete narration and final native/package/upstream pin integration
are pending. Current scope is local Ming for `en es de fr ja ko
zh`, `Misha24-10/F5-TTS_RUSSIAN` for `ru`, and
`Thomcles/Chatterbox-TTS-Czech` for `cs`, and
`FearL0rd/Chatterbox-TTS-Portuguese` for `pt`. Portuguese was restored from
verified recovery copies after the owner's updated request; only Indonesian
and Italian remain removed.
The complete female inventory is 4,960 clips, including 880 new Bruce clips.

Current narration checkpoint (2026-11-09): Portuguese Bruce is 88/88 exact
requested-profile current. Full 48 kHz Opus and paired 16 kHz decodes are finite,
with zero full-scale samples. The original batch ended with code 143 and its
single resume ended with code 0; neither may be replayed. Verification receipts
are `bruce-88-native48-validation.json`, `bruce-88-16k-validation.json` and
`bruce-resume-exit-and-locks.json` under the Portuguese pilot directory below.
The Portuguese workout batch finished with code 1 and 20/29 requested-profile
current clips. Its 20 retained clips pass full finite 48 kHz and 16 kHz decode,
duration and zero-full-scale-sample validation. Nine keys remained pending at
that original checkpoint; later progress is recorded below. The practice is incomplete. All 54 prebatch workout rows/audio and all 98 astral
rows/audio were preserved; five output locks were free and released. The final
proof is `workout-normal-finish-validation.json` in that same pilot directory.
The generator matches its launch hash. All 29 config/text semantics match the
prebatch snapshot; exact-launch config/text byte preservation is unknown because
those hashes were not captured. The media task accepted the source/model slot
for the generic decoded-headroom correction; no new generation is running here.

The later Portuguese six-context run ended with code 1: rotation and switch
passed the unchanged gates, bringing workout to 22/29 requested-profile current.
Counts 3/2/1, go, crunches, step-ups and squats remain pending. All 74 prior
receipt rows/audio and context artifacts were preserved; all 40 actual QA
children were waited successfully and the output lock was independently free.
The final classification is `pt-six-context-run/terminal-verification.json` in
the Portuguese pilot directory. The separate immutable nine-rule PT policy
successor preserves all six original rules and source/profile/quality gates.
Its five focused tests plus the existing 51 retry tests pass (56 total;
`12aad5ce1ec32ead50d37db7c478fd3ac3e1`). No successor generation has run.

Model-free short-cue diagnosis (`5ad5a1ec01782d56a81b27e79ab59b8c3624`) confirms
that the parent ASR emits numeric digits for spelled Portuguese counts. A scoped
Portuguese count-comparison and migration contract is prepared and root accepted;
it preserves default normalization, raw QA, canonical source and all quality gates.
Implementation waits for the active source-pinned narration run to finish. The
15 accepted context proofs require 17 fresh ASR results under successor seals;
count 1/3 have retained parent PCM salvage candidates. This migration and its
4,947-row frozen-default audit have not run. No further synthesis or QA ran here.

The Japanese Tai Chi cached repair for `tai_chi_text_b6eed6cf` is integrated and
root accepted. Independent canonical-path validation passes ordinary current,
complete 16/48 kHz decode with zero full-scale samples, exact staged receipt
bytes and preservation of all 3,069 other clips/rows and outer receipt fields
(`8524824393fa6032269ca9d8362d14456a4e`). The original promotion's final validator
used the default guide path and failed after both successful writes; a separate
read-only followup proved the installed bytes without replaying either write.
Both failed command outcomes and recovery originals remain retained. Evidence is
under `ming-taichi-en-de-ja-01/integrate-ja-b6eed6cf`. Complete narration, final
native/package integration, actual downloads, installation and desktop launch
remain pending; nothing has been committed, pushed, uploaded or installed.

The fresh stable native build and private-display chooser tests pass for all six
exercises at desktop and portrait sizes, including guides, selected cues,
countdowns, pause/resume, restart, switching, finite completion and history.
The fresh native download-flow local test also passes: practice tabs, real sizes
and prices, owned/shipped state, supported narration languages and English/Russian
tab swipes. It used a private display and disposable profile; it does not verify
the installed application's actual downloads.
The exact pack uploader passes 22 local tests, including selected-only signing,
transport and verification, with the shipped signing pin checked first. Nothing
has been uploaded or installed. Final actual download, installed app and desktop
launch verification remain pending after complete narration and integration.

The female-only Portuguese Sun text variant passed actual synthesis for both
changed cues. All 12 registered breathing contexts were refreshed from cached
PCM and validate under the current helper/policy. The complete Portuguese Sun
set is source-compatible, with only 5/20 requested-local clips at that checkpoint.
The incumbent cobra and intro_2 float defects still require replacement through
local generation. English Tai Chi remains 305/307 strict requested-Ming current;
the missing-only resume plan separates the fresh context case cd427ea0 from the
ordinary failed draw ff433c2b. These retries remain pending in the serialized
voice work.

The Russian guide batch exited with 31/32 accepted recordings. Its sole failed
line, profile_guide_more, now uses a voice-only Russian source override while
shared UI text stays unchanged. The other 31 recordings remain strict current,
all nine other locale inputs and model/helper identities are unchanged
(`305a1cae506a97c73f0985566cc578d91b62`). The narration unit suite passes 73 tests
plus the retired-locale assertions (`85a15cab20a7054d9ee580242117969b016c`).
The guide was released to the voice task for the corrected cue's actual synthesis,
full decode and full Russian guide verification, then Czech generation.

The narration coverage test now includes all ten locales and passes
(`15d548558b08624acc7ca1228232e6727f95`). It checks source-compatible Sun narration,
not complete requested-local provenance. All 4,960 requested-local recordings
and final native/package/private-display integration remain required before any
feature commit or push. Detailed current receipts are under ignored
backup/narration/pilots/pt-all-practices-01 and ru-guide-more-wording-01.

The following diagnostic history includes earlier source and policy identities;
its pending statements are superseded by the checkpoint above.

The Czech/Russian onset diagnostic confirms that retaining PCM from sample zero
produces the exact intended cues (`38b1741f22f8f72db4e09f47a8f3a573a3bc`). Czech
candidate 2 already contains strong signal before Whisper's reported first-word
start, so trimming at that timestamp would remove early audio. The local voice
task owns the narrowly registered alignment fix and Portuguese parent change.
Those recipe changes require another cached proof refresh; the earlier six-cue
results below remain historical evidence until that refresh finishes.

The generic CLI now permits non-Ming `--cached-only` only with both explicit
context profiles. Missing or incomplete context options still fail before model
construction. The six provider/CLI fixture tests pass
(`1213b8683477d9d25ca7e41963753880ed90`). An actual accepted English Tai Chi cue
passes receipt validation before and after this isolated change
(`ae15cf60094bded214f239488ef6e9135599`,
`79351b463ac8d47cf82a0475f13007d56190`); all ordinary Ming source/profile hashes,
synthesis, cache and verification identities are unchanged. The context helper
rejects missing or corrupt local cache data before synthesis, with tested adapter
call counters. The final frozen candidate passes all 71 narration fixture tests
and the retired-locale gate (`60ea63038f54a3b0c4a560ad5af99ff6d1f0`). Actual cached
context refresh remains in the serialized voice handoff.

All six Spanish, French and Chinese short-context breath cues now pass actual
generation and fresh receipt validation under the preceding combined policy.
Spanish/French cached revalidation passed (`4ea35761a615ddd1b2840adf0beea8f39a96`),
Chinese cached inhale passed (`25bb4ebb69a28e211c22c7d63d9e7563c245`), and Chinese
exhale passed using the existing canonical plank parent
(`d0a02b1cdf43ad84890285042e8843b9f7c0`). Combined offline validation passes all six
(`a4ba7c058b60a4f0bf6a8a8650e73329a8fb`). Independent float decoding confirms
finite samples, peaks below 1, complete ASR sample coverage, and matching clip
and public parent hashes. Each transcript matches exactly; durations range from
0.602375 to 0.8485625 seconds. Actual short-clip speaker scores remain separate
from the qualifying parent scores. Only these two Chinese context crops use the
pinned Turbo verifier; ordinary routes and the original synthesis profile remain
unchanged. The serialized Sun receipt writer has been handed to the local voice
task for Portuguese/Czech exhale and both Russian context cues.

The final combined narration target passes 66 fixture tests and the retired
locale gate (`3480d813e6d09616e34c65cc0621d1d449c7`). Portuguese/Czech inhale
cached refresh and fresh receipt validation also pass under this exact policy
(`07db4c5c530e63e572f8ecf4c6fba0a30021`). Russian's ordinary short cues each
exhausted four attempts below its unchanged speaker threshold; its longest Sun
cue passed, including independent receipt validation
(`9b0140ee3971202ab6e0741d42b0bd5c3bcc`). Production narration and final native
integration remain incomplete. No feature commit, push, release or installation
has occurred.

The following diagnostic history records the failures and corrections preceding
that final policy validation.

The initial six actual Ming short-context pilots exited with three accepted
recordings (Spanish in/out and French in), and three rejected cues
(`ea5b559637cc6a721ebb93256810081ba7a4`). Spanish exhale demonstrates the bounded
retry fix on real audio: the first crop failed ASR and the next passed. French
exhale exposed a timestamp-token split of `penchez-vous`; the helper now joins
only actual internal hyphen/apostrophe connectors for full-text coherence while
preserving raw chunks and all crop checks.

Both rejected Chinese inhale crops are recognized exactly as `吸气` by pinned
Turbo (`700ea3c0d842318125d6843e4ae0f3689228`), with encoded-packet hashes matching
the original candidates. No new speech was synthesized for this diagnostic.
The implementation now supports an explicit Chinese short-context crop verifier
without changing the public Ming profile or ordinary routes. Chinese exhale's
parent switches to the existing canonical plank instruction. The final CLI proof
refresh above replaces earlier proof identities; old context recordings are not
treated as current under a changed policy.

Generic generation/current tests reject wrong model, revision, artifacts, adapter,
audio, locale, sample count, duration, truncation, words and verification identity;
invalid new ASR metadata preserves the previously accepted clip. These eight
context tests plus eight Ming-verifier and six diagnostic tests pass
(`78b6a588156302d015e7a5d4f2c1a14d8a00`). Independent Czech foundation and guide
receipt checks pass (`b49edea784228bcf87462fd2fe65954157db`). Complete production
voices, remaining provider context pilots and final native integration remain required.

Replacement foundation pilots in all seven Ming languages passed after lossless
segmentation fixed the original German missing ending. The media task completed
cached-only revalidation with the new per-locale verifier, and an independent
generic CLI `--check` passes all seven (`216a6be54ddc188a8385570037fdb53ca954`).
Russian's actual foundation pilot also passed. Portuguese's segmented foundation
pilot passes independent current-receipt validation
(`880c07a17f9ba5fc30b2b1e72367003fa4ab`). Production narration remains unfinished;
short Czech/Portuguese cue validation remains under the separate voice task.
An independent float decode of the Russian pilot records a peak of
1.0008153915, with one sample at or above 1 among 503,444 samples. The parent
accepted this tiny codec overshoot as a recorded metric; no encoder or synthesis
change was made for it.

The Japanese Sun Salutation pilot's four saved clips were all correctly heard
by pinned Whisper Large v3 Turbo. The independent verification wrapper uses
Turbo for Japanese and Korean and Small for the other five Ming languages. Its public
verification block preserves the exact original synthesis profile and cached
PCM; `--cached-only` prevents new speech during pilot revalidation. Chinese Sun
Salutation comparison now permits only the authorized context-bound homophone
and script equivalents, preserving raw ASR and direction/number/ending checks.
Bounded attempt diagnostics retain every attempt and distinguish best from last.
The Japanese Sun pilot passes fresh actual receipt validation
(`6d1052102c37a16c5e89cccbb3287d7446ca`). The encoded Chinese Sun pilot originally
had three speaker failures and one speaker pass that Small transcribed with
another homophone, `向後賣`. The additional source-bound `向後賣`/`向后卖` spellings
are implemented under the parent's reviewed direction. Regression tests preserve
left/right, missing-ending, extra-number and unrelated sale controls
(`21f318489fdc02447456b8481c8d5e99550f`). Independent current-receipt validation now
passes the completed Chinese clip (`d97dc92128e64c97efb13cc47e2334cb9553`):
2.875 seconds, match 1, speaker cosine 0.7197458, and unchanged raw transcript
`吸氣,右腿向後賣,膝蓋落地`. No speaker threshold was relaxed.

All three completed Korean Turbo pilots now pass independent receipt-only
validation: Sun Salutation's shortest and longest cues and Bruce foundation
(`173bd31132a87e2f3ee5aaae5cf8b8de63db`). This reused the media task's completed
work without repeating synthesis or ASR. Explicit prior QA identities remain
valid only for unchanged locale/model/revision/artifact routes; Korean's earlier
Small receipts are rejected. The current generic verifier and context helper are
frozen during real Portuguese/Czech context pilots. Ming Spanish, French and
Chinese context pilots follow their serialized Sun Salutation handoff. These
short-cue proofs and production voice inventories remain required.

The actual Portuguese registered breathing cue passes the generic context
pipeline and independent offline validation (`297c986ff5a00e0378d40dc4f368dcd53cf6`).
Its 0.56-second crop transcribes exactly as `Inspire.` and retains the actual
short score 0.4953606 separately from parent score 0.6780988, which meets the
original provider's 0.65 threshold. The public parent WAV is bound to the crop and
original synthesis profile. This single real proof does not certify the other
configured short cues. The integrated narration target includes all 16 shared
adapter/context tests and passes (`54a354c5efff216c0f6cfd9d3d056c4e1ab1`).

Local adapter preflight and `build-queue -- make ming-narration-test` passed
(`735c1433fb8c49c391f5832123a1717a762f`). Seven new verifier tests also passed,
including an actual encoded-clip `current()` test that rejects wrong model,
revision, artifact hash, transcript and incomplete sample coverage
(`6ca45f4c2e6d52191fe3f0a02925fed53385`). Three diagnostic/comparison tests pass.
The media task owns actual cached pilot revalidation and production narration;
none is reported complete from these local fixture tests.

The original validation below records the earlier twelve-language scope and
HTTP 402 provider failure. The historical sections record the nine-language
native/GUI validation and local-provider work. The ten-language update below
supersedes those earlier counts.

The asset contract is in `exercise-interface.md`. Breeze owns app code, locales,
font subsets, tests, packaging and generation/certification tooling. The separate
media worker owns the practices repository and recordings.

## Implemented

- Start opens six choices before starting narration or a clock. The selected ID
  persists as `astral_projection_exercise`, and How to uses its guide.
- Selected data controls duration, cue keys/text, standard narration paths,
  countdown/progress, pause/resume, restart, finite completion and named history.
- Save-on-exit supplies the identity buffer required by existing details storage.
- Original packages without catalogue.json retain their open-ended session and
  elapsed-time saving. Missing selected new data displays a translated error.
- The new 88-key speech inventory/receipt is separate from the preserved 20-key
  legacy configuration/receipt. Packs require every verified new clip, preserve
  legacy clips, and exclude source drafts.
- Per-cue speech budgets preserve deliberate quiet time; other narration retains
  its default 40-second limit. Scratch stays in ignored backup/narration/tmp.
- Loading errors are translated in all twelve UI locales. Four CJK font subsets
  were regenerated through the standard target for the complete new media.

## Passing local tests

Final native build and unit suites, Harmony receipt
`9d4e36be26e9b5005d27f3fd3796dee3774f`, exit 0:

```sh
build-queue -- sh -c 'test "$(readlink -f build/packages/practices)" = "/mnt/storage/Projects/waozixyz/modules/practices" && make native apps clean-text-api-check button-api-check locale-translated-test build-laws package-check && make astral-projection-test practice-narration-test'
```

This rebuilt the stable Linux executable and app bundles using local Kryon and
practices overrides. Required API, locale, law and package gates passed. Compiled
astral behavior covers selection, bounded malformed data, finite clocks, pause
and reset. Content tests cover six exact sessions, 88 unique cues, 18 metadata
entries and all twelve translations. Narration tests cover all six cue paths,
German routing with a fixture clip, speech/quiet budgets, 45-second generation,
default limits, local staging, incomplete/mismatched pack rejection and legacy
clip preservation. Fixture clips do not certify missing real narration.

The standard `make font-subsets` stage completed inside build-queue receipt
`d4ab5dee181b4a143e99e6750242e8c00d04`. Glyph coverage has zero missing characters:
Japanese 956, Korean 725 and Chinese 1,210 required codepoints. That earlier
combined command then caught a numeric cast mismatch; it was corrected before
the passing native run above.

Full real native GUI suite, receipt `3cc08f57c0e471b857218e4e45bf2ab06b82`, exit 0:

```sh
env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u DBUS_SESSION_BUS_ADDRESS -u GDK_DISPLAY -u SESSION_MANAGER YUE_DESKTOP_RECOVERY=0 python3 -u tests/astral_projection_ui_test.py build/bin/linux/breeze-linux-x86_64
```

Verified all six at 1280x900 and 390x844 before Start: names, descriptions,
duration, persistent selection, guide and initial cue/countdown. Verified
pause/resume, cancelled exit retaining explicit pause, exit/restart, switching
to another exercise within the same app, all six finite completions and named
history across process re-entry, Save at 60 seconds, missing selected content
without legacy fallback, and original-package display plus Save. All six German
portrait selections/guides/cues also passed. Private captures and contact sheets
are in `build/astral-projection-ui-test`.

Existing movement GUI suite, receipt `71ee545d0e96e9f8b3da54fef1b87cdebd10`, exit 0:

```sh
env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u DBUS_SESSION_BUS_ADDRESS -u GDK_DISPLAY -u SESSION_MANAGER YUE_DESKTOP_RECOVERY=0 python3 -u tests/practice_movement_ui_test.py build/bin/linux/breeze-linux-x86_64
```

Sun Salutation settings, Astral pause/resume and Workout start/pause/resume
passed. Both GUI suites use private Xvfb, private profiles and only their own
processes. The owner's running app and profile were not touched.

Also passed:

- `python3 tests/practice_narration_keys_test.py`
- `python3 tests/practice_narration_snapshot_test.py`
- `python3 tests/astral_projection_content_test.py`
- `git diff --check`

## Remaining gate and deployment state

`python3 tests/astral_projection_content_test.py --require-narration` fails with
exactly 1,056 new clips missing. First missing media path:
`voice/en/astral_text_foundation_01.ogg`. No complete new language pack is
certified or advertised. Actual new narration playback remains unverified.

After narration is available: verify receipts and every clip, rebuild packs with
local overrides, rerun strict audio/content and native integration gates, then
coordinate the complete upstream commit followed by the named practices package
update and one coherent Breeze commit. The peer Lumi task owns shared manifest/
lock alignment and unrelated dirty hunks; preserve those edits.

No feature commit, push, release, installation or deployment was performed.
Linux native behavior is validated; other platforms are not claimed validated.

## Local Ming pipeline continuation

The current generation interface and full-artifact descriptor are in
`design/narration/README.md` and `design/narration/ming-female.json`.
The existing female narration inventory is 496 cues per locale, including
the original Astral sessions, so seven Ming locales require 3,472 clips.
Existing male recordings remain available in the nine supported languages.
Retired-language files have verified recovery copies outside active resources.

Real installation fingerprint and preflight passed without loading a model or
generating audio, receipt `87da98c1d56338bb309cb03984cb4b455c8f`. The public profile
pins 84 runtime source files, 10 Ming model files, 11 Whisper files, both female
reference hashes, local adapters and runtime package versions. Absolute paths
stay in ignored `backup/narration/ming-local.json`.

Regression receipt `7087084d52ce1b0944f936a91f067fb2cec7`, exit 0:

```sh
python3 tests/ming_narration_test.py
python3 tests/astral_narration_test.py
python3 tests/practice_narration_keys_test.py
python3 tests/practice_narration_snapshot_test.py
python3 tests/astral_projection_content_test.py
git diff --check
```

The six Ming tests cover explicit language and nonzero speaker conditioning,
full request/source hashes, no model load during preflight, stale or corrupted
receipt rejection, real Opus fixture encoding, reserved quiet intervals,
transcript-tail checks and routing all 40 seconds into the long-form decoder.
These are test fixtures, not real Ming practice recordings.

Real read-only Whisper validation completed in one two-thread process,
receipt `39d74d0eeb7ba762b6e2ff300d3d6c99e2c7`, exit 0. The seven existing Jungle
calm female samples transcribed correctly, apart from Japanese punctuation and
the Chinese equivalent 樹/树 spelling. A 38.6-second concatenated existing
English sample supplied all 617,600 decoded samples and reached the distinct
final badger/magic-pot phrase after 30 seconds. Whisper compressed its repeated
tiger prefix; this establishes decoder end coverage and API compatibility,
not a perfect transcript of repeated audio. The private result is
`backup/narration/qa/asr-runtime-results.json`. No Ming model was loaded in this
test and no production recording changed.

New Bruce pilots are assigned to the existing media task. Their actual speech,
transcript, duration and voice consistency must pass before bulk generation.
There is no feature commit, push, release or installation.

## Nine-language milestone and provider integration

Native build/local-test receipt `f52b35cd3a1398ae77476b1ea7cd1272774a`, exit 0:

```sh
build-queue -- sh -c 'set -e
test "$(readlink -f build/packages/practices)" = /mnt/storage/Projects/waozixyz/modules/practices
make native apps clean-text-api-check button-api-check locale-translated-test build-laws package-check locale-zi-test astral-projection-test practice-narration-test ming-narration-test'
```

All six finite sessions, 88 cues, 18 metadata entries and nine translated
catalogues passed. Audio inventory at build time reported 790 missing files;
the two pilot files do not establish complete narration or accepted quality.

Private native GUI receipt `5be16b2aed95ca6cadfe53768c287aac396c`, exit 0:

```sh
env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u DBUS_SESSION_BUS_ADDRESS -u GDK_DISPLAY -u SESSION_MANAGER YUE_DESKTOP_RECOVERY=0 python3 -u tests/astral_projection_ui_test.py build/bin/linux/breeze-linux-x86_64
```

Verified saved `id`, `it` and `pt` UI/narration preferences migrate to explicit
English despite a German system locale, persist across two reentries, and keep
the selected exercise and unrelated saved data. All six choices, guides,
pause/restart/switch, completion and named history passed at desktop and portrait
sizes; all six German portrait selection/guide/initial-cue paths passed.

QA receipt `9ca3cb29ce6846f3b45ead8d3abead77c9da`, exit 0, ran ten offline
tests plus actual receipt validation: complete English pilot accepted, incomplete
German pilot rejected. The German take scored 0.92958 globally at 23.065 seconds
but omitted its final sensations clause. New local clips at every duration must
match both the final 64 and 24 normalized characters at 0.85, using the same
locale spelling aliases as the unchanged full-transcript threshold. Both new
generation and receipt reuse enforce this rule. No frozen Ming/Whisper source
or public profile changed for this correction.

Shared local-provider receipt `7de6c10ff2ad2b16b6fccb1744bbd246af6b`, exit 0,
ran ten Ming and three provider-routing/resume tests. Russian and Czech use
explicit provider/private-profile flags, their own Python environments, exact
locale filters, and the shared encoded-audio, transcript-ending and speaker QA.
Wrong interpreter and unsupported locale fail before model loading. These are
fixture tests; real Russian/Czech synthesis acceptance remains pending.

Ming model and Whisper weights are copied into the reusable harness store:
`/mnt/storage/Projects/harness/models/weights/tts/ming-3.0-tts-0.5b` and
`/mnt/storage/Projects/harness/models/weights/asr/whisper-small`. Originals remain
untouched. Only ignored private paths changed; actual preflight receipt
`c6a5c95bed45815b428cbe3cebfbd90b512d`, exit 0, verified all public hashes without
loading a model or generating audio. This proves metadata consistency, not voice
quality. All 4,464 female clips, strict nine-language pack/content validation and
final integrated playback remain required before any feature commit.


## Portuguese restoration and lossless Ming requests

Portuguese UI, achievement translations, Android/store resources and existing
narration receipt rows were restored from the verified owning-repository backup.
Only `id` and `it` migrate to English. `pt` stays Portuguese for the UI and all
three saved narration overrides across reopening. Female generation explicitly
routes `pt` to `chatterbox-portuguese`; it cannot fall back to Ming or a network
provider. Direction validation rejects Portuguese left/right substitutions even
when the full transcript score exceeds 0.92.

The 512-token dense Ming cache includes both the input and decoded audio.
Read-only tokenizer inspection measured 221 input tokens for the original
German foundation cue, leaving 23.28 seconds; its rejected recording lasted
23.065 seconds. Raising the explicit 1,000-step limit cannot enlarge that cache.
The new source-preserving segmentation keeps short cues in one request and
splits long cues at natural sentence/clause/word boundaries. Exact Unicode
source spans, seed rule, original speaker embedding, language and zero added
pause are bound to profile/request/cache identity. Whole-cue ASR, both ending
comparisons, speaker similarity, quiet-time and duration limits remain unchanged.
Finite raw float WAVs survive peak rejection for diagnosis; no clipping or
automatic normalization was introduced.

All seven actual foundation plans were inspected with the pinned tokenizer
without synthesis. Minimum per-span decode headroom is 30.88–32.08 seconds;
exact spans and budgets are in ignored
`backup/narration/qa/segmentation-budget.json`. The new profile invalidates the
old pilot identities. The media worker owns the new German/Spanish/Japanese
pilot as session 70497; do not repeat it or modify the frozen Ming, segmenter,
Whisper or public profile while that job remains live.

Local verification:
- Native ten-language build, build laws, locale translation/link tests, API
  gates, package checks, all six practice/content tests, narration behavior and
  offline provider tests passed, command `55c2b9f25039c3a3929a05212085c72e6f6d`.
- Eight segmentation, ten Ming contract and four local routing tests passed.
- Five actual float WAV/cache/PCM fixture tests passed under the existing Ming
  interpreter, command `652c18c7c778956be04ba36b702303251217`.
- New profile preflight passed without inference,
  command `0a8e7879725acfff760432d8394676fc3fc6`.
- Ten-language private GUI validation passed, command
  `0ecab8833dcf3324ccfbb345e8a6080c124b`: all six selections/session paths at
  1280×900 and 390×844, pause/restart/switch, finite completion/history, German
  guidance, Portuguese preference persistence and Indonesian/Italian fallback.

Production narration remains incomplete. No feature commit, push, release or
installation has occurred.

## Reopened integration milestone

The retry test now selects `short-context-provider-v2.json`; every assertion and the protected original policy hash remain. Local command `4c86da328624e1d3bc778eb9d3c4167e244c` passed 109 narration unit tests, all six finite sessions/88 cues/ten locales, cue budgets/pack staging, narration routing, UI API and translated-locale gates.

Fresh native command `fe901b0b93fdb30fa3e3aceece9b6404e8ad` exposed Kryon's Android surface desktop boundary failure. After the upstream specialist corrected that boundary, command `749634492aadefc1675e1bbe8853a981d792` passed native/apps/package-check/locale-zi-test and the stable Linux binary size gate. Fresh private-display GUI command `2a5538ffa5ba05ce2b620b6201d9f4e7ec01` passed all six selections before Start, guides, session cues, pause/resume/restart/switch at 1280×900 and 390×844, finite completion and named history, German portrait guidance, Portuguese preference persistence and retired-locale migration. Complete narration and final media integration remain pending.

The previous Portuguese writer `6d3ca1bea5de6cbfd5c2ed1cf7f4e7736b6a` conclusively ended 143, retaining 78 exact-profile Bruce cues. After parent source-seal verification, ordinary cache-preserving resume `8d371c6cff628cd22dd8401cb2c3c792e462` generated the missing Roll Out 06–15 and finished0, including explicit model-child exit0. Full88 exact-profile/current/source/hash and complete48k finite zero-fullscale validation passed in `c3234c894229d94a3927c622a3ece3483361`; paired complete16k validation passed in `2544dd741758feb10299cd8a1f836bc45221` (maximum peak0.954200, zero fullscale samples). All five output-root locks were free in `5c420d2fcfd5430727fd9db7b46d0a7810bd`. The sole heavy slot was handed to the existing media worker for15ASR; PT workout waits for explicit slot return and protected shared-receipt integration. No further model was started by this worker.

Ignored `backup/narration/pilots/pt-all-practices-01/reopen-batch-plan.json` records exact requested-profile current/remaining keys for all60 practice/locale batches: snapshot1011 current,3949 pending. It excludes accepted assets from fresh invocations and distinguishes ordinary retries from separately coordinated context proofs. Russian51/496, Czech75/496 and Portuguese82/496 at snapshot; Bruce is actively increasing Portuguese coverage. Root locks serialize every locale sharing a receipt. The old Ming exit code remains unknown; its broad regenerate invocation must never be replayed. The existing generator/retry interfaces already support repeated explicit key filters and preserve requested-profile current rows; no sealed-core change is required.

The test-only native audio harness now accepts an explicit astral practice, preserving TaiChi default. `make astral-voice-audio-play-test` requires actual first-cue assets for every supported locale; `ASTRAL_NARRATION_LOCALE=pt` tests the six Portuguese first cues. Local command `3c11b4c8d5587575ca70a4da11e063216830` completed all six through native decoder, PCM16 conversion, null mixer and300ms pause/resume. All produced sound, completed at the correct duration and had zero decoded unit crossings; maximum mixed peak0.622355. This proves component playback, not complete narration or final app integration. No feature commit, push, release or install has occurred.

The owner also requested latest desktop installation and launch after completion. Narration is downloaded as hashed language packs; binary installation alone cannot deliver it. The existing uploader now accepts repeatable exact `--pack` identifiers, stages/signs/transports only that selection, restricts remote permissions to selected archive members, streams full public-byte verification and preserves paid403 gating. Default and `--content` base-only behavior remain. Local command `af986d8a88b3b9368acd31ee07d704b10cb9` passed17 upload/selection/signature/transport tests plus5 content-repair tests; no actual remote action occurred. Final gates remain complete requested-model media, fresh packs, restricted immutable content availability, supported installed-app resolution, atomic desktop installation and root-owned native launch. No version or software release is requested.

## Current narration recovery

### Personal VM recovery, 2026-11-09

Latest resolved Personal results: the saved count attempt 15 completed QA and was
rejected because the extracted word lasts 0.4355 seconds, below the unchanged
0.5-second minimum. Its speaker similarity passed. This reservation has no
unused candidates. The saved Go attempt 12 passed parent transcript and speaker
gates but was rejected at the crop boundary: the next word starts at 0.48
seconds. Both outcomes are recorded; neither source nor alignment is replayed.
Go attempt 13 remains unused. All 24 source files, model files and profile pins
match inside the Personal provider namespace; no synthesis ran in that audit.

The accepted Portuguese Tai Chi recording `tai_chi_text_3d0ce619` and all four
saved ordinary Tai Chi recordings are now copied into canonical practices
locally. Fresh Personal readback is current and complete 16/48 kHz decodes
pass with zero full-scale samples. The transactions preserved other data and
the retry ledger. Eight copy-safety tests passed, including rollback,
changed-file refusal and actual Personal stage ownership. Both unique
synthetic source-route fixtures stopped before source intent on an occupied
model lock; their owned descendants are closed and no real Go attempt was
consumed. Atomic source admission is being handled by the runtime owner.

Native06 cleared the corrected compiler header generation and stopped on
removed Kryon widget import aliases. The necessary app migration uses the
current `kryon/Widgets` catalog and current loading/SVG component modules.
The complete qualified and unqualified app import inventories were reviewed.
Focused native graph validation now reaches the Entity dependency's
`achievement_toast.zi`. Its four obsolete widget imports are now migrated in
canonical Entity to `kryon/Widgets` and `kryon/svgicon`, with an Unreleased
note. The other 31 directly reachable Entity modules need no import changes.
The canonical read-only Personal namespace is verified. The next focused run
matched its source pins, then stopped at offline package resolution before
linking or compiling; app, Entity, Kryon and compiler fingerprints were unchanged.
The 120-second cache probe timed out cleanly. Its finite successor completed
cache validation in 362 seconds and exposed a forwarded locked launcher's
64-module-root limit against current Kryon's 79 roots. The current app CLI
already supports dynamic roots; this was a launcher-selection failure. The
ignored local toolchain override now selects canonical Ziran, mounted read-only
in the app-owned Alpha namespace. Namespace fixtures 16 and 17 passed with the
actual selected CLI and unchanged Entity pins. Canonical Apps host and game HUD
imports now use `kryon/Widgets`; their exact live bytes and read-only boundary
also passed fixture 17. The Apps export remains alive for native consumers.

The app Make prerequisites independently omitted the package CLI's Ziran
sources. Their inventory now covers compiler, package, runtime and standard
sources together. The real toolchain build returned zero, but its provenance
check rejected it because `cmd/zir/zir_zx_native_run.c` changed upstream during
that run. All 333 source fingerprints were checked and the owned unit is
closed. Legitimate upstream performance work continues; no checkout is frozen.
The selected current package CLI is pinned separately. Actual resolver 18
completed successfully on Alpha: `pkg path apps --offline` returned canonical
Apps in 258.438 seconds, with unchanged input pins. Its unit is inactive with
no remaining process or control group. Breeze's package wrapper now retains fetch and uses one ordered `pkg paths`
JSON response for all 28 selectors. It validates the full response before
creating links and preserves previous links on refusal. All nine black-box
consumer tests passed on Alpha, including malformed/incomplete responses,
selector and directory failures, and paths containing spaces, quotes,
backslashes, newlines and Unicode. Both prepared graph scripts parsed on Alpha.
These controlled-CLI tests do not establish actual batch compiler integration.
The upstream batch command subsequently passed its complete constrained local
package suite, including forwarding and immutable-cache refusal. The shared
upstream build changed afterward during independent work, so Breeze rebuilt
its own stable toolchain. Build 23 completed successfully with all 333 source
fingerprints unchanged, and its actual package CLI exactly matches the tested
upstream executable. Its finite Alpha unit is closed. Namespace 24 always uses
that app toolchain through a read-only canonical build overlay. The real
28-selector package integration stopped after helper cleanup disconnected the
Entity source export. Its failed result, unchanged host inputs and closed finite
unit are retained; it is not a package pass. Task-owned Entity, native and Ziran
exports now replace those helper lifetimes. Namespace 27 passed actual source
and compiler hash, write-denial and Git-root checks with all four old native,
Ziran, shared-build and batch-publication exports hidden. A new package run uses
only these verified mappings. Full current native graph, app build and
private-display playback remain pending. The package and compiler
phases are separate, reserving the heavy lock only for compilation.
No package cache was edited.

The first broader static audit timed out after 300 seconds and is closed. Its
directory-indexed successor completed the 495 roots and 987 resolved sources.
The Entity and Apps obsolete imports it identified are now repaired in their
canonical repositories. This static inventory and namespace verification are
not compiler passes. Full native app, package, decoder/mixer and private GUI
validation remain incomplete. No commit, push or installation has occurred.

The later Personal VM recovery supersedes the initial failures below. The fresh
Personal native handoff and actual KVM identity are verified. The saved count
recording passed the unchanged strict verifier on Personal with five tests
for changed metadata, truncation, missing generation wait, valid preserved
input and wrong job identity. The successor exited zero with its SSH worker
waited; no synthesis or model work was repeated. Its raw metadata was
reconciled once against the original reservation. Full audio QA remains
pending before publication.

The current-source suite on Personal passed font coverage, translations, clean
text API, button API, law mutation, sync recovery, version tests and the astral
course/clock/guidance/staging tests. It stopped at an English Sun Salutation
recording whose decoded peak exceeded the unchanged limit. The specialist's
later Personal validation passed all 307 shipped course lines and all 400 Sun
recordings after the scoped legacy headroom repairs. That independent result
clears this failure; the original suite had no changed source inputs.

Native validation uncovered Kryon folder migration in codec source discovery
and compiler search roots. Breeze now uses Kryon source inventory and manifest
roots. The locked compiler then rejected more than 64 module paths; the current
canonical Ziran task owns its dynamic-limit fix. Its Personal live export
passed the source-access probe. The first native run against it stopped before
make on an incorrect validation file list; its successor reached compiler
generation and failed on an undeclared `SliceRangeAt` call in generated
`compiler_parse.c`. All 288 compiler source fingerprints and the app inputs
were unchanged, while upstream HEAD advanced. The compiler task owns that
failure: the generated local `zir_slice.h` lacks the helper already present in
the canonical include header and shadows it through a quoted include. Full
native build and private GUI validation remain incomplete. The prepared next
run includes actual narration linking, six Portuguese decoder/mixer playback
cases, and the private-display chooser/session tests. No feature commit, push,
release or installation is claimed.

PT-specific files were copied with exact hashes. A real nested native/provider
probe passed on Personal. The new scoped QA transport reproduced the full
canonical alignment baseline exactly and preserved owned model waits; a
separate successor passed all nine integration/corruption tests. Full count
QA completed alignment, then stopped before speaker verification because the
canonical verifier interpreter alias is missing in the native importer. Its
owned SSH wait returned one and cleanup returned zero; the recorded unit is
inactive with no processes. Canonical PCM and its amplitude receipt remain
intact and match the retained alignment WAV. Nine retained-conversion tests,
ten scoped QA transport tests, and six completed-alignment reuse tests pass on
Personal. The real canonical context engine reuses the exact saved alignment;
a guard refuses to replay that original alignment before any child is started.
The accepted immutable importer handoff repairs the parent interpreter aliases
without changing the original profiles. A single cache-only count continuation
completed on Personal without any source, conversion or original alignment
replay. Its speaker score passed, but the extracted count lasted 0.4355 seconds,
below the unchanged 0.5-second minimum. The candidate is rejected and all four
reserved attempts are resolved; no unused count candidate remains. The original
alignment, audio and exact failure diagnostic are preserved. The saved Go source
and four never-reviewed ordinary sources are queued independently on Personal.

The original failure below is retained for provenance; the strict Personal
verification and metadata reconciliation above supersede it. The count
candidate in `fresh15-07-01/source` completed generation with an
owned worker and SSH exit of zero. Its separate strict verifier timed out
after 90 seconds; its child was terminated and waited (exit -15), and its SSH
returned one with successful cleanup. Preserve those bytes and the original
failure evidence. There is no verification proof or `raw-request-result.json`.
Continue verification of the saved source without repeating synthesis.

The finite quality batch completed dispatch 001 with an accepted staged
recording. Dispatch 002 returned 78 while queued, without quality output;
dispatches 003 and 004 were never created. The accepted staged Tai Chi clip
is not published: `publication7-production-01` is absent. Continue those
outcomes separately without replaying the finite batch.

The original app source suite failed at the missing `fontTools` import.
A fresh native-runner probe stopped before Python because its mount was absent.
The coordinator verified that `alpha-vm-host` is physical Alpha; the requested
target is the Alpha Personal VM (`alpha-personal`, hostname `personal`, KVM).
Use only the verified Personal VM handoff for future workloads. Earlier host
tests do not establish validation on the selected VM. Infrastructure repair,
full native app tests and private-display desktop/portrait tests remain pending.
No feature commit, push, release or installation has occurred.

The cached Japanese Tai Chi repair is integrated and locally revalidated, including full 16/48 kHz decoding and preservation of the other receipt rows and recordings. The corrected Russian follow-up finished with six accepted cues; its failed cue and all consumed attempts remain recorded. Portuguese Bruce narration is complete at 88 cues, while the wider requested narration set remains unfinished.

The Portuguese workout count comparison now has an explicit three-rule policy, with successor descriptors for the existing context families. Original provider profiles, canonical speech, historical policy bytes and quality limits remain unchanged. All 17 fresh ASR jobs passed for the 15 existing context proofs. Cached count Three passed its three additional checks and full ordinary validation. Both retained count One sources failed the unchanged encoded-duration minimum (0.467125 and 0.4275 seconds); the alternate was rejected before new model checks. All 23 actual model children are finished and reaped. The 16-row candidate passes full 16/48 kHz decoding with zero full-scale samples, 99 relevant local tests pass, and the 4,947-row frozen audit has no new default deltas. The reviewed 16-row migration is integrated locally: every affected public clip passes ordinary validation and full 16/48 kHz decoding, the old 15 recordings and all unrelated receipt entries are preserved, and both writer locks were released. The standard narration target passes 164 local tests plus the locale inventory check. Six Portuguese workout cues remain pending; their cache/ledger continuation plan is prepared without model work or reservations. No feature commit, push, release or installation has occurred.

### Current Personal import integration (2026-11-10)

The documented offline package operation completed and linked all 28 packages,
including the five canonical local overrides. Its broad audit saw unrelated
Kryon onetimecode/scrubfield edits, so that operation is not reported as a
whole-source validation. The subsequent full 495-module graph used stable
source and tool pins, but failed on unresolved layout and text functions.

The app now explicitly imports `kryon/layout_behavior` in the 54 files that
use its helpers. A focused real compiler probe on Alpha Personal passed for
KeyHash, Clamp, CenteredColumnFor and IsDesktopWidth with unchanged compiler
and app inputs; its owned unit is closed. The complete graph is still pending.

The retained widget probe establishes the separate reusable Kryon collision:
standard roots first fails Text and Image; component roots first passes;
qualifying only Text leaves Image failures. The failed overall probe is not a
passing suite. Exact canonical import edges were sent to the coordinator for
upstream repair. Breeze has no local root-order workaround. A fresh full graph
will capture source pins after those edits settle, followed by the native
build, Portuguese audio playback and private desktop/portrait GUI tests.

The native integration launcher was corrected before execution to pass only
its worker's actual argument. It has not run. No feature commit, push, release
or installation is claimed.

The next fresh 495-module graph also failed with stable source and tool pins.
Image lookup is repaired, but standard text and qualified widget text still
conflict. A four-case real compiler diagnostic passed the widget-only case;
adding standard text before or after the widget import failed. Its successful
harness exit is diagnostic completion, not a passing mixed-import test. The
minimal fixtures and exact failures are with the coordinator for upstream
routing. Modal, toolbar and scroll helper imports are now explicit in three
additional app files. The two pre-existing practice-home TextProps members
use explicit local types; the checker itself remains unchanged. Required API
and translation checks plus the practice-package check passed on Personal
before these import-only changes. Full native and GUI validation remains pending.

The focused modal/toolbar/scroll import probe passed on Alpha Personal with
unchanged app and compiler inputs; its owned unit is inactive with no processes.
The coordinator has assigned the mixed-import compiler prerequisite upstream.
There is no active finite app compiler consumer. The four owned source
transports remain open for integration. Resume the full graph only after the
coordinator confirms the new coherent tool set, using a new versioned admission;
the old 741/e292 admission remains immutable. The prepared native test sequence
also includes the existing astral parser/catalogue and narration target. This
task remains open; no feature commit, push, release or install has occurred.

### 2026-11-10 resumed local validation

Restored the Alpha Personal native test route against the canonical checkout,
with project-scoped writes, read-only dependencies/tool cache, cleared desktop
environment and private display sockets. The inherited namespace referenced
exports that no longer existed. The shared replacement is maintained under
Harmony's ignored backup/alpha-live-checkout, not application source.

The clean text API, button API and translated-locale local tests passed
(receipt 5feaabae3bf63bbc9989017054964ec8848e). Build-laws stopped at missing
Chinese U+996E and Korean U+D488 glyphs before compilation. Regenerated the
existing shipped font subsets on Personal; the font coverage test now reports
zero missing glyphs. The focused content, narration timing and package-source
local tests passed (receipt 744cd368474012615c5906294a3fe3fe1f7a). These are
source/data tests, not full native platform validation.

The full graph attempt failed resolving a real relative file import in
app_notifications.zi (receipt a5e1ae3d9c1965773c4fed1524333b8a5176). The
minimal fixture reproduces that physical file import failure until its nested
directory is separately listed as a package source root. No app manifest
workaround was applied. The coordinator has the diagnostic and upstream
compiler repair; all this task's compiler consumers are closed pending its
new stable tool admission. A concurrent peer source change also prevents
accepting that failed full-graph run as a stable integrated result.

Static preflight of practice_audio_ui.py, session_window_ui_test.py and
astral_projection_ui_test.py passed on Personal, including the actual
countdown regex and ALSA config line breaks (receipt
85e14a8e400cdf9b420363a08df7fe130c82). The music modal, focused/unfocused
single-click breathing and all six desktop/portrait astral interaction tests
still require a fresh native build and private-display execution.

Metadata inventory found Portuguese 88/88, Russian 9/88, and one clip in each
of the other eight supported languages: 105/880, with 775 pending. This count
is not new ASR/content certification. Media generation stays with the owning
media task; no generation or unknown publication was replayed. App source,
fonts and tests remain uncommitted. No push, release or installation occurred.

The shared runner's optional native artifact binding is verified separately
(receipt e704759c72929ec7fa7c26cf7ceba3c226d3): worker-owned ext4
output/artifacts can be writable at the Ziran artifact-cache path while the
global cache, dependency sources and compiler remain read-only. No compiler
was invoked by that probe.

Broader source gates passed version consistency, settings persistence keys,
and all 813 used locale keys with matching placeholders. The English unused
media_compression_offline key failure was routed to its owning media task.
Added a dedicated ming-segment-pipeline-test make target for the existing
real float-WAV/cache/PCM fixture test, which needs NumPy and soundfile but
loads no model. All 344 test entry points now have a runner.

The complete Ming/local narration fixture targets passed on Personal through
the build queue (receipt c82ebcba08f23b320a6693474b02339fb57a): 169 unittest
cases plus the ten-locale inventory assertions. Fake synthesis stays inside
test fixtures; no model or recording generation ran. A timed-out dependency
download was recovered from its completed wheel and installed offline into
the existing native Python site, reusing system NumPy/CFFI. The test-target
change remains uncommitted with the rest of the feature. Native compilation,
actual narration playback and private app GUI validation remain pending the
coordinator's new compiler cohort; missing narration remains a separate gate.

Native continuation is now prepared in the existing ignored Alpha preparation
folder: resume_native_worker.py and the updated resume_canonical.py require
an explicit new tool-cohort manifest for native execution (CLI, zi2zir,
zi2c and libziran.a). Personal syntax preflight passed (receipt
a92917a06fad026f04978ca710914b26cb8c). The existing native worker root now
has output/artifacts; its narrow cache bind passed the same read-only source
and tool checks (receipt 06aa61ee28fa51ca52efe398fb20a8729422). The worker
will record each gate separately, including actual Portuguese playback and
both private UI suites, with source/tool audits afterward. It has not run.
The coordinator has this exact continuation contract and will supply the
replacement compiler cohort; no compiler was invoked during its rebuild hold.
