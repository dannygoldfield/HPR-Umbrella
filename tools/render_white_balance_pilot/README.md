# White-balance calibration pilot

This experiment treats manual Lightroom white-balance adjustment as the
creative source for animation. The rendered videos contain only the portrait.
No slider, label, or interface element is burned into the picture.

For each portrait it renders:

1. accurate exported JPEG reference;
2. Temperature search;
3. Tint search;
4. sequential Temperature then Tint correction;
5. coupled white-balance fine-tuning.

The numeric values are stable HPR diagnostic deltas, not claims about exact
Lightroom slider units. Each manifest includes the precise frame-by-frame
values used to render the video. The local review interface reads that
telemetry and moves external Temperature and Tint sliders in sync with the
video.

```bash
python tools/render_white_balance_pilot/render_white_balance_pilot.py \
  --db workspace/registry/hpr.sqlite3 \
  --output-root workspace/white-balance-pilot-v3 \
  --ffmpeg /path/to/ffmpeg
```
