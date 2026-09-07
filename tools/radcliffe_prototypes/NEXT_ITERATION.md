# Focused next-iteration comparison

The round compares 100%, 125%, and 150% development, three restrained WebGL
number-field treatments against a static control, and a 10% reduction of each
selected audio bed. Originals and Registry decisions remain unchanged.

Audio Generator proves exact reconstruction of each selected source and exact
foreground preservation before emitting a bed-only derivative. Video Generator
produces all silent visuals. Umbrella makes 33-second independent review copies
and owns the private comparison page. No approval is inferred from technical
checks or browser draft choices. New audio and visual candidates must receive
independent human approval before final AV assembly.

To reproduce the round in NEW directories, use Python with NumPy and Pillow,
FFmpeg, and a Node runtime with Playwright. Both components must match the strict
component lock and have clean working trees. The selected source manifest is
the existing `Selected-Prototypes_Audio-Loop-Pending/selections.json`.

```sh
python tools/radcliffe_prototypes/reproduce_iteration.py \
  --selections /absolute/path/to/Selected-Prototypes_Audio-Loop-Pending/selections.json \
  --name HPR-next-iteration-NEW \
  --node /absolute/path/to/node
```

For a bundled Playwright installation, set `HPR_PLAYWRIGHT_MODULE` to its module
directory. `HPR_CHROME` can specify the local Chrome executable. No external
pages are visited; the renderer uses a fresh temporary browser profile.

If components were already rendered, `build_iteration_review.py` accepts
`--selections`, `--visuals`, `--audio`, and a NEW `--output` directory. It checks
source hashes, component locks, 792 video frames, continuous timestamps,
decoded image transitions, exact repeated decoded source frames, and exact repeated PCM.
Visual review copies are encoded continuously across 33 seconds from lossless
eleven-second masters; both internal joins must pass the image-change screen. Audio-only files contain
three native cycles without a codec or player restart at 11 and 22 seconds.

Serve only the generated review directory on 127.0.0.1. The page presents
development first, Infinity motion second, and audio third. Choices are local
browser drafts, exportable for confirmation in the HPR task. The final three
AV exports follow the existing assembler after human component selection.
