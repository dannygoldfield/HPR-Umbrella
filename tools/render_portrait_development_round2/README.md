# Portrait-development TIFF round renderer

This batch tool renders the three TIFFs named by the round-two intake config
against the five `PDB` recipes. It deliberately selects those exact current
revisions, leaving prior JPEG portraits and their review history untouched.

The fixed round specification is 11 seconds at the generator's 24 fps: 264
frames per candidate. Source normalization and surrogate construction remain
16-bit until the final H.264 delivery conversion.

```bash
python3 tools/render_portrait_development_round2/render_portrait_development_round2.py \
  --db workspace/registry/hpr.sqlite3 \
  --output-root workspace/portrait-development-tiff-v6
```

If an interrupted run has already produced both the MP4 and JSON manifest for
a candidate, add `--reuse-existing` to finish registration and the experiment
summary without re-encoding that candidate.
