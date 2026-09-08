# Render Portrait Development pilot

This tool renders the three-portrait, five-recipe `PDA-001`–`PDA-005` pilot
from the current finished Registry sources. It creates a deterministic
under-resolved surrogate from each finished portrait and reveals the untouched
finished source through fixed-geometry global, activation-field, and sweep
masks.

The pilot deliberately contains no grain, audio, text, camera movement,
displacement, or facial deformation.

```bash
python tools/render_portrait_development_pilot/render_portrait_development_pilot.py \
  --db workspace/registry/hpr.sqlite3 \
  --output-root workspace/portrait-development-pilot-v5 \
  --ffmpeg /path/to/ffmpeg
```
