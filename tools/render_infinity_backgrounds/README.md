# Infinity layered-background renderer

This tool holds the selected `PDE-002` portrait-development treatment constant
and renders seven background-only experiments from the layered Infinity TIFF.
The source TIFF is never modified. Photoshop is used only to export 16-bit
working copies of the named `Subject` and `Background` layers.

Every candidate is silent, image-only, 11 seconds, 24 fps, 1080 × 1920,
fixed-geometry, and loop-safe. Grain and audio remain deferred.

Pass
`--background-config ../HPR-Video-Generator/config/infinity-background-static-production-recipes.json`
for the selected `IBN-001` production treatment. It preserves the approved
IBK-001 typography, density, size, and palette while holding every digit
completely still. The renderer derives `numberSeed` from portrait identity, so
each Infinity portrait receives a different deterministic digit arrangement
without background motion.

The default configuration reproduces the original restrained `INF` round. Pass
`--background-config ../HPR-Video-Generator/config/infinity-background-visibility-recipes.json`
for the separately versioned `IBV` calibration round. That configuration adds
per-recipe perceptual floors; rendering stops if a background is mathematically
different but too weak to meet its declared display-scale visibility target.

Pass
`--background-config ../HPR-Video-Generator/config/infinity-background-concept-recipes.json`
for the sketch-directed `IBC` round. It resolves Brandon Grotesque Regular from
the local font installation and renders three number-space ideas, a gradient
curtain, a sliding panel, a hinged door, and a number doorway. The font file is
not copied into the repository.

Pass
`--background-config ../HPR-Video-Generator/config/infinity-background-flat-recipes.json`
for the review-driven `IBF` round. Its number fields are strictly two
dimensional: digit size and opacity remain fixed while only x-y position moves.
The last two recipes intentionally hard-reset at replay; the other five close
continuously.

Pass
`--background-config ../HPR-Video-Generator/config/infinity-background-directed-recipes.json`
for the eleven-candidate `IBR` response round. It omits rejected `IBF-003`,
uses Brandon Grotesque Bold for five number treatments, and records coordinated
number-plane speed, balanced digit populations, gradient angle and palette,
panel lightness, door acceleration, wipe acceleration, and hard-reset behavior.
The first three number fields and three curtain studies close continuously;
the two panels, accelerating door, and two number wipes reset intentionally.

Pass
`--background-config ../HPR-Video-Generator/config/infinity-background-fixed-palette-recipes.json`
for the eleven-candidate `IBP` correction round. Every graphic background color
is one of the two supplied endpoints, `#f0eee9` and `#f7f5ef`. This round also
adds frame-edge column bleed, deterministic irregular number placement, two
panel acceleration curves, a softer door edge, and opposing number/wipe travel.

Pass
`--background-config ../HPR-Video-Generator/config/infinity-background-contrast-calibration-recipes.json`
for the six-candidate `IBK` calibration round. It holds `#f7f5ef` constant and
tests `#edeae3`, `#e8e4dc`, and `#e2ddd4` in matched thin-number and broad-panel
pairs. Each effect can raise its explicit `maximumMix` to `1.0`, bypassing the
normal half-strength creative ceiling so the encoded result reaches the saved
color endpoint.

Pass
`--background-config ../HPR-Video-Generator/config/infinity-background-number-blobs-recipes.json`
for the three-candidate `IBL` simplification round. It combines the accepted
subtle number field with one, two, or three nested organic blobs. Shared
`numberSeed` and `blobSeed` values keep the comparison deterministic; changing
those seeds per portrait will produce reproducible number arrangements and blob
geometry for production. Every path and shape function is periodic and closes
inside the 11-second duration.

Pass
`--background-config ../HPR-Video-Generator/config/infinity-background-static-number-blobs-recipes.json`
for the three-candidate `IBS` separation round. It reproduces the exact v17
number arrangement and nested blob paths while setting `numberMotion` to
`static`. This directly tests static numbers with moving blobs. The mutually
exclusive moving-number option remains `IBK-001`, which contains no blobs.
