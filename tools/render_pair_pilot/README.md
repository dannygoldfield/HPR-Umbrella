# HPR 11-second pair pilot

This tool combines one locked 11-second visual with ten newly generated,
native 11-second audio candidates. It records each audio candidate and each
visual/audio pair in the HPR registry.

Unused audio starts and remains in the bank automatically. Selecting a pair
retires that pair's audio from future final use; rejecting a pairing does not
reject its audio unless the reviewer explicitly chooses **Retire audio**.

The source-audio library stays private and outside this repository. Supply its
root with `--asset-root`.

Example:

```sh
python3 tools/render_pair_pilot/render_pair_pilot.py \
  --asset-root /Users/dannygoldfield/Projects/HPR-Audio-Generator \
  --ffmpeg /opt/homebrew/bin/ffmpeg \
  --ffprobe /opt/homebrew/bin/ffprobe
```
