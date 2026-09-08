# Film-grain opacity test

This tool adds scanned film grain after the locked HPR visual treatment. It does
not rerun or change Portrait Development Animation, Infinity backgrounds,
geometry, audio, or text.

The active round uses 10000 and the exact Super 35 Light scan sample from
`FGD-004`. Thirteen candidates move from 10% to 40% opacity in even 2.5-point
steps. Plate sample, grain size, signal contrast, temporal smoothing, loop,
Development Animation, camera, and delivery settings remain identical. The
photographed image never translates, scales, or rotates; `PDE-002` remains
active underneath the grain.

Source plates remain outside Git in Danny's local media library. The tracked
recipe file records their filenames and the TDCatTech/LightKino download page;
each local candidate manifest records a plate checksum, deterministic starting
frame, deterministic crop position, and output checksum.

Run from the repository root:

```sh
python3 tools/render_film_grain_test/render_film_grain_test.py \
  --grain-root /Users/dannygoldfield/Media/Video \
  --ffmpeg /opt/homebrew/bin/ffmpeg
```

The outputs are written to
`workspace/film-grain-opacity-v25/` and registered in
`workspace/registry/hpr.sqlite3`. Both are intentionally excluded from Git.

## Guardrails

- 1080 × 1920, 24 fps, 11 seconds, and exactly 264 frames.
- Complete limited-range BT.709 delivery labels.
- Luma-only grain; the approved chroma planes pass through unchanged.
- No grain plate shorter than the selected 11-second sample window.
- Identical plate sample for recipes that differ only in opacity.
- Exactly 13 opacities from 10% through 40%; opacity is the sole test variable.
- Explicit grain-signal gain and texture scale recorded in every manifest.
- Explicit temporal-smoothing window recorded in every manifest.
- Temporal pre-roll prevents the smoothing window from creating a start flash.
- A one-second normalized loop blend returns the grain to its opening state.
- No source plate is copied into the repository or exposed by the review server.
