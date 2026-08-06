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

## 3. Prepare the archive portrait manifest

Create `workspace/archive-portraits.csv` with exactly 120 rows:

```csv
portrait_id,path
POR-001,workspace/portraits/portrait-001.tif
POR-002,workspace/portraits/portrait-002.tif
```

The portrait is replaceable later. `portrait_id` identifies the editorial source; the path identifies its current rendered export.

## 4. Plan the complete production run

```bash
hpr-candidate archive-plan \
  --portraits-csv workspace/archive-portraits.csv \
  --seed 2026080601 \
  --output workspace/archive-production
```

This is a dry run. It writes separate JSONL banks and a summary before rendering media:

```text
archive-production/
  archive-production-plan.json
  banks/
    episodes.jsonl
    visual.jsonl
    audio.jsonl
    pair.jsonl
    publishing.jsonl
```

The initial Pair bank is empty. Pair candidates are created only after a visual is selected.

## 5. Visual review

Render five restrained motion candidates for each portrait. Review in finite sets. Cull first, then rate survivors. A 5 means bankable or publishable; rejection is 0 and remains distinct from a low survivor rating.

## 6. Audio bank

Generate 50 unique tracks at each duration using the successful existing audio methods and source library. Audio remains independently reviewable and bankable.

## 7. Pair review

After selecting one visual for an episode, surface 10 compatible audio options. Record visual, audio, and pair ratings separately. Rejected combinations return unselected components to their banks. Selecting a final pair retires its audio from future final use.

## 8. Last look and photo replacement

If skin tone, color, or another photographic issue is discovered, replace the source export. Preserve the selected motion recipe, duration, audio, optional text treatment, and publication metadata. Rerender only the visual and dependent final master.

## 9. Text and publishing

Consider the optional “How People Relate” treatment only after the audio-video master is selected. Store published masters and metadata permanently. Disposable low-rated renders may be regenerated from their records.

## Legacy single-candidate planning

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

## Legacy generation

After local media is available, replace `plan` with `generate`. For every seed, the Candidate Generator:

1. renders a silent loop-safe portrait video;
2. generates a matching loop-ready soundtrack;
3. muxes the streams without re-encoding the picture;
4. writes an MP4 and adjacent JSON manifest.

## Review boundary

Generated candidates enter a human review queue. Approval is an explicit artistic decision and is never inferred from a score or analytic signal.

## Publish, observe, and refine

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
