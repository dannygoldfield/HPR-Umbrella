# Render the motion-rhythm pilot

This repository tool renders all five configured motion rhythms for every
current portrait revision in the HPR Registry. It also registers each visual
candidate and writes a reproducible JSON manifest beside every MP4.

```bash
python tools/render_motion_pilot/render_motion_pilot.py \
  --db workspace/registry/hpr.sqlite3 \
  --output-root workspace/motion-pilot \
  --ffmpeg /path/to/ffmpeg
```

The first pilot fixes all candidates at seven seconds and omits grain so that
review differences come only from motion timing. The source JPEGs are read but
never modified.
