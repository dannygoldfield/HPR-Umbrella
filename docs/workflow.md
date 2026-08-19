# Production workflow

## 1. Install

Requires Python 3.11 or newer and FFmpeg.

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e components/audio-generator
python3 -m pip install -e 'components/video-generator[render]'
python3 -m pip install -e components/candidate-generator
python3 -m pip install -e components/registry
python3 -m pip install -e components/review-interface
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

## 3. Inspect and ingest Lightroom exports

Export selected production portraits with their original filenames. Run the
metadata inspector, then ingest its report into the Registry:

```bash
hpr-registry ingest-metadata-report \
  --db workspace/registry/hpr.sqlite3 \
  --report workspace/metadata-pilot/metadata-report.json \
  --intake-config workspace/metadata-pilot/expected.json \
  --manifest-root workspace/registry/manifests/portraits
```

Intake assigns an immutable `portrait_id` and revision number. It does not
assign an episode number. Re-exporting a corrected JPEG creates a new revision
under the same portrait.

## 4. Legacy archive planner

The existing CSV planner predates the deferred-sequence decision. Its `ARC-NNN`
IDs are legacy production slots, not approved episode numbers. Do not use their
order as the release sequence.

```bash
hpr-candidate archive-plan \
  --portraits-csv workspace/archive-portraits.csv \
  --seed 2026080601 \
  --output workspace/archive-production
```

This dry run writes separate JSONL banks and a summary before rendering media:

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

## 5. Portrait development source preparation

The active process needs one finished Lightroom export per portrait revision.
The export is the authoritative maximum: the animation may move only from a
deliberately under-resolved surrogate toward the untouched finished pixels. It
cannot recover clipped highlights or blocked shadows that are absent from the
file, and it never moves beyond the final image.

The first conceptual pilot used three JPEGs. The active round uses three
embedded-profile 16-bit TIFFs so the generator retains more tonal precision.
Seven aligned Lightroom stage exports may be useful later as a one-time
calibration experiment, but they are not required for every portrait or every
video.

Candidate duration is an explicit creative property and must not be derived
from episode position. The first Portrait Development Animation pilot remains
seven seconds, silent, without grain or text.

## 6. Development candidate production

The implemented generator normalizes the finished source, creates a
deterministic aligned surrogate with restrained color, tonal, and texture
withholding, and reveals the untouched final through five fixed-geometry modes:

- `PDA-001`: static final reference;
- `PDA-002`: global development diagnostic;
- `PDA-003`: broad sparse activation field;
- `PDA-004`: overlapping swell-like activation field;
- `PDA-005`: one extremely soft sweep.

Render and register the first pilot with:

```bash
python tools/render_portrait_development_pilot/render_portrait_development_pilot.py \
  --db workspace/registry/hpr.sqlite3 \
  --output-root workspace/portrait-development-pilot-v5 \
  --ffmpeg /path/to/ffmpeg
```

The 15 round-1 candidates are rendered and registered. Their manifests record
the source and surrogate checksums, one-direction limits, field parameters,
exact 168-frame telemetry, fixed geometry, and loop closure.

The active TIFF timing/easing round uses `PDB-001`–`PDB-005`: a finished TIFF
reference, global development with a long finished rest, slow sparse
activation, faster overlapping swells, and an unhurried soft sweep. Render it
with:

```bash
python tools/render_portrait_development_round2/render_portrait_development_round2.py \
  --db workspace/registry/hpr.sqlite3 \
  --output-root workspace/portrait-development-tiff-v6 \
  --ffmpeg /path/to/ffmpeg
```

These 15 candidates are 11 seconds at 24 fps (264 frames), silent, without
grain or text. Embedded source profiles are transformed to sRGB at 16-bit
precision, compositing remains 16-bit until H.264 delivery conversion, and the
output is tagged BT.709.

## 7. Visual review

Review the five development candidates for each portrait in finite sets at
normal phone size. Reject and rate remain separate controls; ratings run from 1
to 5.

```bash
PYTHONPATH=components/registry/src:components/review-interface/src \
python -m hpr_review.server --db workspace/registry/hpr.sqlite3
```

The local screen loops each video, exposes its provenance, and saves rating,
reject, notes, and selection directly to SQLite. It explicitly leaves episode
unassigned. Review human presence, mentalizing, skin accuracy, tactile realism,
organic emergence, effect invisibility, and loop continuity. Reject any facial
distortion, visible mask, liquid/boiling behavior, scanner-like sweep, tonal
pumping, clarity artifact, or software-demo quality.

## 8. Audio bank

Generate 50 unique tracks at each duration using the successful existing audio methods and source library. Audio remains independently reviewable and bankable.

The existing Google Sheet remains the Audio Recipe Library authoring surface.
Before a production audio batch, export it through a future importer as a
dated, checksummed snapshot. Audio manifests and Registry rows reference the
snapshot ID. Do not manually re-enter the same recipes in both the Sheet and
SQLite. The snapshot importer is specified but not yet built.

## 9. Pair review

After selecting one visual for a portrait, surface 10 compatible audio options.
Record visual, audio, and pair ratings separately. Rejected combinations return
unselected components to their banks. Selecting a final pair retires its audio
from future final use.

## 10. Last look and photo replacement

If skin tone, color, or another photographic issue is discovered, replace the
finished source export. Preserve the selected surface recipe, duration, audio,
optional text treatment, and publication metadata. Recreate the surrogate and
rerender only the visual and dependent final master.

## 11. Final masters and sequencing

Approve the completed visual-and-audio master for each portrait. Arrange the
approved videos in a Lightroom Classic collection or the HPR sequence view.
Commit that custom order as a draft Registry sequence and continue revising it
until the complete order is approved.

Locking the 120-item sequence assigns episode numbers and creates the
publication ledger. Numbered filenames are release-stage outputs, not intake
portrait names.

## 12. Text and publishing

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

## Historical visual experiments

The motion-rhythm, motion-variable, White Balance, and extreme White Balance
pilots remain registered and reproducible. They document how the current
direction emerged, but their render commands and selections are no longer the
active visual testing workflow.

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

PYTHONPATH=components/registry/src \
  python3 -m unittest discover -s components/registry/tests -v

python3 -m unittest discover -s tools/inspect_metadata/tests -v
```
