# Motion-variable experiment

This tool reads the selected visual from the first rhythm pilot for each of the
three portraits. It preserves that timing rhythm and renders four new probes:

1. half the scale-change amplitude;
2. one-and-a-half times the scale-change amplitude;
3. horizontal micro-movement with constant scale;
4. vertical micro-movement with constant scale.

Together with the selected original, this produces five comparisons per
portrait. The prior candidates and reviews remain unchanged.

```bash
python tools/render_motion_variables/render_motion_variables.py \
  --db workspace/registry/hpr.sqlite3 \
  --output-root workspace/motion-variable-pilot-v2 \
  --ffmpeg /path/to/ffmpeg
```
