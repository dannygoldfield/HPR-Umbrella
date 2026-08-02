# HPR Candidate Generator

The Candidate Generator coordinates the HPR Audio Generator and HPR Video Generator. It creates reproducible portrait-video candidates for human review; it does not select the final work.

## Responsibilities

1. Accept a portrait, duration, motion preset, audio recipe, and seed.
2. Generate one silent, loop-safe portrait video.
3. Generate one soundtrack with the same duration and seed.
4. Mux the video and soundtrack without re-encoding the picture.
5. Write a JSON provenance manifest beside the review candidate.

## Plan without rendering

```bash
hpr-candidate plan \
  --portrait workspace/portraits/example.tif \
  --grain workspace/grain/filmgrain.mov \
  --duration 7 \
  --video-preset VP-002 \
  --audio-recipe AR-008 \
  --seed 2026080201 \
  --count 3
```

Use `generate` instead of `plan` after the private portrait, grain, and audio libraries have been supplied locally.

If `--audio-recipe` is omitted, the generator selects a seamless ambient recipe for the requested duration: AR-008 for 7 seconds, AR-009 for 9 seconds, or AR-010 for 11 seconds.
