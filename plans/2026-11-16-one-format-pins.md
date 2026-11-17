# Breeze on pushed one-format pins

Owner: "i like what we did with tao te ching in inner breez, jsut i want the miage if
enabeld to be its own page with the titel" / "cleanyl centered" / "okay but you should
pin to veriosns we have aon igthpbu". Decisions: migrate Breeze to the namespaced Kryon
API, fix the whole chain first (no overrides anywhere), redesign Apps add-ons now.

## Target pins (one set for the whole chain)

- Ziran toolchain `v0.6.0` at released commit `d17c7aa1`, including the hosted
  record-identity compiler fix. Build from the immutable package cache; leave the
  shared canonical compiler outputs alone.
- Target Kryon pushed master `1b290f19`, including Markdown preview/editor exports,
  the TitleBar/Dropdown canonical hosted-record fix and its Ziran 0.6.0 pin.
  Breeze now locks it with the aligned upstream chain. CI has not been checked.
- Shared packages: Css `71a1b9f3`, Plot `b1e9b025`, Game2D `5b8007ae`,
  Entity `d9c0c38b`, Apps `67ed956f`; all pushed and locally tested upstream.
  Arcade `712e99e` still needs its bundled artifacts regenerated for ZX 28.
- practices `893e5b6f` (keeps the `f27afecf` banners; regenerated Lumi guide voice takes).
- Use one Kryon revision across the package chain. Update transitive declarations
  in their owning upstream repositories; do not edit cached packages.
- Breeze keeps the node-request edits from the compatible-versions task (sends `zx=28`,
  web builds ask for `format=wasm`) and commits them after testing.
- Known Ziran gap, not in 0.5.0: a module string constant becomes a bare C
  `#define NAME "..."` and rewrites same-named fields, parameters and locals; rename
  the constant in our code if a build hits it.

## Open work

1. Finish the existing desktop migration and run the node-download private-display
   test against the regenerated Arcade catalog.
2. Rebuild bundled Arcade as ZX 28 and update its recorded metadata, hashes and game
   art. `make collection` currently stops at the version ledger: Shovey records
   0.6.169 versus source 0.6.171, and its editor 0.2.149 versus 0.2.150. Preserve the
   unrelated dirty Arcade work and use its catalog version update command. Publish
   the current-format add-ons requested by the owner, keeping older artifacts.
3. Finish the Moto photo checks listed in `2026-11-16-crash-safety.md`.
4. Verify the web node-app request/loader boundary. Pre-lowered `.wasm` payloads still
   need upstream Ziran runtime support before `format=wasm` can be selected safely.
