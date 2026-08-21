# Film-grain character and strength test

This tool adds scanned film grain after the locked HPR visual treatment. It does
not rerun or change Portrait Development Animation, Infinity backgrounds,
geometry, audio, or text.

The active round applies the same seven grain comparisons to all three locked
pilot visuals. NYChildren and 10000 retain `PDE-002`; Infinity retains the
complete `PDE-002 + IBK-001` composite, including its moving-number background.
The photographed image never translates, scales, or rotates. The seven recipes
separate a no-grain transcode control, 35mm/Super 35/16mm character,
Light/Heavy source plates, and three Super 35 Light strengths.

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
`workspace/film-grain-composite-v21/` and registered in
`workspace/registry/hpr.sqlite3`. Both are intentionally excluded from Git.

## Guardrails

- 1080 × 1920, 24 fps, 11 seconds, and exactly 264 frames.
- Complete limited-range BT.709 delivery labels.
- Luma-only grain; the approved chroma planes pass through unchanged.
- No grain plate shorter than the selected 11-second sample window.
- Identical plate sample for recipes that differ only in opacity.
- No source plate is copied into the repository or exposed by the review server.
