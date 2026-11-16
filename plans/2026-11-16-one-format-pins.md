# Breeze on pushed one-format pins

Owner: "i like what we did with tao te ching in inner breez, jsut i want the miage if
enabeld to be its own page with the titel" / "cleanyl centered" / "okay but you should
pin to veriosns we have aon igthpbu". Decisions: migrate Breeze to the namespaced Kryon
API, fix the whole chain first (no overrides anywhere), redesign Apps add-ons now.

## Target pins (one set for the whole chain)

- Ziran toolchain `v0.5.0` (tag commit `f9f92b46`, includes the web `libziran.a` fix).
- Kryon pushed master `b45cc524` (built on Ziran v0.5.0; hosted `kryon/menu`,
  `kryon/layout`, `kryon/toolbar`, public `kryon/tree_frame` and the raylib-free desktop
  host pieces). Breeze pins Apps, Entity and Arcade, so all three share it. Move to the
  Kryon 0.4.0 tag once cut (no master commit is CI-green yet).
- Pushed on Kryon `245605c3` (repin to `cc731751` in progress): Apps `1c84ea0`, Entity
  `c1d8803`, Gamekit `69b44c69`, Shovey `59a47447` (completion_path_test and
  level_replay_test crash in Ziran), Arcade `7417c159` (full `make test` not run yet).
- Breeze keeps the node-request edits from the compatible-versions task (sends `zx=28`,
  web builds ask for `format=wasm`) and commits them after testing.
- Known Ziran gap, not in 0.5.0: a module string constant becomes a bare C
  `#define NAME "..."` and rewrites same-named fields, parameters and locals; rename
  the constant in our code if a build hits it.
- Kryon pushed master `0dea8bc2`; every repo in the chain pins this same commit. In
  Breeze's lock one `kryon` entry (ref `master`, commit `0dea8bc2`) serves both the
  exact root edge and the Css/Plot `master` edges.
- practices `f27afecf` (sharpened banners).

## Open work

1. Arcade on Kryon `b45cc524` (Apps child): `apps/bundled/arcade.zx` and
   `apps/bundled/arcade.games/*.zx` are still ZX revision 26, which Ziran v0.5.0 does not
   open (it runs revision 28 only). Rebuild the bundled Arcade from the new Arcade commit,
   update `apps/bundled.json`, and repin Breeze's `arcade` source.
2. `tests/node_child_download_ui_test.py` rewrites fixture assets in a v26 bundle; ZX 28
   also needs the manifest's asset and content identities recomputed.
3. Web node apps: Breeze sends `format=zx&zx=28`; a `format=wasm` request needs a web
   loader for pre-lowered `.wasm` payloads that Ziran's web runtime does not have.
4. Game2D `8b5a989d` still pins its own Kryon `1cd873fd`; Breeze imports none of its
   modules (only Makefile/CMake module paths), so it is a candidate for removal.
