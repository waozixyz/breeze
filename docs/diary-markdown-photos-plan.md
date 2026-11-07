# Diary as Markdown with photo embeds, and Photos in Inner Breeze

Owner request, 2026-10-17: a Diary entry is one clean Markdown document whose
photos are image embeds pointing at internal keys and shown inline, with no
separate photo list or Remove buttons. Photos becomes an optional app inside
Inner Breeze, not preinstalled: the encrypted, Ente-like library from
`waozixyz/photos`, syncing through Daochi. With Photos installed, the Diary
shows that day's library photos in a gallery under the entry; dragging one into
the entry adds an embed that refers to the same encrypted photo, so nothing is
stored or uploaded twice.

This plan lists the data formats, the migration of existing entries, how the
two apps share photos through the host, the editor and drag-and-drop
primitives, and the stages in which they ship.

## 1. Entry format

The per-day document keeps Harmony's version-1 shape, so every released app
can still read it:

```json
{"version":1,"date":"2026-10-17","text":"Morning walk.\n\n![IMG_2041.jpg](diary:photo-20261017081500-1.bin)\n","photos":[{"file":"photo-20261017081500-1.bin","name":"IMG_2041.jpg"}]}
```

- `text` is the entry and the only source of truth.
- `photos` is a mirror for older app versions. On every save the package
  derives it from the `diary:` embeds in `text`, in order, once per file. Older
  apps keep showing those photos in their carousel and the embed lines as
  plain text.

### Embed grammar

An embed line is a line that, with its surrounding spaces, tabs and a final
`\r` removed, is exactly `![ALT](SCHEME:TARGET)`:

| Part | Rule |
|---|---|
| `ALT` | 0 to 200 bytes, no `[`, `]` or line breaks. The file's original name. |
| `diary:TARGET` | A Diary file: `[0-9a-z.-]{1,200}`, not `.` or `..` (the existing `SafePhoto` rule). |
| `photos:TARGET` | A Photos library item: its 64 lowercase hex SHA-256 of the original bytes. |

The internal keys never leave the account: a `diary:` name is a private file
name, and a `photos:` hash is resolved only inside the account's library.
Embeds inside a line of other text, unknown schemes and invalid targets stay
ordinary text. Inserted embeds always get their own line (§4).

### Migration of existing entries

No stored data is rewritten on load and no file moves:

1. Load validates the document exactly as today (version 1, date, text, valid
   `photos` rows), so damaged documents stay read-only and untouched.
2. Every `photos` row whose file no `diary:` embed in `text` names becomes an
   embed line appended to the text, in array order:
   `![<name>](diary:<file>)`. The block is separated from existing text by a
   blank line. Names lose `[`, `]` and line breaks (replaced with spaces).
3. The migrated text is kept in memory only (`saved` stays true). Viewing an
   old day therefore writes nothing; the first real edit saves the migrated
   text and the derived `photos` array.

Mixed versions: a photo attached by an older app (a new `photos` row) appears
as an embed on the newer app. A photo removed with an older app's Remove
button reappears on the newer app while its embed line remains in the text;
deleting the embed line removes it everywhere. Undo, redo, Lumi's
`/journal`, calendar marks and the version-1 checks need no change, because
embeds are text.

Spelling: the host replaces each embed line with an empty line before the
text goes to the node's spelling service and puts the lines back afterwards.
A correction that changes the number of lines is refused with the existing
`diary_spelling_error` notice. File names and photo hashes never reach the
service.

## 2. Editor

The entry stays one `TextArea` with the existing live preview: Markdown
markers are hidden away from the line holding the caret or a selection.

CommonMark basics, as the coordinator set for this change:

| Markdown | Away from the caret's line | On the caret's line |
|---|---|---|
| `# ` to `###### ` headings | marker hidden; the line is bold and larger (1.6, 1.4, 1.25, 1.1, 1, 1 times the entry's size) | marker shown, size kept |
| `**bold**`, `__bold__` | markers hidden, text bold (as now) | markers shown |
| `*italic*`, `_italic_` | markers hidden, text slanted | markers shown |
| `[text](url)` links | `[` and `](url)` hidden, text in the link color | all shown, text in the link color |
| `- `, `* `, `+ `, `1. ` list items | marker kept, in a muted color | same |
| `> ` quotes | marker and quoted text in a muted color | same |
| whole-line photo embed | line hidden, photo drawn in its place | source shown, photo kept under it |

Emphasis follows CommonMark's flanking rules within one line: an opening run
is followed by a non-space, a closing run follows a non-space, and `_` does
not emphasize inside a word. Code spans, tables and HTML stay plain text.
Links are not followed from the editor.

- Clicking a photo puts the caret at the end of its line, which shows its
  source; deleting that line removes the photo from the entry.
- The photo carousel, its arrows and the Remove photo button are removed. The
  toolbar's photo button stays and inserts an embed at the caret. Without
  Photos the picked photo is saved as today (`DiaryStoreAttach`) and embedded
  as `diary:`. With Photos installed it is added to the Photos library (once
  per hash, dated by its capture day) and embedded as `photos:`, so every
  picture lives in one place.
- A photo whose bytes are not on this device (not downloaded yet, or a
  `photos:` key the library does not have) shows the existing placeholder text
  `diary_photo_unavailable` in its frame.

### Kryon primitive: blocks in a TextArea

Hosted cells cannot measure text, so a Diary package cannot place pictures
between wrapped rows itself. Kryon's `TextArea` gains one reusable primitive
(in `kryonlabs/kryon`, master):

```
TextAreaBlock :: struct {
    start: s32      // byte offset of a logical line's start
    height: s32     // the box's height
    cover: bool     // the box takes the place of the line's last row
    image: string   // asset path drawn fitted in the box, or ""
    label: string   // shown when the image is empty or unavailable
}
TextAreaProps.blocks: []TextAreaBlock   // sorted, unique, at line starts
```

- A block adds a box under its line (or in place of the line's last row when
  `cover` is set, for a line whose bytes are all hidden). Rows, wrapping and
  caret stops are unchanged; only vertical positions, content height, hit
  testing and painting account for boxes. A point inside a box maps to the end
  of its line.
- The image is drawn with the `Image` widget's contain fit and clipped to the
  area; a missing image draws a soft rounded frame with `label`. A loading
  image draws only the frame.
- During an IME composition, block offsets after the composition move with
  the preedit text, so photos do not jump while typing on Android.
- An invalid list is ignored as a whole, as for `hidden`. With no blocks the
  layout is byte-for-byte the current one.

Two more styling inputs complete the CommonMark basics:

```
TextAreaLine :: struct { start: s32; font: s32 }   // a logical line's font size
TextAreaProps.lines: []TextAreaLine                // sorted, unique, at line starts
TextAreaProps.italic: []TextRange                  // slanted bytes, as strong
```

A line's font size changes its rows' height, wrapping, caret and hit
testing; all rows of other lines keep the area's font. Italic keeps the text's
advances: backends that register a slant raster (raylib through an rlgl shear
of the glyph quads, the canvas host through its italic font) draw the bytes
slanted, as backends register the emphasis raster for bold today; others draw
them upright.

A last addition makes the area a drop target for app data:

```
TextAreaProps.drop: bool; drop_x, drop_y: float32
TextAreaResult.drop_cursor: s32   // -1 when the point is outside the area
```

While `drop` is set, the area paints a drop caret at the text position under
the point and reports it. Both fields are new names in the widget codec, so
older packages and hosts keep working (records match fields by name).

## 3. Photos in Inner Breeze

### One library, one encryption model

The standalone Photos app encrypts each original on the client, addresses it
by its plaintext SHA-256, seals it deterministically so retries reuse the same
copy, binds it to the account, and verifies size and hash on download. Inner
Breeze already has the same model for Diary photos (Inbe c4babc97):

- per-file key `HMAC-SHA256(account key for "inbe-diary-blob-key-v1", sha256)`,
  ChaCha20-Poly1305 with the fixed zero nonce (one key seals one file),
  AAD `inbe.diary.blob.v1`;
- sealed copy = file + 16-byte tag, stored as `PUT /api/v1/blobs/inbe/<sha256 of
  the copy>` (up to 16 MiB, counted once per account by the node even when put
  again);
- the key and copy address travel only inside the account's encrypted
  records.

Photos in Inner Breeze uses this scheme unchanged, including the historical
`diary` context and AAD names: the same photo in Diary and in Photos is the
same sealed copy at the same address. Renaming the context would change every
key and re-upload every photo. Videos and originals over 16 MiB need chunking
(stage 4), as standalone Photos already does with 8 MiB chunks.

### The account's media library is a host service

Photos is the library's interface, not its owner. The host keeps one media
library per account, so Diary never reads another app's records:

| Record (settings key) | Collection | Value |
|---|---|---|
| `cell.media.<sha256>` | `private.inbe.v1.media` | `{"hash","size","type","name","day","taken","added","trashed"[,"blob","key"]}` |
| `cell.media.preview.<sha256>` | `private.inbe.v1.media` | `{"hash","size","type"[,"blob","key"]}` of the item's preview file |

- `day` is the capture day in local time (`YYYY-MM-DD`): the EXIF original
  date when the file has one, otherwise the day it was added. `taken` is the
  full capture time with its offset when known.
- The preview is a JPEG (quality 80) at most 512 px on its longest side,
  turned upright by its Exif orientation, made on import by a new Kryon
  backend primitive, `ImagePreview(bytes, type, max_edge, orientation,
  quality)`: the host's decoder (raylib, or the canvas backend's
  raylib-compatible functions in a browser), then portable Ziran for turning,
  area-averaged scaling and a baseline JPEG encoder. Galleries and Diary
  embeds draw previews, never originals; small upright photos are their own
  preview.
- Files live per account under `media/<account>/<sha256>` and
  `media/<account>/<sha256>.preview`, beside the Diary's directory.
- `blob` and `key` appear once a copy is on a node, as in Diary entries. The
  pass sets them with `json_set`, so fields added by a later version survive.
- The collection's apply branch accepts every `cell.media.*` key and the
  store ignores kinds it does not know, so later versions can add records
  (albums of the library, for example) without breaking this one.
- Photos' own organization (albums, favorites, captions) lives in Photos'
  app records, `cell.photos.*` in its own collection
  `private.inbe.v1.app.photos`, keyed by the same hashes.

Every new record goes into a new collection. A released app that receives an
unknown key in an existing collection (`private.inbe.v1.cells`,
`private.inbe.v1.app-preferences`) fails the whole sync page, while it skips
unknown collections. The node already accepts these names (Daochi registers
`private.inbe.v1.*` for Inbe); Lumi's move to `private.inbe.v2.lumi` is the
precedent.

### Copies move once, to every node that takes photos

`diary_blobs.zi` becomes the account's media pass. It plans over Diary file
entries and media originals and previews alike (each job knows its record key
and local path). Two rules make duplicates impossible:

- Before a PUT, a copy whose address this device already knows is on that
  node (`diary_blobs(node, blob)`) only has its entry completed; nothing is
  sent.
- Previews download for every item, so galleries work everywhere. Originals
  download only when wanted: opened in Photos, or embedded in a Diary entry
  on screen.

A Diary embed of a library photo (`photos:<sha256>`) creates no file, no
record and no upload. The same picture attached as a Diary file seals to the
same address as its library copy, so it is uploaded at most once per node.

### Nodes chosen for photos

Owner, 2026-10-17: "we can add multiple nodes and we can configure what to
store there this way you can avoid paying the waozi fees". Records keep going
to the active sync node (the Waozi node by default). Photo and video copies,
Diary files and the media library alike, go to every node in the account's
node list (`SyncNodeCount`, `SyncNodeAt`) whose photo upload is on
(`sync_node_<sha>.media_upload`, the switch on Profile › Data node cards), not
only the active one. With photo upload off on the Waozi node and on for their
own node, a person keeps their records on Waozi and their photos, and the
storage they cost, on their own node.

- Uploads: each pass walks those nodes, starting where the previous pass
  stopped so every node makes progress within the pass's limit (8 files,
  32 MiB). A copy goes to each such node that it is not known on. Turning a
  node's photo upload on queues every copy for it; turning it off stops new
  uploads there and keeps what it holds.
- Downloads: the active node first, then the other nodes in list order. A
  404 moves on to the next node; a copy found anywhere is remembered on that
  node.
- Per node: `diary_blobs(node, blob)` remembers copies by normalized
  address, a 413 marks only that node full (`SyncNodeStorageRecordFull`) and
  stops uploads to it for the pass, and its storage report is shown on its
  card as today.
- Sessions: blob requests never use the sync's `sync_auth_*` token. Each node
  has its own media session, saved device-locally under its node key
  (`SyncNodeCursorKey(address, "media_auth_*")`, account and address
  hashed), signed in with daochi-client's `Login`/`EnsureSession` (desktop)
  or `BeginSession` (Android and web, frame by frame), and the device is
  registered with that node (`RegisterDevice`, async `BeginRequest` to
  `/api/v1/account/devices`) once per new session. A 401 renews only that
  node's media session. Removing a node from the list forgets its session and
  its `diary_blobs` rows.
- Delegate (Telegram) accounts still never move copies.

### Host interface

Apps reach the library only through these generic calls, with capabilities
`media.read`, `media.import` and `media.write`. They join the generic
node-app interface (frame and route messages, `AppLocaleHost`) that More apps
introduces, and share its `host_api`.

| Call | Purpose |
|---|---|
| `MediaQueryHost(day, after, limit) -> MediaPage` | Items of one capture day, or all, newest first; trashed items left out. |
| `MediaAssetHost(hash, original) -> string` | `media/preview/<sha256>.<fmt>` or `media/<sha256>.<fmt>`, or `""` while missing. Asking for an original queues its download. |
| frame `media_pick_requested`, `MediaImportedHost() -> hashes` | The platform picker; each picked file is stored once by its hash, with its preview. |
| `MediaUpdateHost(hash, field, value)` | The name or trashed state (Photos only). |

The hosted asset policy allows `media/<sha256>.<fmt>` and
`media/preview/<sha256>.<fmt>` for items of the current account's library.

- Photos gets read, import and write.
- Diary, built in, gets read and import. Its view also gets
  `DiaryPhotoHost(target) -> string`: the asset path of an embed target
  (`diary/photos/<file>.<fmt>`, or the media asset for `photos:`), from a
  small format cache invalidated when a copy arrives.
- Diary's gallery and its photo button use the library only while
  `inbe.photos` is installed. Embeds keep rendering if Photos is removed later,
  because the library belongs to the account.

### The Photos app package

`inbe.photos`, now built and released in `waozixyz/photos`, is not part of
the APK's bundled cells. It is listed under More apps and installed from the node's signed package store,
through the node-app mechanism the Chess app introduces (a registry entry,
`app_used_photos` in `private.inbe.v1.app-installs`, a device-local node-app
slot). Its first version:

- a newest-first grid grouped by capture day, with day headings, drawing
  previews only;
- Add photos through the platform picker, each saved once by its hash;
- a viewer with previous/next, the photo's day and name, and Move to Trash
  (recoverable: the library keeps the item with `"trashed"`).

The standalone Photos repository stays the reference for the remaining Ente
features (albums, favorites, archive, search, map, people, editing, video,
Android camera backup). They move into this package in later releases.
Photos in Inner Breeze always syncs through the account's Daochi node, the
Waozi node (api.waozi.xyz) by default as everywhere in Inner Breeze (owner,
2026-10-17). The standalone app's ThinkPad-only pin does not apply here.
Importing the standalone library is not part of this work.

## 4. Diary day gallery and drag-and-drop

With Photos installed, the Diary day view shows the day's library photos as a
wrapping grid of square previews under the entry, headed "Photos from this
day". Days without library photos show nothing.

- Hold a preview briefly (0.2 s) and drag it. A copy follows the pointer;
  over the entry the TextArea's drop caret shows where it will go. Releasing
  there inserts `![<name>](photos:<sha256>)` on its own line: after the line
  under the point, or before it when the point is at the line's start.
  Releasing elsewhere, Escape, or leaving the day cancels. A quick swipe still
  scrolls the page.
- A tap, or Enter on a focused preview, inserts the photo at the caret, so the
  same action works without a pointer.
- Insertion is one edit: undo removes it, and it saves after the usual delay.

`EmbedInsertion(text, at, embed, snap_to_line)` in the Diary package computes
the edit: no blank lines are doubled, the caret lands on the line after the
photo, and an empty entry receives only the embed.

## 5. Stages

| Stage | Contents | Ships as |
|---|---|---|
| 1 | Kryon `TextArea` blocks, line fonts, italic and drop target; Diary 1.2.0: embeds, migration, inline photos, CommonMark basics, no carousel; host `DiaryPhotoHost`, spelling masking; `host_api` 12 | Kryon commits, Inbe APK + Diary package |
| 2 | Host media library: records in `private.inbe.v1.media`, files, previews (Kryon `ImagePreview`), `Media*Host` calls and grants; media pass over several record kinds and every node with photo upload on, per-node media sessions, skip of known copies, on-demand originals | Inbe APK (shares the node-app `host_api`) |
| 3 | Photos package through More apps; Diary gallery, drag-and-drop, photo button into the library | Photos package, Diary 1.3.0 |
| 4 | Ente features from standalone Photos, video chunks, camera backup, standalone-library import, further Markdown styling | Packages and APKs |

## 6. Files

New: `apps/diary/diary_markdown.zi` (embed grammar, Markdown preview
ranges, migration, mirror, insertion; no host access),
`src/cells/media_store.zi` and `src/cells/media_types.zi` (the host media
library and its calls), `src/storage/media_node_session.zi` (a media
session per node), `apps/photos/{photos.zi,photos_view.zi,CHANGELOG.md}`
(since moved to `waozixyz/photos`),
`tests/diary_markdown_behavior.zi` and its runner, and Kryon
`tests/ziran_text_area_blocks_test.{zi,sh}`.

Changed: `apps/diary/diary.zi`, `apps/diary/diary_view.zi`,
`apps/diary/CHANGELOG.md`, `src/screens/diary_screen.zi`,
`src/cells/module_host.zi`, `src/cells/hosted_assets.zi`,
`src/cells/diary_blobs.zi`, `src/cells/diary_blobs_native.zi`,
`src/app/app_sync.zi` (the pass over several nodes), `src/storage/sync_nodes.zi`
(removing a node forgets its media session), `src/cells/diary_store.zi`,
`src/cells/diary_spelling.zi`, the sync collection mapping in
`src/storage/storage_core.zi` and `src/storage/cell_records.zi`,
`apps/versions.json`, every locale for the new strings, `docs/cells.md`,
and `ziran.lock` after the Kryon commits.

## 7. Tests

- Diary package: embed grammar, migration of version-1 fixtures with photos
  (including names with brackets, duplicates and damaged rows), the derived
  `photos` mirror, insertion edits, round trips through an older-app save.
- `make cells-test`: a 1.1.x entry with photos loads with its embeds, saves the
  same files, keeps photo bytes, and attach inserts an embed.
- Kryon: block layout, caret and hit testing, composition offsets, drop caret;
  identical results without blocks.
- Storage sync: media records in their collection, an older build skipping
  them, copies reaching a second node with photo upload on and not the active
  node with it off, separate tokens per node, download falling back to the
  second node, a Diary embed of a library photo causing no upload, a second device
  downloading one copy (real Daochi node via `make sync-server-test`).
- Private Xvfb UI checks at phone and desktop width: inline photos, source
  reveal on the caret line, attach, drag from the gallery, spelling masking.

## 8. Open questions for the owner

Answered (owner, 2026-10-17): "photos should always use daochi nodes, in inbe
waozi is the default node no exceptions". Inside Inner Breeze the media
library syncs through the account's node like all its data; no ThinkPad
pinning and no import of the standalone library.

Defaults set by the coordinator until the owner answers: originals on demand
with previews everywhere; tap or Enter inserts as the non-drag form; CommonMark
basics as in §2; Diary's photo button adds to the Photos library when Photos
is installed. Node registration and other operator-key steps go through the
coordinator.

1. Registering `inbe.photos` on the node needs the registry operator key, and
   `apps/publishers.json` must include the new app ID.
2. Confirm the defaults above.
