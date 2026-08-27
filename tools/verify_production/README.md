# Verify production sources

Run this gate before producing or assembling HPR candidates:

```bash
python3 tools/verify_production/verify_production.py
```

It verifies that the standalone Audio and Video Generator repositories match
the exact commits in `config/component-lock.json`, have clean working trees,
and retain the expected production configuration. It then fingerprints the
three approved pilot visuals against `config/approved-visual-baseline.json`.

Set `HPR_AUDIO_GENERATOR_ROOT` or `HPR_VIDEO_GENERATOR_ROOT` only when the
repositories are not sibling folders of HPR Umbrella. Overrides still have to
match the locked repository and commit.
