# Production workflow

## 1. Install

Requires Python 3.11 or newer and FFmpeg.

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e components/audio-generator
python3 -m pip install -e 'components/video-generator[render]'
python3 -m pip install -e components/candidate-generator
```

## 2. Supply private media locally

The Git repository excludes source and generated media. A production workstation supplies:

```text
components/audio-generator/audio/source/
  beds/
  gestures/
  music-stems/
workspace/
  portraits/
  grain/
  output/
```

The audio configuration records the expected paths and metadata for licensed local assets.

## 3. Plan candidates

Planning creates deterministic IDs and output paths without rendering:

```bash
hpr-candidate plan \
  --portrait workspace/portraits/example.tif \
  --grain workspace/grain/filmgrain.mov \
  --duration 7 \
  --video-preset VP-002 \
  --audio-recipe AR-008 \
  --seed 2026080201 \
  --count 10
```

The selected audio recipe must have the same duration as the candidate.
If no audio recipe is supplied, the Candidate Generator chooses the default seamless ambient recipe for 7, 9, or 11 seconds.

## 4. Generate candidates

After local media is available, replace `plan` with `generate`. For every seed, the Candidate Generator:

1. renders a silent loop-safe portrait video;
2. generates a matching loop-ready soundtrack;
3. muxes the streams without re-encoding the picture;
4. writes an MP4 and adjacent JSON manifest.

## 5. Review and select

Generated candidates enter a human review queue. Approval is an explicit artistic decision and is never inferred from a score or analytic signal.

## 6. Publish, observe, and refine

Publishing and analytics remain downstream of candidate creation. Observations can change future constraints, but they do not retroactively decide which work was artistically successful.

## Tests

The public test suite synthesizes temporary audio fixtures, so licensed audio is not required:

```bash
PYTHONPATH=components/audio-generator/src:components/video-generator/src:components/candidate-generator/src \
  python3 -m unittest discover -s components/audio-generator/tests -v

PYTHONPATH=components/audio-generator/src:components/video-generator/src:components/candidate-generator/src \
  python3 -m unittest discover -s components/video-generator/tests -v

PYTHONPATH=components/audio-generator/src:components/video-generator/src:components/candidate-generator/src \
  python3 -m unittest discover -s components/candidate-generator/tests -v
```
