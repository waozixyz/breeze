# Astral practice asset interface

The app reads `assets/practices/astral_projection/catalogue.json`:
`{"schema":1,"practices":[{"id":"bruce_foundation_touch","duration":1200,"title_key":"astral_practice_foundation_title","description_key":"astral_practice_foundation_description","guide_key":"astral_practice_foundation_guide"}, ...]}`.

Six IDs in draft order: `bruce_foundation_touch`, `bruce_full_body_current`,
`bruce_elevator_trance`, `bruce_spin_loosening`, `bruce_rope_exit`,
`bruce_roll_out_exit`. Durations: 1200, 1500, 1800, 1800, 2400, 1800 seconds.
Metadata key middles: foundation, current, elevator, spin, rope, roll_out.

`sessions/{id}.json` uses the existing schema 1 session format:
`{"schema":1,"duration":1200,"cues":[{"second":0,"key":"astral_text_foundation_01"}, ...]}`.
Globally unique new cue keys use `astral_text_{middle}_{01..20}` and stay below
64 ASCII bytes. Cue starts include spoken time and deliberate quiet time.
The finite session ends at its duration, following the return cue.

All ten `text/{locale}.txt` files retain the established `[key]`, body,
`---` format. They contain all 18 translated title/description/guide entries
and 88 new translated cues. Guides use readable paragraphs for prerequisites,
setup, procedure, return and recall. The 88 new cues keep the existing paths
at `voice/{locale}/{key}.ogg`: 880 clips across ten locales. Female narration
uses local Ming for `en es de fr ja ko zh`, the selected Russian F5 model for
`ru`, the selected Czech Chatterbox model for `cs`, and
`FearL0rd/Chatterbox-TTS-Portuguese` for `pt`. Indonesian and Italian are
removed from the supported catalogues and packs.
The old `session.json`, old text keys and 20 English clips remain available.

The app persists the selected ID in `astral_projection_exercise`, resolves
names, descriptions, guide and cues from the same text catalogue, and uses
standard narration, locale, voice, music, history and result flows. Start and
How to open the selection/guide page before a session starts. No new host API.

Precommit gate: complete localized media and recordings, full native build,
behavior/content/API/locale/law local tests and private-display GUI coverage of
all six selections at desktop and portrait sizes. No release or version bump.
