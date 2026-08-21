# HPR Video Generator

An image-first, audio-independent system for generating silent, loop-safe
vertical videos from portraits.

The generator deliberately knows nothing about audio, pairing, publishing, or analytics. Its output becomes an eligible video pool for the future HPR Generator.

## Active visual direction

Portrait Development Animation keeps the photograph's geometry fixed while
the untouched finished Lightroom export emerges from a deliberately
under-resolved surrogate across the surface. Global development, a very soft
sweep, and activation fields are implemented in the first 15-candidate pilot.
See the complete
[Portrait Development Animation specification](docs/PORTRAIT-DEVELOPMENT-ANIMATION.md).

The shared five-star `PDE-002` Development Animation is now locked. Infinity
adds the locked `IBK-001` moving-number background. The active finishing test
compares seven scanned-film grain treatments on all three complete locked
visuals after those visual stages. The photographed image remains fixed in the
frame; only Development Animation, Infinity's approved background, and film
grain move;
see [Film Grain Animation](docs/FILM-GRAIN-ANIMATION.md).

The older camera-motion, texture, and White Balance-only renderers remain
reproducible research tools; they are not the active production direction.

## Production format

- one portrait per candidate
- 1080 × 1920, 9:16
- 24 frames per second
- 11-second active portrait format; earlier 7-second research retained
- fixed geometry with loop-safe tonal and surface development
- optional luma-only scanned grain applied after visual compositing
- deterministic seeds and complete provenance

## Local media

Source portraits, grain, and rendered videos are intentionally excluded from Git. Put local media under `media/source/`; generated candidates go under `media/output/candidates/`.

## Generate

```text
python -m hpr_video_generator.cli generate --portrait media/source/portraits/bhutan_450.jpg --preset VP-002 --seed 2026073101
```

Generation requires FFmpeg. The program accepts a system FFmpeg or the executable supplied by the optional `imageio-ffmpeg` package.
