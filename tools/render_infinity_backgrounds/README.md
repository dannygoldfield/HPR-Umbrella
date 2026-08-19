# Infinity layered-background renderer

This tool holds the selected `PDE-002` portrait-development treatment constant
and renders seven background-only experiments from the layered Infinity TIFF.
The source TIFF is never modified. Photoshop is used only to export 16-bit
working copies of the named `Subject` and `Background` layers.

Every candidate is silent, image-only, 11 seconds, 24 fps, 1080 × 1920,
fixed-geometry, and loop-safe. Grain and audio remain deferred.

The default configuration reproduces the original restrained `INF` round. Pass
`--background-config components/video-generator/config/infinity-background-visibility-recipes.json`
for the separately versioned `IBV` calibration round. That configuration adds
per-recipe perceptual floors; rendering stops if a background is mathematically
different but too weak to meet its declared display-scale visibility target.

Pass
`--background-config components/video-generator/config/infinity-background-concept-recipes.json`
for the sketch-directed `IBC` round. It resolves Brandon Grotesque Regular from
the local font installation and renders three number-space ideas, a gradient
curtain, a sliding panel, a hinged door, and a number doorway. The font file is
not copied into the repository.
