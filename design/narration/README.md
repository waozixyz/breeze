# Local female narration

The app supports `en es cs de fr pt ru ja ko zh`. Ming handles `en es de fr ja ko zh`;
Russian uses `Misha24-10/F5-TTS_RUSSIAN`, and Czech uses
`Thomcles/Chatterbox-TTS-Czech`. Portuguese selects
`FearL0rd/Chatterbox-TTS-Portuguese`. Indonesian and Italian are removed
from active UI, text, packs and inventories, with verified recovery copies.
The inventory has 496 female cues per language: guide 32, Tai Chi 307, Sun
Salutation 20, original Astral 20, Workout 29, and the six Bruce practices 88.
Replacing the seven Ming languages requires 3,472 clips; all ten female
inventories require 4,960, including 880 new Bruce recordings. Male recordings
retain their existing provider and paths in supported languages. WHM,
meditation and patterns currently have no spoken narration inventory.

`ming-inventory.json` is an inventory snapshot, not a generation receipt. Refresh
it without changing package links:

```sh
python3 scripts/practice-narration-inventory.py \
  --media-root /mnt/storage/Projects/waozixyz/modules/practices \
  --output design/narration/ming-inventory.json
```

The public `ming-female.json` descriptor pins the official model/runtime
revisions, every runtime/model/ASR artifact, the synthetic female WAV and CAMPPlus
embedding, the local adapter source, and Python package versions. Female configs
reference it through `ming`. The default generation command retains the previous
provider; Ming is selected explicitly with `--ming-profile`. No unsupported
locale is sent to Ming or silently redirected to another service.

The ignored `backup/narration/ming-local.json` supplies existing absolute paths.
Model and ASR weights now use the shared harness store; the runtime, environment
and female reference remain at their original read-only installation paths:

```json
{
  "runtime": "/absolute/existing/ming/runtime",
  "model": "/mnt/storage/Projects/harness/models/weights/tts/ming-3.0-tts-0.5b",
  "reference": "/absolute/existing/calm-female.wav",
  "embedding": "/absolute/existing/calm-female.pt",
  "asr": "/mnt/storage/Projects/harness/models/weights/asr/whisper-small",
  "verification_models": {
    "openai/whisper-small": "/mnt/storage/Projects/harness/models/weights/asr/whisper-small",
    "openai/whisper-large-v3-turbo": "/mnt/storage/Projects/harness/models/weights/asr/whisper-large-v3-turbo"
  },
  "threads": 2
}
```

Use the interpreter of that installation. No command below downloads or installs
models. To deliberately fingerprint an installation after a reviewed adapter or
runtime change, run `scripts/prepare-ming-profile.py --local
backup/narration/ming-local.json --output design/narration/ming-female.json`.
Changing verification settings invalidates affected QA receipts. The separate
`verification` block pins Japanese and Korean to Whisper Large v3 Turbo; the
other five Ming languages retain Whisper Small. Each transcript records its actual model,
revision, artifact manifest hash, language, full sample count and encoded audio
hash. One recognizer is loaded at a time, including language switches.
`--previous-verification-profile` may retain explicitly pinned prior QA identities
only for locales whose model, revision and artifact manifest are unchanged. It
does not accept Korean's earlier Small receipts under the Turbo route.

Removing only `verification` reconstructs the exact original synthesis profile.
The original Ming and Whisper adapter files remain unchanged, so cached PCM,
request hashes and original synthesis provenance survive the verifier update.
Use `--cached-only` with the generation command to recheck existing pilot PCM;
it refuses missing or changed cached audio before any new synthesis. Fresh ASR,
speaker, duration, direction, number and ending validation still runs.

Attempt diagnostics are saved under ignored
`backup/narration/diagnostics/<locale>/<key>/<run>.json`. Each bounded record
retains the actual attempt's duration, speaker threshold, ASR identity, raw text,
scores and rejection reasons. A final failure distinguishes the best transcript
from the last attempt. These records never certify a recording by themselves.

The Sun Salutation comparison permits `向后脉`/`向後脈` and `向后卖`/`向後賣` only when its source
contains `向后迈`, plus that cue's traditional script equivalents. The raw ASR
text stays intact, and pulse words elsewhere are unchanged. The MOE dictionary
lists the shared pronunciation for [邁](https://dict.revised.moe.edu.tw/dictView.jsp?ID=1115&la=0&powerMode=0)
and [脈](https://dict.revised.moe.edu.tw/dictView.jsp?ID=1110&la=0&powerMode=0).
Its [賣 entry](https://dict.concised.moe.edu.tw/dictView.jsp?ID=3820&q=1) also records that pronunciation.
Japanese and Korean have no new pronunciation aliases: Turbo correctly recognizes
the saved Japanese leg instruction and Korean breathing cue that Small misrecognized.

Very short Sun Salutation cues have an explicit context path for `pt cs ru es fr zh`.
`short-context-provider-v4.json` binds each exact short phrase to a longer existing practice
instruction, the helper and verifier sources, and the blind alignment model.
Ordinary cues keep their original synthesis requests and receipt identity. Use
both options for context generation or preflight:

```sh
--context-profile design/narration/short-context-provider-v4.json \
--context-local-profile backup/narration/context-local.json
```

The current helper/verifier use explicit successor descriptors: Sun Salutation
`short-context-provider-v4.json`, Czech workout
`workout-czech-context-provider-v4.json`, Tai Chi
`tai-chi-short-context-provider-v4.json`, Czech counts
`workout-czech-count-semantics-v3.json`, and Portuguese workout
`workout-portuguese-context-v3.json`. Historical descriptors retain their original
source seals. Existing accepted proofs need fresh actual alignment before they
can migrate to a changed helper; the helper-successor staging command plans
exactly fifteen parent alignments and two Chinese crop transcriptions without
running inference or writing live receipts.

Portuguese counts opt in separately through
`workout-portuguese-count-semantics-v1.json`. Only the exact registered workout
cues and parents equate standalone ASCII `1`, `2`, `3` with `um`, `dois`, `três`.
Raw ASR remains unchanged. Signed, decimal, ordinal, combined and non-ASCII
number forms, missing or extra words and the start cue receive no aliases.
The same sealed comparison reaches final assessment and receipt replay;
existing speaker, prefix, duration, ending and complete decoding gates remain.

The parent instruction must pass complete blind transcription and the original
provider's speaker threshold. Actual word timestamps select one contiguous prefix;
the encoded crop must contain exactly the short phrase, stay within the existing
speech budget and remain below full scale. Its receipt retains the actual short
speaker score separately from the parent's score. The original female reference,
model, thresholds and raw transcript remain intact.

The two configured Chinese short cues use separately pinned Turbo verification
for the final crop. Their receipts record the actual model, revision, artifacts,
audio hash and full sample coverage under the context recipe. This applies only
after the complete parent/crop proof validates; ordinary Ming routes and its
public synthesis profile remain unchanged. Chinese exhale uses the existing
plank instruction as its parent, preserving the spoken short cue `呼气。`.

Accepted parent proof WAVs are copied as binary files into
`sunsalutation/voice-context/<locale>/<sha256>.wav` in the practices package, outside
the playback and voice-pack globs. The proof binds the original synthesis identity,
parent hash, word alignment, crop range and actual encoded audio. `--check` verifies
the public proof and receipt without private weights or caches; supply only
`--context-profile` alongside the normal provider selection. Fixture tests verify
the protocol; each configured real cue still needs its own successful generation
and current-receipt validation.

An explicit context candidate may use the normal four attempts when its parent
fails speech quality or its exact crop fails quality checks. Each rejection
retains the actual parent/crop reason, scores and identity, including failures
before a short clip exists. Changed model/reference/source hashes, invalid
configuration and system errors remain fatal. Ordinary provider retry behavior
is unchanged.

Before generation, validate all actual file hashes without loading a model:

```sh
PYTHON scripts/generate-lumi-guide-narration.py \
  --practice astral_projection_bruce \
  --ming-profile backup/narration/ming-local.json --preflight
```

Replace `PYTHON` with the existing runtime interpreter. To generate the first
English and German pilot cues, remove `--preflight` and add `--locale en --locale
de --key astral_text_foundation_01 --jobs 1`. Only the media task runs generation;
coordinate the shared runtime's resources and package-link ownership first.
After actual foundation pilots in all seven languages pass, omit `--key` and `--locale` for all seven supported
locales. Prioritize Bruce and original Astral, then `guide`, `taichi`,
`sunsalutation`, and `workout`. The same command with `--check` verifies selected
receipts offline. Male inventories reject `--ming-profile`.

Russian, Czech and Portuguese select a provider explicitly, using the Python interpreter
recorded in that provider's ignored private JSON. Their incompatible synthesis
environments remain separate; shared QA runs in its own pinned environment.
Use `f5-russian` with `backup/narration/local-models/ru-local.json`, or
`chatterbox-czech` with `backup/narration/local-models/cs-local.json`, or
`chatterbox-portuguese` with `backup/narration/local-models/pt-local.json`:

```sh
PROVIDER_PYTHON scripts/generate-lumi-guide-narration.py \
  --practice astral_projection_bruce --local-provider f5-russian \
  --local-voice-profile backup/narration/local-models/ru-local.json --preflight
```

Replace `PROVIDER_PYTHON` with the JSON's `python` path. Generation rejects a
different interpreter before loading models. To generate a pilot, replace
`--preflight` with `--key astral_text_foundation_01 --jobs 1`. `--check` validates
receipts without an installed runtime or private model files. A provider never
receives another provider's locale or falls back to a remote service. Existing
clips from other providers/locales remain in mixed receipts. Actual provider
pilots must pass before bulk generation; descriptor status alone is insufficient.

One process caches one Ming model and one Whisper model. Each synthesis uses
explicit `language_id`, FREEFORM calm delivery and the same nonzero female
speaker embedding. Text hashes bind the complete request, language, seed, model,
reference, runtime, adapter and output encoding. Atomic per-cue receipts resume
completed work. Ignored `backup/narration/cache/` preserves exact generated PCM
requests across interrupted QA, avoiding another synthesis of the same request.
The output remains mono Ogg Opus at the existing app paths.

Ming's dense runtime shares a 512-token cache between the input and generated
audio. The original German foundation request left only 23.28 seconds of audio
budget. `narration_segments.py` now preserves exact source spans and splits long
cues at sentences, clauses and safe whitespace, targeting 24 semantic units.
Short cues remain one request; words, decimal numbers and Unicode whitespace
are preserved. Every span uses the same original female embedding and explicit
language, with a deterministic seed. Float waveform caches resume completed
spans. Assembly concatenates their audio without overlap or added silence.
The profile and request identity bind the segmenter, plan and assembly settings.
Every actual prompt must leave at least 16 seconds of decode budget before
synthesis. Whole-cue QA remains required after assembly. Finite raw waveforms
are saved as float WAV before peak rejection; empty and nonfinite results are
rejected with numeric diagnostics. No automatic clipping or gain is applied.

Every accepted clip must be finite and unclipped, fit its speech budget, retain
the reserved Bruce quiet interval, match its complete transcript, and meet the
recorded CAMPPlus speaker-similarity bound. Sun Salutation also fits its shortest
six-second default breath with a 0.2-second margin. Whisper receives all samples
without truncation and uses its sequential timestamp-based decoder, including
cues longer than 30 seconds. QA supplies no expected-text prompt. Every local cue
also requires matching final 64- and 24-character transcript endings, using the
same locale aliases as the whole-cue comparison. This rejects the initial
23-second German pilot's missing final clause despite its 0.92958 overall score;
the complete English pilot remains accepted. Receipts bind QA to the actual encoded
audio hash and full decoded duration. Speaker similarity measures consistency;
it does not establish how a listener perceives the voice.

`python3 tests/ming_narration_test.py` tests hashes, request identity, rejected
locales, real Opus fixture encoding, quiet intervals and full long-audio routing.
Fixtures are separate from production media and do not certify real Ming speech.
`python3 tests/local_narration_pipeline_test.py` verifies separate provider
routing, wrong-interpreter rejection and full receipt identity. These local
tests use isolated fixtures. `tests/ming_segment_pipeline_test.py`, run under the
existing Ming interpreter, verifies real float WAV, PCM assembly and cache resume
without loading a model. Real seven-language Ming pilots and all selected
Russian/Czech/Portuguese pilots, all recordings and final native playback remain required
before the feature can be committed or described as complete. No partial pack
may advertise missing languages as complete.

Official references: [Ming controls](https://github.com/inclusionAI/Ming-3.0-tts/blob/main/cookbooks/instruction_en.md)
and [Whisper long-form decoding](https://huggingface.co/docs/transformers/model_doc/whisper).
