# Film-grain character and strength test

This tool adds scanned film grain after the locked HPR visual treatment. It does
not rerun or change Portrait Development Animation, Infinity backgrounds,
geometry, audio, or text.

The active slow-swim refinement uses 10000 and Super 35 Light grain. It retains
the prior `FGV-002` result as an exact checksum-matching reference, then
correlates three, five, or seven neighboring grain frames to replace rapid
flicker with a calmer swim. Mix and texture size increase only modestly. The
photographed image never translates, scales, or rotates; `PDE-002` remains
active underneath the grain.

Source plates remain outside Git in Danny's local media library. The tracked
recipe file records their filenames and the TDCatTech/LightKino download page;
each local candidate manifest records a plate checksum, deterministic starting
frame, deterministic crop position, and output checksum.

Run from the repository root:

```sh
PYTHONPATH=components/video-generator/src:components/registry/src \
python3 tools/render_film_grain_test/render_film_grain_test.py \
  --grain-root /Users/dannygoldfield/Media/Video \
  --ffmpeg /opt/homebrew/bin/ffmpeg
```

The outputs are written to
`workspace/film-grain-slow-swim-v23/` and registered in
`workspace/registry/hpr.sqlite3`. Both are intentionally excluded from Git.

## Guardrails

- 1080 × 1920, 24 fps, 11 seconds, and exactly 264 frames.
- Complete limited-range BT.709 delivery labels.
- Luma-only grain; the approved chroma planes pass through unchanged.
- No grain plate shorter than the selected 11-second sample window.
- Identical plate sample for recipes that differ only in opacity.
- Explicit grain-signal gain and texture scale recorded in every manifest.
- Explicit temporal-smoothing window recorded in every manifest.
- No source plate is copied into the repository or exposed by the review server.
