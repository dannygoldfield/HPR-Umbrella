# HPR Umbrella

HPR Umbrella is the custom production system for [How People Relate](https://danielg805.sg-host.com/)(Temp page for future dannygoldfield.com site), a daily series of seven-, nine-, and eleven-second looping portrait videos by photographer Danny Goldfield.

The system automates repetitive production steps while leaving portrait selection, movement, timing, sound, sequencing, and final approval to the artist.

> **Design principle:** Automate everything except taste.

## Why it exists

How People Relate draws from an archive of hundreds of thousands of photographs. Publishing a carefully considered video every day requires a system that can generate possibilities without pretending to make artistic judgments.

HPR Umbrella is centered on a Candidate Engine with focused media plugins:

| Component | Responsibility | Does not decide |
| --- | --- | --- |
| [Candidate Engine](components/candidate-generator/) | Plans finite option sets, maintains separate banks, coordinates plugins, and records human decisions | Which candidate becomes the published work |
| [Audio Plugin](components/audio-generator/) | Builds reproducible, loop-ready soundtracks from constrained recipes | Which soundtrack is right |
| [Video Plugin](components/video-generator/) | Builds silent, loop-safe vertical videos from portrait photographs | Which movement best serves a portrait |
| Text Plugin | Adds optional nondestructive identity treatments after a pair is selected | Whether text is needed for a channel |

## How the system works

```mermaid
flowchart LR
    P[Portrait archive] --> C[Candidate Engine]
    A[Private audio library] --> C
    C --> V[Video Plugin]
    C --> G[Audio Plugin]
    V --> C
    G --> C
    C --> R[Review candidates]
    R --> H[Human selection]
    H --> E[Published episode]
```

Each candidate can be recreated from its portrait, duration, presets, recipes, generator versions, and random seed. The system generates constrained variation; Danny listens, looks, compares, and selects.

## Current status

- **Audio Generator:** implemented with deterministic recipes for 7-, 9-, and 11-second loops.
- **Video Generator:** implemented with 31 loop-safe motion presets for 1080 × 1920 video.
- **Candidate Engine:** now implements the 120-episode archive production plan, separate Audio/Visual/Pair/Publishing banks, deterministic option sets, independent component review fields, and replaceable photo sources.
- **Human review:** deliberately remains outside the automated decision path.
- **Text Plugin:** deferred until selected audio-video masters are ready.
- **Now mode:** explicitly deferred; the archive workflow is the production focus.

Portraits, licensed audio, generated videos, workbooks, and private production data are intentionally excluded from this public repository.

## Repository layout

```text
components/
  audio-generator/
  video-generator/
  candidate-generator/
docs/
  architecture.md
  creative-principles.md
  workflow.md
examples/
  candidate-manifest.example.json
```

## Plan a batch

The Candidate Generator can plan deterministic outputs without access to private media:

```bash
python -m hpr_candidate_generator.cli plan \
  --portrait workspace/portraits/example.tif \
  --grain workspace/grain/filmgrain.mov \
  --duration 9 \
  --video-preset VP-012 \
  --audio-recipe AR-009 \
  --seed 2026080201 \
  --count 3
```

Production rendering requires Python 3.11 or newer, FFmpeg, and the locally managed portrait, grain, and licensed audio libraries. See [Workflow](docs/workflow.md) for setup and use.

## Plan the 120-video archive production run

Prepare a CSV with `portrait_id,path` columns and exactly 120 selected portraits, then run:

```bash
hpr-candidate archive-plan \
  --portraits-csv workspace/archive-portraits.csv \
  --seed 2026080601 \
  --output workspace/archive-production
```

The dry run creates 120 episode records, 600 visual options, 150 unique audio plans, an empty Pair bank awaiting visual selections, and 120 Publishing slots.

## Documentation

- [Architecture](docs/architecture.md)
- [Creative principles](docs/creative-principles.md)
- [Production workflow](docs/workflow.md)
- [Danny Goldfield’s portrait projects](https://dannygoldfield.com/)

## Rights

Copyright © 2026 Danny Goldfield. All rights reserved. Source portraits, licensed audio, and generated media are not distributed with this repository.
