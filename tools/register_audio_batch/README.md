# Register Audio Batch

This importer preserves the boundary between HPR components:

- HPR Audio Generator creates and validates standalone WAV candidates.
- HPR Umbrella registers those finished files for human review.
- This tool never generates, remixes, stretches, or combines audio with video.

Run from the HPR Umbrella repository root:

```bash
PYTHONPATH=components/registry/src \
python tools/register_audio_batch/register_audio_batch.py \
  --db workspace/registry/hpr.sqlite3 \
  --batch-manifest /path/to/batch-manifest.json
```

The importer verifies candidate identity and file fingerprints before updating
the Registry. Re-running the same import is safe.
